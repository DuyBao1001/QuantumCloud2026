"""
task_generator.py

Task Generator for the QAISim (Quantum Cloud Resource Scheduling) framework.
Generates quantum tasks (QTasks) and feeds them into the Broker's queue within
a SimPy discrete-event simulation environment.

Key features:
1. MQTBench Integration: Extracts real quantum circuits (QFT, Grover, VQE, QAOA, GHZ, etc.)
   using `mqt.bench` if installed, with automatic synthetic fallback if not.
2. Network-Aware (Geo-distributed): Attaches `user_location` to tasks so Broker can query
   `geo_network.py` for WAN propagation & transmission latency.
3. QoS & SLA Constraints: Generates `deadline` & `deadline_factor` for SLA tracking and
   DRL penalty rewards.
4. Pluggable Traffic Distribution: Supports arbitrary arrival distributions via callable
   functions (Poisson / M/M/1 default, MMPP, Pareto, bursty traffic) without modifying core code.
5. In-Memory Circuit Cache: Caches circuit specs by (algorithm, qubits) for instantaneous
   synthesis during high-throughput DRL training episodes.
6. Flexible Workload Modes:
   - Real-time SimPy stream into Broker (`run_stream` / `run_poisson`).
   - Fixed-batch generation for reproducible Gym / DRL episodes (`generate_batch`).
   - Trace-driven playback from pre-saved MQTBench datasets (`run_from_workload`).
   - Workload serialization to/from JSON (`save_workload_to_json`, `load_workload_from_json`).
"""

import json
import os
import random
from typing import Any, Callable, Dict, List, Optional, Tuple, Union
import simpy
from qtask import QTask

# Attempt to import MQTBench for authentic quantum circuits
try:
    from mqt.bench import get_benchmark
    MQT_AVAILABLE = True
except ImportError:
    MQT_AVAILABLE = False


# Supported MQTBench algorithm benchmarks
MQT_ALGORITHMS = [
    "qft",
    "grover",
    "ghz",
    "vqe",
    "qaoa",
    "qpe",
    "wstate",
    "dj"
]

# Standard Geo-distributed user client regions
DEFAULT_USER_LOCATIONS = ["US_East", "EU_West", "AP_South"]

# In-memory circuit cache: (algo, num_qubits, level) -> (depth, gates_profile)
_CIRCUIT_CACHE: Dict[Tuple[str, int, str], Tuple[int, Dict[str, Any]]] = {}


def _classify_gates(ops_dict: Dict[str, int]) -> Dict[str, Any]:
    """
    Classifies raw Qiskit gate operations into 1-qubit, 2-qubit, and measurement counts
    to enable precise fidelity calculations on IBM calibration data.
    """
    two_q_types = {"cx", "ecr", "cz", "swap", "cp", "crx", "cry", "crz", "rxx", "ryy", "rzz"}
    measure_types = {"measure", "reset", "barrier"}

    count_1q = 0
    count_2q = 0
    count_measure = 0

    for gate_name, count in ops_dict.items():
        name_lower = gate_name.lower()
        if name_lower in measure_types:
            count_measure += count
        elif name_lower in two_q_types:
            count_2q += count
        else:
            count_1q += count

    return {
        "ops": ops_dict,
        "total_gates": count_1q + count_2q,
        "1q_gates": count_1q,
        "2q_gates": count_2q,
        "measurements": count_measure
    }


class TaskGenerator:
    """
    SimPy-compatible Task Generator for QAISim.
    
    Attributes:
        env (simpy.Environment, optional): The simulation environment.
        broker (BaseBroker, optional): Target broker receiving generated tasks.
        arrival_rate (float): Default lambda parameter for Poisson arrival process.
        inter_arrival_fn (Callable[[random.Random], float], optional): Pluggable function
            returning the next inter-arrival interval. Defaults to Poisson process.
        qubit_range (Tuple[int, int]): Min and max qubits required per task.
        depth_range (Tuple[int, int]): Min and max depth for synthetic fallback circuits.
        shot_choices (List[int]): Discrete shot choices (default [1024, 2048, 4096]).
        priority_weights (List[float]): Sampling weights for priorities [P1, P2, P3].
        user_locations (List[str]): Candidate geographical regions for client requests.
        deadline_factor_range (Tuple[float, float]): Range of slack factor for deadline.
        algorithms (List[str]): Benchmark algorithms to sample from.
        use_mqt (bool): Whether to query MQTBench (if available).
        seed (int, optional): Random seed for reproducible experiments.
        printlog (bool): Enable or disable generation logging to stdout.
    """

    def __init__(
        self,
        env: Optional[simpy.Environment] = None,
        broker=None,
        arrival_rate: float = 0.5,
        inter_arrival_fn: Optional[Callable[[random.Random], float]] = None,
        qubit_range: Tuple[int, int] = (4, 27),
        depth_range: Tuple[int, int] = (10, 100),
        shot_choices: Optional[List[int]] = None,
        priority_weights: Optional[List[float]] = None,
        user_locations: Optional[List[str]] = None,
        deadline_factor_range: Tuple[float, float] = (1.5, 3.0),
        algorithms: Optional[List[str]] = None,
        use_mqt: bool = True,
        seed: Optional[int] = None,
        printlog: bool = True,
    ):
        self.env = env
        self.broker = broker
        self.arrival_rate = arrival_rate
        self.qubit_range = qubit_range
        self.depth_range = depth_range
        self.shot_choices = shot_choices or [1024, 2048, 4096]
        self.priority_weights = priority_weights or [0.2, 0.6, 0.2]  # [High, Medium, Low]
        self.user_locations = user_locations or DEFAULT_USER_LOCATIONS
        self.deadline_factor_range = deadline_factor_range
        self.algorithms = algorithms or MQT_ALGORITHMS
        self.use_mqt = use_mqt and MQT_AVAILABLE
        self.printlog = printlog

        self.rng = random.Random(seed)
        self.generated_tasks: List[QTask] = []
        self._task_counter = 0

        # Pluggable inter-arrival generator (Proposal 3)
        # Default is standard Poisson arrival: inter-arrival ~ Exp(lambda)
        if inter_arrival_fn is not None:
            self.inter_arrival_fn = inter_arrival_fn
        else:
            self.inter_arrival_fn = lambda rng: rng.expovariate(self.arrival_rate)

        if not MQT_AVAILABLE and use_mqt and self.printlog:
            print("[INFO] 'mqt.bench' not found. Using high-performance synthetic circuit fallback. "
                  "(Install via 'pip install mqt.bench' to enable real MQTBench circuits).")

    def assign_env(self, env: simpy.Environment):
        """Assigns or updates the SimPy simulation environment."""
        self.env = env

    def assign_broker(self, broker):
        """Assigns or updates the target Broker."""
        self.broker = broker

    def set_inter_arrival_fn(self, fn: Callable[[random.Random], float]):
        """
        Dynamically swaps the arrival traffic process (e.g. Markov-Modulated Poisson Process (MMPP),
        Pareto distribution, bursty / peak-hour models).
        """
        self.inter_arrival_fn = fn

    def _extract_circuit_metrics(self, algo: str, num_qubits: int) -> Tuple[int, Dict[str, Any], str]:
        """
        Retrieves circuit depth and gate profile from cache or MQTBench,
        falling back to synthetic profile if unavailable.
        """
        cache_key = (algo, num_qubits, "alg")
        if cache_key in _CIRCUIT_CACHE:
            depth, gates_profile = _CIRCUIT_CACHE[cache_key]
            circuit_name = f"MQT_{algo.upper()}_{num_qubits}q"
            return depth, gates_profile, circuit_name

        if self.use_mqt:
            try:
                qc = get_benchmark(benchmark_name=algo, level="alg", circuit_size=num_qubits)
                depth = qc.depth()
                raw_ops = dict(qc.count_ops())
                gates_profile = _classify_gates(raw_ops)
                circuit_name = f"MQT_{algo.upper()}_{num_qubits}q"

                _CIRCUIT_CACHE[cache_key] = (depth, gates_profile)
                return depth, gates_profile, circuit_name
            except Exception:
                # Fall through to synthetic generation if MQT does not support specific qubit size
                pass

        # Synthetic Fallback: Realistic circuit approximation
        depth = self.rng.randint(*self.depth_range)
        est_2q = int(depth * num_qubits * 0.25)
        est_1q = int(depth * num_qubits * 0.70)
        gates_profile = {
            "ops": {"1q": est_1q, "2q": est_2q, "measure": num_qubits},
            "total_gates": est_1q + est_2q,
            "1q_gates": est_1q,
            "2q_gates": est_2q,
            "measurements": num_qubits
        }
        circuit_name = f"Synthetic_{algo.upper()}_{num_qubits}q"
        _CIRCUIT_CACHE[cache_key] = (depth, gates_profile)
        return depth, gates_profile, circuit_name

    def create_task(
        self,
        arrival_time: float,
        num_qubits: Optional[int] = None,
        algo: Optional[str] = None,
        num_shots: Optional[int] = None,
        priority: Optional[int] = None,
        user_location: Optional[str] = None,
        deadline_factor: Optional[float] = None,
        deadline: Optional[float] = None,
        payload_size_bytes: Optional[float] = None,
    ) -> QTask:
        """
        Creates a single QTask with specified or randomly sampled parameters.
        Includes user location (Proposal 1) and QoS deadline (Proposal 2).
        """
        self._task_counter += 1
        task_id = self._task_counter

        selected_algo = algo or self.rng.choice(self.algorithms)
        sampled_qubits = num_qubits or self.rng.randint(*self.qubit_range)
        sampled_shots = num_shots or self.rng.choice(self.shot_choices)

        if priority is None:
            sampled_priority = self.rng.choices([1, 2, 3], weights=self.priority_weights)[0]
        else:
            sampled_priority = priority

        # Proposal 1: User / Client Location for WAN Latency calculation
        sampled_location = user_location or self.rng.choice(self.user_locations)

        # Proposal 2: Deadline & SLA factor
        sampled_factor = deadline_factor or self.rng.uniform(*self.deadline_factor_range)
        depth, gates_profile, circuit_name = self._extract_circuit_metrics(selected_algo, sampled_qubits)

        # Compute baseline execution duration estimate to set an intelligent deadline
        # Roughly: D * shots / baseline_clops (e.g. 500 clops) in sim-mins
        if deadline is None:
            est_exec_time = max(0.5, (depth * sampled_shots) / (1400 * 60))
            computed_deadline = round(arrival_time + (est_exec_time * sampled_factor), 4)
        else:
            computed_deadline = deadline

        task = QTask(
            task_id=task_id,
            num_qubits=sampled_qubits,
            depth=depth,
            num_shots=sampled_shots,
            priority=sampled_priority,
            arrival_time=round(arrival_time, 4),
            circuit_name=circuit_name,
            gates=gates_profile,
            user_location=sampled_location,
            deadline_factor=round(sampled_factor, 2),
            deadline=computed_deadline,
            payload_size_bytes=payload_size_bytes,
        )
        self.generated_tasks.append(task)
        return task

    def run_stream(
        self,
        max_tasks: Optional[int] = None,
        duration: Optional[float] = None,
    ):
        """
        SimPy process: Continuously generates tasks using `inter_arrival_fn` (pluggable distribution)
        and dispatches them to the broker in real simulation time.
        """
        if self.env is None:
            raise ValueError("SimPy Environment has not been assigned to TaskGenerator.")

        task_count = 0
        while True:
            if max_tasks is not None and task_count >= max_tasks:
                break
            if duration is not None and self.env.now >= duration:
                break

            inter_arrival = self.inter_arrival_fn(self.rng)
            yield self.env.timeout(inter_arrival)

            if duration is not None and self.env.now > duration:
                break

            task = self.create_task(arrival_time=self.env.now)
            task_count += 1

            if self.printlog:
                print(
                    f"[{self.env.now:.2f}] TaskGenerator: Created Task #{task.task_id} "
                    f"| {task.circuit_name} | Qubits: {task.num_qubits} | Shots: {task.num_shots} "
                    f"| Loc: {task.user_location} | Deadline: {task.deadline:.2f} | Prio: {task.priority}"
                )

            if self.broker is not None:
                self.broker.receive_task(task)

    def run_poisson(
        self,
        max_tasks: Optional[int] = None,
        duration: Optional[float] = None,
    ):
        """Backward-compatible alias for run_stream()."""
        return self.run_stream(max_tasks=max_tasks, duration=duration)

    def run_from_workload(self, tasks: List[QTask]):
        """
        SimPy process: Replays a pre-defined list of QTasks (e.g. from a benchmark dataset)
        into the broker at each task's specified arrival_time.
        """
        if self.env is None:
            raise ValueError("SimPy Environment has not been assigned to TaskGenerator.")

        sorted_tasks = sorted(tasks, key=lambda t: t.arrival_time)
        for task in sorted_tasks:
            time_until_arrival = task.arrival_time - self.env.now
            if time_until_arrival > 0:
                yield self.env.timeout(time_until_arrival)

            task.arrival_time = self.env.now
            if self.printlog:
                print(
                    f"[{self.env.now:.2f}] TaskGenerator: Dispatched Trace Task #{task.task_id} "
                    f"| {task.circuit_name} | Loc: {task.user_location} | Qubits: {task.num_qubits}"
                )

            if self.broker is not None:
                self.broker.receive_task(task)

    def generate_batch(
        self,
        num_tasks: int,
        start_time: float = 0.0,
        fixed_interval: Optional[float] = None,
    ) -> List[QTask]:
        """
        Pre-generates a reproducible batch of QTasks without running a SimPy loop.
        Crucial for DRL episode resets and offline multi-agent comparisons.
        """
        batch: List[QTask] = []
        current_time = start_time

        for _ in range(num_tasks):
            if fixed_interval is not None:
                inter_arrival = fixed_interval
            else:
                inter_arrival = self.inter_arrival_fn(self.rng)

            current_time += inter_arrival
            task = self.create_task(arrival_time=current_time)
            batch.append(task)

        return batch

    def save_workload_to_json(self, tasks: List[QTask], file_path: str):
        """Serializes a list of QTasks into a standardized JSON workload file."""
        data = [t.to_dict() for t in tasks]
        os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def load_workload_from_json(self, file_path: str) -> List[QTask]:
        """Loads a list of QTasks from a JSON workload file."""
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        tasks = []
        for item in data:
            self._task_counter += 1
            if "task_id" not in item:
                item["task_id"] = self._task_counter
            task = QTask.from_dict(item)
            tasks.append(task)
            self.generated_tasks.append(task)
        return tasks
