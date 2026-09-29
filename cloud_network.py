"""
cloud_network.py

CloudNetwork: lop dieu phoi cap cao nhat, gom nhieu Datacenter (datacenter.py)
lai thanh mot "Quantum Cloud" thong nhat. Day chinh la phan khung (skeleton)
cho:

    - B2.2 Content 1 "Constructing a Multi-Datacenter Framework"
    - Cung cap action space `adc` (routing toi Datacenter) cho DRL Agent o
      Content 3 (xem QSTAR modeling: At = (adc, anode, asubgraph))
    - Action masking: loai cac Datacenter dang bao tri khoi action space
    - Failover Mechanism (Active-Standby / load balancing) khi DC chinh
      gap su co hoac dang bao tri dinh ky

Broker (broker.py hien dang trong - se code o Content 3, chua Deep
Reinforcement Learning Agent) se dung CloudNetwork lam "world model" de
chon adc -> anode -> asubgraph, va CloudNetwork.resolve_datacenter() co the
dung truc tiep lam BASELINE rule-based scheduler de so sanh voi DRL Agent
o Content 4 (Baseline Schedulers).
"""


class CloudNetwork:
    def __init__(self, env, printlog=True):
        self.env = env
        self.printlog = printlog
        self.datacenters = {}  # name -> Datacenter

    # ------------------------------------------------------------------ #
    # Dang ky / cau hinh
    # ------------------------------------------------------------------ #
    def register_datacenter(self, datacenter):
        """Dang ky mot Datacenter vao mang luoi Cloud."""
        self.datacenters[datacenter.name] = datacenter

    def set_failover(self, primary_name, backup_names):
        """
        Khai bao thu tu uu tien Datacenter du phong cho mot DC chinh.
        Vi du: set_failover("DC-C-Far", ["DC-B-Mid", "DC-A-Near"])
        """
        primary = self.datacenters[primary_name]
        primary.failover_targets = [self.datacenters[n] for n in backup_names]

    # ------------------------------------------------------------------ #
    # Phuc vu Action Space (adc) cua DRL Agent - Content 3
    # ------------------------------------------------------------------ #
    def get_action_mask(self):
        """
        Tra ve dict {dc_name: bool} - dung lam action mask cho `adc`.
        True = co the chon, False = dang bao tri / khong kha dung.
        Tuong ung phan "action masking mechanism" mo ta trong B2.2 Content 3.
        """
        return {name: dc.is_available() for name, dc in self.datacenters.items()}

    def list_available_datacenters(self):
        return [dc for dc in self.datacenters.values() if dc.is_available()]

    def find_best_datacenter(self, user_location: str, task=None):
        """
        Dinh tuyen thong minh: Tim Datacenter toi uu nhat dua tren:
        Cost = WAN Latency (user_location -> DC) + Queue Delay (tai DC).
        Tu dong bo qua cac Datacenter dang bao tri toan cuc.
        Tra ve (best_datacenter, wan_latency, queue_delay).
        """
        available_dcs = self.list_available_datacenters()
        if not available_dcs:
            return None, float("inf"), float("inf")

        best_dc = None
        min_total_cost = float("inf")
        best_wan = 0.0
        best_queue = 0.0

        payload_size = getattr(task, "payload_size_bytes", 0) if task else 0

        for dc in available_dcs:
            wan = dc.wan_latency(user_location=user_location, payload_size_bytes=payload_size)
            queue = dc.estimate_queue_delay(task=task)
            total_cost = wan + queue

            if total_cost < min_total_cost:
                min_total_cost = total_cost
                best_dc = dc
                best_wan = wan
                best_queue = queue

        return best_dc, best_wan, best_queue

    # ------------------------------------------------------------------ #
    # Failover Mechanism
    # ------------------------------------------------------------------ #
    def resolve_datacenter(self, preferred_name):
        """
        Tra ve Datacenter THUC SU se nhan task, uu tien `preferred_name`.
        Neu DC do dang bao tri -> tu dong thu lan luot cac failover_targets
        (Active-Standby). Tra ve None neu khong con DC nao kha dung (toan
        he thong qua tai / su co dien rong).

        Day la BASELINE rule-based failover, dung lam baseline scheduler de
        so sanh voi DRL Agent o Content 4. Khi Content 3 hoan thanh, hanh
        dong `adc` do RL Agent chon co the GHI DE logic nay bang policy da
        hoc duoc (agent co the chu dong chon DC gan/nhanh hon thay vi chi
        phan ung khi co su co).
        """
        primary = self.datacenters.get(preferred_name)
        if primary is None:
            raise KeyError(f"Datacenter '{preferred_name}' chua duoc dang ky.")

        if primary.is_available():
            return primary

        primary.reroute_count += 1
        if self.printlog:
            print(f"{self.env.now:.2f}: [FAILOVER] {preferred_name} dang bao tri, "
                  f"thu dinh tuyen sang DC du phong...")

        for backup in primary.failover_targets:
            if backup.is_available():
                if self.printlog:
                    print(f"{self.env.now:.2f}: [FAILOVER] -> chuyen task sang {backup.name}.")
                return backup

        if self.printlog:
            print(f"{self.env.now:.2f}: [FAILOVER] Khong con Datacenter du phong kha dung!")
        return None

    # ------------------------------------------------------------------ #
    # Truy van phuc vu State Space (St) cua DRL Agent - Content 3
    # ------------------------------------------------------------------ #
    def build_state_snapshot(self):
        """
        Tra ve snapshot trang thai toan he thong tai thoi diem hien tai,
        dung lam nguyen lieu tho de Broker / RL Agent build State Vector St
        (mo ta trong B2.2 Content 3 - State Space Modeling), bao gom them
        vector do tre mang uoc luong toi tung Datacenter kha dung.
        """
        snapshot = {}
        for name, dc in self.datacenters.items():
            snapshot[name] = {
                "available": dc.is_available(),
                "idle_qubits": dc.total_idle_qubits(),
                "num_qnodes": len(dc.qnodes),
                "wan_latency": dc.wan_latency(),
                "region_tier": dc.region_tier,
                "reroute_count": dc.reroute_count,
            }
        return snapshot

    def all_qnodes(self):
        """Tra ve toan bo QNode tren tat ca Datacenter (ke ca dang bao tri)."""
        return [qn for dc in self.datacenters.values() for qn in dc.qnodes]

    def __repr__(self):
        return f"<CloudNetwork datacenters={list(self.datacenters.keys())}>"