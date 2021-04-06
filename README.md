# terabit-network-stack: Understanding Network Stack performance for High Speed Networks



## 1. Install tools
### Perf and Flamegraph
1. Install the perf by apt-get if you are using the default kernel version. If you build the kernel by source, then:
   ```
   sudo -s
   cd /path/to/kernel/source/tools/perf
   make
   ```
2. Git clone the Flamegraph tool. This tool is useful for understanding/visualizing the data path of the kernel:
   ```
   git clone https://github.com/brendangregg/FlameGraph.git
   ```
3. Revise the data path of perf and flamegraph in `run_experiment_receiver.py` and `run_experiment_sender.py`:
   ```
   PERF_PATH = "/path/to/perf"
   FLAME_PATH = "/path/to/FlameGraph"   
   ```
## 2. Getting the mapping between CPU and receive queues of NIC
The default RSS or RPS will forward packets to a receive queue of NIC or CPU based on the hash value of five tuples, leading performance fluctuation
for different runs. Hence, in order to make the performance reproducible, we use `ntuple` instead to steer packets to a specific queue/CPU. The setup script is covered by th

## Authors
* Shubham Chaudhary 
* Qizhe Cai
