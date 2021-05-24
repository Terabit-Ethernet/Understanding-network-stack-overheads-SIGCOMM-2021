#!/bin/bash
# Get the dir of this project
DIR=$(realpath $(dirname $(readlink -f $0))/../..)

# Parse arguments
# Example: ./single-flow.sh ~/results/
results_dir=${1:-$DIR/results}

# Print the results
tmp=`mktemp`
echo -e "*** single-flow summary ***"
echo -e "****** throughput per core with different optimisations ******"
echo -e "config\t$(awk -F'\t' '/summary/{getline; print $4}' $results_dir/single-flow_no-opts.log)" > $tmp
for config in no-opts tsogro jumbo tsogro+jumbo tsogro+arfs jumbo+arfs all-opts; do
    echo -e "${config}\t$(awk -F'\t' '/summary/{getline; getline; print $4}' $results_dir/single-flow_${config}.log)" >> $tmp
done
column -t -s $'\t' $tmp
echo

echo -e "****** throughput and CPU utilisation with different optimisations ******"
echo -e "config\t$(awk -F'\t' '/summary/{getline; print $1 "\t" $2 "\t" $3}' $results_dir/single-flow_no-opts.log)" > $tmp
for config in no-opts tsogro tsogro+jumbo all-opts; do
    echo -e "${config}\t$(awk -F'\t' '/summary/{getline; getline; print $1 "\t" $2 "\t" $3}' $results_dir/single-flow_${config}.log)" >> $tmp
done
column -t -s $'\t' $tmp
echo

echo -e "****** sender CPU utilisation breakdown with different optimisations ******"
echo -e "config\t$(awk '/sender utilisation breakdown/{getline; print}' $results_dir/single-flow_no-opts.log)" > $tmp
for config in no-opts tsogro tsogro+jumbo all-opts; do
    echo -e "${config}\t$(awk '/sender utilisation breakdown/{getline; getline; print}' $results_dir/single-flow_${config}.log)" >> $tmp
done
column -t -s $'\t' $tmp
echo

echo -e "****** receiver CPU utilisation breakdown with different optimisations ******"
echo -e "config\t$(awk '/receiver utilisation breakdown/{getline; print}' $results_dir/single-flow_no-opts.log)" > $tmp
for config in no-opts tsogro tsogro+jumbo all-opts; do
    echo -e "${config}\t$(awk '/receiver utilisation breakdown/{getline; getline; print}' $results_dir/single-flow_${config}.log)" >> $tmp
done
column -t -s $'\t' $tmp
rm $tmp
