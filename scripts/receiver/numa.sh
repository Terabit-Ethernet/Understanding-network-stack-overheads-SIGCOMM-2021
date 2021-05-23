#!/bin/bash
# Get the dir of this project
DIR=$(realpath $(dirname $(readlink -f $0))/../..)

# Parse arguments
# Example: $DIR/numa.sh enp37s0f1
iface=${1:-enp37s0f1}
results_dir=${2:-$DIR/results}

# Create results directory
mkdir -p $results_dir

# TSO/GRO+Jumbo Frame+aRFS
$DIR/network_setup.py $iface --gro --tso --mtu 9000 --sock-size --arfs

# Long Flow
$DIR/run_experiment_receiver.py --throughput --utilisation --cache-miss --arfs --output $results_dir/numa_long_all-opts_local | tee $results_dir/numa_long_all-opts_local.log
$DIR/run_experiment_receiver.py --throughput --cpus 1 --utilisation --cache-miss --arfs --output $results_dir/numa_long_all-opts_remote | tee $results_dir/numa_long_all-opts_remote.log

# Short Flow
$DIR/run_experiment_receiver.py --throughput --config incast --flow-type short --num-connections 16 --utilisation --cache-miss --arfs --output $results_dir/numa_short_all-opts_local | tee $results_dir/numa_short_all-opts_local.log
$DIR/run_experiment_receiver.py --throughput --config incast --flow-type short --num-connections 16 --cpus 1 --utilisation --cache-miss --arfs --output $results_dir/numa_short_all-opts_remote | tee $results_dir/numa_short_all-opts_remote.log
