# System Constants

# In the default IRQ affinity config mode
# ID of the RX queue for each CPU 0-23
CPU_TO_RX_QUEUE_MAP = [0, 6, 7, 8, 1, 9, 10, 11, 2, 12, 13, 14, 3, 15, 16, 17, 4, 18, 19, 20, 5, 21, 22, 23]

# DDIO IO WAYS LLC mm register location
DDIO_REG = 0xc8b

# Port for running the coordination service
COMM_PORT = 50000

# Base port of using iperf and netperf
BASE_PORT = 30000
ADDITIONAL_BASE_PORT = 40000

# Maximum number of ntuple filters
MAX_RULE_LOC = 1023

# Maximum number of CPUs/connections
# NOTE: This should be the same as number of CPUs
MAX_CPUS = 24
CPUS = list(range(MAX_CPUS))
MAX_CONNECTIONS = MAX_CPUS
MAX_RPCS = 24

# Path to executables of profiling tools
PERF_PATH = "/usr/bin/perf"
FLAME_PATH = "/opt/FlameGraph"

