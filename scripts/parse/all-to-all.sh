#!/bin/bash
# Get the dir of this project
DIR=$(realpath $(dirname $(readlink -f $0))/../..)

# Parse arguments
# Example: ./all-to-all.sh ~/results/
results_dir=${1:-$DIR/results}

# Print the results
tmp=`mktemp`
echo -e "*** all-to-all summary ***"
echo -e "****** throughput per core with varying number of flows and different optimisations ******"
echo -e "config\tn\t$(awk -F'\t' '/summary/{getline; print $4}' $results_dir/all-to-all_8_no-opts.log)" > $tmp
for config in no-opts tsogro tsogro+jumbo all-opts; do
    for n in 8 16 24; do
        echo -e "${config}\t${n}\t$(awk -F'\t' '/summary/{getline; getline; print $4}' $results_dir/all-to-all_${n}_${config}.log)" >> $tmp
    done
done
column -t -s $'\t' $tmp
echo

echo -e "****** receiver CPU utilisation breakdown with varying number of flows and all optimisations enabled ******"
echo -e "n\t$(awk '/receiver utilisation breakdown/{getline; print}' $results_dir/all-to-all_8_all-opts.log)" > $tmp
for n in 8 16 24; do
    echo -e "${n}\t$(awk '/receiver utilisation breakdown/{getline; getline; print}' $results_dir/all-to-all_${n}_all-opts.log)" >> $tmp
done
column -t -s $'\t' $tmp
echo

echo -e "****** skb size histogram with varying number of flows and all optimisations enabled ******"
echo -e "n\t$(awk '/skb sizes histogram/{getline; print}' $results_dir/all-to-all_8_all-opts.log)" > $tmp
for n in 8 16 24; do
    echo -e "${n}\t$(awk '/skb sizes histogram/{getline; getline; print}' $results_dir/all-to-all_${n}_all-opts.log)" >> $tmp
done
column -t -s $'\t' $tmp
rm $tmp
