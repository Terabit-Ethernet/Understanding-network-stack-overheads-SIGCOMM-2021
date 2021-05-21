# Parse arguments 
# Example: ./numa.sh 128.84.155.115 192.168.10.115 enp37s0f1
public_dst_ip=${1:-128.84.155.115}
device_dst_ip=${2:-192.168.10.115}
iface=${3:-enp37s0f1}

# TSO/GRO+Jumbo Frame+aRFS
./network_setup.py $iface --gro --tso --arfs --mtu 9000 --sock-size

# Long Flow
./run_experiment_sender.py --receiver $public_dst_ip --addr $device_dst_ip --throughput --utilisation --cache-miss --arfs --output results/numa_long_all-opts_local | results/numa_long_all-opts_local.log
./run_experiment_sender.py --receiver $public_dst_ip --addr $device_dst_ip --throughput --cpus 1 --utilisation --cache-miss --arfs --output results/numa_long_all-opts_remote | results/numa_long_all-opts_remote.log

# Short Flow
./run_experiment_sender.py --receiver $public_dst_ip --addr $device_dst_ip --throughput --flow-type short --utilisation --cache-miss --arfs --output results/numa_short_all-opts_local | results/numa_long_all-opts_local.log
./run_experiment_sender.py --receiver $public_dst_ip --addr $device_dst_ip --throughput --flow-type short --cpus 1 --utilisation --cache-miss --arfs --output results/numa_short_all-opts_remote | results/numa_long_all-opts_remote.log

