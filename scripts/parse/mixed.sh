#!/bin/bash
# Get the dir of this project
DIR=$(realpath $(dirname $(readlink -f $0))/../..)

# Parse arguments
# Example: ./mixed.sh ~/results/
results_dir=${1:-$DIR/results}

# Print the results
tmp=`mktemp`
echo -e "*** mixed summary ***"
echo -e "****** throughput per core with varying number of flows and different optimisations ******"
echo -e "config\tn\t$(awk -F'\t' '/summary/{getline; print $4}' $results_dir/mixed_no-opts_1.log)" > $tmp
for config in no-opts tsogro tsogro+jumbo all-opts; do
    for n in 1 4 16; do
        echo -e "${config}\t${n}\t$(awk -F'\t' '/summary/{getline; getline; print $4}' $results_dir/mixed_${config}_${n}.log)" >> $tmp
    done
done
column -t -s $'\t' $tmp
echo

echo -e "****** receiver CPU utilisation breakdown with varying number of flows and all optimisations enabled ******"
echo -e "n\t$(awk '/receiver utilisation breakdown/{getline; print}' $results_dir/mixed_all-opts_1.log)" > $tmp
for n in 1 4 16; do
    echo -e "${n}\t$(awk '/receiver utilisation breakdown/{getline; getline; print}' $results_dir/mixed_all-opts_${n}.log)" >> $tmp
done
column -t -s $'\t' $tmp
rm $tmp
