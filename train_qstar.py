import os
import time
from rl_env import QuantumCloudEnv
from stable_baselines3 import PPO
from stable_baselines3.common.evaluation import evaluate_policy
from stable_baselines3.common.callbacks import EvalCallback, StopTrainingOnRewardThreshold
from stable_baselines3.common.monitor import Monitor

def main():
    print("="*50)
    print("🚀 KHỞI ĐỘNG HUẤN LUYỆN AI QSTAR (PPO ALGORITHM)")
    print("="*50)

    # 1. Thiết lập thư mục lưu trữ Log (Tensorboard) và Models
    log_dir = "./qstar_logs/"
    os.makedirs(log_dir, exist_ok=True)
    model_path = os.path.join(log_dir, "qstar_ppo_best_model")

    # 2. Khởi tạo môi trường mô phỏng (Huấn luyện với 100 tasks mỗi ván)
    # Dùng class Monitor để dễ dàng theo dõi chỉ số Reward của Stable-Baselines
    env = QuantumCloudEnv(num_tasks=100)
    env = Monitor(env, log_dir)

    # Khởi tạo môi trường Đánh giá (Eval Env) độc lập để test mô hình sau mỗi chu kỳ
    eval_env = QuantumCloudEnv(num_tasks=100)
    eval_env = Monitor(eval_env)

    # 3. Tạo cơ chế Callback: Dừng training sớm nếu AI đạt điểm số quá xuất sắc
    stop_callback = StopTrainingOnRewardThreshold(reward_threshold=800.0, verbose=1)
    eval_callback = EvalCallback(
        eval_env, 
        best_model_save_path=log_dir,
        log_path=log_dir,
        eval_freq=2000, 
        callback_on_new_best=stop_callback,
        deterministic=True, 
        render=False
    )

    # 4. Định nghĩa Mô hình AI (Thuật toán PPO - Proximal Policy Optimization)
    # MlpPolicy: Sử dụng mạng Nơ-ron nhân tạo thông thường (Multi-Layer Perceptron)
    print("\n[1] Đang khởi tạo mô hình mạng Nơ-ron...")
    model = PPO(
        "MlpPolicy", 
        env, 
        learning_rate=0.0003,
        n_steps=2048,
        batch_size=64,
        gamma=0.99, # Hệ số chiết khấu (Discount factor) quan trọng cho Q-Learning/PPO
        verbose=1, 
        tensorboard_log=log_dir
    )

    # 5. Bắt đầu quá trình Huấn luyện (Training)
    print("\n[2] Bắt đầu quá trình học (Training)...")
    start_time = time.time()
    
    # Train AI qua 20,000 steps. (Trong bài báo thực tế bạn có thể tăng lên 500,000)
    model.learn(total_timesteps=20000, callback=eval_callback)
    
    end_time = time.time()
    print(f"\n✅ Quá trình huấn luyện kết thúc! Thời gian: {end_time - start_time:.2f} giây")

    # 6. Lưu lại mô hình cuối cùng
    model.save("qstar_ppo_final")
    print("Mô hình đã được lưu tại: qstar_ppo_final.zip")

    # 7. Kiểm tra lại trí thông minh của AI bằng cách cho nó thi tài 5 ván (Episodes)
    print("\n[3] Đánh giá năng lực của QSTAR Model (Evaluation):")
    mean_reward, std_reward = evaluate_policy(model, eval_env, n_eval_episodes=5)
    print(f"👉 Điểm Reward Trung bình: {mean_reward:.2f} +/- {std_reward:.2f}")

    # =========================================================================
    # CHẠY THỬ MỘT VÁN THỰC TẾ ĐỂ XEM AI RA QUYẾT ĐỊNH CHỌN MÁY NHƯ THẾ NÀO
    # =========================================================================
    print("\n[4] Chạy mô phỏng thực tế với mô hình đã train (1 Episode):")
    obs, info = env.reset()
    done = False
    step = 0
    total_reward = 0.0

    while not done:
        # AI đọc State (obs) và ra Quyết định chọn QNode (action)
        action, _states = model.predict(obs, deterministic=True)
        
        # Đẩy hành động đó vào môi trường mô phỏng
        obs, reward, done, truncated, info = env.step(action)
        
        total_reward += reward
        step += 1
        
        # Log 10 task đầu tiên để xem AI hoạt động
        if step <= 10:
            print(f"  Step {step:02d} | Task #{info['task_id']:03d} -> Điều phối tới QNode Index [{action}]: {info['assigned_device']} | Reward kiếm được: {reward:.2f}")

    print(f"\n🎉 Ván đấu mô phỏng kết thúc! Tổng điểm AI đạt được: {total_reward:.2f}")

if __name__ == "__main__":
    main()
