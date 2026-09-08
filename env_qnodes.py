from qnode import IBM_QuantumDevice
class IBM_guadalupe(IBM_QuantumDevice):
    """
    IBM Guadalupe is one of IBM's quantum processors based on superconducting qubits.
    Source: https://quantum-computing.ibm.com/
    """
    def __init__(self, env, name=None, printlog=True):

        super().__init__(name = name if name else __class__.__name__ , 
                         nodes_file_name = 'IBM_guadalupe_nodes.json', 
                         pos_file_name = 'IBM_guadalupe_pos.json', 
                         env = env, 
                         maintenance_interval = 100, 
                         maintenance_duration = 15, 
                         maintenance_switch = False, 
                         clops=1400,  # Example value, need to update real data
                         qvol = 32,
                         median_T1=80,  # Example value in microseconds, need to update real data
                         median_T2=120,  # Example value in microseconds, need to update real data
                         processor_type="superconducting",
                         printlog=printlog)       
        
        
               
class IBM_tokyo(IBM_QuantumDevice):
    """
    IBM Tokyo is part of IBM's fleet of quantum processors. 
    It has been used for collaborative research with academic and industrial partners.
    Source: https://quantum-computing.ibm.com/
    """
    def __init__(self, env, name=None, printlog=True):   
        
        super().__init__(name = name if name else __class__.__name__ , 
                         nodes_file_name = 'IBM_tokyo_nodes.json', 
                         pos_file_name = 'IBM_tokyo_pos.json', 
                         env = env, 
                         maintenance_interval = 120, 
                         maintenance_duration = 15, 
                         maintenance_switch = False,
                         clops=1400,  # Example value, need to update real data
                         qvol = 32,
                         median_T1=80,  # Example value in microseconds, need to update real data
                         median_T2=120,  # Example value in microseconds, need to update real data
                         processor_type="superconducting",
                         printlog=printlog)       

                      
        
                
class IBM_montreal(IBM_QuantumDevice): 
    """
    IBM Montreal is a superconducting qubit-based quantum processor.
    Source: https://quantum-computing.ibm.com/
    """
    def __init__(self, env, name=None, printlog=True):    
                
        super().__init__(name = name if name else __class__.__name__ , 
                         nodes_file_name = 'IBM_montreal_nodes.json', 
                         pos_file_name = 'IBM_montreal_pos.json', 
                         env = env, 
                         maintenance_interval = 140, 
                         maintenance_duration = 25, 
                         maintenance_switch = False,
                         clops=1400,  # Example value, need to update real data
                         qvol = 32,
                         median_T1=80,  # Example value in microseconds, need to update real data
                         median_T2=120,  # Example value in microseconds, need to update real data
                         processor_type="superconducting",
                         printlog=printlog)       
        
   
           
class IBM_rochester(IBM_QuantumDevice):
    """
    IBM Rochester is one of the early quantum processors from IBM, 
    named after the city of Rochester, New York, where IBM has a 
    significant presence. It is primarily used for foundational 
    research in quantum computing and testing new quantum algorithms.
    Source: https://quantum-computing.ibm.com/
    """
    def __init__(self, env, name=None, printlog=True):    
        
        super().__init__(name = name if name else __class__.__name__ , 
                         nodes_file_name = 'IBM_rochester_nodes.json', 
                         pos_file_name = 'IBM_rochester_pos.json', 
                         env = env, 
                         maintenance_interval = 140, 
                         maintenance_duration = 25, 
                         maintenance_switch = False,
                         clops=1400,  # Example value, need to update real data
                         qvol = 32,
                         median_T1=80,  # Example value in microseconds, need to update real data
                         median_T2=120,  # Example value in microseconds, need to update real data
                         processor_type="superconducting",
                         printlog=printlog)       
  
        
        
class IBM_hummingbird(IBM_QuantumDevice):
    """
    IBM Hummingbird is a more advanced quantum processor, part of IBM's effort to scale up quantum computing capabilities significantly. It is designed for more complex quantum computations, exploring error correction techniques, and scaling towards practical quantum advantage.
    Source: https://quantum-computing.ibm.com/
    """
    def __init__(self, env, name=None, printlog=True):

        super().__init__(name = name if name else __class__.__name__ , 
                         nodes_file_name = 'IBM_hummingbird_nodes.json', 
                         pos_file_name = 'IBM_hummingbird_pos.json', 
                         env = env, 
                         maintenance_interval = 140, 
                         maintenance_duration = 25, 
                         maintenance_switch = False,
                         clops=1400,  # Example value, need to update real data
                         qvol = 128, # https://docs.quantum.ibm.com/guides/processor-types
                         median_T1=80,  # Example value in microseconds, need to update real data
                         median_T2=120,  # Example value in microseconds, need to update real data
                         processor_type="superconducting",
                         printlog=printlog)                   

### IBM machines that are online as of 01-26-2025        
        
class IBM_Marrakesh(IBM_QuantumDevice):
    """
    Source: https://quantum.ibm.com/services/resources
    """
    def __init__(self, env, name=None, printlog=True):     
                
        super().__init__(name = name if name else __class__.__name__ , 
                         nodes_file_name = 'IBM_heron_r2_nodes.json', 
                         pos_file_name = 'IBM_heron_r2_pos.json', 
                         env = env, 
                         maintenance_interval = 180, # randomly assigned minutes 
                         maintenance_duration = 40, # randomly assigned minutes 
                         maintenance_switch = False,
                         clops=195000,  # updated real data on 01-26-2025
                         qvol = 128, # https://docs.quantum.ibm.com/guides/processor-types
                         median_T1=163.59,  # in microseconds, updated real data on 12-8-2024
                         median_T2=108.55,  # in microseconds, updated real data on 12-8-2024
                         processor_type="Heron r2",
                         printlog=printlog)      

        
        
class IBM_Fez(IBM_QuantumDevice):
    """
    Source: https://quantum.ibm.com/services/resources
    """
    def __init__(self, env, name=None, printlog=True):     
                
        super().__init__(name = name if name else __class__.__name__ , 
                         nodes_file_name = 'IBM_heron_r2_nodes.json', 
                         pos_file_name = 'IBM_heron_r2_pos.json', 
                         env = env, 
                         maintenance_interval = 120, # randomly assigned minutes 
                         maintenance_duration = 60, # randomly assigned minutes 
                         maintenance_switch = False,
                         clops=195000,  # updated real data on 01-26-2025
                         qvol = 128, # https://docs.quantum.ibm.com/guides/processor-types
                         median_T1=110.89,  # in microseconds, updated real data on 12-8-2024
                         median_T2=91.27,  # in microseconds, updated real data on 12-8-2024
                         processor_type="Heron r2",
                         printlog=printlog)              

        

class IBM_Torino(IBM_QuantumDevice):
    """
    Source: https://quantum.ibm.com/services/resources
    """
    def __init__(self, env, name=None, printlog=True):     
                
        super().__init__(name = name if name else __class__.__name__ , 
                         nodes_file_name = 'IBM_heron_r1_nodes.json', 
                         pos_file_name = 'IBM_heron_r1_pos.json', 
                         env = env, 
                         maintenance_interval = 150, # randomly assigned minutes
                         maintenance_duration = 45, # randomly assigned minutes
                         maintenance_switch = False,
                         clops=210000,  # updated real data on 01-26-2025
                         qvol = 128, # https://docs.quantum.ibm.com/guides/processor-types
                         median_T1=170.21,  # in microseconds, updated real data on 12-8-2024
                         median_T2=134.5,  # in microseconds, updated real data on 12-8-2024
                         processor_type="Heron r1",
                         printlog=printlog)                

        
        
class IBM_Quebec(IBM_QuantumDevice):
    """
    Source: https://quantum.ibm.com/services/resources
    """
    def __init__(self, env, name=None, printlog=True):     
                
        super().__init__(name = name if name else __class__.__name__ , 
                         nodes_file_name = 'IBM_eagle_r3_nodes.json', 
                         pos_file_name = 'IBM_eagle_r3_pos.json', 
                         env = env, 
                         maintenance_interval = 150, # randomly assigned minutes
                         maintenance_duration = 45, # randomly assigned minutes
                         maintenance_switch = False,
                         clops=32000,  # updated real data on 01-26-2025
                         qvol = 128, # https://docs.quantum.ibm.com/guides/processor-types
                         median_T1=299.8,  # in microseconds, updated real data on 12-8-2024
                         median_T2=209.3,  # in microseconds, updated real data on 12-8-2024
                         processor_type="Eagle r3",
                         printlog=printlog)     

        
        

class IBM_Kyiv(IBM_QuantumDevice):
    """
    Source: https://quantum.ibm.com/services/resources
    """
    def __init__(self, env, name=None, printlog=True):     
                
        super().__init__(name = name if name else __class__.__name__ , 
                         nodes_file_name = 'IBM_eagle_r3_nodes.json', 
                         pos_file_name = 'IBM_eagle_r3_pos.json', 
                         env = env, 
                         maintenance_interval = 160, # randomly assigned minutes
                         maintenance_duration = 40, # randomly assigned minutes
                         maintenance_switch = False,
                         clops=30000,  # updated real data on 01-26-2025
                         qvol = 128, # https://docs.quantum.ibm.com/guides/processor-types
                         median_T1=185.7,  # in microseconds, updated real data on 12-8-2024
                         median_T2=146.38,  # in microseconds, updated real data on 12-8-2024
                         processor_type="Eagle r3",
                         printlog=printlog)    
        
        
        
class IBM_Brisbane(IBM_QuantumDevice):
    """
    Source: https://quantum.ibm.com/services/resources
    """
    def __init__(self, env, name=None, printlog=True):     
                
        super().__init__(name = name if name else __class__.__name__ , 
                         nodes_file_name = 'IBM_eagle_r3_nodes.json', 
                         pos_file_name = 'IBM_eagle_r3_pos.json', 
                         env = env, 
                         maintenance_interval = 180, # randomly assigned minutes
                         maintenance_duration = 60, # randomly assigned minutes
                         maintenance_switch = False,
                         clops=180000,  # updated real data on 01-26-2025
                         qvol = 128, # https://docs.quantum.ibm.com/guides/processor-types
                         median_T1=212.07,  # in microseconds, updated real data on 12-8-2024
                         median_T2=124.65,  # in microseconds, updated real data on 12-8-2024
                         processor_type="Eagle r3",
                         printlog=printlog)    

        
        
        
class IBM_Sherbrooke(IBM_QuantumDevice):
    """
    Source: https://quantum.ibm.com/services/resources
    """
    def __init__(self, env, name=None, printlog=True):     
                
        super().__init__(name = name if name else __class__.__name__ , 
                         nodes_file_name = 'IBM_eagle_r3_nodes.json', 
                         pos_file_name = 'IBM_eagle_r3_pos.json', 
                         env = env, 
                         maintenance_interval = 120, # randomly assigned minutes
                         maintenance_duration = 40, # randomly assigned minutes
                         maintenance_switch = False,
                         clops=30000,  # updated real data on 01-26-2025
                         qvol = 128, # https://docs.quantum.ibm.com/guides/processor-types
                         median_T1=269.72,  # in microseconds, updated real data on 12-8-2024
                         median_T2=159.98,  # in microseconds, updated real data on 12-8-2024
                         processor_type="Eagle r3",
                         printlog=printlog)    
        
        
        
        
class IBM_Kawasaki(IBM_QuantumDevice):
    """
    Source: https://quantum.ibm.com/services/resources
    """
    def __init__(self, env, name=None, printlog=True):     
                
        super().__init__(name = name if name else __class__.__name__ , 
                         nodes_file_name = 'IBM_eagle_r3_nodes.json', 
                         pos_file_name = 'IBM_eagle_r3_pos.json', 
                         env = env, 
                         maintenance_interval = 140, # randomly assigned minutes
                         maintenance_duration = 40, # randomly assigned minutes
                         maintenance_switch = False,
                         clops=29000,  # updated real data on 01-26-2025
                         qvol = 128, # https://docs.quantum.ibm.com/guides/processor-types
                         median_T1=185.7,  # in microseconds, updated real data on 12-8-2024
                         median_T2=146.38,  # in microseconds, updated real data on 12-8-2024
                         processor_type="Eagle r3",
                         printlog=printlog)    
        
         
        
class IBM_Rensselaer(IBM_QuantumDevice):
    """
    Source: https://quantum.ibm.com/services/resources
    """
    def __init__(self, env, name=None, printlog=True):     
                
        super().__init__(name = name if name else __class__.__name__ , 
                         nodes_file_name = 'IBM_eagle_r3_nodes.json', 
                         pos_file_name = 'IBM_eagle_r3_pos.json', 
                         env = env, 
                         maintenance_interval = 120, # randomly assigned minutes
                         maintenance_duration = 30, # randomly assigned minutes
                         maintenance_switch = False,
                         clops=32000,  # updated real data on 01-26-2025
                         qvol = 128, # https://docs.quantum.ibm.com/guides/processor-types
                         median_T1=232.22,  # in microseconds, updated real data on 12-8-2024
                         median_T2=158.19,  # in microseconds, updated real data on 12-8-2024
                         processor_type="Eagle r3",
                         printlog=printlog)    
        
        

class IBM_Brussels(IBM_QuantumDevice):
    """
    Source: https://quantum.ibm.com/services/resources
    """
    def __init__(self, env, name=None, printlog=True):     
                
        super().__init__(name = name if name else __class__.__name__ , 
                         nodes_file_name = 'IBM_eagle_r3_nodes.json', 
                         pos_file_name = 'IBM_eagle_r3_pos.json', 
                         env = env, 
                         maintenance_interval = 160, # randomly assigned minutes
                         maintenance_duration = 40, # randomly assigned minutes
                         maintenance_switch = False,
                         clops=220000,  # updated real data on 01-26-2025
                         qvol = 128, # https://docs.quantum.ibm.com/guides/processor-types
                         median_T1=308.18,  # in microseconds, updated real data on 12-8-2024
                         median_T2=177.36,  # in microseconds, updated real data on 12-8-2024
                         processor_type="Eagle r3",
                         printlog=printlog)    
        
        
        
class IBM_Strasbourg(IBM_QuantumDevice):
    """
    Source: https://quantum.ibm.com/services/resources
    """
    def __init__(self, env, name=None, printlog=True):     
                
        super().__init__(name = name if name else __class__.__name__ , 
                         nodes_file_name = 'IBM_eagle_r3_nodes.json', 
                         pos_file_name = 'IBM_eagle_r3_pos.json', 
                         env = env, 
                         maintenance_interval = 180, # randomly assigned minutes
                         maintenance_duration = 60, # randomly assigned minutes
                         maintenance_switch = False,
                         clops=220000,  # updated real data on 01-26-2025
                         qvol = 128, # https://docs.quantum.ibm.com/guides/processor-types
                         median_T1=280.84,  # in microseconds, updated real data on 12-8-2024
                         median_T2=143.8,  # in microseconds, updated real data on 12-8-2024
                         processor_type="Eagle r3",
                         printlog=printlog)    
        
        
        
class Amazon_dwave(QuantumDevice):
    """
    The D-Wave QPU is a lattice of interconnected qubits. While some qubits connect to others via couplers, the D-Wave QPU is not fully connected. Instead, the qubits of D-Wave annealing quantum computers interconnect in one of the following topologies:

    Pegasus: 14-1026 Next-Generation Topology of D-Wave Quantum Processors
    https://www.dwavesys.com/media/jwwj5z3z/14-1026a-c_next-generation-topology-of-dw-quantum-processors.pdf?_gl=1*sl9028*_gcl_au*NDI1MTIwMzY4LjE3MjI1NDgzNTk.*_ga*OTk3MzI5MzA0LjE3MjI1NDgzNTk.*_ga_DXNKH9HE3W*MTcyMjU3MDMwOC4yLjEuMTcyMjU3MDM3Ni42MC4wLjA.

    Zephyr: 14-1056 Zephyr Topology of D-Wave Quantum Processors
    https://www.dwavesys.com/media/2uznec4s/14-1056a-a_zephyr_topology_of_d-wave_quantum_processors.pdf?_gl=1*sl9028*_gcl_au*NDI1MTIwMzY4LjE3MjI1NDgzNTk.*_ga*OTk3MzI5MzA0LjE3MjI1NDgzNTk.*_ga_DXNKH9HE3W*MTcyMjU3MDMwOC4yLjEuMTcyMjU3MDM3Ni42MC4wLjA.

    Source: https://docs.dwavesys.com/docs/latest/c_gs_4.html
    """
    def __init__(self, env, name=None, printlog=True):     
        
        super().__init__(name = name if name else __class__.__name__ , 
                         nodes_file_name = 'Amazon_dwave_nodes.json', 
                         pos_file_name = 'Amazon_dwave_pos.json', 
                         env = env, 
                         maintenance_interval = 140, 
                         maintenance_duration = 25, 
                         maintenance_switch = False,
                         printlog=printlog)     
        
        
        
        
class Chimera_dwave_72(QuantumDevice):
    """
    The Chimera topology is a specific layout of qubits used in D-Wave quantum annealers. It is designed to optimize the interconnectivity between qubits while maintaining a scalable and manufacturable architecture [1]. 

    Reference: [1] Ayanzadeh, Ramin & Mousavi, Ahmad & Halem, Milton & Finin, Tim. (2018). Quantum Annealing Based Binary Compressive Sensing with Matrix Uncertainty. 

    Source: https://www.researchgate.net/figure/Chimera-Topology-in-D-Wave-Quantum-Annealers_fig1_330102244
    
    """
    
    def __init__(self, env, name=None, printlog=True):

        super().__init__(name = name if name else __class__.__name__ , 
                         nodes_file_name = 'Chimera_dwave_72_nodes.json', 
                         pos_file_name = 'Chimera_dwave_72_pos.json', 
                         env = env, 
                         maintenance_interval = 200, 
                         maintenance_duration = 25, 
                         maintenance_switch = False,
                         printlog=printlog)     
   
  

class Chimera_dwave_128(QuantumDevice):
    """

    The Chimera topology is a specific layout of qubits used in D-Wave quantum annealers. It is designed to optimize the interconnectivity between qubits while maintaining a scalable and manufacturable architecture [1]. 

    Reference: [1] Ayanzadeh, Ramin & Mousavi, Ahmad & Halem, Milton & Finin, Tim. (2018). Quantum Annealing Based Binary Compressive Sensing with Matrix Uncertainty. 

    Source: https://www.researchgate.net/figure/Chimera-Topology-in-D-Wave-Quantum-Annealers_fig1_330102244
    
    """
    
    def __init__(self, env, name=None, printlog=True):

        super().__init__(name = name if name else __class__.__name__ , 
                         nodes_file_name = 'Chimera_dwave_128_nodes.json', 
                         pos_file_name = 'Chimera_dwave_128_pos.json', 
                         env = env, 
                         maintenance_interval = 250, 
                         maintenance_duration = 40, 
                         maintenance_switch = False,
                         printlog=printlog)     
        
        
               
class Amazon_rigetti(QuantumDevice):
    """
    The Rigetti quantum computer is one of the quantum processing units (QPUs) available through Amazon Braket, AWS's quantum computing service. The Rigetti QPUs use superconducting qubits, which are a popular choice for building quantum computers due to their scalability and relatively high coherence times. 

    References: 
    Amazon Braket - Quantum Computers https://aws.amazon.com/braket/
    Rigetti Computing - Quantum Cloud Services https://docs.rigetti.com/qcs
    Amazon Braket – Go Hands-On with Quantum Computing https://aws.amazon.com/blogs/aws/amazon-braket-go-hands-on-with-quantum-computing/

    """
    def __init__(self, env, name=None, printlog=True):

        super().__init__(name = name if name else __class__.__name__ , 
                         nodes_file_name = 'Amazon_rigetti_nodes.json', 
                         pos_file_name = 'Amazon_rigetti_pos.json', 
                         env = env, 
                         maintenance_interval = 250, 
                         maintenance_duration = 40, 
                         maintenance_switch = False,
                         printlog=printlog)     
        
        
               
class Google_sycamore(QuantumDevice):
    """
    The Sycamore quantum computer is a quantum processor developed by Google AI Quantum. The Sycamore processor uses superconducting qubits arranged in a two-dimensional grid. Each qubit is connected to four nearest neighbors, which allows for high connectivity and complex interactions needed for quantum computations.

    The processor utilizes a combination of single-qubit and two-qubit gates to perform quantum operations. The fidelity (accuracy) of these gates is crucial for the performance of the quantum computer, with single-qubit gate fidelities exceeding 99.9% and two-qubit gate fidelities around 99.4% [1].

    The Sycamore quantum computer leverages transmon qubits, which can be considered as nonlinear superconducting resonators functioning at 5 to 7 GHz. The quantum bits are encoded as the resonant circuit’s two lowest quantum eigenstates. 

    Reference: [1] AbuGhanem, M., Eleuch, H. Full quantum tomography study of Google’s Sycamore gate on IBM’s quantum computers. EPJ Quantum Technol. 11, 36 (2024). https://doi.org/10.1140/epjqt/s40507-024-00248-8

    Source: https://epjquantumtechnology.springeropen.com/articles/10.1140/epjqt/s40507-024-00248-8
    """
    
    def __init__(self, env, name=None, printlog=True):

        super().__init__(name = name if name else __class__.__name__ , 
                         nodes_file_name = 'Google_sycamore_nodes.json', 
                         pos_file_name = 'Google_sycamore_pos.json', 
                         env = env, 
                         maintenance_interval = 150, 
                         maintenance_duration = 20, 
                         maintenance_switch = False,
                         printlog=printlog)    


class Google_sycamore_53(QuantumDevice):
    """
    The Sycamore 
    quantum computer is a quantum processor developed by Google AI Quantum. The Sycamore processor uses superconducting qubits arranged in a two-dimensional grid. Each qubit is connected to four nearest neighbors, which allows for high connectivity and complex interactions needed for quantum computations.

    The processor utilizes a combination of single-qubit and two-qubit gates to perform quantum operations. The fidelity (accuracy) of these gates is crucial for the performance of the quantum computer, with single-qubit gate fidelities exceeding 99.9% and two-qubit gate fidelities around 99.4% [1].

    The Sycamore quantum computer leverages transmon qubits, which can be considered as nonlinear superconducting resonators functioning at 5 to 7 GHz. The quantum bits are encoded as the resonant circuit’s two lowest quantum eigenstates. 

    Reference: [1] AbuGhanem, M., Eleuch, H. Full quantum tomography study of Google’s Sycamore gate on IBM’s quantum computers. EPJ Quantum Technol. 11, 36 (2024). https://doi.org/10.1140/epjqt/s40507-024-00248-8

    Source: https://epjquantumtechnology.springeropen.com/articles/10.1140/epjqt/s40507-024-00248-8
    """
    
    def __init__(self, env, name=None, printlog=True):

        super().__init__(name = name if name else __class__.__name__ , 
                         nodes_file_name = 'Google_sycamore_53_nodes.json', 
                         pos_file_name = 'Google_sycamore_53_pos.json', 
                         env = env, 
                         maintenance_interval = 140, 
                         maintenance_duration = 25, 
                         maintenance_switch = False,
                         printlog=printlog)    
        