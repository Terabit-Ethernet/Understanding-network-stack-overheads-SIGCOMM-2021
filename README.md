# terabit-network-stack-profiling: Understanding Network Stack performance for High Speed Networks



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
### Install OFED Driver (Mellanox NIC Only) 
1. Download the OFED drier from the Mellanox website: https://www.mellanox.com/products/infiniband-drivers/linux/mlnx_ofed.
2. Untar and install:
   ```
   cd /path/to/driver/directory
   sudo ./mlnxofedinstall
   ```
## 2. Getting the mapping between CPU and receive queues of NIC
The default RSS or RPS will forward packets to a receive queue of NIC or CPU based on the hash value of five tuples, leading performance fluctuation
for different runs. Hence, in order to make the performance reproducible, we use `ntuple` to steer packets to a specific queue/CPU. The setup script is covered by `network_setup.py`. The only thing you need to do is to get the mapping between CPUs and receive queues. 

The following instruction is for Mellanox NIC, which may be okay to extend for other NIC as well. We will use IRQ affinity to infer the mapping between the receive queues and the CPU cores. The assumption here is there is a one-to-one mapping between receive queue and IRQ as well.

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
IRQ 152 can be ignored. To interpret the line `153: 000001`, 153 is the IRQ number and it maps to the receive queue 0, while `000001` refers to core 0 and this number is in hex format. For example, `000002` refers to core 1 and `000010` refers to core 4.

3. Change CPU_TO_RX_QUEUE_MAP in the `network_setup.py`. This is the mapping from CPUs to their corresponding receive queues. For the example stated above, the mapping is:
```
CPU_TO_RX_QUEUE_MAP = [int(i) for i in "0 6 7 8 1 9 10 11 2 12 13 14 3 15 16 17 4 18 19 20 5 21 22 23".split()]
```
Core 0 maps to queue 0(IRQ 153), Core 1 maps to queue 6 (IRQ 159).
4. Change NUMA_TO_RX_QUEUE_MAP in the `network_setup.py`; it would be the first CPU node in each NUMA node; for example, if the server has 4 NUMA nodes and Core 0 is in NUMA node 0, Core 1 is in NUMA node 1, Core 2 is in NUMA noded 2, Core 3 is in NUMA node 3, then
```
NUMA_TO_RX_QUEUE_MAP = [int(i) for i in "0 6 7 8".split()]
```

## 3. Running the experiment
To run the experiment (eg. single flow case), 
1. At the receiver side, 
```
sudo -s
sh receiver/single-flow.sh <iface>
```
`<iface>` is the interface name of the receiver's NIC.

2. At the sender side,
```
sudo -s
sh sender/single-flow.sh <public_ip> <ip of iface> <iface>
```
`<public_ip>` is for synchronizing between sender and receiver for running the experiments; currently, we are using XMLServer to control the synchronization. `<ip of iface>` is the dst interface's IP, which you'd like to evaluate the performance. Both IP addresses (`<public ip>` and `<ip of iface>`) are **receiver** addresses. `<iface>` is the NIC name in the sender side.

3. The results can be found in `results/`; if you would like to get CPU profiling results organized by categories, you can look at log file. For example, in no optimization single flow case, `results/single-flow_no-opts.log`contained this info:  `data_copy       etc     lock    mm      netdev  sched   skb     tcp/ip
4.590   9.650   4.980   7.030   16.090  4.880   7.060   37.210`.

## 4. Artifact Evaluation
Enter the sudo mode first and then enter the directory:
```
 sudo -s
 cd terabit-network-stack-profiling
```
- Figure 3(a)-3(d) (single flow):
   - Sender: ``` sh ./sender/single-flow.sh 128.84.155.115 192.168.10.115 enp37s0f1 ```
   - Receiver: ``` sh ./receiver/single-flow.sh enp37s0f1 ```
- Figure 3(e)(single flow):
   - To Do: add script   
- Figuree 3(f)(single flow):
   - To measure the latency, you need to switch to a different kernel in the receiver side:
   ```
     sudo vim /etc/default/grub
   ```
   In the grub file, comment out the current GRUB_DEFAULT line:
   ```
    #GRUB_DEFAULT="1>Ubuntu, with Linux 5.4.43-qizhe" 
   ```
   And uncomment the line:
   ```
    GRUB_DEFAULT="1>Ubuntu, with Linux 5.4.43-qizhe.latency"
   ```
   Save and exit the file, and then update grub menu and reboot
   ```
   sudo update-grub2
   sudo reboot
   ```
   - After rebooting, follow 3(e) instruction to run the tests (but with one setup each time), with two additional steps:
       - turn on qizhe_dist_on before running experiment 
         ```
         sudo -s
         // start measuring the latency
         echo 1 > /sys/module/tcp/parameters/qizhe_dist_on
         ```
      - Open a new termnal to record the latency (eg. if the window size is 200KB):
        ```
         sudo tail -f /var/log/kern.log > results/200_latency
        ```
      - Follow 3(e) instruction to run experiment (with one window size at a time)
  - After finish all experiments, turn off the qizhe_dist_on 
      ```
      sudo -s
      // start measuring the latency
      echo 0 > /sys/module/tcp/parameters/qizhe_dist_on
      ```
  - Get Latency results
      ```
      python get_latency.py
      ```
- Figure 4 (one-to-one):
   - Sender: ``` sh ./sender/one-to-one.sh 128.84.155.115 192.168.10.115 enp37s0f1 ```
   - Receiver: ``` sh ./receiver/one-to-one.sh enp37s0f1 ```
   - Figure 4c: NIC-remote Flow:
      - To Do: add script
- Figure 5 (incast):
   - Sender: ``` sh ./sender/incast.sh 128.84.155.115 192.168.10.115 enp37s0f1 ```
   - Receiver: ``` sh ./receiver/incast.sh enp37s0f1 ```
- Figure 6 (all-to-all):
   - Sender: ``` sh ./sender/all-to-all.sh 128.84.155.115 192.168.10.115 enp37s0f1 ```
   - Receiver: ``` sh ./receiver/all-to-all.sh enp37s0f1 ```
   - Figure 6c: skb size distribution
      - ``` cd gro_measure ```
      - Change the source (line 21) and destination IP address (line 22)
       ```
         line 21: if(iph->saddr == in_aton("**192.168.10.114**") &&
         line 22: iph->daddr == in_aton("**192.168.10.115**")) {
       ```
      - Build and Install gro_measure kernel module
       ```
         make
         insmod gro_measure.ko
       ```
      - Enable the gro counting
       ```
        echo 1 > /sys/module/gro_measure/parameters/gro_gen
       ```
      - GRO counting results are in the kernel.log:
       ```
        sudo tail -f /var/log/kern.log
       ```
      - Run the experiment as usual (recommended: run experiment one by one) and record the results
- Figure 7 (pkt drop):
   - Follow the Figure 3f instruction to change the kernel at the receiver siide to 5.4.43.qizhe.latency. 
   - Then enable the packet drop and set the packet drop rate(eg. rate = 0.0001)
     ```
     sudo -s
     sysctl -w net.core.packet_loss_gen=10000
     ```
     Here, 1/packet_loss_gen is packet drop rate.
   - To Do: add script  
- Figure 8 (short flow incast):
   - To Do: add script  
- Figure 9 (mixed flow):
  - To Do: add script  
- outcast:
   - Sender: ``` sh ./sender/one-to-one.sh 128.84.155.115 192.168.10.115 enp37s0f1 ```
   - Receiver: ``` sh ./receiver/one-to-one.sh enp37s0f1 ```
## Authors
* Shubham Chaudhary 
* Qizhe Cai

