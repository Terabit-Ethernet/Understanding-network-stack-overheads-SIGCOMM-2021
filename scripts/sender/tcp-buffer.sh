#!/bin/bash
# Get the dir of this project
DIR=$(realpath $(dirname $(readlink -f $0))/../..)

# Parse arguments
# Example: ./tcp-buffer.sh 128.84.155.115 192.168.10.115 enp37s0f1
public_dst_ip=${1:-128.84.155.115}
device_dst_ip=${2:-192.168.10.115}
iface=${3:-enp37s0f1}
results_dir=${4:-$DIR/results}

# Create results directory
mkdir -p $results_dir

# TSO/GRO+Jumbo Frame+aRFS
$DIR/network_setup.py $iface --gro --tso --arfs --mtu 9000 --sock-size
for i in 100 200 400 800 1600 3200 6400 12800; do
    $DIR/run_experiment_sender.py --receiver $public_dst_ip --addr $device_dst_ip --window $i --throughput --utilisation --cache-miss --latency --arfs --output $results_dir/tcp-buffer_all-opts_${i} | tee $results_dir/tcp-buffer_all-opts_${i}.log
done

# Print results
$DIR/scripts/parse/tcp-buffer.sh $results_dir
