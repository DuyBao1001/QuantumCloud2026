import simpy
from task_generator import TaskGenerator

def build_offline_dataset():
    print(">>> BẮT ĐẦU SINH DỮ LIỆU TỪ MQT.BENCH <<<")
    print("Quá trình này có thể mất vài phút vì phải biên dịch mạch thật...")
    
    # 1. Môi trường giả
    env = simpy.Environment()
    
    # 2. BẬT mqt.bench (use_mqt=True) để lấy mạch lượng tử thực tế
    gen = TaskGenerator(
        env=env, 
        use_mqt=True,         # Rất quan trọng!
        qubit_range=(4, 25), 
        printlog=False        # Tắt log để màn hình đỡ giật
    )
    
    # 3. Dùng hàm ông đã viết để đẻ ra 5000 tasks 
    # (fixed_interval=12.0 nghĩa là cách nhau 12 giây ảo có 1 task)
    tasks = gen.generate_batch(num_tasks=5000, fixed_interval=12.0)
    
    # 4. Lưu toàn bộ 5000 tasks đó vào file JSON
    gen.save_workload_to_json(tasks, "real_workload_5000.json")
    
    print(f">>> HOÀN TẤT! Đã lưu {len(tasks)} tasks vào file real_workload_5000.json <<<")

if __name__ == "__main__":
    build_offline_dataset()