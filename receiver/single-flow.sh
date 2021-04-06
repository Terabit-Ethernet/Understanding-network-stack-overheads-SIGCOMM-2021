iface=$1
# No Optimisations
./network_setup.py $iface --no-lro --no-gso --no-gro --no-tso --no-arfs --receiver --mtu 1500 --sock-size
./run_experiment_receiver.py --throughput --utilisation --cache-miss --util-breakdown --output results/single-flow_no-opts | tee results/single-flow_no-opts.log

# TSO/GRO
./network_setup.py $iface --gro --tso
./run_experiment_receiver.py --throughput --utilisation --cache-miss --util-breakdown --output results/single-flow_tsogro | tee results/single-flow_tsogro.log

# Jumbo
./network_setup.py $iface --no-gro --no-tso --mtu 9000
./run_experiment_receiver.py --throughput --utilisation --cache-miss --util-breakdown --output results/single-flow_jumbo | tee results/single-flow_jumbo.log

# TSO/GRO+Jumbo Frame
./network_setup.py $iface --gro --tso
./run_experiment_receiver.py --throughput --utilisation --cache-miss --util-breakdown --output results/single-flow_tsogro+jumbo | tee results/single-flow_tsogro+jumbo.log

# TSO/GRO+aRFS
./network_setup.py $iface --arfs --mtu 1500
./run_experiment_receiver.py --throughput --utilisation --cache-miss --util-breakdown --arfs --output results/single-flow_tsogro+arfs | tee results/single-flow_tsogro+arfs.log

# Jumbo+aRFS
./network_setup.py $iface --no-gro --no-tso --mtu 9000
./run_experiment_receiver.py --throughput --utilisation --cache-miss --util-breakdown --arfs --output results/single-flow_jumbo+arfs | tee results/single-flow_jumbo+arfs.log

# TSO/GRO+Jumbo Frame+aRFS
./network_setup.py $iface --gro --tso
./run_experiment_receiver.py --throughput --utilisation --cache-miss --util-breakdown --arfs --output results/single-flow_all-opts | tee results/single-flow_all-opts.log
