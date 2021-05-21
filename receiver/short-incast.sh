# Parse arguments
# Example: ./short-incast.sh enp37s0f1
iface=${1:-enp37s0f1}

# No Optimisations
./network_setup.py $iface --no-lro --no-gso --no-gro --no-tso --mtu 1500 --sock-size --no-arfs --flow-type short --config incast --receiver
for i in 4000 16000 32000 64000; do
        ./run_experiment_receiver.py --config incast --flow-type short --num-connections 16 --throughput --utilisation --util-breakdown --output results/short-incast_16_${i}_no-opts | tee results/short-incast_16_${i}_no-opts.log
done

# TSO/GRO
./network_setup.py $iface --gro --tso
for i in 4000 16000 32000 64000; do
        ./run_experiment_receiver.py --config incast --flow-type short --num-connections 16 --throughput --utilisation --util-breakdown --output results/short-incast_16_${i}_tsogro | tee results/short-incast_16_${i}_tsogro.log
done

# TSO/GRO+Jumbo Frame
./network_setup.py $iface --mtu 9000
for i in 4000 16000 32000 64000; do
        ./run_experiment_receiver.py --config incast --flow-type short --num-connections 16 --throughput --utilisation --util-breakdown --output results/short-incast_16_${i}_tsogro+jumbo | tee results/short-incast_16_${i}_tsogro+jumbo.log
done

# TSO/GRO+Jumbo Frame+aRFS
./network_setup.py $iface --arfs
for i in 4000 16000 32000 64000; do
        ./run_experiment_receiver.py --config incast --flow-type short --num-connections 16 --throughput --utilisation --util-breakdown --arfs --output results/incast_${i}_all-opts | tee results/incast_${i}_all-opts.log
done
