# No Optimisations
./network_setup.py enp37s0f1 --no-lro --no-gso --no-gro --no-tso --no-arfs --sender --config one-to-one --mtu 1500 --sock-size
for i in 2 4 8; do
        ./run_experiment_sender.py --addr 192.168.10.115 --receiver genie02 --config one-to-one --num-connections $i --throughput --utilisation --cache-miss --util-breakdown --output results/one-to-one_${i}_no-opts | tee results/one-to-one_${i}_no-opts.log
done

# TSO/GRO
./network_setup.py enp37s0f1 --gro --tso
for i in 2 4 8; do
        ./run_experiment_sender.py --addr 192.168.10.115 --receiver genie02 --config one-to-one --num-connections $i --throughput --utilisation --cache-miss --util-breakdown --output results/one-to-one_${i}_tsogro | tee results/one-to-one_${i}_tsogro.log
done

# TSO/GRO+Jumbo Frame
./network_setup.py enp37s0f1 --mtu 9000
for i in 2 4 8; do
        ./run_experiment_sender.py --addr 192.168.10.115 --receiver genie02 --config one-to-one --num-connections $i --throughput --utilisation --cache-miss --util-breakdown --output results/one-to-one_${i}_tsogro+jumbo | tee results/one-to-one_${i}_tsogro+jumbo.log
done

# TSO/GRO+Jumbo Frame+aRFS
./network_setup.py enp37s0f1 --arfs
for i in 2 4 8; do
        ./run_experiment_sender.py --addr 192.168.10.115 --receiver genie02 --config one-to-one --num-connections $i --throughput --utilisation --cache-miss --util-breakdown --arfs --output results/one-to-one_${i}_all-opts | tee results/one-to-one_${i}_all-opts.log
done
