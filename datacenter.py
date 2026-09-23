"""
datacenter.py

Lop Datacenter: dai dien cho MOT cum (cluster) cac QNode vat ly (cac instance
QuantumDevice / IBM_QuantumDevice da co san trong qnode.py va env_qnodes.py),
dat tai mot vi tri dia ly cu the, co khoang cach rieng toi Gateway trung tam
va co lich bao tri rieng o CAP DO DATACENTER.

Day la thanh phan lap day cho:
    - B2.2 Content 1 "Quantum Simulation Core Layer" (Datacenter framework
      encapsulates clusters of Quantum Computing Nodes...)
    - B2.2 Content 1 "Constructing a Multi-Datacenter Framework"

LUU Y QUAN TRONG:
    Datacenter KHONG can sua doi gi trong qnode.py. Bao tri o cap Datacenter
    (mo phong su co ha tang / bao tri toan bo trung tam du lieu) la mot khai
    niem KHAC voi maintenance() cua tung QuantumDevice (mo phong bao tri may
    le). Hai co che nay hoat dong doc lap va CONG DON: mot QNode co the
    khong kha dung vi (a) chinh no dang maintenance rieng, HOAC (b) ca
    Datacenter chua no dang bao tri toan bo.
"""

import random


class Datacenter:
    """
    Parameters
    ----------
    name : str
        Ten dinh danh, vd "DC-A-Near", "DC-B-Mid", "DC-C-Far".
    env : simpy.Environment
        Moi truong mo phong dung chung toan he thong.
    distance_km : float
        Khoang cach vat ly (km) tu Gateway trung tam toi Datacenter nay.
        Dung de tinh WAN latency (xem geo_network.propagation_delay).
    region_tier : str
        Nhan mo ta (near / mid / far) - phuc vu thiet ke kich ban
        Geo-distribution trong B2.2 Content 4.
    qnodes : list[QuantumDevice] | None
        Danh sach QNode vat ly ban dau. Co the add_qnode() them sau.
    dc_maintenance_interval / dc_maintenance_duration : float | None
        Chu ky / thoi luong bao tri O CAP DATACENTER. None -> DC nay khong
        co lich bao tri toan bo tu dong (van co the bi bao tri thu cong qua
        set_maintenance()).
    intra_dc_latency_fn : callable | None
        Ham tuy chinh tinh do tre noi bo (dc, qnode) -> seconds. None se
        dung geo_network.default_intra_dc_latency.
    """

    def __init__(self, name, env, distance_km, region_tier="mid",
                 qnodes=None, dc_maintenance_interval=None,
                 dc_maintenance_duration=None, intra_dc_latency_fn=None,
                 printlog=True):
        self.name = name
        self.env = env
        self.distance_km = distance_km
        self.region_tier = region_tier
        self.qnodes = qnodes if qnodes is not None else []
        self.dc_maintenance_interval = dc_maintenance_interval
        self.dc_maintenance_duration = dc_maintenance_duration
        self.intra_dc_latency_fn = intra_dc_latency_fn
        self.printlog = printlog

        # Trang thai san sang cua TOAN BO Datacenter (khac maint_lock tung QNode)
        self.under_maintenance = False

        # Failover: danh sach Datacenter du phong, gan boi CloudNetwork.set_failover()
        self.failover_targets = []  # list[Datacenter], theo thu tu uu tien

        # Thong ke phuc vu B2.2 Content 4 (Evaluation Metrics: reroute rate, uptime)
        self.reroute_count = 0
        self.total_uptime = 0.0
        self.total_downtime = 0.0

        if self.dc_maintenance_interval is not None:
            self.env.process(self._maintenance_process())

    # ------------------------------------------------------------------ #
    # Quan ly QNode trong Datacenter
    # ------------------------------------------------------------------ #
    def add_qnode(self, qnode):
        """Them mot QNode (QuantumDevice / IBM_QuantumDevice) vao Datacenter."""
        qnode.datacenter = self  # backref, huu ich khi log / dinh tuyen nguoc
        self.qnodes.append(qnode)

    def available_qnodes(self):
        """
        QNode co the nhan task ngay bay gio, thoa ca hai dieu kien:
        - Datacenter khong bi bao tri toan cuc.
        - Ban than QNode khong bi maint_lock rieng (thuoc tinh co san trong
          qnode.QuantumDevice).
        """
        if self.under_maintenance:
            return []
        return [qn for qn in self.qnodes if not getattr(qn, "maint_lock", False)]

    def total_idle_qubits(self):
        """Tong so qubit ranh tren toan Datacenter (dung cho state/action masking)."""
        return sum(qn.container.level for qn in self.available_qnodes())

    def is_available(self):
        """Datacenter co the nhan task hay khong (dung cho action masking `adc`)."""
        return not self.under_maintenance and len(self.available_qnodes()) > 0

    # ------------------------------------------------------------------ #
    # Bao tri cap Datacenter
    # ------------------------------------------------------------------ #
    def set_maintenance(self, flag: bool):
        """Bat/tat bao tri thu cong (vd de dung test kich ban Content 4)."""
        self.under_maintenance = flag

    def _maintenance_process(self):
        """
        Tien trinh SimPy: dinh ky dua TOAN BO Datacenter vao trang thai bao
        tri, mo phong su co ha tang / bao tri trung tam du lieu (khac bao
        tri may le da co trong qnode.py). Phuc vu kich ban Failover o
        Content 1 va do luong "Reroute rate" o Content 4.
        """
        # jitter khoi dong de cac DC khong bao tri dong loat cung mot luc
        yield self.env.timeout(random.randint(0, 60))
        while True:
            uptime_start = self.env.now
            yield self.env.timeout(self.dc_maintenance_interval)
            self.total_uptime += self.env.now - uptime_start

            self.under_maintenance = True
            if self.printlog:
                print(f"{self.env.now:.2f}: [MAINTENANCE] {self.name} "
                      f"bat dau bao tri toan bo Datacenter.")

            downtime_start = self.env.now
            yield self.env.timeout(self.dc_maintenance_duration)
            self.total_downtime += self.env.now - downtime_start

            self.under_maintenance = False
            if self.printlog:
                print(f"{self.env.now:.2f}: [MAINTENANCE] {self.name} "
                      f"da hoat dong tro lai.")

    # ------------------------------------------------------------------ #
    # Network latency (Geo-Network Layer, Content 1)
    # ------------------------------------------------------------------ #
    def wan_latency(self):
        """WAN latency: User -> Datacenter Gateway."""
        from geo_network import propagation_delay
        return propagation_delay(self.distance_km)

    def intra_dc_latency(self, qnode=None):
        """Do tre noi bo: Datacenter Gateway -> QNode vat ly ben trong DC."""
        if self.intra_dc_latency_fn is not None:
            return self.intra_dc_latency_fn(self, qnode)
        from geo_network import default_intra_dc_latency
        return default_intra_dc_latency(self, qnode)

    def estimate_total_network_latency(self, qnode=None):
        """Tong do tre mang end-to-end (WAN + Intra-DC) toi mot QNode cu the."""
        return self.wan_latency() + self.intra_dc_latency(qnode)

    def __repr__(self):
        return (f"<Datacenter {self.name} tier={self.region_tier} "
                f"dist={self.distance_km}km qnodes={len(self.qnodes)} "
                f"maintenance={self.under_maintenance}>")