#!/bin/bash
# Get the dir of this project
DIR=$(realpath $(dirname $(readlink -f $0))/../..)

# Parse arguments
# Example: ./packet-loss.sh 128.84.155.115 192.168.10.115 enp37s0f1
public_dst_ip=${1:-128.84.155.115}
device_dst_ip=${2:-192.168.10.115}
iface=${3:-enp37s0f1}
results_dir=${4:-$DIR/results}

# Create results directory
mkdir -p $results_dir

# No Optimisations
$DIR/network_setup.py $iface --no-lro --no-gso --no-gro --no-tso --no-arfs --sender --mtu 1500 --sock-size
for i in 100 1000 10000; do
    $DIR/run_experiment_sender.py --receiver $public_dst_ip --addr $device_dst_ip --throughput --utilisation --output $results_dir/packet-loss_no-opts_${i} | tee $results_dir/packet-loss_no-opts_${i}.log
done

# TSO/GRO
$DIR/network_setup.py $iface --gro --tso
for i in 100 1000 10000; do
    $DIR/run_experiment_sender.py --receiver $public_dst_ip --addr $device_dst_ip --throughput --utilisation --output $results_dir/packet-loss_tsogro_${i} | tee $results_dir/packet-loss_tsogro_${i}.log
done

# TSO/GRO+Jumbo Frame
$DIR/network_setup.py $iface --mtu 9000
for i in 100 1000 10000; do
    $DIR/run_experiment_sender.py --receiver $public_dst_ip --addr $device_dst_ip --throughput --utilisation --output $results_dir/packet-loss_tsogro+jumbo_${i} | tee $results_dir/packet-loss_tsogro+jumbo_${i}.log
done

# TSO/GRO+Jumbo Frame+aRFS
$DIR/network_setup.py $iface --arfs
for i in 100 1000 10000; do
    $DIR/run_experiment_sender.py --receiver $public_dst_ip --addr $device_dst_ip --throughput --utilisation --util-breakdown --arfs --output $results_dir/packet-loss_all-opts_${i} | tee $results_dir/packet-loss_all-opts_${i}.log
done

# Print results
$DIR/scripts/parse/packet-loss.sh $results_dir
