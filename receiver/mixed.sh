# Parse arguments
# Example: ./mixed-loss.sh enp37s0f1
iface=${1:-enp37s0f1}

# No Optimisations
./network_setup.py $iface --no-lro --no-gso --no-gro --no-tso --no-arfs --receiver --flow-type mixed --mtu 1500 --sock-size
for i in 1 4 16; do
    ./run_experiment_receiver.py --flow-type mixed --num-rpcs $i --throughput --utilisation --util-breakdown --output results/mixed_no-opts_${i} | results/mixed_no-opts_${i}.log
done

# TSO/GRO
./network_setup.py $iface --gro --tso
for i in 1 4 16; do
    ./run_experiment_receiver.py --flow-type mixed --num-rpcs $i --throughput --utilisation --util-breakdown --output results/mixed_tsogro_${i} | results/mixed_tsogro_${i}.log
done

# TSO/GRO+Jumbo Frame
./network_setup.py $iface --mtu 9000
for i in 1 4 16; do
    ./run_experiment_receiver.py --flow-type mixed --num-rpcs $i --throughput --utilisation --util-breakdown --output results/mixed_tsogro+jumbo_${i} | results/mixed_tsogro+jumbo_${i}.log
done

# TSO/GRO+Jumbo Frame+aRFS
./network_setup.py $iface --arfs
for i in 1 4 16; do
    ./run_experiment_receiver.py --flow-type mixed --num-rpcs $i --throughput --utilisation --util-breakdown --arfs --output results/mixed_all-opts_${i} | results/mixed_all-opts_${i}.log
done

