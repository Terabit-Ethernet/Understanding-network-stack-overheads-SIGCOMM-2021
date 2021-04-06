# No Optimisations
./network_setup.py enp37s0f1 --no-lro --no-gso --no-gro --no-tso --no-arfs --config all-to-all --receiver --mtu 1500 --sock-size
for i in 2 4 6 8 12; do
        ./run_experiment_receiver.py --config all-to-all --num-connections $i --throughput --utilisation --cache-miss --output results/all-to-all_${i}_no-opts | tee results/all-to-all_${i}_no-opts.log
done

# TSO/GRO
./network_setup.py enp37s0f1 --gro --tso 
for i in 2 4 6 8 12; do
        ./run_experiment_receiver.py --config all-to-all --num-connections $i --throughput --utilisation --cache-miss --output results/all-to-all_${i}_tsogro | tee results/all-to-all_${i}_tsogro.log
done

# TSO/GRO+Jumbo Frame
./network_setup.py enp37s0f1 --mtu 9000
for i in 2 4 6 8 12; do
        ./run_experiment_receiver.py --config all-to-all --num-connections $i --throughput --utilisation --cache-miss --output results/all-to-all_${i}_tsogro+jumbo | tee results/all-to-all_${i}_tsogro+jumbo.log
done

# TSO/GRO+Jumbo Frame+aRFS
./network_setup.py enp37s0f1 --arfs
for i in 2 4 6 8 12; do
        ./run_experiment_receiver.py --config all-to-all --num-connections $i --throughput --utilisation --cache-miss --util-breakdown --arfs --output results/all-to-all_${i}_all-opts | tee results/all-to-all_${i}_all-opts.log
done
