"""
broker.py

Hierarchical Quantum Cloud Broker for the QAISim framework.
Responsible for network-aware, QoS-aware task scheduling across geo-distributed
Datacenters and physical quantum processors (QNodes).

Key features:
1. Geo-Network Aware Routing (Replaced random.choice):
   Evaluates each candidate Datacenter using:
     Score = WAN Latency (user_location -> DC Gateway) + Estimated Queue Delay
   Selects the Datacenter with the minimum total end-to-end turnaround latency.
2. Best-Fit QNode Allocation:
   Within the chosen Datacenter, selects the QNode with the most fitting idle qubit
   capacity (minimizing qubit fragmentation) and highest computational capability.
3. Multi-programming & Single-programming execution models:
   - SerialBroker: Exclusive single-tenant QPU lock.
   - ParallelBroker: Multi-programming spatial sharing via subgraph partitioning.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Tuple
import simpy

from cloud_network import CloudNetwork
from datacenter import Datacenter
from geo_network import calculate_wan_latency


class BaseBroker(ABC):
    """
    Abstract Base Broker with Hierarchical Geo-Routing capabilities.
    """

    def __init__(
        self,
        env: simpy.Environment,
        cloud_network: Optional[CloudNetwork] = None,
        devices: Optional[List] = None,
        printlog: bool = True,
    ):
        self.env = env
        self.printlog = printlog
        self.task_queue = []
        self.is_running = False

        # Configure CloudNetwork reference
        if cloud_network is not None:
            self.cloud_network = cloud_network
            self.devices = devices or cloud_network.all_qnodes()
        elif devices:
            self.devices = devices
            # Auto-aggregate CloudNetwork from QNodes' parent datacenters if available
            parent_dcs = {}
            for d in devices:
                dc = getattr(d, "datacenter", None)
                if dc is not None:
                    parent_dcs[dc.name] = dc

            if parent_dcs:
                self.cloud_network = CloudNetwork(env, printlog=printlog)
                for dc in parent_dcs.values():
                    self.cloud_network.register_datacenter(dc)
            else:
                # Fallback: create a default Datacenter wrapping provided devices
                fallback_dc = Datacenter("Default-DC", env, distance_km=50.0, region_tier="near", qnodes=devices)
                self.cloud_network = CloudNetwork(env, printlog=printlog)
                self.cloud_network.register_datacenter(fallback_dc)
        else:
            self.devices = []
            self.cloud_network = CloudNetwork(env, printlog=printlog)

    def receive_task(self, task):
        """Receives a QTask from TaskGenerator or external client."""
        self.task_queue.append(task)
        if not getattr(self, "is_running", False):
            self.is_running = True
            self.env.process(self.run())

    def route_task(self, task) -> Tuple[Optional[Datacenter], Optional[object], float]:
        """
        Hierarchical 2-Tier Scheduling (No random choice):
        Tier 1: Identify best Datacenter based on WAN Latency (user_location -> DC) + Queue Delay.
        Tier 2: Identify best QNode inside chosen Datacenter based on Best-Fit idle qubits.

        Returns:
            Tuple[Optional[Datacenter], Optional[QuantumDevice], float]:
                (chosen_datacenter, chosen_qnode, wan_latency_seconds)
        """
        user_loc = getattr(task, "user_location", "US_East") or "US_East"

        # --- TIER 1: Select Optimal Datacenter ---
        best_dc, wan_latency, queue_delay = self.cloud_network.find_best_datacenter(user_loc, task=task)

        if best_dc is None:
            if self.printlog:
                print(f"[{self.env.now:.2f}] Broker: No available Datacenter found for Task #{task.task_id} (All under maintenance).")
            return None, None, 0.0

        # --- TIER 2: Select Best QNode within Chosen Datacenter ---
        avail_qnodes = best_dc.available_qnodes()
        if not avail_qnodes:
            # Fallback to any QNode in DC if none currently marked available
            avail_qnodes = best_dc.qnodes

        chosen_qnode = self._select_qnode_best_fit(avail_qnodes, task)

        # Cache routing decisions on the task object
        task.assigned_datacenter = best_dc.name
        task.assigned_device = chosen_qnode.name if chosen_qnode else None
        task.network_latency = wan_latency

        if self.printlog:
            print(
                f"[{self.env.now:.2f}] Broker: Routed Task #{task.task_id} "
                f"| Origin: {user_loc} -> Datacenter: {best_dc.name} ({best_dc.location}) "
                f"| WAN Latency: {wan_latency * 1000:.2f} ms | Est. Queue: {queue_delay * 1000:.2f} ms "
                f"-> QNode: {chosen_qnode.name if chosen_qnode else 'None'}"
            )

        return best_dc, chosen_qnode, wan_latency

    def _select_qnode_best_fit(self, qnodes: List, task) -> Optional[object]:
        """
        Best-Fit qubit allocation:
        1. Filters QNodes with sufficient idle qubits (container.level >= task.num_qubits).
        2. Selects the one that leaves the least leftover space (minimizing qubit fragmentation).
        3. If no QNode has enough qubits right now, picks the one with the shortest queue.
        """
        if not qnodes:
            return None

        needed_qubits = getattr(task, "num_qubits", 1)

        # QNodes that can run this task immediately
        eligible = [qn for qn in qnodes if getattr(qn.container, "level", 0) >= needed_qubits]

        if eligible:
            # Sort by least surplus qubits (tightest fit first), then by highest CLOPS
            eligible.sort(
                key=lambda qn: (
                    qn.container.level - needed_qubits,
                    -getattr(qn, "clops", 0)
                )
            )
            return eligible[0]

        # If none can run immediately, choose the QNode with fewest queued tasks
        qnodes_sorted = sorted(
            qnodes,
            key=lambda qn: (
                len(getattr(qn.container, "get_queue", [])),
                -getattr(qn.container, "level", 0)
            )
        )
        return qnodes_sorted[0]

    @abstractmethod
    def assign_device(self, task):
        """Assigns task to a device."""
        pass

    @abstractmethod
    def run(self):
        """Main broker scheduling loop."""
        pass


class SerialBroker(BaseBroker):
    """
    Serial (Single-programming) Broker:
    Allocates task via Geo-Routing, but enforces exclusive QPU access
    (only 1 task occupies the whole device at a time).
    """

    def __init__(self, env: simpy.Environment, cloud_network: Optional[CloudNetwork] = None, devices: Optional[List] = None, printlog: bool = True):
        super().__init__(env, cloud_network=cloud_network, devices=devices, printlog=printlog)

    def assign_device(self, task):
        """Finds best device via hierarchical geo-routing."""
        best_dc, chosen_qnode, wan_latency = self.route_task(task)
        return chosen_qnode

    def run(self):
        """Processes task queue sequentially with exclusive resource locking."""
        while len(self.task_queue) > 0:
            current_task = self.task_queue.pop(0)

            best_dc, device, wan_latency = self.route_task(current_task)

            # Wait if all Datacenters are down
            while device is None or getattr(device, "maint_lock", False):
                if self.printlog and device:
                    print(f"[{self.env.now:.2f}] SerialBroker: Task #{current_task.task_id} waiting, {device.name} under maintenance...")
                yield self.env.timeout(1.0)
                best_dc, device, wan_latency = self.route_task(current_task)

            # Simulate network transmission delay across WAN
            if wan_latency > 0:
                yield self.env.timeout(wan_latency)

            # Exclusive Single-programming lock on the QPU
            with device.resource.request(priority=2) as req:
                yield req
                yield self.env.process(device.process_task(current_task, self.env.now))

            # Simulate result transmission delay back to user
            if wan_latency > 0:
                yield self.env.timeout(wan_latency)

        self.is_running = False


class ParallelBroker(BaseBroker):
    """
    Parallel (Multi-programming) Broker:
    Uses Hierarchical Geo-Routing to dispatch tasks to the nearest, least-loaded Datacenter.
    Dispatches tasks concurrently without full-device resource locks, enabling
    spatial multi-programming on QNodes.
    """

    def __init__(self, env: simpy.Environment, cloud_network: Optional[CloudNetwork] = None, devices: Optional[List] = None, printlog: bool = True):
        super().__init__(env, cloud_network=cloud_network, devices=devices, printlog=printlog)

    def assign_device(self, task):
        """Dispatches task using intelligent geo-distributed routing."""
        best_dc, chosen_qnode, wan_latency = self.route_task(task)
        return chosen_qnode

    def run(self):
        """Processes task queue concurrently."""
        while len(self.task_queue) > 0:
            current_task = self.task_queue.pop(0)

            best_dc, device, wan_latency = self.route_task(current_task)

            # If no DC/device available (e.g. system maintenance outage), requeue and wait
            if device is None or getattr(device, "maint_lock", False):
                if self.printlog and device:
                    print(f"[{self.env.now:.2f}] ParallelBroker: Task #{current_task.task_id} waiting, {device.name} unavailable.")
                yield self.env.timeout(1.0)
                self.task_queue.insert(0, current_task)
                continue

            # Asynchronous execution process: WAN Transfer -> QNode Spatial Execution -> WAN Return
            self.env.process(self._execute_task_pipeline(device, current_task, wan_latency))

            # Small simulation yield to prevent thread lock in SimPy
            yield self.env.timeout(0.01)

        self.is_running = False

    def _execute_task_pipeline(self, device, task, wan_latency: float):
        """Pipeline simulating WAN upload, QNode execution, and WAN download."""
        if wan_latency > 0:
            yield self.env.timeout(wan_latency)

        yield self.env.process(device.process_task(task, self.env.now))

        if wan_latency > 0:
            yield self.env.timeout(wan_latency)