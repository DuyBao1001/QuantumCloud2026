"""
qtask.py

Quantum Task representation for QAISim framework.
Encapsulates circuit characteristics, QoS/SLA constraints, network origin,
and execution lifecycle states.
"""

from typing import Any, Dict, List, Optional


class QTask:
    def __init__(
        self,
        task_id: int,
        num_qubits: int,
        depth: int,
        num_shots: int,
        priority: int,
        arrival_time: float,
        circuit_name: Optional[str] = None,
        gates: Optional[Any] = None,
        user_location: str = "US_East",
        deadline_factor: float = 2.0,
        deadline: Optional[float] = None,
        payload_size_bytes: Optional[float] = None,
    ):
        self.task_id = task_id
        self.circuit_name = circuit_name or f"task_{task_id}"
        self.num_qubits = num_qubits
        self.depth = depth
        self.num_shots = num_shots
        self.gates = gates
        self.priority = priority  # 1 = High, 2 = Medium, 3 = Low
        self.arrival_time = arrival_time

        # --- Network & Geo attributes (WAN Latency modeling) ---
        self.user_location = user_location

        # --- QoS / SLA constraints (DRL Reward penalty) ---
        self.deadline_factor = deadline_factor
        # If deadline is not pre-computed, initialize with an estimated slack
        self.deadline = deadline

        # Transmission payload size (circuit upload + measurement results download)
        # Default approximation: 500 bytes base + 50 bytes per gate + 2 bytes per shot
        if payload_size_bytes is not None:
            self.payload_size_bytes = payload_size_bytes
        else:
            total_g = gates.get("total_gates", depth * num_qubits // 2) if isinstance(gates, dict) else depth * 5
            self.payload_size_bytes = 500.0 + (total_g * 50.0) + (num_shots * 2.0)

        # --- Execution Lifecycle States (Updated continuously during simulation) ---
        self.start_time: Optional[float] = None          # Thời điểm job bắt đầu chạy trên QNode
        self.finish_time: Optional[float] = None         # Thời điểm job hoàn thành
        self.assigned_datacenter: Optional[str] = None   # Tên Datacenter xử lý
        self.assigned_device: Optional[str] = None       # Tên device xử lý job
        self.assigned_qubits: Optional[List[int]] = None # List index qubit vật lý
        self.estimated_fidelity: Optional[float] = None  # Cache độ trung thực
        self.qpu_time: Optional[float] = None            # Thời gian thực thi phần cứng QPU
        self.network_latency: Optional[float] = None     # Tổng độ trễ truyền dẫn mạng (WAN + LAN)

    def wait_time(self, current_time: Optional[float] = None) -> float:
        """Thời gian chờ từ lúc đến tới lúc bắt đầu chạy (hoặc đến current_time nếu chưa chạy)."""
        if self.start_time is not None:
            return self.start_time - self.arrival_time
        if current_time is not None:
            return max(0.0, current_time - self.arrival_time)
        return 0.0

    def turnaround_time(self) -> Optional[float]:
        """Tổng thời gian từ lúc đến đến khi hoàn tất (Turnaround Time)."""
        if self.finish_time is not None:
            return self.finish_time - self.arrival_time
        return None

    def is_deadline_violated(self, current_time: Optional[float] = None) -> bool:
        """Kiểm tra xem task đã bị quá hạn chót (Deadline) hay chưa."""
        if self.deadline is None:
            return False
        eval_time = self.finish_time if self.finish_time is not None else current_time
        if eval_time is None:
            return False
        return eval_time > self.deadline

    def lateness(self, current_time: Optional[float] = None) -> float:
        """Độ trễ quá hạn (>= 0). Nếu chưa vượt deadline thì bằng 0."""
        if self.deadline is None:
            return 0.0
        eval_time = self.finish_time if self.finish_time is not None else current_time
        if eval_time is None:
            return 0.0
        return max(0.0, eval_time - self.deadline)

    def sla_penalty(self, current_time: Optional[float] = None, penalty_weight: float = 1.0) -> float:
        """
        Tính điểm phạt SLA cho hàm Reward DRL.
        Task có priority cao hơn (p=1) sẽ bị phạt nặng hơn khi vi phạm deadline.
        """
        late = self.lateness(current_time)
        if late <= 0.0:
            return 0.0
        priority_multiplier = {1: 3.0, 2: 1.5, 3: 1.0}.get(self.priority, 1.0)
        return late * priority_multiplier * penalty_weight

    def to_dict(self) -> Dict[str, Any]:
        """Chuyển đổi QTask thành dictionary để lưu trữ JSON."""
        return {
            "task_id": self.task_id,
            "circuit_name": self.circuit_name,
            "num_qubits": self.num_qubits,
            "depth": self.depth,
            "num_shots": self.num_shots,
            "priority": self.priority,
            "arrival_time": self.arrival_time,
            "user_location": self.user_location,
            "deadline_factor": self.deadline_factor,
            "deadline": self.deadline,
            "payload_size_bytes": self.payload_size_bytes,
            "gates": self.gates,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "QTask":
        """Khôi phục QTask từ dictionary."""
        return cls(
            task_id=data["task_id"],
            num_qubits=data["num_qubits"],
            depth=data["depth"],
            num_shots=data["num_shots"],
            priority=data.get("priority", 2),
            arrival_time=data.get("arrival_time", 0.0),
            circuit_name=data.get("circuit_name"),
            gates=data.get("gates"),
            user_location=data.get("user_location", "US_East"),
            deadline_factor=data.get("deadline_factor", 2.0),
            deadline=data.get("deadline"),
            payload_size_bytes=data.get("payload_size_bytes"),
        )