#!/bin/bash
# Get the dir of this project
DIR=$(realpath $(dirname $(readlink -f $0))/../..)

# Parse arguments
# Example: ./single-flow.sh enp37s0f1
iface=${1:-enp37s0f1}
results_dir=${2:-$DIR/results}

# Create results directory
mkdir -p $results_dir

# No Optimisations
$DIR/network_setup.py $iface --no-lro --no-gso --no-gro --no-tso --no-arfs --receiver --mtu 1500 --sock-size
$DIR/run_experiment_receiver.py --throughput --utilisation --util-breakdown --output $results_dir/single-flow_no-opts | tee $results_dir/single-flow_no-opts.log

# TSO/GRO
$DIR/network_setup.py $iface --gro --tso
$DIR/run_experiment_receiver.py --throughput --utilisation --util-breakdown --output $results_dir/single-flow_tsogro | tee $results_dir/single-flow_tsogro.log

# Jumbo
$DIR/network_setup.py $iface --no-gro --no-tso --mtu 9000
$DIR/run_experiment_receiver.py --throughput --utilisation --output $results_dir/single-flow_jumbo | tee $results_dir/single-flow_jumbo.log

# TSO/GRO+Jumbo Frame
$DIR/network_setup.py $iface --gro --tso
$DIR/run_experiment_receiver.py --throughput --utilisation --util-breakdown --output $results_dir/single-flow_tsogro+jumbo | tee $results_dir/single-flow_tsogro+jumbo.log

# TSO/GRO+aRFS
$DIR/network_setup.py $iface --arfs --mtu 1500
$DIR/run_experiment_receiver.py --throughput --utilisation --arfs --output $results_dir/single-flow_tsogro+arfs | tee $results_dir/single-flow_tsogro+arfs.log

# Jumbo+aRFS
$DIR/network_setup.py $iface --no-gro --no-tso --mtu 9000
$DIR/run_experiment_receiver.py --throughput --utilisation --arfs --output $results_dir/single-flow_jumbo+arfs | tee $results_dir/single-flow_jumbo+arfs.log

# TSO/GRO+Jumbo Frame+aRFS
$DIR/network_setup.py $iface --gro --tso
$DIR/run_experiment_receiver.py --throughput --utilisation --util-breakdown --arfs --output $results_dir/single-flow_all-opts | tee $results_dir/single-flow_all-opts.log
