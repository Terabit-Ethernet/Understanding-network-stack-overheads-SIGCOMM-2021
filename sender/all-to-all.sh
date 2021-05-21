# Parse arguments 
# Example: ./all-to-all.sh 128.84.155.115 192.168.10.115 enp37s0f1
public_dst_ip=${1:-128.84.155.115}
device_dst_ip=${2:-192.168.10.115}
iface=${3:-enp37s0f1}

# Increase the number of open files
ulimit -n 2048

# No Optimisations
./network_setup.py $iface --no-lro --no-gso --no-gro --no-tso --no-arfs --sender --config all-to-all --mtu 1500 --sock-size
for i in 8 16 24; do
        ./run_experiment_sender.py --addr $device_dst_ip --receiver $public_dst_ip --config all-to-all --num-connections $i --throughput --utilisation --cache-miss --util-breakdown --output results/all-to-all_${i}_no-opts | tee results/all-to-all_${i}_no-opts.log
done

# TSO/GRO
./network_setup.py $iface --gro --tso
for i in 8 16 24; do
        ./run_experiment_sender.py --addr $device_dst_ip --receiver $public_dst_ip --config all-to-all --num-connections $i --throughput --utilisation --cache-miss --util-breakdown --output results/all-to-all_${i}_tsogro | tee results/all-to-all_${i}_tsogro.log
done

# TSO/GRO+Jumbo Frame
./network_setup.py $iface --mtu 9000
for i in 8 16 24; do
        ./run_experiment_sender.py --addr $device_dst_ip --receiver $public_dst_ip --config all-to-all --num-connections $i --throughput --utilisation --cache-miss --util-breakdown --output results/all-to-all_${i}_tsogro+jumbo | tee results/all-to-all_${i}_tsogro+jumbo.log
done

# TSO/GRO+Jumbo Frame+aRFS
./network_setup.py $iface --arfs
for i in 8 16 24; do
        ./run_experiment_sender.py --addr $device_dst_ip --receiver $public_dst_ip --config all-to-all --num-connections $i --throughput --utilisation --cache-miss --util-breakdown --arfs --output results/all-to-all_${i}_all-opts | tee results/all-to-all_${i}_all-opts.log
done
