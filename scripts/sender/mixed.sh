#!/bin/bash
# Get the dir of this project
DIR=$(realpath $(dirname $(readlink -f $0))/../..)

# Parse arguments
# Example: ./mixed.sh 128.84.155.115 192.168.10.115 enp37s0f1
public_dst_ip=${1:-128.84.155.115}
device_dst_ip=${2:-192.168.10.115}
iface=${3:-enp37s0f1}
results_dir=${4:-$DIR/results}

# Create results directory
mkdir -p $results_dir

# No Optimisations
$DIR/network_setup.py $iface --no-lro --no-gso --no-gro --no-tso --no-arfs --sender --flow-type mixed --mtu 1500 --sock-size
for i in 1 4 16; do
    $DIR/run_experiment_sender.py --flow-type mixed --num-rpcs $i --receiver $public_dst_ip --addr $device_dst_ip --throughput --utilisation --output $results_dir/mixed_no-opts_${i} | tee $results_dir/mixed_no-opts_${i}.log
done

# TSO/GRO
$DIR/network_setup.py $iface --gro --tso
for i in 1 4 16; do
    $DIR/run_experiment_sender.py --flow-type mixed --num-rpcs $i --receiver $public_dst_ip --addr $device_dst_ip --throughput --utilisation --output $results_dir/mixed_tsogro_${i} | tee $results_dir/mixed_tsogro_${i}.log
done

# TSO/GRO+Jumbo Frame
$DIR/network_setup.py $iface --mtu 9000
for i in 1 4 16; do
    $DIR/run_experiment_sender.py --flow-type mixed --num-rpcs $i --receiver $public_dst_ip --addr $device_dst_ip --throughput --utilisation --output $results_dir/mixed_tsogro+jumbo_${i} | tee $results_dir/mixed_tsogro+jumbo_${i}.log
done

# TSO/GRO+Jumbo Frame+aRFS
$DIR/network_setup.py $iface --arfs
for i in 1 4 16; do
    $DIR/run_experiment_sender.py --flow-type mixed --num-rpcs $i --receiver $public_dst_ip --addr $device_dst_ip --throughput --utilisation --util-breakdown --arfs --output $results_dir/mixed_all-opts_${i} | tee $results_dir/mixed_all-opts_${i}.log
done

# Print results
$DIR/scripts/parse/mixed.sh $results_dir
