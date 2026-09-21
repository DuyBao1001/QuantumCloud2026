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

        remove_connectivity(self, selected_vertices, 'red')

        
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
        if self.cali_filepath is None: 
            self.cali_filepath = 'QCloud/calibration/ibm_fez_calibrations_2025-01-13T16_54_24Z.csv'
            
        file_path = self.cali_filepath
        calibration_data = pd.read_csv(file_path)
        calibration_data.columns = calibration_data.columns.str.strip()

        readout_errors = calibration_data["Readout assignment error"].tolist()
        single_qubit_gate_errors = {
            "rx": calibration_data["RX error"].mean(),
            "x": calibration_data["Pauli-X error"].mean(),
        }
        two_qubit_gate_errors = {}
        for cz_errors in calibration_data["CZ error"]:
            pairs = cz_errors.split(";")
            for pair in pairs:
                gate, error = pair.split(":")
                two_qubit_gate_errors[gate] = float(error)

        return readout_errors, single_qubit_gate_errors, two_qubit_gate_errors

    def estimate_fidelity(self, task):
        """
        Estimate fidelity for a quantum task using IBM calibration data.
        """
        num_qubits = task.num_qubits
        depth = task.depth

        # Estimate single-qubit gate fidelity
        avg_single_qubit_error = self.single_qubit_gate_errors["rx"]
        single_qubit_fidelity = (1 - avg_single_qubit_error) ** depth

        # Estimate readout fidelity
        avg_readout_error = sum(self.readout_errors) / len(self.readout_errors)
        readout_fidelity = (1 - avg_readout_error) ** num_qubits

        # Combined fidelity
        estimated_fidelity = single_qubit_fidelity * readout_fidelity
        
        if hasattr(self, 'task_records_manager') and self.task_records_manager:
            self.task_records_manager.log_task_event(task.task_id, 'fidelity', round(estimated_fidelity,4))   
        return estimated_fidelity