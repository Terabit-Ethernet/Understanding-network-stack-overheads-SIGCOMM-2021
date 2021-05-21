# Parse arguments 
# Example: ./tcp-buffer.sh 128.84.155.115 192.168.10.115 enp37s0f1
public_dst_ip=${1:-128.84.155.115}
device_dst_ip=${2:-192.168.10.115}
iface=${3:-enp37s0f1}

# TSO/GRO+Jumbo Frame+aRFS
./network_setup.py $iface --gro --tso --arfs --mtu 9000 --sock-size
for i in 100 200 400 800 1600 3200 6400 12800; do
    ./run_experiment_sender.py --receiver $public_dst_ip --addr $device_dst_ip --throughput --utilisation --cache-miss --latency --arfs --output results/tcp-buffer_all-opts_${i} | results/tcp-buffer_all-opts_${i}.log
done
