# Parse arguments
# Example: ./one-to-one.sh enp37s0f1
iface=${1:-enp37s0f1}

# No Optimisations
./network_setup.py $iface --no-lro --no-gso --no-gro --no-tso --no-arfs --config one-to-one --receiver --mtu 1500 --sock-size
for i in 8 16 24; do
        ./run_experiment_receiver.py --config one-to-one --num-connections $i --throughput --utilisation --cache-miss --util-breakdown --output results/one-to-one_${i}_no-opts | tee results/one-to-one_${i}_no-opts.log
done

# TSO/GRO
./network_setup.py $iface --gro --tso 
for i in 8 16 24; do
        ./run_experiment_receiver.py --config one-to-one --num-connections $i --throughput --utilisation --cache-miss --util-breakdown --output results/one-to-one_${i}_tsogro | tee results/one-to-one_${i}_tsogro.log
done

# TSO/GRO+Jumbo Frame
./network_setup.py $iface --mtu 9000
for i in 8 16 24; do
        ./run_experiment_receiver.py --config one-to-one --num-connections $i --throughput --utilisation --cache-miss --util-breakdown --output results/one-to-one_${i}_tsogro+jumbo | tee results/one-to-one_${i}_tsogro+jumbo.log
done

# TSO/GRO+Jumbo Frame+aRFS
./network_setup.py $iface --arfs
for i in 8 16 24; do
        ./run_experiment_receiver.py --config one-to-one --num-connections $i --throughput --utilisation --cache-miss --util-breakdown --arfs --output results/one-to-one_${i}_all-opts | tee results/one-to-one_${i}_all-opts.log
done
