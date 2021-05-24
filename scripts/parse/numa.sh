#!/bin/bash
# Get the dir of this project
DIR=$(realpath $(dirname $(readlink -f $0))/../..)

# Parse arguments
# Example: ./numa.sh ~/results/
results_dir=${1:-$DIR/results}

# Print the results
tmp=`mktemp`
echo -e "*** NUMA summary ***"
echo -e "****** throughput per core and receiver cache miss for long and short flows on local and remote NUMA and all optimisations ******"
echo -e "flow\tNUMA\t$(awk -F'\t' '/summary/{getline; print $5 "\t" $6}' $results_dir/numa_long_all-opts_local.log)" > $tmp
echo -e "long\tlocal\t$(awk -F'\t' '/summary/{getline; getline; print $5 "\t" $6}' $results_dir/numa_long_all-opts_local.log)" >> $tmp
echo -e "long\tremote\t$(awk -F'\t' '/summary/{getline; getline; print $5 "\t" $6}' $results_dir/numa_long_all-opts_remote.log)" >> $tmp
echo -e "short\tlocal\t$(awk -F'\t' '/summary/{getline; getline; print $5 "\t" $6}' $results_dir/numa_short_all-opts_local.log)" >> $tmp
echo -e "short\tremote\t$(awk -F'\t' '/summary/{getline; getline; print $5 "\t" $6}' $results_dir/numa_short_all-opts_remote.log)" >> $tmp
column -t -s $'\t' $tmp
rm $tmp
