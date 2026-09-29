import os
import json
import math
import random
from abc import ABC, abstractmethod

import simpy
import networkx as nx
import pandas as pd

from utility_functions.graph_manipulation import *

class BaseQNode(ABC):
    """
    Abstract base class for quantum devices.
    """
    def __init__(self, name, env, event_bus):
        """
        Initialize a base device.

        Parameters:
        - name (str): Name of the quantum device.
        - env (simpy.Environment): The simulation environment.
        - event_bus (EventBus): EventBus instance for event-driven communication.
        """
        self.name = name
        self.env = env
        self.event_bus = event_bus

    @abstractmethod
    def process_task(self, task, wait_time_start=0):
        """
        Abstract method for processing a task on the device.
        """
        pass

    @abstractmethod
    def maintenance(self):
        """
        Abstract method for performing maintenance on the device.
        """
        pass

    @abstractmethod
    def calculate_process_time(self, task):
        """
        Abstract method to calculate the processing time for a task.
        """
        pass
    

class QuantumDevice(BaseQNode):
    """
    QuantumDevice is a class representing a quantum computing device with a specific topology.
    """

    def __init__(self, name, nodes_file_name, pos_file_name, env, maintenance_interval, maintenance_duration, maintenance_switch, event_bus=None, task_records_manager=None, printlog=True):
        super().__init__(name=name, env=env, event_bus=event_bus)
        self.name = name
        self.env = env    
        self.maintenance_interval = maintenance_interval
        self.maintenance_duration = maintenance_duration
        self.maintenance_switch = maintenance_switch
        self.task_records_manager = task_records_manager
        self.event_bus = event_bus
        self.printlog = printlog

        # Load nodes and positions from files
        self.nodes, self.pos = self.load_topology(nodes_file_name, pos_file_name)
        
        # number of qubits calculated from position dictionary
        self.number_of_qubits = len(self.pos)
        
        # generate the color_map as 'skyblue' for each qubit
        self.color_map = ['skyblue' for _ in range(self.number_of_qubits)]
        
        # Initialize the graph with nodes
        self.graph = nx.Graph()
        self.graph.add_edges_from(self.nodes)
        
        # Initialize the simpy container and resource
        self.container = simpy.Container(env=self.env, capacity=len(self.pos), init=len(self.pos))
        self.resource = simpy.PriorityResource(env=self.env, capacity=1)
        self.maint_lock = False
        
    def assign_env(self, env):
        """
        Assigns a SimPy environment and initializes SimPy-dependent attributes.
        """
        self.env = env
        self.container = simpy.Container(env=env, capacity=len(self.pos), init=len(self.pos))
        self.resource = simpy.PriorityResource(env=env, capacity=1)

        # Start maintenance process if required
        if self.maintenance_switch:
            self.env.process(self.maintenance())
            
    def load_topology(self, nodes_file_name, pos_file_name):
        
        """Loads the nodes and positions from the specified JSON files."""
        
        # Get the directory of the current file
        current_dir = os.path.dirname(os.path.abspath(__file__))  
        topology_dir = os.path.join(current_dir, 'topology')
        nodes_file = os.path.join(topology_dir, nodes_file_name)
        pos_file = os.path.join(topology_dir, pos_file_name)
        
        with open(nodes_file, 'r') as f:
            nodes = json.load(f)['nodes']
     
        with open(pos_file, 'r') as f:
            pos = {int(k): tuple(v) for k, v in json.load(f)['pos'].items()}
        
        return nodes, pos
    
    def maintenance(self): 
        """
        Maintenance process that will run at regular intervals.
        The interval and duration of maintenance are set by the child class.
        """
        yield self.env.timeout(random.randint(60, 120))
        
        if self.maintenance_switch: 
            while True:
                # Wait for the maintenance interval
                yield self.env.timeout(self.maintenance_interval)
                             
                # New task won't be able to process on the machine
                self.maint_lock = True
                
                # Block the resource during maintenance with highest priority (priority=1)
                with self.resource.request(priority=1) as req:

                    remaining_qubits = self.container.level                                                   
                    yield self.env.timeout(self.maintenance_duration)

                    # task will be able to assign the machine again
                    self.maint_lock = False
            
    def calculate_process_time(self, task):
        """Simple way to calculate the processing time based on the number of qubits required.
            Child class will override this"""
        if self.printlog:
            print(f"{self.env.now:.2f}: Calculating process time for {task.num_qubits} qubits on {self.name}.")
        return task.num_qubits * 100

    def process_task(self, task, wait_time_start=0): 
        
        task_id = task.task_id 
        qubits_required = task.num_qubits
        """Process a task on this quantum device."""
        if self.printlog:
            print(f"{self.env.now:.2f}: {self.name} received task #{task_id} requiring {qubits_required} qubits.")
        
        # Log task start processing
        if self.task_records_manager:
            self.task_records_manager.log_task_event(task_id, 'devc_name', self.name)
            self.task_records_manager.log_task_event(task_id, 'devc_start', round(self.env.now,4))
        
        # Publish a 'device_start' event
        if self.event_bus:
            self.event_bus.publish("device_start", {
                "device": self.name,
                "task_id": task_id,
                "timestamp": round(self.env.now, 2),
            })
        
        selected_vertices = select_vertices_fast(self, qubits_required, task_id)

        while selected_vertices is None or self.maint_lock:
            if self.printlog:
                print(f"{self.env.now:.2f}: Task #{task_id} is waiting for {self.name}.")
            yield self.env.timeout(1)  # Wait before retrying
            selected_vertices = select_vertices_fast(self, qubits_required, task_id)

        yield self.container.get(qubits_required)
        remove_connectivity(self, selected_vertices, 'red')

        task.start_time = self.env.now
        task.assigned_device = self.name
        task.assigned_qubits = list(selected_vertices)
        
        process_time = self.calculate_process_time(task)
        if self.printlog:
            print(f"{self.env.now:.2f}: Task #{task_id} will take {process_time:.4f} sim-mins on {self.name}.")
        
        yield self.env.timeout(process_time)
        

        # Log task finish processing
        if self.task_records_manager:
            self.task_records_manager.log_task_event(task_id, 'devc_finish', round(self.env.now,4))
        
        
        # Publish a 'device_finish' event
        if self.event_bus:
            self.event_bus.publish("device_finish", {
                "device": self.name,
                "task_id": task_id,
                "timestamp": round(self.env.now, 2),
            })
        
        task.finish_time = self.env.now
        task.qpu_time = process_time
        
        yield self.container.put(qubits_required)
        reconnect_nodes(self, selected_vertices)
        if self.printlog:
            print(f"{self.env.now:.2f}: Task #{task_id} completed on {self.name}.")
    
    def estimate_fidelity(self, task):
        pass
            
class IBM_QuantumDevice(QuantumDevice):
    """
    A base class for IBM quantum devices that defines common attributes.
    """

    def __init__(self, name, nodes_file_name, pos_file_name, env, maintenance_interval, maintenance_duration, maintenance_switch, clops, qvol, median_T1, median_T2, processor_type, event_bus=None, task_records_manager=None, cali_filepath=None, printlog=True):
        
        super().__init__(
            name=name,
            nodes_file_name=nodes_file_name,
            pos_file_name=pos_file_name,
            env=env,
            maintenance_interval=maintenance_interval,
            maintenance_duration=maintenance_duration,
            maintenance_switch=maintenance_switch,
            event_bus=event_bus,
            task_records_manager=task_records_manager,
            printlog=printlog
        )
        
        # IBM-specific attributes
        self.clops = clops  # Circuit Layer Operations Per Second
        self.qvol = qvol # Quantum Volume
        self.median_T1 = median_T1  # Median T1 time in microseconds
        self.median_T2 = median_T2  # Median T2 time in microseconds
        self.processor_type = processor_type  # Type of quantum processor
        self.cali_filepath = cali_filepath # Calibration file path
        self.printlog = printlog
        self.readout_errors, self.single_qubit_gate_errors, self.two_qubit_gate_errors = self.extract_errors_from_csv()

    def calculate_process_time(self, task):
        """
        Calculate processing time considering IBM-specific metrics.
        """
        M = 100
        K = 10
        S = task.num_shots
        D = math.log2(self.qvol)

        return  M * K * S * D / self.clops / 60
    
    def extract_errors_from_csv(self):
        """
        Extract errors specific to IBM devices from calibration data.
        """
        current_dir = os.path.dirname(os.path.abspath(__file__))
        cali_dir = os.path.join(current_dir, 'calibration')
        
        if self.cali_filepath is None:
            # Try to auto-match calibration file based on device name
            matched_file = 'ibm_fez_calibrations_2025-01-13T16_54_24Z.csv' # Fallback
            device_id = self.__class__.__name__.lower().replace("ibm_", "")
            if os.path.exists(cali_dir):
                for fname in os.listdir(cali_dir):
                    if device_id in fname and fname.endswith(".csv"):
                        matched_file = fname
                        break
            file_path = os.path.join(cali_dir, matched_file)
        else:
            # Handle old hardcoded paths gracefully
            if "QCloud/calibration" in self.cali_filepath:
                fname = os.path.basename(self.cali_filepath)
                file_path = os.path.join(cali_dir, fname)
            else:
                file_path = self.cali_filepath
            
        calibration_data = pd.read_csv(file_path)
        calibration_data.columns = calibration_data.columns.str.strip()

        readout_errors = []
        if "Readout assignment error" in calibration_data.columns:
            readout_errors = calibration_data["Readout assignment error"].dropna().tolist()

        rx_col = next((c for c in ["RX error", "√x (sx) error", "SX error", "Pauli-X error"] if c in calibration_data.columns), None)
        x_col = next((c for c in ["Pauli-X error", "x error"] if c in calibration_data.columns), None)
        
        single_qubit_gate_errors = {
            "rx": calibration_data[rx_col].mean() if rx_col else 0.001,
            "x": calibration_data[x_col].mean() if x_col else 0.001,
        }

        two_qubit_gate_errors = {}
        two_q_col = next((c for c in ["CZ error", "ECR error"] if c in calibration_data.columns), None)
        if two_q_col:
            for gate_errors in calibration_data[two_q_col].dropna():
                pairs = str(gate_errors).split(";")
                for pair in pairs:
                    if ":" in pair:
                        gate, error = pair.split(":")
                        try:
                            two_qubit_gate_errors[gate.strip()] = float(error.strip())
                        except ValueError:
                            pass

        return readout_errors, single_qubit_gate_errors, two_qubit_gate_errors

    def estimate_fidelity(self, task):
        """
        Estimate fidelity for a quantum task using IBM calibration data and precise gate counts.
        """
        # Trích xuất profile số lượng cổng (từ phiên bản task_generator mới)
        gates_profile = getattr(task, 'gates', {})
        
        # Nếu task được sinh từ generator cũ không có dictionary gates, dùng fallback xấp xỉ
        if not isinstance(gates_profile, dict):
            num_1q = task.depth * task.num_qubits * 0.5
            num_2q = task.depth * task.num_qubits * 0.1
            num_meas = task.num_qubits
        else:
            num_1q = gates_profile.get("1q_gates", task.depth * task.num_qubits * 0.5)
            num_2q = gates_profile.get("2q_gates", task.depth * task.num_qubits * 0.1)
            num_meas = gates_profile.get("measurements", task.num_qubits)

        # 1. Single-qubit gate fidelity
        # Ưu tiên lấy lỗi cổng X, nếu không có thì lấy RX (Mặc định 0.1%)
        avg_1q_error = self.single_qubit_gate_errors.get("x", self.single_qubit_gate_errors.get("rx", 0.001))
        fidelity_1q = (1 - avg_1q_error) ** num_1q

        # 2. Two-qubit gate fidelity (CZ hoặc ECR gate)
        if self.two_qubit_gate_errors:
            avg_2q_error = sum(self.two_qubit_gate_errors.values()) / len(self.two_qubit_gate_errors)
        else:
            avg_2q_error = 0.01  # Fallback 1%
        fidelity_2q = (1 - avg_2q_error) ** num_2q

        # 3. Readout/Measurement fidelity
        avg_meas_error = sum(self.readout_errors) / len(self.readout_errors) if self.readout_errors else 0.01
        fidelity_meas = (1 - avg_meas_error) ** num_meas

        # Combined Expected Fidelity = Tích của tất cả các xác suất thành công
        estimated_fidelity = fidelity_1q * fidelity_2q * fidelity_meas
        
        task.estimated_fidelity = estimated_fidelity
        
        if hasattr(self, 'task_records_manager') and self.task_records_manager:
            self.task_records_manager.log_task_event(task.task_id, 'fidelity', round(estimated_fidelity,4))   
        return estimated_fidelity