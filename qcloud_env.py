"""
qcloud_env.py

Gymnasium Environment wrapper for Quantum Cloud Resource Scheduling (QAISim).
Bridges SimPy discrete-event multi-datacenter simulation with Deep Reinforcement
Learning (DRL) algorithms (e.g. Stable-Baselines3, Ray RLlib, SB3-Contrib).

Key Features & Enhancements:
1. Multi-Objective Optimization: Balances Fidelity (from IBM calibration errors),
   WAN latency (propagation + transmission), Queue makespan, and QoS SLA deadlines.
2. 13-Dimensional Observation Space: Captures task demands, user location, DC maintenance
   status, WAN latencies, and idle qubit capacities.
3. Invalid Action Masking (`action_masks`): Prevents Agent from assigning tasks to
   Datacenters undergoing maintenance outages.
4. Robust SimPy Time Sync: Avoids SimPy `until <= now` crashes with safe simulation stepping.
5. Configurable Episode Horizons: Supports `max_steps_per_episode` for stable PPO/DQN rollouts.
6. Graceful Workload Loading: Reads from JSON dataset with automatic RAM batch fallback.
"""

import os
from typing import Any, Dict, List, Optional, Tuple
import gymnasium as gym
from gymnasium import spaces
import numpy as np
import simpy

from cloud_network import CloudNetwork
from datacenter import Datacenter
from task_generator import TaskGenerator
from env_qnodes import IBM_Marrakesh, IBM_Fez, IBM_Torino, IBM_Quebec
from broker import ParallelBroker


class QuantumCloudEnv(gym.Env):
    """
    Gymnasium Environment for Multi-Objective Quantum Cloud Scheduling.
    """
    metadata = {"render_modes": ["human"]}

    def __init__(
        self,
        workload_filepath: str = "real_workload_5000.json",
        max_steps_per_episode: Optional[int] = 100,
        alpha_fidelity: float = 100.0,
        beta_wan: float = 0.1,
        gamma_queue: float = 0.1,
        delta_sla: float = 1.0,
        penalty_maintenance: float = -100.0,
        render_mode: Optional[str] = None,
    ):
        super(QuantumCloudEnv, self).__init__()
        self.workload_filepath = workload_filepath
        self.max_steps_per_episode = max_steps_per_episode
        self.render_mode = render_mode

        # Reward weights for multi-objective balancing
        self.alpha_fidelity = alpha_fidelity
        self.beta_wan = beta_wan
        self.gamma_queue = gamma_queue
        self.delta_sla = delta_sla
        self.penalty_maintenance = penalty_maintenance

        # Supported geographical client locations
        self.locations = ["US_East", "EU_West", "AP_South"]
        self.dc_names = ["DC-A-Near", "DC-B-Mid", "DC-C-Far"]

        # =====================================================================
        # 1. ACTION SPACE: Discrete(3) -> 0: DC-A (US), 1: DC-B (EU), 2: DC-C (AP)
        # =====================================================================
        self.action_space = spaces.Discrete(3)

        # =====================================================================
        # 2. OBSERVATION SPACE: 13-dimensional continuous vector
        # [0,1,2]   : One-hot encoded User Location (US_East, EU_West, AP_South)
        # [3]       : Number of qubits required by the task
        # [4,5,6]   : Maintenance flag of 3 DCs (1.0 = Down/Maintenance, 0.0 = Active)
        # [7,8,9]   : WAN Latencies from task origin to 3 DCs (in ms)
        # [10,11,12]: Total idle qubits available at 3 DCs
        # =====================================================================
        self.observation_space = spaces.Box(
            low=0.0, high=10000.0, shape=(13,), dtype=np.float32
        )

        # Runtime placeholders
        self.simpy_env: Optional[simpy.Environment] = None
        self.cloud: Optional[CloudNetwork] = None
        self.broker: Optional[ParallelBroker] = None
        self.generator: Optional[TaskGenerator] = None
        self.tasks: List = []
        self.current_task_idx = 0
        self.current_task = None
        self.episode_step = 0

    def reset(
        self,
        seed: Optional[int] = None,
        options: Optional[Dict[str, Any]] = None,
    ) -> Tuple[np.ndarray, Dict[str, Any]]:
        """Resets the simulation environment for a new RL episode."""
        super().reset(seed=seed)

        # 1. Reset SimPy discrete-event engine and rebuild infrastructure
        self.simpy_env = simpy.Environment()
        self.cloud = self._build_infrastructure(self.simpy_env)
        self.broker = ParallelBroker(self.simpy_env, cloud_network=self.cloud, printlog=False)
        self.generator = TaskGenerator(self.simpy_env, broker=self.broker, seed=seed, printlog=False)

        # 2. Load workload (with graceful fallback if JSON is not found)
        if os.path.exists(self.workload_filepath):
            self.tasks = self.generator.load_workload_from_json(self.workload_filepath)
        else:
            # Fallback to direct RAM batch generation
            num_fallback_tasks = self.max_steps_per_episode or 100
            self.tasks = self.generator.generate_batch(num_tasks=num_fallback_tasks, fixed_interval=12.0)

        self.current_task_idx = 0
        self.episode_step = 0
        self.current_task = self.tasks[self.current_task_idx]

        info = {
            "action_mask": self.action_masks(),
            "total_tasks": len(self.tasks),
            "user_location": self.current_task.user_location,
        }
        return self._get_state(self.current_task), info

    def action_masks(self) -> np.ndarray:
        """
        Action Masking mechanism (crucial for invalid action masking in MaskablePPO):
        Returns a boolean array of length 3: [True, True, False] indicates which
        Datacenters are currently available (not under maintenance and have active QNodes).
        """
        masks = np.zeros(3, dtype=bool)
        if self.cloud is not None:
            for i, name in enumerate(self.dc_names):
                dc = self.cloud.datacenters.get(name)
                masks[i] = dc.is_available() if dc is not None else False
        else:
            masks[:] = True
        return masks

    def step(self, action: int) -> Tuple[np.ndarray, float, bool, bool, Dict[str, Any]]:
        """
        Executes the agent's action (routing task to selected Datacenter)
        and advances the simulation.
        """
        self.episode_step += 1
        chosen_dc_name = self.dc_names[action]
        chosen_dc = self.cloud.datacenters[chosen_dc_name]

        # 1. Penalty if agent chose an invalid/under-maintenance Datacenter
        maintenance_violation = chosen_dc.under_maintenance
        if maintenance_violation:
            reward = self.penalty_maintenance
            # Failover redirect so simulation proceeds without breaking
            resolved_dc = self.cloud.resolve_datacenter(chosen_dc_name)
            chosen_dc = resolved_dc or chosen_dc

        # 2. Calculate network latencies and find best QNode within the DC
        wan_latency = chosen_dc.wan_latency(self.current_task.user_location, payload_size_bytes=self.current_task.payload_size_bytes)
        queue_delay = chosen_dc.estimate_queue_delay(self.current_task)
        best_qnode = self.broker._select_qnode_best_fit(chosen_dc.available_qnodes(), self.current_task)

        # 3. Dispatch task to QNode pipeline in SimPy
        if best_qnode is not None:
            self.simpy_env.process(self.broker._execute_task_pipeline(best_qnode, self.current_task, wan_latency))
            est_fidelity = best_qnode.estimate_fidelity(self.current_task)
        else:
            est_fidelity = 0.0
            queue_delay += 50.0  # Penalty for queue stall

        # 4. Advance SimPy clock safely to the next task's arrival time
        self.current_task_idx += 1
        terminated = self.current_task_idx >= len(self.tasks)
        truncated = False

        if self.max_steps_per_episode is not None and self.episode_step >= self.max_steps_per_episode:
            truncated = True

        if not terminated and not truncated:
            self.current_task = self.tasks[self.current_task_idx]
            # Advance simulation clock safely (preventing until <= now error)
            target_time = max(self.simpy_env.now + 0.001, self.current_task.arrival_time)
            self.simpy_env.run(until=target_time)

        # 5. Multi-Objective Reward Calculation
        if not maintenance_violation:
            sla_penalty = self.current_task.sla_penalty(self.simpy_env.now)
            reward = self._calculate_reward(est_fidelity, wan_latency, queue_delay, sla_penalty)

        next_state = self._get_state(self.current_task) if not terminated else np.zeros(13, dtype=np.float32)

        info = {
            "fidelity": float(est_fidelity),
            "wan_latency_ms": float(wan_latency * 1000.0),
            "queue_delay_s": float(queue_delay),
            "maintenance_violation": bool(maintenance_violation),
            "action_mask": self.action_masks(),
            "chosen_dc": chosen_dc.name,
            "qnode": best_qnode.name if best_qnode else None,
            "sim_time": float(self.simpy_env.now),
        }

        if self.render_mode == "human":
            self.render()

        return next_state, float(reward), terminated, truncated, info

    def _get_state(self, task) -> np.ndarray:
        """Constructs the 13-dimensional state vector for the agent."""
        state = np.zeros(13, dtype=np.float32)

        # [0, 1, 2]: One-hot encoding of user location
        if task.user_location in self.locations:
            state[self.locations.index(task.user_location)] = 1.0

        # [3]: Number of qubits required
        state[3] = float(task.num_qubits)

        # [4..12]: Status of 3 Datacenters (Maintenance, WAN Latency ms, Idle Qubits)
        idx = 4
        for name in self.dc_names:
            dc = self.cloud.datacenters[name]
            state[idx] = 1.0 if dc.under_maintenance else 0.0
            state[idx + 1] = float(dc.wan_latency(task.user_location, payload_size_bytes=task.payload_size_bytes) * 1000.0)
            state[idx + 2] = float(dc.total_idle_qubits())
            idx += 3

        return state

    def _calculate_reward(
        self,
        fidelity: float,
        wan_latency: float,
        queue_delay: float,
        sla_penalty: float = 0.0,
    ) -> float:
        """
        Scalarized Multi-Objective Reward:
        R = (alpha * Fidelity) - (beta * WAN_ms) - (gamma * Queue_s) - (delta * SLA_Penalty)
        """
        reward = (
            (self.alpha_fidelity * fidelity)
            - (self.beta_wan * wan_latency * 1000.0)
            - (self.gamma_queue * queue_delay)
            - (self.delta_sla * sla_penalty)
        )
        return float(reward)

    def _build_infrastructure(self, env: simpy.Environment) -> CloudNetwork:
        """Constructs identical 3-Datacenter infrastructure matching QAISim specifications."""
        cloud = CloudNetwork(env, printlog=False)

        dc_a = Datacenter("DC-A-Near", env, distance_km=50, region_tier="near", location="US_East")
        dc_a.add_qnode(IBM_Marrakesh(env, name="Marrakesh-A1", printlog=False))
        dc_a.add_qnode(IBM_Fez(env, name="Fez-A2", printlog=False))

        dc_b = Datacenter("DC-B-Mid", env, distance_km=800, region_tier="mid", location="EU_West")
        dc_b.add_qnode(IBM_Torino(env, name="Torino-B1", printlog=False))

        dc_c = Datacenter(
            "DC-C-Far", env, distance_km=9000, region_tier="far", location="AP_South",
            dc_maintenance_interval=250, dc_maintenance_duration=80
        )
        dc_c.add_qnode(IBM_Quebec(env, name="Quebec-C1", printlog=False))

        for dc in (dc_a, dc_b, dc_c):
            cloud.register_datacenter(dc)

        cloud.set_failover("DC-C-Far", backup_names=["DC-B-Mid", "DC-A-Near"])

        for qn in cloud.all_qnodes():
            qn.assign_env(env)

        return cloud

    def render(self):
        """Displays the current environment state in human-readable console format."""
        if self.current_task is None or self.simpy_env is None:
            return
        masks = self.action_masks()
        print(f"\n[Gym t={self.simpy_env.now:.1f}s | Step {self.episode_step}] "
              f"Task #{self.current_task.task_id} ({self.current_task.circuit_name}) | "
              f"Qubits: {self.current_task.num_qubits} | Loc: {self.current_task.user_location} | "
              f"DC Masks (Available): {masks}")
