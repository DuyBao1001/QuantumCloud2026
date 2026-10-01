"""
geo_network.py

Geo-Network Layer (thuyet minh B2.2 - Content 1):
    - WAN latency   : User/IoT device -> Datacenter Gateway
                      (mo hinh lan truyen quang trong soi cap: propagation_delay ~ d / (2/3 * c))
    - Intra-DC latency : Datacenter Gateway -> QNode vat ly ben trong DC
    - Queuing delay, payload transmission time: gop chung vao Total End-to-end Turnaround Time
      (theo B2.1 - "Optimizing End-to-end Turnaround Time")

Toan bo ham trong file nay la pure function (khong phu thuoc simpy), de co
the unit-test doc lap truoc khi rap vao Datacenter / Broker / RL Agent.
"""

import random

# Van toc anh sang trong chan khong (km/s)
SPEED_OF_LIGHT_KM_S = 299_792.458

# He so suy giam van toc lan truyen trong soi quang so voi chan khong (~2/3 c)
FIBER_VELOCITY_FACTOR = 2 / 3

# Bang khoang cach quang hoc (km) giua cac vung dia ly lon tren the gioi:
# Dung de tinh toan WAN propagation delay tu User Client toi Datacenter
GEO_DISTANCE_MATRIX = {
    # US_East (Vi du: Bac My - Virginia, New York)
    ("US_East", "US_East"): 80.0,
    ("US_East", "EU_West"): 6000.0,
    ("US_East", "AP_South"): 14000.0,
    
    # EU_West (Vi du: Tay Au - Frankfurt, London)
    ("EU_West", "US_East"): 6000.0,
    ("EU_West", "EU_West"): 100.0,
    ("EU_West", "AP_South"): 8500.0,
    
    # AP_South (Vi du: Chau A - Singapore, Tokyo)
    ("AP_South", "US_East"): 14000.0,
    ("AP_South", "EU_West"): 8500.0,
    ("AP_South", "AP_South"): 120.0,
}


def get_geo_distance(user_loc: str, dc_loc: str, fallback_dist: float = 1000.0) -> float:
    """
    Tra ve khoang cach vat ly (km) giua vi tri user va Datacenter.
    Neu khong tim thay trong matrix, tra ve fallback_dist.
    """
    key = (user_loc, dc_loc)
    if key in GEO_DISTANCE_MATRIX:
        return GEO_DISTANCE_MATRIX[key]
    reverse_key = (dc_loc, user_loc)
    if reverse_key in GEO_DISTANCE_MATRIX:
        return GEO_DISTANCE_MATRIX[reverse_key]
    if user_loc == dc_loc:
        return 100.0
    return fallback_dist


def calculate_wan_latency(user_location: str, datacenter, payload_size_bytes: float = 0,
                          bandwidth_bps: float = 1e9, velocity_factor: float = FIBER_VELOCITY_FACTOR) -> float:
    """
    Tinh toan toan bo do tre WAN (Propagation delay + Payload transmission delay)
    tu user_location toi Datacenter (tra ve giay).
    """
    dc_location = getattr(datacenter, "location", None)
    if not dc_location:
        # Fallback suy dien dua tren tier hoac name
        tier = getattr(datacenter, "region_tier", "").lower()
        name_lower = getattr(datacenter, "name", "").lower()
        if "near" in tier or "a" in name_lower:
            dc_location = "US_East"
        elif "mid" in tier or "b" in name_lower:
            dc_location = "EU_West"
        elif "far" in tier or "c" in name_lower:
            dc_location = "AP_South"
        else:
            dc_location = getattr(datacenter, "name", "US_East")

    dist_km = get_geo_distance(user_location, dc_location, fallback_dist=getattr(datacenter, "distance_km", 1000.0))
    prop_delay = propagation_delay(dist_km, velocity_factor)
    trans_delay = payload_transmission_time(payload_size_bytes, bandwidth_bps) if payload_size_bytes > 0 else 0.0
    return prop_delay + trans_delay


def propagation_delay(distance_km: float, velocity_factor: float = FIBER_VELOCITY_FACTOR) -> float:
    """
    propagation_delay = distance_km / (velocity_factor * c)

    Tra ve don vi: giay.
    Neu simulation clock cua toolkit dang dung "sim-mins" (nhu trong
    qnode.py: calculate_process_time tra ve phut), hay tu quy doi don vi
    (vd nhan 60 hoac chia 60) o lop goi cho dong nhat truoc khi cong vao
    tong turnaround time.
    """
    effective_speed = velocity_factor * SPEED_OF_LIGHT_KM_S
    return distance_km / effective_speed


def queuing_delay(queue_length: int, service_rate_per_sec: float) -> float:
    """
    Xap xi do tre hang doi theo mo hinh M/M/1 don gian hoa.
    Dung tam thoi lam baseline; Content 3 co the thay bang gia tri do
    truc tiep tu SimPy Resource queue neu can chinh xac hon.
    """
    if service_rate_per_sec <= 0:
        return float("inf")
    return queue_length / service_rate_per_sec


def payload_transmission_time(payload_size_bytes: float, bandwidth_bps: float) -> float:
    """Thoi gian truyen tai payload (circuit description, ket qua do) qua mang."""
    if bandwidth_bps <= 0:
        return float("inf")
    return (payload_size_bytes * 8) / bandwidth_bps


def default_intra_dc_latency(datacenter, qnode=None, base_switch_delay: float = 0.001,
                              jitter_ms=(0.1, 0.5)) -> float:
    """
    Baseline mac dinh cho do tre noi bo (Datacenter Gateway -> QNode).

    - base_switch_delay: do tre co dinh qua switch noi bo (giay).
    - jitter_ms: dao dong ngau nhien nho (ms) mo phong tai tuc thoi trong DC.

    Day chi la baseline don gian de he thong chay duoc ngay. Khi Content 1
    can mo hinh thuc te hon (nhieu hop, bang thong tung switch), nen thay
    bang mo hinh graph-based, tuong tu cach networkx da duoc dung cho
    topology qubit trong qnode.py (co the tai su dung utility_functions/
    graph_manipulation.py cho phan nay).
    """
    jitter_s = random.uniform(*jitter_ms) / 1000.0
    return base_switch_delay + jitter_s


def total_end_to_end_latency(datacenter, qnode=None, queue_length: int = 0,
                              service_rate_per_sec: float = None,
                              payload_size_bytes: float = 0,
                              bandwidth_bps: float = None) -> float:
    """
    Tong hop toan bo do tre mang end-to-end, phuc vu tinh Turnaround Time
    (B2.1 - Optimizing End-to-end Turnaround Time):

        Total = WAN latency + Intra-DC latency + Queuing delay (neu co)
                + Payload transmission time (neu co)

    `datacenter` phai co thuoc tinh `distance_km` va phuong thuc
    `intra_dc_latency(qnode)` (xem class Datacenter trong datacenter.py).
    """
    # total = propagation_delay(datacenter.distance_km)
    total += datacenter.intra_dc_latency(qnode)
    if service_rate_per_sec is not None:
        total += queuing_delay(queue_length, service_rate_per_sec)
    if bandwidth_bps is not None:
        total += payload_transmission_time(payload_size_bytes, bandwidth_bps)
    return total