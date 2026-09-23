
import random
from abc import ABC, abstractmethod

class BaseBroker(ABC):
    #Xóa 'job' và 'job_records_manager'. Broker giờ là thực thể duy nhất
    def __init__(self, env, devices):
        """
        Base class for all brokers.
        """
        self.env = env
        # self.job = job
        self.devices = devices
        # self.job_records_manager = job_records_manager
        
        #Thêm hàng đợi để chứa các QTask
        self.task_queue = []

    #Bổ sung hàm nhận Task từ Generator
    def receive_task(self, task):
        self.task_queue.append(task)
        # Chỉ đánh thức vòng lặp run() nếu nó chưa chạy
        if not getattr(self, 'is_running', False):
            self.is_running = True
            self.env.process(self.run())

    @abstractmethod
    def assign_device(self, task): 
        # --- THAY ĐỔI 5: Truyền 'task' vào để hàm này biết đang xét task nào ---
        """
        Assign a task to an appropriate quantum device.
        """
        pass

    @abstractmethod
    def run(self):
        """
        Run the broker's main functionality for task processing.
        """
        pass
    
    
class SerialBroker(BaseBroker):
    # --- THAY ĐỔI 6: Xóa các tham số rườm rà của QCloudSim ---
    def __init__(self, env, devices):
        super().__init__(env, devices)
        # self.qcloud = qcloud
        
    def assign_device(self, task):
        """
        Assign a task to a random available device.
        """
        device = random.choice(self.devices)
        while device.maint_lock:
            # --- THAY ĐỔI 7: Đổi chữ Job thành Task ---
            print(f'{self.env.now:.2f}: Task #{task.task_id} waiting. {device.name} under maintenance...')
            yield self.env.timeout(1)
        return device

    def run(self):
        """
        Assign a device and process the task.
        """
        # --- THAY ĐỔI 8: Chạy vòng lặp xử lý hàng đợi ---
        while len(self.task_queue) > 0:
            current_task = self.task_queue.pop(0)
            
            device = yield from self.assign_device(current_task)

            # Process the task (Chế độ Đơn chương - Khóa toàn bộ thiết bị)
            with device.resource.request(priority=2) as req:
                yield req
                # --- THAY ĐỔI 9: Gọi process_task thay vì process_job ---
                yield self.env.process(device.process_task(current_task, self.env.now))
                
        self.is_running = False

            
class ParallelBroker(BaseBroker):
    # --- THAY ĐỔI 10: Tương tự, dọn dẹp các tham số thừa ---
    def __init__(self, env, devices):
        super().__init__(env, devices)
        # self.qcloud = qcloud
    
    def assign_device(self, task):
        # --- THAY ĐỔI 11: Nơi AI (DRL) sẽ ra quyết định. Tạm thời dùng Random ---
        device = random.choice(self.devices)
        return device
    
    def run(self):
        """
        Process tasks with device allocation (Chế độ Đa chương).
        """
        # --- THAY ĐỔI 12: Xử lý theo hàng đợi ---
        while len(self.task_queue) > 0:
            current_task = self.task_queue.pop(0)
            
            device = self.assign_device(current_task)
            
            if device.maint_lock:
                print(f'{self.env.now:.2f}: Task #{current_task.task_id} waiting. {device.name} under maintenance...')
                yield self.env.timeout(1)
                # Bỏ lại vào đầu hàng đợi để xét lại sau
                self.task_queue.insert(0, current_task) 
                continue
            
            # --- THAY ĐỔI 13: XÓA LỆNH KHÓA MÁY (with device.resource.request...) ---
            # Vì là Đa chương (Multi-programming), Broker chỉ việc "bắn" Task vào QNode.
            # QNode sẽ tự dùng logic cắt đồ thị của nó để chạy song song.
            self.env.process(device.process_task(current_task, self.env.now))
            
            # Tính fidelity (Đã comment lại vì trong qnode.py cũng đã tính)
            # fidelity = device.estimate_fidelity(current_task)
            
            # Nhịp nghỉ mô phỏng để SimPy không bị treo vòng lặp
            yield self.env.timeout(0.1)

        self.is_running = False