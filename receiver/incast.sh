iface=$1
# No Optimisations
./network_setup.py $iface --no-lro --no-gso --no-gro --no-tso --mtu 1500 --sock-size  --no-arfs --config incast --receiver
for i in 1 2 4 8; do
        ./run_experiment_receiver.py --config incast --num-connections $i --throughput --utilisation --cache-miss --output results/incast_${i}_no-opts | tee results/incast_${i}_no-opts.log
done

# TSO/GRO
./network_setup.py $iface --gro --tso
for i in 1 2 4 8; do
        ./run_experiment_receiver.py --config incast --num-connections $i --throughput --utilisation --cache-miss --output results/incast_${i}_tsogro | tee results/incast_${i}_tsogro.log
done

# TSO/GRO+Jumbo Frame
./network_setup.py $iface --mtu 9000
for i in 1 2 4 8; do
        ./run_experiment_receiver.py --config incast --num-connections $i --throughput --utilisation --cache-miss --output results/incast_${i}_tsogro+jumbo | tee results/incast_${i}_tsogro+jumbo.log
done

# TSO/GRO+Jumbo Frame+aRFS
./network_setup.py $iface --arfs
for i in 1 2 4 8; do
        ./run_experiment_receiver.py --config incast --num-connections $i --throughput --utilisation --cache-miss --util-breakdown --arfs --output results/incast_${i}_all-opts | tee results/incast_${i}_all-opts.log
done
