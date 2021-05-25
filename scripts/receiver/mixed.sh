#!/bin/bash
# Get the dir of this project
DIR=$(realpath $(dirname $(readlink -f $0))/../..)

# Parse arguments
# Example: ./mixed-loss.sh enp37s0f1
iface=${1:-enp37s0f1}
results_dir=${2:-$DIR/results}

# Create results directory
mkdir -p $results_dir

# No Optimisations
$DIR/network_setup.py $iface --no-lro --no-gso --no-gro --no-tso --no-arfs --receiver --flow-type mixed --mtu 1500 --sock-size
for i in 1 4 16; do
    $DIR/run_experiment_receiver.py --flow-type mixed --throughput --utilisation --output $results_dir/mixed_no-opts_${i} | tee $results_dir/mixed_no-opts_${i}.log
done

# TSO/GRO
$DIR/network_setup.py $iface --gro --tso
for i in 1 4 16; do
    $DIR/run_experiment_receiver.py --flow-type mixed --throughput --utilisation --output $results_dir/mixed_tsogro_${i} | tee $results_dir/mixed_tsogro_${i}.log
done

# TSO/GRO+Jumbo Frame
$DIR/network_setup.py $iface --mtu 9000
for i in 1 4 16; do
    $DIR/run_experiment_receiver.py --flow-type mixed --throughput --utilisation --output $results_dir/mixed_tsogro+jumbo_${i} | tee $results_dir/mixed_tsogro+jumbo_${i}.log
done

# TSO/GRO+Jumbo Frame+aRFS
$DIR/network_setup.py $iface --arfs
for i in 1 4 16; do
    $DIR/run_experiment_receiver.py --flow-type mixed --throughput --utilisation --util-breakdown --arfs --output $results_dir/mixed_all-opts_${i} | tee $results_dir/mixed_all-opts_${i}.log
done

