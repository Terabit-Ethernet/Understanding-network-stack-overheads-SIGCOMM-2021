#!/bin/bash
# Get the dir of this project
DIR=$(realpath $(dirname $(readlink -f $0))/../..)

# Parse arguments
# Example: ./one-to-one.sh 128.84.155.115 192.168.10.115 enp37s0f1
public_dst_ip=${1:-128.84.155.115}
device_dst_ip=${2:-192.168.10.115}
iface=${3:-enp37s0f1}
results_dir=${4:-$DIR/results}

# Create results directory
mkdir -p $results_dir

# No Optimisations
$DIR/network_setup.py $iface --no-lro --no-gso --no-gro --no-tso --no-arfs --sender --config one-to-one --mtu 1500 --sock-size
for i in 8 16 24; do
        $DIR/run_experiment_sender.py --addr $device_dst_ip --receiver $public_dst_ip --config one-to-one --num-connections $i --throughput --utilisation --output $results_dir/one-to-one_${i}_no-opts | tee $results_dir/one-to-one_${i}_no-opts.log
done

# TSO/GRO
$DIR/network_setup.py $iface --gro --tso
for i in 8 16 24; do
        $DIR/run_experiment_sender.py --addr $device_dst_ip --receiver $public_dst_ip --config one-to-one --num-connections $i --throughput --utilisation --output $results_dir/one-to-one_${i}_tsogro | tee $results_dir/one-to-one_${i}_tsogro.log
done

# TSO/GRO+Jumbo Frame
$DIR/network_setup.py $iface --mtu 9000
for i in 8 16 24; do
        $DIR/run_experiment_sender.py --addr $device_dst_ip --receiver $public_dst_ip --config one-to-one --num-connections $i --throughput --utilisation --output $results_dir/one-to-one_${i}_tsogro+jumbo | tee $results_dir/one-to-one_${i}_tsogro+jumbo.log
done

# TSO/GRO+Jumbo Frame+aRFS
$DIR/network_setup.py $iface --arfs
for i in 8 16 24; do
        $DIR/run_experiment_sender.py --addr $device_dst_ip --receiver $public_dst_ip --config one-to-one --num-connections $i --throughput --utilisation --util-breakdown --arfs --output $results_dir/one-to-one_${i}_all-opts | tee $results_dir/one-to-one_${i}_all-opts.log
done

# Print results
$DIR/scripts/parse/one-to-one.sh $results_dir
