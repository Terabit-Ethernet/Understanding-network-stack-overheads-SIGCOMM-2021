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
for different runs. Hence, in order to make the performance reproducible, we use `ntuple` instead to steer packets to a specific queue/CPU. The setup script is covered by `network_setup.py`. The only thing you need to do is to get the mappiing between CPUs and receive queues. 

The following instruction is for Mellanox NIC, which may be okay to extend for other NIC as well. We will use IRQ affinity to infer the mapping. The assumption here is there is a one-to-one mapping between receive queue and IRQ as well.

1. Set IRQ mapping between CPU and IRQ:
 ```
  sudo set_irq_affinity.sh  <iface>
 ```
2. Show the IRQ affinity:
 ```
  sudo show_irq_affinity.sh <iface>
 ```
 The example is:
 ```
152: 000001
153: 000001
154: 000010
155: 000100
156: 001000
157: 010000
158: 100000
159: 000002
160: 000004
161: 000008
162: 000020
163: 000040
164: 000080
165: 000200
166: 000400
167: 000800
168: 002000
169: 004000
170: 008000
171: 020000
172: 040000
173: 080000
174: 200000
175: 400000
176: 800000
 ```
IRQ 152 can be ignored. To interpret the line `153: 000001`, 153 is the IRQ number and it maps to the receive queue 0, while `000001` refers to core 0 and this number is in hex format. `000002` refers to core 1 and `000010` refers to core 4.

3. Change CPU_TO_RX_QUEUE_MAP in the `network_setup.py`. For the example stated above, the mapping is:
```
CPU_TO_RX_QUEUE_MAP = [int(i) for i in "0 6 7 8 1 9 10 11 2 12 13 14 3 15 16 17 4 18 19 20 5 21 22 23".split()]
```
4. Change NUMA_TO_RX_QUEUE_MAP in the `network_setup.py`; it would be the first CPU node in the server; for example, if the server has 4 NUMA nodes and Core 0 is in NUMA node 0, Core 1 is in NUMA node 1, Core 2 is in NUMA noded 2, Core 3 is in NUMA node 3, then
```
NUMA_TO_RX_QUEUE_MAP = [int(i) for i in "0 6 7 8".split()]
```
## Authors
* Shubham Chaudhary 
* Qizhe Cai
