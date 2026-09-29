import gymnasium as gym
from gymnasium import spaces
import numpy as np
import simpy
import math
import random

from datacenter import Datacenter
from cloud_network import CloudNetwork
import env_qnodes
from task_generator import TaskGenerator

class QuantumCloudEnv(gym.Env):
    """
    Môi trường Gymnasium mô phỏng Bản sao kỹ thuật số (Digital Twin) mạng lượng tử đám mây.
    Được thiết kế cho Agent QSTAR tối ưu đa mục tiêu (Multi-Objective: Makespan, Fidelity, Deadline).
    Hỗ trợ cơ chế đa chương (Multi-programming).
    """
    
    def __init__(self, num_tasks=50):
        super(QuantumCloudEnv, self).__init__()
        self.num_tasks = num_tasks
        
        # Số lượng thiết bị mặc định trong Topology (Marrakesh, Fez, Torino, Quebec)
        self.num_qnodes = 4 
        
        # ACTION SPACE: Agent chọn 1 trong số 4 QNode để gán Task
        self.action_space = spaces.Discrete(self.num_qnodes)
        
        # OBSERVATION SPACE (State vector):
        # - Thông tin Task hiện tại (6 chiều): Qubits, Depth, Shots, Priority, Deadline Factor, Location(encoded)
        # - Thông tin các QNodes (3 x 4 = 12 chiều): % Qubit rảnh, trạng thái bảo trì, Latency ước tính
        # Tổng = 18 chiều
        obs_dim = 6 + 3 * self.num_qnodes
        self.observation_space = spaces.Box(low=0.0, high=1.0, shape=(obs_dim,), dtype=np.float32)
        
        # Map location string to index for encoding
        self.loc_mapping = {"near": 0.0, "mid": 0.5, "far": 1.0}

    def _build_digital_twin(self):
        """Khởi tạo lại toàn bộ hạ tầng mạng phân tán cho mỗi Episode."""
        self.simpy_env = simpy.Environment()
        self.cloud = CloudNetwork(self.simpy_env)

        # Lấy danh sách tất cả các class thiết bị IBM từ env_qnodes (Bỏ class base)
        device_classes = [
            cls for name, cls in vars(env_qnodes).items() 
            if isinstance(cls, type) and name.startswith("IBM_") and name != "IBM_QuantumDevice"
        ]
        
        # ĐỘT PHÁ: Bốc ngẫu nhiên 4 loại thiết bị cho Episode này để AI không bị Overfitting
        selected_classes = random.sample(device_classes, self.num_qnodes)

        # Khởi tạo 3 Datacenter phân tán địa lý (Digital Twin)
        dc_a = Datacenter("DC-A-Near", self.simpy_env, distance_km=50, region_tier="near")
        dc_b = Datacenter("DC-B-Mid", self.simpy_env, distance_km=800, region_tier="mid")
        dc_c = Datacenter("DC-C-Far", self.simpy_env, distance_km=9000, region_tier="far",
                          dc_maintenance_interval=300, dc_maintenance_duration=90)

        # Khởi tạo 4 thiết bị với tên chứa luôn dòng chip để tiện theo dõi
        qnode0 = selected_classes[0](self.simpy_env, name=f"{selected_classes[0].__name__}-A1")
        qnode1 = selected_classes[1](self.simpy_env, name=f"{selected_classes[1].__name__}-A2")
        qnode2 = selected_classes[2](self.simpy_env, name=f"{selected_classes[2].__name__}-B1")
        qnode3 = selected_classes[3](self.simpy_env, name=f"{selected_classes[3].__name__}-C1")
        
        dc_a.add_qnode(qnode0)
        dc_a.add_qnode(qnode1)
        dc_b.add_qnode(qnode2)
        dc_c.add_qnode(qnode3)

        for dc in (dc_a, dc_b, dc_c):
            self.cloud.register_datacenter(dc)

        # Phân bổ môi trường SimPy cho thiết bị
        self.qnodes = self.cloud.all_qnodes()
        for qn in self.qnodes:
            qn.assign_env(self.simpy_env)
            
        # Lưu mapping QNode -> Datacenter để tính Latency
        self.node_to_dc = {}
        self.node_to_dc[qnode0.name] = dc_a
        self.node_to_dc[qnode1.name] = dc_a
        self.node_to_dc[qnode2.name] = dc_b
        self.node_to_dc[qnode3.name] = dc_c

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        
        # 1. Reset Hạ tầng mô phỏng
        self._build_digital_twin()
        
        # 2. Sinh Workload (Batch) cho Episode này
        # Tạo TaskGenerator, không cần Broker vì Env sẽ đóng vai trò Broker (do DRL Agent điều khiển)
        self.tg = TaskGenerator(self.simpy_env, broker=None)
        
        # Dùng tính năng xịn xò generate_batch() của bạn để tạo dataset cố định cho Episode
        self.tasks_batch = self.tg.generate_batch(self.num_tasks, start_time=0.0)
        
        self.current_task_index = 0
        
        # 3. Tua thời gian mô phỏng đến lúc Task đầu tiên đến
        first_task = self.tasks_batch[0]
        if first_task.arrival_time > 0:
            self.simpy_env.run(until=first_task.arrival_time)
            
        return self._get_obs(), {}

    def _get_obs(self):
        """Mã hóa Trạng thái hệ thống (State) thành Vector."""
        if self.current_task_index >= len(self.tasks_batch):
            return np.zeros(self.observation_space.shape, dtype=np.float32)
            
        task = self.tasks_batch[self.current_task_index]
        
        # Feature 1: Task (Chuẩn hóa về [0, 1])
        t_qubits = min(task.num_qubits / 127.0, 1.0)
        t_depth = min(task.depth / 1000.0, 1.0)
        t_shots = min(task.num_shots / 4096.0, 1.0)
        t_prio = task.priority / 3.0
        t_deadline = min(getattr(task, 'deadline_factor', 1.0) / 3.0, 1.0)
        
        loc_str = getattr(task, 'user_location', 'near').lower()
        t_loc = self.loc_mapping.get(loc_str, 0.5)
        
        obs = [t_qubits, t_depth, t_shots, t_prio, t_deadline, t_loc]
        
        # Feature 2: QNodes & Datacenters (Multi-programming capacity & Digital Twin latency)
        for qn in self.qnodes:
            # Thuộc tính 1: Tỷ lệ Qubit còn trống (Phục vụ Multi-programming)
            cap = qn.container.capacity
            idle = qn.container.level
            idle_ratio = idle / cap if cap > 0 else 0.0
            
            # Thuộc tính 2: Đang bảo trì không?
            maint = 1.0 if qn.maint_lock else 0.0
            
            # Thuộc tính 3: Khoảng cách địa lý ước lượng (Digital twin WAN latency)
            dc = self.node_to_dc[qn.name]
            dist_ratio = min(dc.distance_km / 10000.0, 1.0) 
            
            obs.extend([idle_ratio, maint, dist_ratio])
            
        return np.array(obs, dtype=np.float32)

    def step(self, action):
        task = self.tasks_batch[self.current_task_index]
        device = self.qnodes[action]
        dc = self.node_to_dc[device.name]
        
        # --- TÍNH TOÁN REWARD TRỰC TIẾP (Heuristic Multi-Objective Reward cho QSTAR) ---
        reward = 0.0
        
        # Mục tiêu 1: Fidelity (Độ trung thực) - Càng cao càng tốt
        expected_fidelity = device.estimate_fidelity(task)
        reward += (expected_fidelity * 10) 
        
        # Mục tiêu 2: Bị phạt nếu gán vào thiết bị đang kẹt/bảo trì (Makespan / Queue penalty)
        if device.maint_lock:
            reward -= 5.0  # Phạt nặng vì đẩy vào lúc bảo trì
            
        # Thưởng khi gán vào thiết bị có đủ Qubit trống ngay lập tức (Ủng hộ Multi-programming)
        if device.container.level >= task.num_qubits:
            reward += 2.0
        else:
            reward -= 2.0  # Bị vào hàng đợi chờ Qubit giải phóng
            
        # Mục tiêu 3: WAN Latency (Độ trễ đường truyền vật lý)
        # Bị trừ điểm nếu user ở xa DC xử lý
        task_loc = getattr(task, 'user_location', 'near')
        if task_loc != dc.region_tier:
            reward -= 1.0
            if task_loc == 'near' and dc.region_tier == 'far':
                reward -= 2.0 # Penalty nặng hơn vì đi xuyên lục địa
                
        # --- THỰC THI ACTION TRONG MÔ PHỎNG ---
        # Chèn quá trình chạy task vào QNode (Multi-programming không dùng lock phần cứng)
        self.simpy_env.process(device.process_task(task, self.simpy_env.now))
        
        # --- CHUYỂN SANG BƯỚC TIẾP THEO ---
        self.current_task_index += 1
        done = self.current_task_index >= self.num_tasks
        
        info = {
            "task_id": task.task_id,
            "assigned_device": device.name,
            "fidelity": expected_fidelity,
            "reward": reward
        }
        
        if not done:
            # Tua thời gian mô phỏng đến lúc Task MỚI xuất hiện
            next_task = self.tasks_batch[self.current_task_index]
            time_to_advance = next_task.arrival_time - self.simpy_env.now
            if time_to_advance > 0:
                self.simpy_env.run(until=self.simpy_env.now + time_to_advance)
        else:
            # Chạy nốt những task cuối cùng còn trong hàng đợi
            self.simpy_env.run(until=self.simpy_env.now + 500)
            
        return self._get_obs(), reward, done, False, info
