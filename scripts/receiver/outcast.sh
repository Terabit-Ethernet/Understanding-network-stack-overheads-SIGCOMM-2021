#!/bin/bash
# Get the dir of this project
DIR=$(realpath $(dirname $(readlink -f $0))/../..)

# Parse arguments
# Example: ./outcast.sh enp37s0f1
iface=${1:-enp37s0f1}
results_dir=${2:-$DIR/results}

# Create results directory
mkdir -p $results_dir

# No Optimisations
$DIR/network_setup.py $iface --no-lro --no-gso --no-gro --no-tso --no-arfs --config outcast --receiver --mtu 1500 --sock-size
for i in 2 4 8; do
        $DIR/run_experiment_receiver.py --config outcast --num-connections $i --throughput --utilisation --output $results_dir/outcast_${i}_no-opts | tee $results_dir/outcast_${i}_no-opts.log
done

# TSO/GRO
$DIR/network_setup.py $iface --gro --tso
for i in 2 4 8; do
        $DIR/run_experiment_receiver.py --config outcast --num-connections $i --throughput --utilisation --output $results_dir/outcast_${i}_tsogro | tee $results_dir/outcast_${i}_tsogro.log
done

# TSO/GRO+Jumbo Frame
$DIR/network_setup.py $iface --mtu 9000
for i in 2 4 8; do
        $DIR/run_experiment_receiver.py --config outcast --num-connections $i --throughput --utilisation --output $results_dir/outcast_${i}_tsogro+jumbo | tee $results_dir/outcast_${i}_tsogro+jumbo.log
done

# TSO/GRO+Jumbo Frame+aRFS
$DIR/network_setup.py $iface --arfs
for i in 2 4 8; do
        $DIR/run_experiment_receiver.py --config outcast --num-connections $i --throughput --utilisation --util-breakdown --arfs --output $results_dir/outcast_${i}_all-opts | tee $results_dir/outcast_${i}_all-opts.log
done
