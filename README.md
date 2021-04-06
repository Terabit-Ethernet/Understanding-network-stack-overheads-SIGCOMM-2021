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
   '''
   git clone https://github.com/brendangregg/FlameGraph.git
   '''
3. Revise the data path of perf and flamegraph in  

## Authors
* Shubham Chaudhary 
* Qizhe Cai
