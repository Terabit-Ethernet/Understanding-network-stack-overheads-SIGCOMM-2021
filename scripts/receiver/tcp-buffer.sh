#!/bin/bash
# Get the dir of this project
DIR=$(realpath $(dirname $(readlink -f $0))/../..)

# Parse arguments
# Example: ./tcp-buffer.sh enp37s0f1
iface=${1:-enp37s0f1}
results_dir=${2:-$DIR/results}

# Create results directory
mkdir -p $results_dir

# TSO/GRO+Jumbo Frame+aRFS
$DIR/network_setup.py $iface --gro --tso --mtu 9000 --sock-size --arfs
for i in 100 200 400 800 1600 3200 6400 12800; do
    $DIR/run_experiment_receiver.py --window $i --throughput --utilisation --cache-miss --latency --arfs --output $results_dir/tcp-buffer_all-opts_${i} | tee $results_dir/tcp-buffer_all-opts_${i}.log
done
