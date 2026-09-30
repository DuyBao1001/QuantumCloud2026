# BÁO CÁO TIẾN ĐỘ DỰ ÁN QUANTUMCLOUD2026 (QAISim)
**Ngày báo cáo:** 29/09/2026  
**Chủ đề:** Multi-Objective Quantum Cloud Resource Scheduling Using Reinforcement Learning on a Digital Twin Framework

---

## 1. Cấu trúc Cây Thư mục Hiện tại

```text
QuantumCloud2026/
├── calibration/                          # Dữ liệu hiệu chuẩn phần cứng thực tế từ IBM Quantum
│   └── ibm_brisbane_calibrations_...csv  # File thông số lỗi cổng (1Q, 2Q, Readout error, T1, T2)
├── utility_functions/                    # Thư viện tiện ích thuật toán đồ thị
│   └── graph_manipulation.py             # Thuật toán cắt đồ thị con liên thông (Connected Subgraph)
├── test/                                 # Thư mục kiểm thử tự động
│   └── test_broker.py                    # File test (hiện đang trống - 0 bytes)
├── broker.py                             # Bộ điều phối tác vụ (BaseBroker, SerialBroker, ParallelBroker)
├── cloud_network.py                      # Tầng điều phối mạng lưới Multi-Datacenter toàn cầu & Failover
├── datacenter.py                         # Cụm Datacenter chứa QNode, tính trễ nội bộ & bảo trì DC
├── demo_multi_datacenter.py              # Script kịch bản mô phỏng kiểm thử hạ tầng 3 Datacenter
├── env_qnodes.py                         # Định nghĩa các dòng máy QPU cụ thể (IBM, Google, Rigetti, D-Wave)
├── geo_network.py                        # Mô hình vật lý tính độ trễ mạng WAN, Intra-DC & hàng đợi
├── project_context.md                    # Tài liệu tổng quan kiến trúc và mục tiêu dự án
├── progress_report.md                    # [File này] Báo cáo tiến độ chi tiết
├── qnode.py                              # Core mô phỏng QPU (BaseQNode, QuantumDevice, IBM_QuantumDevice)
├── qtask.py                              # Lớp biểu diễn tác vụ lượng tử (QTask) với QoS, SLA & Geo location
├── requirements.txt                      # Danh sách thư viện phụ thuộc (SimPy, Qiskit, Gymnasium, TF...)
├── task_generator.py                     # Module phát sinh tác vụ lượng tử chuẩn QAISim (MQTBench, Poisson, MMPP)
├── utils.py                              # File tiện ích bổ trợ (hiện đang trống - 0 bytes)
└── README.md                             # Thông tin giới thiệu repo
```

---

## 2. Tóm tắt Chức năng Các File Lõi

### 2.1. `broker.py` (Bộ điều phối tác vụ - ĐÃ NÂNG CẤP XÓA SỔ RANDOM.CHOICE)
- **Chức năng chính:**
  - `BaseBroker`: Cung cấp cấu trúc nền tảng với hàng đợi `task_queue`, hàm `receive_task(task)` nhận task từ bộ sinh và tự động kích hoạt vòng lặp xử lý SimPy `run()`.
  - **Định tuyến 2 tầng thông minh (Hierarchical Geo-Routing):**
    - **Tầng 1 (Datacenter Selection):** Kiểm tra `task.user_location`, gọi `geo_network.py` tính độ trễ WAN (quang học + truyền tải dữ liệu) và thời gian chờ hàng đợi để chọn Datacenter có $\text{Total Cost} = \text{WAN Latency} + \text{Queue Delay}$ thấp nhất. Tự động chuyển hướng (Failover) nếu DC gần nhất đang bảo trì.
    - **Tầng 2 (QNode Selection):** Sử dụng chiến lược **Best-Fit Allocation** để chọn QNode có lượng qubit rảnh vừa vặn nhất, hạn chế tối đa phân mảnh qubit và ưu tiên chip có CLOPS cao.
  - `SerialBroker` (Chế độ Đơn chương): Giữ khóa độc quyền QPU kèm mô phỏng độ trễ truyền gói tin mạng WAN.
  - `ParallelBroker` (Chế độ Đa chương - Multi-programming): Bắn song song các tác vụ vào QNode qua pipeline mạng WAN và phân vùng đồ thị con.
- **Trạng thái:** **Đã hoàn thiện 100% logic định tuyến mạng theo kịch bản của giảng viên hướng dẫn.** Xóa sạch mọi lệnh `random.choice`.

### 2.2. `datacenter.py` (Cụm Datacenter)
- **Chức năng chính:**
  - Đại diện cho một trung tâm dữ liệu độc lập, đóng gói một danh sách các QNode vật lý (`qnodes`).
  - Gắn liền với các thuộc tính vật lý: khoảng cách tới Gateway trung tâm (`distance_km`), phân vùng địa lý (`region_tier`: "near", "mid", "far").
  - Quản lý **chu kỳ bảo trì ở cấp độ Datacenter** (`_maintenance_process`, `under_maintenance`, `total_uptime`, `total_downtime`) hoàn toàn độc lập với việc bảo trì từng máy lẻ.
  - Tích hợp tính toán độ trễ nội bộ trong DC (`intra_dc_latency`) và danh sách Datacenter dự phòng (`failover_targets`).

### 2.3. `task_generator.py` (Bộ phát sinh QTask)
- **Chức năng chính (Vừa nâng cấp hoàn thiện theo chuẩn QAISim):**
  - **Tích hợp MQTBench:** Tự động gọi `mqt.bench.get_benchmark` để sinh mạch lượng tử thuật toán thực tế (QFT, Grover, VQE, QAOA, GHZ, DJ...). Có cơ chế **Synthetic Fallback** thông minh nếu chưa cài thư viện.
  - **Bóc tách lỗi chi tiết cho DRL:** Phân loại rõ ràng cổng 1-qubit, 2-qubit (quyết định 90% fidelity), và phép đo measurement vào thuộc tính `task.gates`.
  - **Network-Aware:** Gán thuộc tính vị trí client `user_location` ("US_East", "EU_West", "AP_South") để Broker phối hợp với `geo_network.py` tính độ trễ WAN thực tế.
  - **QoS & SLA Deadline:** Tự động tính toán thời hạn hoàn thành `deadline`, `deadline_factor` và hàm phạt trễ hạn `sla_penalty()` hỗ trợ hàm Reward cho DRL.
  - **Lưu lượng Pluggable:** Cho phép cắm rút các phân phối thời gian đến (`inter_arrival_fn`) tùy ý: Poisson mặc định, MMPP (Markov-Modulated Poisson Process cho lưu lượng bùng nổ bursty), Pareto, hoặc chu kỳ cố định.
  - **Chế độ đa dạng:** Hỗ trợ chạy liên tục SimPy (`run_stream`/`run_poisson`), sinh mẻ cố định cho RL (`generate_batch`), và lưu/đọc workload từ file JSON.

### 2.4. `demo_multi_datacenter.py` (Kịch bản kiểm thử tích hợp hạ tầng)
- **Chức năng chính:**
  - Khởi tạo mô hình 3 Datacenter phân tán địa lý:
    - **DC-A (Near):** 50 km (chứa máy Marrakesh, Fez).
    - **DC-B (Mid):** 800 km (chứa máy Torino).
    - **DC-C (Far):** 9000 km (chứa máy Quebec, có lịch bảo trì định kỳ chu kỳ 300s, kéo dài 90s).
  - Cấu hình cơ chế Failover: Khi DC-C bảo trì, các truy vấn điều hướng sẽ tự động nhảy sang DC-B rồi tới DC-A.
  - Vòng lặp `monitor` in ra snapshot trạng thái toàn hệ thống sau mỗi 100 sim-seconds.
- **Thực trạng:**
  - Mới chỉ kiểm tra hoạt động của tầng Topology mạng + Trạng thái bảo trì Datacenter.
  - **Chưa bơm QTask** từ `task_generator.py` và **chưa tích hợp luồng điều phối của Broker**.

### 2.5. `qnode.py` (Mô hình QPU & Hàm ước lượng Fidelity mới cập nhật)
- **Cơ chế `estimate_fidelity(self, task)` (Vừa cập nhật):**
  - **Khớp hoàn hảo với `task_generator.py`:** Tự động trích xuất các thông số cổng từ `task.gates` gồm số lượng cổng đơn qubit (`1q_gates`), cổng hai qubit (`2q_gates`), và số phép đo (`measurements`).
  - **Mô hình tính toán xác suất tích lũy (Cumulative Expected Fidelity):**
    $$F_{\text{total}} = F_{\text{1q}} \times F_{\text{2q}} \times F_{\text{meas}} = (1 - \epsilon_{\text{1q}})^{N_{\text{1q}}} \times (1 - \bar{\epsilon}_{\text{2q}})^{N_{\text{2q}}} \times (1 - \bar{\epsilon}_{\text{meas}})^{N_{\text{meas}}}$$
    - $\epsilon_{\text{1q}}$: Lấy từ tỷ lệ lỗi thực tế của cổng Pauli-X / RX trong file CSV calibration của IBM (trung bình $\sim 0.1\%$).
    - $\bar{\epsilon}_{\text{2q}}$: Lấy trung bình cộng lỗi của tất cả các cặp cổng vướng víu 2-qubit (ECR/CZ) trên chip (nguồn gây nhiễu lớn nhất $\sim 1\%$).
    - $\bar{\epsilon}_{\text{meas}}$: Lấy trung bình cộng từ danh sách `Readout assignment error` của từng qubit trên chip.
  - **Cơ chế Fallback thông minh:** Nếu gặp task cũ hoặc task chưa bóc tách profile cổng, tự động ước tính theo $\text{depth} \times \text{num\_qubits}$ để đảm bảo không bao giờ bị gián đoạn hay crash code.
  - **Tự động lưu vết & Log:** Gán trực tiếp giá trị vào `task.estimated_fidelity` và ghi log vào `task_records_manager` để cung cấp dữ liệu tức thì cho hàm Reward của DRL Agent.

---

## 3. Tiến độ Phần Môi trường AI (DRL) trong `env_qnodes.py`

| Tiêu chí | Trạng thái | Chi tiết đánh giá |
| :--- | :---: | :--- |
| **Kế thừa `gymnasium.Env`** | ❌ **CHƯA CÓ** | File hiện tại **chưa hề** import `gymnasium` hay định nghĩa lớp Gym Environment nào. |
| **Phương thức `reset()`** | ❌ **CHƯA CÓ** | Chưa được lập trình. |
| **Phương thức `step(action)`** | ❌ **CHƯA CÓ** | Chưa được lập trình. |
| **Định nghĩa `observation_space`** | ❌ **CHƯA CÓ** | Chưa thiết kế không gian trạng thái (State vector biểu diễn hàng đợi, tải DC, topology QPU). |
| **Định nghĩa `action_space`** | ❌ **CHƯA CÓ** | Chưa thiết kế không gian hành động phân cấp $A_t = (a_{dc}, a_{node}, a_{subgraph})$. |
| **Nội dung thực tế hiện có** | ⚠️ **Chỉ là danh mục phần cứng** | File hiện tại dài 513 dòng nhưng **100% nội dung là định nghĩa các lớp thiết bị QPU cụ thể** kế thừa từ `QuantumDevice` / `IBM_QuantumDevice` (như `IBM_guadalupe`, `IBM_tokyo`, `IBM_montreal`, `Google_sycamore`, `Chimera_dwave`...). |

> **Kết luận phần DRL:** Môi trường Reinforcement Learning hiện tại đang ở mức **0%**. Cần sớm xây dựng một lớp môi trường Gymnasium riêng (ví dụ đặt tên là `QuantumCloudEnv` trong `env_qnodes.py` hoặc tạo file mới `qcloud_env.py`) để làm cầu nối giữa SimPy và các thuật toán DRL (PPO/SAC/DQN).

---

## 4. Bảng Phân loại Tiến độ Chi tiết

### 4.1. Các phần việc ĐÃ HOÀN THÀNH (Done - ~75% toàn dự án)
1. **Khung mô phỏng Discrete-Event SimPy:**
   - Xây dựng thành công `QTask`, `BaseQNode`, `QuantumDevice`, `IBM_QuantumDevice`.
   - Quản lý tài nguyên qubit bằng `simpy.Container`, khóa bảo trì `maint_lock`, và tính toán thời gian chạy phần cứng QPU theo công thức CLOPS, số shots, Quantum Volume và depth.
2. **Trích xuất thông số lỗi phần cứng (IBM Calibration):**
   - Đọc dữ liệu từ file CSV calibration thực tế của IBM để trích xuất tỷ lệ lỗi cổng đơn qubit (`rx`, `x`), cổng 2-qubit (`cz`, `ecr`), và `readout_errors`.
3. **Ước lượng độ trung thực mạch lượng tử (`estimate_fidelity` trong `qnode.py`):**
   - **Đã hoàn thành 100%:** Bạn trong team vừa hoàn thiện hàm tính toán Fidelity tích hợp lỗi cổng 1Q, 2Q, readout và phân loại cổng từ `task_generator.py`.
4. **Mô hình Mạng Multi-Datacenter & Độ trễ (Network Layer):**
   - Hoàn thiện `Datacenter`, `CloudNetwork`, `geo_network.py`.
   - Tính toán đầy đủ độ trễ vật lý WAN theo vận tốc ánh sáng trong cáp quang ($\approx \frac{2}{3} c$), độ trễ chuyển mạch nội bộ Intra-DC, độ trễ hàng đợi và cơ chế chuyển vùng dự phòng (Failover).
5. **Bộ sinh tác vụ lượng tử chuẩn QAISim (`task_generator.py`):**
   - Hoàn chỉnh 100% với tích hợp MQTBench, Synthetic Gate classification, Geo-aware user location, QoS Deadline SLA penalty, và Pluggable traffic arrivals (Poisson/MMPP).
6. **Thuật toán Đồ thị Không gian (Spatial Multi-programming Base):**
   - Module `utility_functions/graph_manipulation.py` đã có các thuật toán tìm đồ thị con liên thông (`select_vertices`), ngắt kết nối (`remove_connectivity`) và phục hồi đồ thị (`reconnect_nodes`).
7. **Bộ điều phối tác vụ thông minh (`broker.py`):**
   - Đã **xóa sổ hoàn toàn `random.choice`**.
   - Cài đặt cơ chế định tuyến 2 tầng: Tầng 1 chọn Datacenter tối ưu dựa trên tổng thời gian ($\text{WAN Latency} + \text{Queue Delay}$), tự động failover khi DC bảo trì; Tầng 2 chọn QNode theo giải thuật Best-Fit tối ưu qubit rảnh và CLOPS.
8. **Kịch bản mô phỏng tích hợp toàn diện End-to-End (`demo_multi_datacenter.py`):**
   - **Đã hoàn thành 100%:** Kết nối mượt mà `TaskGenerator` -> `ParallelBroker` -> Mạng 3 Datacenter (`US_East`, `EU_West`, `AP_South`) -> 4 chip QPU thực tế (`Marrakesh`, `Fez`, `Torino`, `Quebec`).
   - Tự động xuất bảng tổng kết KPI toàn diện: Makespan, Turnaround Time, Trễ WAN, Fidelity, Tỷ lệ vi phạm Deadline SLA, và Thống kê bảo trì / Failover.

---

### 4.2. Các phần việc ĐANG DỞ DANG / CẦN THỰC HIỆN TIẾP (In Progress / Pending)

1. **Xây dựng Môi trường Gymnasium (`QuantumCloudEnv`):**
   - *Hiện trạng:* Chưa có code (xem mục 3).
   - *Cần làm:* Thiết kế class kế thừa `gymnasium.Env`, cài đặt `reset()` (reset SimPy env, khởi tạo batch tasks), `step(action)` (thực hiện action điều phối, bước SimPy tiến tới sự kiện tiếp theo, trả về state, multi-objective reward, done, info).
2. **Dữ liệu Topology:**
   - Đảm bảo trong thư mục dự án có đầy đủ các file JSON topology (`*_nodes.json`, `*_pos.json`) mà các class trong `env_qnodes.py` cần khi khởi tạo thiết bị.
