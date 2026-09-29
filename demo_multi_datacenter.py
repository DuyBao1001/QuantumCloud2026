"""
demo_multi_datacenter.py

Vi du dung lai cac lop QNode co san trong env_qnodes.py de dung mot kich ban
3 Datacenter (Near / Mid / Far) minh hoa dung Figure 1 trong thuyet minh de
tai (Gateway -> Broker -> DC-A/B/C, DC-C dang bao tri -> Failover).

Script nay CHUA dung den Broker/DRL Agent (Content 3, broker.py con trong) -
no chi dung de kiem chung khung Datacenter + CloudNetwork hoat dong dung
truoc khi rap them logic scheduling.
"""

import simpy

from datacenter import Datacenter
from cloud_network import CloudNetwork
from env_qnodes import IBM_Marrakesh, IBM_Fez, IBM_Torino, IBM_Quebec


def build_demo_cloud(env):
    cloud = CloudNetwork(env)

    # --- Datacenter A (Near) ---
    dc_a = Datacenter("DC-A-Near", env, distance_km=50, region_tier="near")
    dc_a.add_qnode(IBM_Marrakesh(env, name="Marrakesh-A1"))
    dc_a.add_qnode(IBM_Fez(env, name="Fez-A2"))

    # --- Datacenter B (Mid) ---
    dc_b = Datacenter("DC-B-Mid", env, distance_km=800, region_tier="mid")
    dc_b.add_qnode(IBM_Torino(env, name="Torino-B1"))

    # --- Datacenter C (Far, co lich bao tri dinh ky toan bo DC) ---
    dc_c = Datacenter("DC-C-Far", env, distance_km=9000, region_tier="far",
                       dc_maintenance_interval=300, dc_maintenance_duration=90)
    dc_c.add_qnode(IBM_Quebec(env, name="Quebec-C1"))

    for dc in (dc_a, dc_b, dc_c):
        cloud.register_datacenter(dc)

    # Failover: neu DC-C (Far) dang bao tri -> uu tien ne sang DC-B roi DC-A
    cloud.set_failover("DC-C-Far", backup_names=["DC-B-Mid", "DC-A-Near"])

    # Gan simpy.Environment thuc su cho tung QNode (xem assign_env trong qnode.py)
    for qn in cloud.all_qnodes():
        qn.assign_env(env)

    return cloud


def run_demo(sim_duration=1000):
    env = simpy.Environment()
    cloud = build_demo_cloud(env)

    def monitor(env, cloud, interval=100):
        while True:
            print(f"\n--- t={env.now:.1f} | State snapshot ---")
            for name, info in cloud.build_state_snapshot().items():
                print(f"  {name}: {info}")

            # Vi du goi thu failover mechanism
            resolved = cloud.resolve_datacenter("DC-C-Far")
            print(f"  -> resolve_datacenter('DC-C-Far') = "
                  f"{resolved.name if resolved else None}")

            yield env.timeout(interval)

    env.process(monitor(env, cloud))
    env.run(until=sim_duration)


if __name__ == "__main__":
    run_demo()