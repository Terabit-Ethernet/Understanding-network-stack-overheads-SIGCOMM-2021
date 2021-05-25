#!/bin/bash
# Get the dir of this project
DIR=$(realpath $(dirname $(readlink -f $0))/../..)

# Parse arguments
# Example: ./short-incast.sh ~/results/
results_dir=${1:-$DIR/results}

# Print the results
tmp=`mktemp`
echo -e "*** short-incast summary ***"
echo -e "****** throughput per core with varying number of flows and different optimisations ******"
echo -e "config\trpc size (bytes)\t$(awk -F'\t' '/summary/{getline; print $4}' $results_dir/short-incast_16_4000_no-opts.log)" > $tmp
for config in no-opts tsogro tsogro+jumbo all-opts; do
    for n in 4000 16000 32000 64000; do
        echo -e "${config}\t${n}\t$(awk -F'\t' '/summary/{getline; getline; print $4}' $results_dir/short-incast_16_${n}_${config}.log)" >> $tmp
    done
done
column -t -s $'\t' $tmp
echo

echo -e "****** receiver CPU utilisation breakdown with varying number of flows and all optimisations enabled ******"
echo -e "rpc size (bytes)\t$(awk '/receiver utilisation breakdown/{getline; print}' $results_dir/short-incast_16_4000_all-opts.log)" > $tmp
for n in 4000 16000 32000 64000; do
    echo -e "${n}\t$(awk '/receiver utilisation breakdown/{getline; getline; print}' $results_dir/short-incast_16_${n}_all-opts.log)" >> $tmp
done
column -t -s $'\t' $tmp
rm $tmp
