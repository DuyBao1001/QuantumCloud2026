class QTask:
    def __init__(self, task_id,
                 num_qubits,
                 depth,
                 num_shots,
                 priority,
                 arrival_time,
                 circuit_name=None,
                 gates=None):

        self.task_id = task_id
        self.circuit_name = circuit_name
        self.num_qubits = num_qubits
        self.depth = depth
        self.num_shots = num_shots
        self.gates = gates
        self.priority = priority
        self.arrival_time = arrival_time

        # --- Các field trạng thái (Cập nhật liên tục trong quá trình mô phỏng) ---
        self.start_time = None                   # THÊM: Thời điểm job bắt đầu chạy trên QNode
        self.finish_time = None                  # THÊM: Thời điểm job hoàn thành
        
        self.assigned_device = None              # Tên device xử lý job
        self.assigned_qubits = None              # List index qubit vật lý
        self.estimated_fidelity = None           # Cache độ trung thực
        self.qpu_time = None                     # THÊM: Cache thời gian thực thi (rút ra từ CLOPS)

    def wait_time(self):
        # Hàm hỗ trợ tính nhanh thời gian chờ cho hàm Reward của DRL
        if self.start_time is not None:
            return self.start_time - self.arrival_time
        return 0