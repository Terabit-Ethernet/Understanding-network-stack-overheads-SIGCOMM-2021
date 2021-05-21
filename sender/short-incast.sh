# Parse arguments
# Example: ./incast.sh 128.84.155.115 192.168.10.115 enp1
public_dst_ip=${1:-128.84.155.115}
device_dst_ip=${2:-192.168.10.115}
iface=${3:-enp37s0f1}

# No Optimisations
./network_setup.py $iface --no-lro --no-gso --no-gro --no-tso --mtu 1500 --sock-size --no-arfs --flow-type short --config incast --sender
for i in 4000 16000 32000 64000; do
        ./run_experiment_sender.py --addr $device_dst_ip --receiver $public_dst_ip --config incast --flow-type short --rpc-size $i --num-connections 16 --throughput --utilisation --util-breakdown --output results/short-incast_16_${i}_no-opts | tee results/short-incast_16_${i}_no-opts.log
done

# TSO/GRO
./network_setup.py $iface --gro --tso
for i in 4000 16000 32000 64000; do
        ./run_experiment_sender.py --addr $device_dst_ip --receiver $public_dst_ip --config incast --flow-type short --rpc-size $i --num-connections 16 --throughput --utilisation --util-breakdown --output results/short-incast_16_${i}_tsogro | tee results/short-incast_16_${i}_tsogro.log
done

# TSO/GRO+Jumbo Frame
./network_setup.py $iface --mtu 9000
for i in 4000 16000 32000 64000; do
        ./run_experiment_sender.py --addr $device_dst_ip --receiver $public_dst_ip --config incast --flow-type short --rpc-size $i --num-connections 16 --throughput --utilisation --util-breakdown --output results/short-incast_16_${i}_tsogro+jumbo | tee results/short-incast_16_${i}_tsogro+jumbo.log
done

# TSO/GRO+Jumbo Frame+aRFS
./network_setup.py $iface --arfs
for i in 4000 16000 32000 64000; do
        ./run_experiment_sender.py --addr $device_dst_ip --receiver $public_dst_ip --config incast --flow-type short --rpc-size $i --num-connections 16 --throughput --utilisation --util-breakdown --arfs --output results/incast_${i}_all-opts | tee results/incast_${i}_all-opts.log
done
