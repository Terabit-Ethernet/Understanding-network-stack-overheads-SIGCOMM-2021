# Parse arguments
# Example: ./numa.sh enp37s0f1
iface=${1:-enp37s0f1}

# TSO/GRO+Jumbo Frame+aRFS
./network_setup.py $iface --gro --tso --mtu 9000 --sock-size --arfs

# Long Flow
./run_experiment_receiver.py --throughput --utilisation --cache-miss --arfs --output results/numa_long_all-opts_local | results/numa_long_all-opts_local.log
./run_experiment_receiver.py --throughput --cpus 1 --utilisation --cache-miss --arfs --output results/numa_long_all-opts_remote | results/numa_long_all-opts_remote.log

# Short Flow
./run_experiment_receiver.py --throughput --flow-type short --utilisation --cache-miss --arfs --output results/numa_short_all-opts_local | results/numa_long_all-opts_local.log
./run_experiment_receiver.py --throughput --flow-type short --cpus 1 --utilisation --cache-miss --arfs --output results/numa_short_all-opts_remote | results/numa_long_all-opts_remote.log
