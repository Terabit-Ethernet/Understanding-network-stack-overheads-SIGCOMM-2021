# No Optimisations
./network_setup.py enp37s0f1 --no-lro --no-gso --no-gro --no-tso --no-arfs --sender --config all-to-all --mtu 1500 --sock-size
for i in 1 2 4 8; do
        ./run_experiment_sender.py --addr 192.168.10.115 --receiver genie02 --config all-to-all --num-connections $i --throughput --utilisation --cache-miss --output results/all-to-all_${i}_no-opts | tee results/all-to-all_${i}_no-opts.log
done

# TSO/GRO
./network_setup.py enp37s0f1 --gro --tso
for i in 1 2 4 8; do
        ./run_experiment_sender.py --addr 192.168.10.115 --receiver genie02 --config all-to-all --num-connections $i --throughput --utilisation --cache-miss --output results/all-to-all_${i}_tsogro | tee results/all-to-all_${i}_tsogro.log
done

# TSO/GRO+Jumbo Frame
./network_setup.py enp37s0f1 --mtu 9000
for i in 1 2 4 8; do
        ./run_experiment_sender.py --addr 192.168.10.115 --receiver genie02 --config all-to-all --num-connections $i --throughput --utilisation --cache-miss --util-breakdown --output results/all-to-all_${i}_tsogro+jumbo | tee results/all-to-all_${i}_tsogro+jumbo.log
done

# TSO/GRO+Jumbo Frame+aRFS
./network_setup.py enp37s0f1 --arfs
for i in 1 2 4 8; do
        ./run_experiment_sender.py --addr 192.168.10.115 --receiver genie02 --config all-to-all --num-connections $i --throughput --utilisation --cache-miss --arfs --output results/all-to-all_${i}_all-opts | tee results/all-to-all_${i}_all-opts.log
done
