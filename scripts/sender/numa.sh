#!/bin/bash
# Get the dir of this project
DIR=$(realpath $(dirname $(readlink -f $0))/../..)

# Parse arguments
# Example: $DIR/numa.sh 128.84.155.115 192.168.10.115 enp37s0f1
public_dst_ip=${1:-128.84.155.115}
device_dst_ip=${2:-192.168.10.115}
iface=${3:-enp37s0f1}
results_dir=${4:-$DIR/results}

# Create results directory
mkdir -p $results_dir

# TSO/GRO+Jumbo Frame+aRFS
$DIR/network_setup.py $iface --gro --tso --arfs --mtu 9000 --sock-size

# Long Flow
$DIR/run_experiment_sender.py --receiver $public_dst_ip --addr $device_dst_ip --throughput --utilisation --cache-miss --arfs --output $results_dir/numa_long_all-opts_local | tee $results_dir/numa_long_all-opts_local.log
$DIR/run_experiment_sender.py --receiver $public_dst_ip --addr $device_dst_ip --throughput --cpus 1 --utilisation --cache-miss --arfs --output $results_dir/numa_long_all-opts_remote | tee $results_dir/numa_long_all-opts_remote.log

# Short Flow
$DIR/run_experiment_sender.py --receiver $public_dst_ip --addr $device_dst_ip --throughput --config incast --flow-type short --num-connections 16 --utilisation --cache-miss --arfs --output $results_dir/numa_short_all-opts_local | tee $results_dir/numa_short_all-opts_local.log
$DIR/run_experiment_sender.py --receiver $public_dst_ip --addr $device_dst_ip --throughput --config incast --flow-type short --num-connections 16 --utilisation --cache-miss --arfs --output $results_dir/numa_short_all-opts_remote | tee $results_dir/numa_short_all-opts_remote.log

# Print results
$DIR/scripts/parse/numa.sh $results_dir
