# Parse arguments
# Example: ./tcp-buffer.sh enp37s0f1
iface=${1:-enp37s0f1}

# TSO/GRO+Jumbo Frame+aRFS
./network_setup.py $iface --gro --tso --mtu 9000 --sock-size --arfs
for i in 100 200 400 800 1600 3200 6400 12800; do
    ./run_experiment_receiver.py --window $i --throughput --utilisation --cache-miss --latency --arfs --output results/tcp-buffer_all-opts_${i} | tee results/tcp-buffer_all-opts_${i}.log
done
