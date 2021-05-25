#!/bin/bash
# Get the dir of this project
DIR=$(realpath $(dirname $(readlink -f $0))/../..)

# Parse arguments
# Example: ./tcp-buffer.sh ~/results/
results_dir=${1:-$DIR/results}

# Print the results
tmp=`mktemp`
echo -e "*** tcp-buffer summary ***"
echo -e "****** throughput per core and receiver cache miss for varying TCP buffer size and all optimisations ******"
echo -e "tcp buffer (KB)\t$(awk -F'\t' '/summary/{getline; print $5 "\t" $8}' $results_dir/tcp-buffer_all-opts_100.log)" > $tmp
for n in 100 200 400 800 1600 3200 6400 12800; do
    echo -e "${n}\t$(awk -F'\t' '/summary/{getline; getline; print $5 "\t" $8}' $results_dir/tcp-buffer_all-opts_${n}.log)" >> $tmp
done
column -t -s $'\t' $tmp
echo

echo -e "****** average and tail data copy latency for varying TCP buffer size and all optimisations ******"
echo -e "tcp buffer (KB)\t$(awk -F'\t' '/summary/{getline; print $6 "\t" $7}' $results_dir/tcp-buffer_all-opts_100.log)" > $tmp
for n in 100 200 400 800 1600 3200 6400 12800; do
    echo -e "${n}\t$(awk -F'\t' '/summary/{getline; getline; print $6 "\t" $7}' $results_dir/tcp-buffer_all-opts_${n}.log)" >> $tmp
done
column -t -s $'\t' $tmp
rm $tmp
