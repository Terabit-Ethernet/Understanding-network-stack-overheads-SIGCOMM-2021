# terabit-network-stack-profiling: Understanding Network Stack performance for High Speed Networks

## 1. Install Tools and Patch Kernel for Profiling

### Patch Linux kernel for enabling deep profiling

We have tested our setup on Ubuntu 16.04 LTS with kernel 5.4.43. Building the kernel and installing the tools should be done on both servers.

1. Download Linux kernel source tree.

```
cd ~
wget https://mirrors.edge.kernel.org/pub/linux/kernel/v5.x/linux-5.4.43.tar.gz
tar xzvf linux-5.4.43.tar.gz
```

2. Download and apply the path to the kernel source.

```
git clone https://github.com/WarpSpeed-Networking/terabit-network-stack-profiling
cd ~/linux-5.4.43/
git apply ../terabit-network-stack-profiling/kernel_patch/profiling.patch
```

3. Update kernel configuration.

```
cp /boot/config-x.x.x .config
make oldconfig
```

`x.x.x` is a kernel version. It can be your current kernel version or latest version your system has. Type  `uname -r` to see your current kernel version.  

5. Compile and install. The `LOCALVERSION=-sigcomm21` option can be replaced by any custom marker. Remember to replace `sigcomm21` with your own definition in the rest of the instructions.

```
make -j`nproc` LOCALVERSION=-sigcomm21 bindeb-pkg
sudo dpkg -i ../linux-headers-5.4.43-sigcomm21_5.4.43-sigcomm21-1_amd64.deb ../linux-image-5.4.43-sigcomm21_5.4.43-sigcomm21-1_amd64.deb
```

6. Edit `/etc/default/grub` to boot with your new kernel by default. For example

```
GRUB_DEFAULT="1>Ubuntu, with Linux 5.4.43-sigcomm21"
```

7. Update the grub configuration and reboot into the new kernel.

```
sudo update-grub && reboot
```

8. Do the same steps 1--7 for both servers.

9. When systems are rebooted, check the kernel version, type `uname -r` in the command-line. It should be `5.4.43-sigcomm21`.

### Perf

1. To install `perf` from the kernel source directory, first install the build dependencies.

```
sudo apt install -y systemtap-sdt-dev libaudit-common libaudit-dev libaudit1 libssl-dev libiberty-dev binutils-dev zlib1g zlib1g-dev libzstd1-dev liblzma-dev libcap-dev libnuma-dev libbabeltrace-ctf-dev libbabeltrace-dev
```

2. Build and install `perf`.

```
cd ~/linux-5.4.43/tools
sudo make perf_install prefix=/usr/
```

3. Revise the path of `perf` in `constants.py`.

```
PERF_PATH = "/path/to/perf"
```

### Flamegraph (Optional)

1. Clone the Flamegraph tool. This tool is useful for understanding/visualizing the data path of the kernel.

```
cd ~
sudo git clone https://github.com/brendangregg/FlameGraph.git
```

3. Revise the path of Flamegraph in `constants.py`.

```
FLAME_PATH = "/path/to/FlameGraph"   
```

### Install OFED Driver (Mellanox NIC) and Configure NICs

1. Download the OFED drier from the Mellanox website: [https://www.mellanox.com/products/infiniband-drivers/linux/mlnx_ofed](https://www.mellanox.com/products/infiniband-drivers/linux/mlnx_ofed).

2. Extract the installation file and install.

```
cd /path/to/driver/directory
sudo ./mlnxofedinstall
```

3. The NICs must be configured with certain addresses hardcoded in the kernel patch to enable deep profiling of the TCP connections. This allows us to augment the kernel code without affecting the performance of other TCP connections, and makes the measurements more accurate. Set the IP address of the sender to `192.168.10.114/24` and the IP address of the receiver to `192.168.10.115/24`. IP addresses can be set using the following command.

```
sudo ifconfig <iface> <ip_addr>/<prefix_len>
```

Here, `<iface>` is the network interface on which the experiments are to be run. Replace `<ip_addr>` and `<prefix_len>` by their appropriate values for the sender and receiver respectively.

## 2. Getting the Mapping Between CPU and Receive Queues of NIC

The default RSS or RPS will forward packets to a receive queue of NIC or CPU based on the hash value of five tuples, leading performance fluctuation for different runs. Hence, in order to make the performance reproducible, we use flow steering to steer packets to a specific queue/CPU. The setup is done by `network_setup.py`. The only thing you need to do is to get the mapping between CPUs and receive queues. 

The following instruction is for Mellanox NIC, which may be okay to extend for other NIC as well. We will use IRQ affinity to infer the mapping between the receive queues and the CPU cores. The assumption here is there is a one-to-one mapping between receive queue and IRQ as well.

1. Reset IRQ mapping between CPU and IRQ to default and disable `irqbalance` as it dynamically changes the IRQ affinity causing unexpected performance deviations.

```
sudo set_irq_affinity.sh <iface>
```

2. Show the IRQ affinity.

```
sudo show_irq_affinity.sh <iface>
```
 
For example:
 
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

IRQ 152 can be ignored. The IRQs 153-176 map to receive queues 0-23 respectively. To interpret the line `N: xxxxxx`, N is the IRQ number, while `xxxxxx` is a bitmap for the cores the IRQ will be sent to. The number `xxxxxx` can be interpreted as follows.

```
Index starting
from the right
   |
   v
___x__ <- NUMA ID
^    ^
|    |
6    1
```

The index in the bitmap denotes the core ID. The number `x` denotes the NUMA node of the core when interpreted as a bitmap. So the bitmap `004000` will be interpreted as 3nd NUMA (i.e NUMA 2 as `4 = 0100`) and since it's at index 4 from the left, it's the 4th core. So this is the 4th core in 3nd NUMA node which is core 14. 

3. Change `CPU_TO_RX_QUEUE_MAP` in the `constants.py`. This is the mapping from CPUs to their corresponding receive queues. For the example stated above, the mapping is

```
CPU_TO_RX_QUEUE_MAP = [int(i) for i in "0 6 7 8 1 9 10 11 2 12 13 14 3 15 16 17 4 18 19 20 5 21 22 23".split()]
```

Core 0 maps to queue 0 (IRQ 153), core 1 maps to queue 6 (IRQ 159).

4. Change `NUMA_TO_RX_QUEUE_MAP` in the `constants.py`; it would be the first CPU node in each NUMA node; for example, if the server has 4 NUMA nodes and core 0 is in NUMA 0, core 1 is in NUMA 1, core 2 is in NUMA 2, core 3 is in NUMA 3, then

```
NUMA_TO_RX_QUEUE_MAP = [int(i) for i in "0 6 7 8".split()]
```

## 3. Running the experiment

To run the experiment (eg. Single Flow case), 

1. At the receiver, 

```
sudo -s
bash -x receiver/single-flow.sh <iface>
```

`<iface>` is the interface name of the receiver's NIC.

2. At the sender,

```
sudo -s
bash -x sender/single-flow.sh <public_ip> <ip_iface> <iface>
```

`<public_ip>` is an IP address for synchronization between sender and receiver for running the experiments; it's recommended that you use another (secondary) NIC for this purpose. Currently, we are using `SimpleXMLRPCServer` to control the synchronization. `<ip_iface>` is the IP of the receiver's NIC whose performance you'd like to evaluate. Both IP addresses (`<public_ip>` and `<ip_iface>`) are **receiver** addresses. `<iface>` is the NIC interface name on the sender side.

3. The results can be found in `results/`; if you would like to get CPU profiling results organized by categories, you can look at `stdout` and log files. For example, in no optimization single flow case, `results/single-flow_no-opts.log` contains this info

```
data_copy etc   lock  mm    netdev sched skb   tcp/ip
4.590     9.650 4.980 7.030 16.090 4.880 7.060 37.210
```

## 4. Artifact Evaluation

All experiments must be run as `sudo`.

```
sudo -s
cd ~/terabit-network-stack-profiling
mkdir results
```

- Figure 3(a)-3(d) (Single Flow):
   - Sender: `bash -x ./sender/single-flow.sh 128.84.155.115 192.168.10.115 enp37s0f1`
   - Receiver: `bash -x ./receiver/single-flow.sh enp37s0f1`

- Figure 3(e)-3(f) (Single Flow):
   - Sender: `bash -x ./sender/tcp-buffer.sh 128.84.155.115 192.168.10.115 enp37s0f1`
   - Receiver: `bash -x ./receiver/tcp-buffer.sh enp37s0f1`

- Figure 4(a)-4(b) (One-to-One):
   - Sender: `bash -x ./sender/one-to-one.sh 128.84.155.115 192.168.10.115 enp37s0f1`
   - Receiver: `bash -x ./receiver/one-to-one.sh enp37s0f1`

- Figure 5 (Incast):
   - Sender: `bash -x ./sender/incast.sh 128.84.155.115 192.168.10.115 enp37s0f1`
   - Receiver: `bash -x ./receiver/incast.sh enp37s0f1`

- Figure 6 (All-to-All):
   - Sender: `bash -x ./sender/all-to-all.sh 128.84.155.115 192.168.10.115 enp37s0f1`
   - Receiver: `bash -x ./receiver/all-to-all.sh enp37s0f1`

- Figure 7 (Packet Drop):
   - Sender: `bash -x ./sender/packet-loss.sh 128.84.155.115 192.168.10.115 enp37s0f1`
   - Receiver: `bash -x ./receiver/packet-loss.sh enp37s0f1`

- Figure 8(a)-8(b) (Short Flow Incast):
   - Sender: `bash -x ./sender/short-incast.sh 128.84.155.115 192.168.10.115 enp37s0f1`
   - Receiver: `bash -x ./receiver/short-incast.sh enp37s0f1`

- Figure 9 (Mixed Flow):
   - Sender: `bash -x ./sender/mixed.sh 128.84.155.115 192.168.10.115 enp37s0f1`
   - Receiver: `bash -x ./receiver/mixed.sh enp37s0f1`

- Figure 4(c) and 8(c) (Local vs Remote NUMA):
   - Sender: `bash -x ./sender/numa.sh 128.84.155.115 192.168.10.115 enp37s0f1`
   - Receiver: `bash -x ./receiver/numa.sh enp37s0f1`

- Outcast:
   - Sender: ` sh ./sender/outcast.sh 128.84.155.115 192.168.10.115 enp37s0f1`
   - Receiver: ` sh ./receiver/outcast.sh enp37s0f1`

## Authors

* Shubham Chaudhary 
* Qizhe Cai
