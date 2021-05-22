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
$DIR/run_experiment_receiver.py --throughput --utilisation --cache-miss --arfs --output $results_dir/numa_long_all-opts_local | $results_dir/numa_long_all-opts_local.log
$DIR/run_experiment_receiver.py --throughput --cpus 1 --utilisation --cache-miss --arfs --output $results_dir/numa_long_all-opts_remote | $results_dir/numa_long_all-opts_remote.log

# Short Flow
$DIR/run_experiment_receiver.py --throughput --flow-type short --utilisation --cache-miss --arfs --output $results_dir/numa_short_all-opts_local | $results_dir/numa_long_all-opts_local.log
$DIR/run_experiment_receiver.py --throughput --flow-type short --cpus 1 --utilisation --cache-miss --arfs --output $results_dir/numa_short_all-opts_remote | $results_dir/numa_long_all-opts_remote.log
