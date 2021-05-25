#!/bin/bash
# Get the dir of this project
DIR=$(realpath $(dirname $(readlink -f $0))/../..)

# Parse arguments
# Example: ./packet-loss.sh ~/results/
results_dir=${1:-$DIR/results}

# Print the results
tmp=`mktemp`
echo -e "*** packet-loss summary ***"
echo -e "****** throughput per core with varying loss rate and different optimisations ******"
echo -e "config\inv. loss rate\t$(awk -F'\t' '/summary/{getline; print $4}' $results_dir/packet-loss_no-opts_1000.log)" > $tmp
for config in no-opts tsogro tsogro+jumbo all-opts; do
    for n in 10000 1000 100; do
        echo -e "${config}\t${n}\t$(awk -F'\t' '/summary/{getline; getline; print $4}' $results_dir/packet-loss_${config}_${n}.log)" >> $tmp
    done
done
column -t -s $'\t' $tmp
echo

echo -e "****** receiver CPU utilisation breakdown with varying loss rate and all optimisations enabled ******"
echo -e "inv. loss rate\t$(awk '/receiver utilisation breakdown/{getline; print}' $results_dir/packet-loss_all-opts_1000.log)" > $tmp
for n in 10000 1000 100; do
    echo -e "${n}\t$(awk '/receiver utilisation breakdown/{getline; getline; print}' $results_dir/packet-loss_all-opts_${n}.log)" >> $tmp
done
column -t -s $'\t' $tmp
rm $tmp
