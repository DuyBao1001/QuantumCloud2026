"""
demo_multi_datacenter.py

Kich ban mo phong kiem thu tich hop toan dien kien truc Multi-Datacenter (QAISim):
1. Ha tang Multi-Datacenter:
   - DC-A (Near / US_East): 50 km (chua chip IBM Marrakesh, IBM Fez).
   - DC-B (Mid / EU_West): 800 km (chua chip IBM Torino).
   - DC-C (Far / AP_South): 9000 km (chua chip IBM Quebec, co chu ky bao tri dinh ky 250s / 80s).
2. Tich hop TaskGenerator & Broker:
   - TaskGenerator sinh cac QTask theo luong Poisson tu cac khu vuc dia ly khac nhau.
   - ParallelBroker dinh tuyen 2 tang thong minh dua tren do tre quang hoc WAN va hang doi.
   - Co che Failover tu dong chuyen huong khi Datacenter gap su co bao tri.
   - QNode tinh toan do tre CLOPS va uoc luong do trung thuc (estimate_fidelity).
3. Bao cao thong ke hieu nang (KPI Summary): Makespan, Fidelity, Latency, SLA.
"""

import sys
import simpy

# Dam bao terminal Windows khong bi loi encode ky tu Unicode
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from datacenter import Datacenter
from cloud_network import CloudNetwork
from broker import ParallelBroker
from task_generator import TaskGenerator
from env_qnodes import IBM_Marrakesh, IBM_Fez, IBM_Torino, IBM_Quebec


def build_demo_cloud(env: simpy.Environment) -> CloudNetwork:
    """Khoi tao mo hinh 3 Datacenter phan tan toan cau va nap cac QNode thuc te."""
    cloud = CloudNetwork(env, printlog=True)

    # --- Datacenter A (Near - Bac My) ---
    dc_a = Datacenter("DC-A-Near", env, distance_km=50, region_tier="near", location="US_East")
    dc_a.add_qnode(IBM_Marrakesh(env, name="Marrakesh-A1", printlog=False))
    dc_a.add_qnode(IBM_Fez(env, name="Fez-A2", printlog=False))

    # --- Datacenter B (Mid - Tay Au) ---
    dc_b = Datacenter("DC-B-Mid", env, distance_km=800, region_tier="mid", location="EU_West")
    dc_b.add_qnode(IBM_Torino(env, name="Torino-B1", printlog=False))

    # --- Datacenter C (Far - Chau A, co lich bao tri dinh ky toan bo DC) ---
    dc_c = Datacenter("DC-C-Far", env, distance_km=9000, region_tier="far", location="AP_South",
                       dc_maintenance_interval=250, dc_maintenance_duration=80)
    dc_c.add_qnode(IBM_Quebec(env, name="Quebec-C1", printlog=False))

    for dc in (dc_a, dc_b, dc_c):
        cloud.register_datacenter(dc)

    # Cau hinh Failover: Neu DC-C (Chau A) bao tri -> tu dong ne sang DC-B (Chau Au) roi DC-A (My)
    cloud.set_failover("DC-C-Far", backup_names=["DC-B-Mid", "DC-A-Near"])

    # Gan SimPy Environment cho tung QNode vat ly
    for qn in cloud.all_qnodes():
        qn.assign_env(env)

    return cloud


def run_full_end_to_end_demo(num_tasks=12, sim_duration=400):
    """
    Kich ban chay thu End-to-End: Bom QTask vao Broker va thuc thi tren ha tang Multi-Datacenter.
    """
    print("\n" + "=" * 80)
    print(" KHOI CHAY MO PHONG END-TO-END MULTI-DATACENTER QUANTUM CLOUD (QAISim)")
    print("=" * 80)

    env = simpy.Environment()
    cloud = build_demo_cloud(env)

    # Khoi tao Broker da chuong thong minh (Hierarchical Geo-Routing)
    broker = ParallelBroker(env, cloud_network=cloud, printlog=True)

    # Khoi tao TaskGenerator chuan QAISim (MQTBench + Geo user location + QoS SLA)
    gen = TaskGenerator(
        env=env,
        broker=broker,
        arrival_rate=0.08,  # Trung binh cach ~12.5 giay co 1 task
        qubit_range=(4, 25),
        shot_choices=[1024, 2048, 4096],
        seed=100,
        printlog=True
    )

    # Tien trinh sinh task
    env.process(gen.run_poisson(max_tasks=num_tasks))

    # Tien trinh theo doi dinh ky trang thai ha tang
    def monitor(env, cloud, interval=100):
        while True:
            yield env.timeout(interval)
            print(f"\n[Snapshot t={env.now:.1f}s] Uptime/Maintenance:")
            for name, dc in cloud.datacenters.items():
                status = "DANG BAO TRI (FAILOVER ACTIVE)" if dc.under_maintenance else "SAN SANG"
                print(f"  * {name} ({dc.location}): {status} | Idle Qubits: {dc.total_idle_qubits()} | Reroutes: {dc.reroute_count}")
            print("-" * 60)

    env.process(monitor(env, cloud))

    # Chay mo phong
    env.run(until=sim_duration)

    # In ket qua thong ke tong ket
    print("\n" + "=" * 80)
    print(" BANG TONG KET HIEU NANG MO PHONG (EVALUATION METRICS)")
    print("=" * 80)
    completed_tasks = [t for t in gen.generated_tasks if t.finish_time is not None]
    print(f"Tong so Task da sinh        : {len(gen.generated_tasks)}")
    print(f"Tong so Task da hoan thanh  : {len(completed_tasks)}")

    if completed_tasks:
        avg_turnaround = sum(t.turnaround_time() for t in completed_tasks) / len(completed_tasks)
        avg_wan = sum(getattr(t, 'network_latency', 0) for t in completed_tasks) / len(completed_tasks)
        fidelities = [t.estimated_fidelity for t in completed_tasks if t.estimated_fidelity is not None]
        avg_fidelity = sum(fidelities) / len(fidelities) if fidelities else 0.0
        sla_violations = sum(1 for t in completed_tasks if t.is_deadline_violated())

        print(f"Thoi gian hoan tat TB (TAT) : {avg_turnaround:.2f} sim-seconds")
        print(f"Do tre truyen dan WAN TB    : {avg_wan * 1000:.2f} ms")
        print(f"Do trung thuc TB (Fidelity) : {avg_fidelity:.4f}")
        print(f"So Task vi pham Deadline    : {sla_violations} / {len(completed_tasks)} ({sla_violations/len(completed_tasks)*100:.1f}%)")

    print("\nThong ke Datacenter Failover:")
    for name, dc in cloud.datacenters.items():
        print(f"  * {name}: Tong Uptime = {dc.total_uptime:.1f}s | Downtime = {dc.total_downtime:.1f}s | Reroute Failover = {dc.reroute_count}")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    run_full_end_to_end_demo()