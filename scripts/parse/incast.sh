#!/bin/bash
# Get the dir of this project
DIR=$(realpath $(dirname $(readlink -f $0))/../..)

# Parse arguments
# Example: ./incast.sh ~/results/
results_dir=${1:-$DIR/results}

# Print the results
tmp=`mktemp`
echo -e "*** incast summary ***"
echo -e "****** throughput per core with varying number of flows and different optimisations ******"
echo -e "config\tn\t$(awk -F'\t' '/summary/{getline; print $4}' $results_dir/incast_8_no-opts.log)" > $tmp
for config in no-opts tsogro tsogro+jumbo; do
    for n in 8 16 24; do
        echo -e "${config}\t${n}\t$(awk -F'\t' '/summary/{getline; getline; print $4}' $results_dir/incast_${n}_${config}.log)" >> $tmp
    done
done
for n in 8 16 24; do
    echo -e "all-opts\t${n}\t$(awk -F'\t' '/summary/{getline; getline; print $6}' $results_dir/incast_${n}_all-opts.log)" >> $tmp
done
column -t -s $'\t' $tmp
echo

echo -e "****** receiver CPU utilisation breakdown with varying number of flows and all optimisations enabled ******"
echo -e "n\t$(awk '/receiver utilisation breakdown/{getline; print}' $results_dir/incast_8_all-opts.log)" > $tmp
for n in 8 16 24; do
    echo -e "${n}\t$(awk '/receiver utilisation breakdown/{getline; getline; print}' $results_dir/incast_${n}_all-opts.log)" >> $tmp
done
column -t -s $'\t' $tmp
echo

echo -e "****** cache miss rate with varying number of flows and all optimisations enabled ******"
echo -e "n\t$(awk -F'\t' '/summary/{getline; print $5 "\t" $6}' $results_dir/incast_8_all-opts.log)" > $tmp
for n in 8 16 24; do
    echo -e "${n}\t$(awk -F'\t' '/summary/{getline; getline; print $5 "\t" $6}' $results_dir/incast_${n}_all-opts.log)" >> $tmp
done
column -t -s $'\t' $tmp
rm $tmp
