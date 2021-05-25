# Understanding Network Stack Performance for Terabit Ethernet Networks

### Overview

We provide here the scripts that can be used to profile the Linux kernel TCP stack running over terabit ethernet networks. [Section 1](#organisation) describes the organisation of the repository. [Section 2](#setup-servers) contains the steps required to setup the servers to perform profiling. This involves patching and installing an appproriate kernel, installing additional tools like `perf`, and configuring the NIC which one would like to use for the profiling. [Section 3](#running-an-experiment) gives a general overview of how to use our evaluation scripts. And finally, in [Section 4](#sigcomm-2021-artifact-evaluation) you will find the necessary instructions to reproduce the results from our SIGCOMM 2021 paper.

## Organisation

The repository is organised as follows.

* `kernel_patch` contains some modifications in the kernel code to enable efficient profiling of the TCP stack.
* `scripts` contains scripts used to run experiments for our SIGCOMM 2021 paper.
    * `scripts/sender` are the scripts that must be run on the sender-side.
    * `scripts/receiver` are the respective receiver-side scripts.
    * `scripts/parse` are the scripts that can be used to parse and pretty print the results of an experiment after it's finished.
* `run_experiment_sender.py`, `run_experiment_receiver.py` are the scripts that actually run the experiment.
    * `network_setup.py` allows us to configure the NIC to enable/disable various offloads, set parameters and so on.
    * `constants.py` contains the constants used by our scripts.
    * `process_output.py` contains utilily code to parse outputs from the benchmarking programs.
* `symbol_mapping.tsv` is a map from kernel symbols/function names to the classification into one of seven categories depending on their function or their location in the kernel TCP stack.

Below you will find instructions on how to use the tools provided in this repository to either reproduce our findings or profile your own setup to explore it's characteristics.

## Setup Servers

### Install Prerequisites

We need to install prerequisites to compile the kernel, and other benchmarking utilities. On Ubuntu 16.04, this can be done with

```
sudo apt-get install libncurses-dev gawk flex bison openssl libssl-dev dkms   \
                     libelf-dev libudev-dev libpci-dev libiberty-dev autoconf \
                     iperf netperf sysstat
```

### Patch Linux Kernel to Enable Deep Profiling (~30 minutes)

The given kernel patch includes the following features.

* By default, the kernel forcibly enables GSO (Generic Segmentation Offload) even when explicity disabled. This would not let us compare the performance of TSO to the baseline, so we patch the kernel to allow us to truly disable GSO.
* Since we want to test the performace of the TCP stack in presence of packet loss, we introduce a `sysctl` parameter `net.core.packet_loss_gen` which, when enabled, drops packets in the lower layers of packet processing.
* We introduce a patch to measure scheduling/data copy latency, by timestamping each `skb` shortly after it's created and logging the delta between then and right before data copy is performed.
* We also patch the kernel to capture a histogram of `skb` sizes after GRO (Generic Segmentation Offload) and log them.

Our patch is based on Linux 5.4.43. On Ubuntu 16.04, you can use the following instructions to build and install the kernel.

1. Download Linux kernel source tree.

```
cd ~
wget https://mirrors.edge.kernel.org/pub/linux/kernel/v5.x/linux-5.4.43.tar.gz
tar xzvf linux-5.4.43.tar.gz
```

2. Download and apply the patch to the kernel source.

```
git clone https://github.com/WarpSpeed-Networking/terabit-network-stack-profiling
cd ~/linux-5.4.43/
git apply ../terabit-network-stack-profiling/kernel_patch/profiling.patch
```

3. Update kernel configuration.

```
cp /boot/config-x.x.x .config
make oldconfig
scripts/config --disable DEBUG_INFO # Disables building debugging related files
```

`x.x.x` is a kernel version. It can be your current kernel version or latest version your system has. Type  `uname -r` to see your current kernel version.

5. Compile and install. The `LOCALVERSION=-profiling` option can be replaced by any custom marker. Remember to replace `profiling` with your own definition in the rest of the instructions.

```
make -j`nproc` LOCALVERSION=-profiling bindeb-pkg
sudo dpkg -i ../linux-headers-5.4.43-profiling_5.4.43-profiling-1_amd64.deb \
             ../linux-image-5.4.43-profiling_5.4.43-profiling-1_amd64.deb   \
             ../linux-libc-dev_5.4.43-profiling-1_amd64.deb
```

**NOTE** If you rebuild the kernel packages more than once, they might have a different version, for example, `linux-headers-5.4.43-profiling_5.4.43-profiling-2_amd64.deb`. Make sure you install the `.deb` packages you have just built and not an old one.

6. Edit `/etc/default/grub` to boot with your new kernel by default. For example

```
GRUB_DEFAULT="1>Ubuntu, with Linux 5.4.43-profiling"
```

7. Update the grub configuration and reboot into the new kernel.

```
sudo update-grub && reboot
```

8. When system is rebooted, check the kernel version, type `uname -r` in the command-line. It should be `5.4.43-profiling`.

### Install perf

1. To install `perf` from the kernel source directory, first install the build dependencies.

```
sudo apt install -y systemtap-sdt-dev libaudit-common libaudit-dev libaudit1 libssl-dev   \
                    libiberty-dev binutils-dev zlib1g zlib1g-dev libzstd1-dev liblzma-dev \
                    libcap-dev libnuma-dev libbabeltrace-ctf-dev libbabeltrace-dev
```

2. Build and install `perf`.

```
cd ~/linux-5.4.43/tools
sudo make perf_install prefix=/usr/
```

3. Revise the path of `perf` in `constants.py`; should be `/usr/bin/perf` if you used the above instructions.

```
PERF_PATH = "/path/to/perf"
```

### Install Flamegraph (Optional)

1. Clone the Flamegraph tool. This tool is useful for understanding/visualizing the data path of the kernel.

```
cd /opt/
sudo git clone https://github.com/brendangregg/FlameGraph.git
```

2. Revise the path of Flamegraph in `constants.py`; should be `/opt/FlameGraph` if you used the above instructions.

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

3. **IMPORTANT** The NICs must be configured with certain addresses hardcoded in the kernel patch to enable deep profiling of the TCP connections. This allows us to augment the kernel code without affecting the performance of other TCP connections, and makes the measurements more accurate. Set the IP address of the server which is designated as the sender to `192.168.10.114/24` and similarly set the IP address of the server designated as the receiver to `192.168.10.115/24`. IP addresses can be set using the following command.

```
sudo ifconfig <iface> <ip_addr>/<prefix_len>
```

Here, `<iface>` is the network interface on which the experiments are to be run. Replace `<ip_addr>` and `<prefix_len>` by their appropriate values for the sender and receiver respectively.

### Getting the Mapping Between CPU and Receive Queues of NIC

**NOTE** You only need to follow these instructions if your CPU or NIC configuration is different from ours.

The default RSS or RPS will forward packets to a receive queue of NIC or CPU based on the hash value of the five tuple, leading performance fluctuation for different runs. Hence, in order to make the performance reproducible, we use flow steering to steer packets to a specific queue/CPU. The setup is done by `network_setup.py`. The only thing you need to do is to get the mapping between CPUs and receive queues.

The following instructions are for Mellanox NIC, which may or may not apply to other NICs as well. We will use IRQ affinity table to infer the mapping between the receive queues and the CPU cores. The assumption here is there is a one-to-one mapping between receive queue and IRQ as well.

1. Reset IRQ mapping between CPU and IRQ to default and disable `irqbalance` as it dynamically changes the IRQ affinity causing unexpected performance deviations.

```
sudo set_irq_affinity.sh <iface>
sudo service irqbalance stop
```

2. Show the IRQ affinity table.

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

IRQ 152 can be ignored. The IRQs 153-176 map to receive queues 0-23 respectively (this server has 24 cores). To interpret the line `N: xxxxxx`, N is the IRQ number, while `xxxxxx` is a bitmap for the cores the IRQ will be sent to. The number `xxxxxx` can be interpreted as follows.

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

The index in the bitmap denotes the core ID. The number `x` denotes the NUMA node of the core when interpreted as a bitmap. So the bitmap `004000` will be interpreted as 3rd NUMA (i.e NUMA 2 as `4 = 0100`) and since it's at index 4 from the left, it's the 4th core. So this is the 4th core of the 3rd NUMA node which is core 14.

3. Change `CPU_TO_RX_QUEUE_MAP` in the `constants.py`. This is the mapping from CPUs to their corresponding receive queues. For the example stated above, the mapping is

```
CPU_TO_RX_QUEUE_MAP = [0, 6, 7, 8, 1, 9, 10, 11, 2, 12, 13, 14, 3, 15, 16, 17, 4, 18, 19, 20, 5, 21, 22, 23]
```

Core 0 maps to queue 0 (IRQ 153), core 1 maps to queue 6 (IRQ 159).

## Running an Experiment

To run any experiment (eg. Single Flow), configure two servers as the sender and the receiver, and install the requisite kernel and tools on both of them. Then

1. At the receiver,

```
sudo -s
cd ~/terabit-network-stack-profiling/scripts
bash receiver/single-flow.sh <iface> <results_dir>
```

`<iface>` is the interface name of the receiver's NIC.

2. At the sender,

```
sudo -s
cd ~/terabit-network-stack-profiling/scripts
bash sender/single-flow.sh <public_ip> <ip_iface> <iface> <results_dir>
```

`<public_ip>` is an IP address for synchronization between sender and receiver for running the experiments; it's recommended that you use another (secondary) NIC for this purpose. Currently, we are using `SimpleXMLRPCServer` for synchronization. `<ip_iface>` is the IP of the receiver's NIC whose performance you'd like to evaluate. Both IP addresses (`<public_ip>` and `<ip_iface>`) are **receiver** addresses. `<iface>` is the NIC interface name on the sender side.

**NOTE** `<ip_iface>` must be `192.168.10.115`. See [Section 2.5](#install-ofed-driver-mellanox-nic-and-configure-nics).

3. A summary of the results of the experiment is printed on the sender-side. The relevant logs can be found in `<results_dir>`. It is also possible to pretty print the results of an experiment later. Simply point the relevant script in `~/terabit-network-stack-profiling/scripts/parse` to the `<results_dir>` on the sender-side. For instance, after running the `scripts/sender/single-flow.sh ... <results_dir>` script, running `scripts/parse/single-flow.sh <results_dir>` produces the following output.

```
*** single-flow summary ***
****** throughput per core with different optimisations ******
config        throughput per core (Gbps)
no-opts       4.783
tsogro        14.976
jumbo         25.876
tsogro+jumbo  27.642
tsogro+arfs   28.254
jumbo+arfs    40.801
all-opts      41.210

****** throughput and CPU utilisation with different optimisations ******
config        throughput (Gbps)  sender utilisation (%)  receiver utilisation (%)
no-opts       9.009              101.523                 185.764
tsogro        26.590             80.036                  175.146
tsogro+jumbo  32.540             67.420                  114.462
all-opts      42.200             59.813                  100.000

****** sender CPU utilisation breakdown with different optimisations ******
config        data_copy  etc    lock   mm     netdev  sched  skb    tcp/ip
no-opts       5.900      4.940  4.520  8.230  17.500  2.160  9.450  41.460
tsogro        28.630     7.260  6.100  8.070  10.160  9.040  7.650  15.760
tsogro+jumbo  36.760     4.290  6.860  9.290  7.900   7.100  7.720  13.370
all-opts      47.950     4.750  1.810  6.790  8.480   6.980  3.390  12.730

****** receiver CPU utilisation breakdown with different optimisations ******
config        data_copy  etc    lock   mm      netdev  sched  skb     tcp/ip
no-opts       7.390      0.540  8.900  4.430   9.270   2.400  7.260   54.820
tsogro        29.810     1.430  1.080  5.680   33.840  5.170  13.310  4.700
tsogro+jumbo  44.510     0.560  1.550  15.930  15.060  1.980  11.400  4.030
all-opts      54.330     1.770  0.610  10.990  18.250  2.960  3.670   2.220
```

## SIGCOMM 2021 Artifact Evaluation

### Hardware/Software Configuration

We have used the follwing hardware and software configurations for running the experiments shown in the paper.

* CPU: 4-Socket Intel Xeon Gold 6128 3.4 GHz with 6 Cores per Socket (with Hyperthreading Disabled)
* RAM: 256 GB
* NIC: Mellanox ConnectX-5 Ex VPI (100 Gbps)
* OS: Ubuntu 16.04 with Linux 5.4.43 (patched)

#### Caveats of Our Work

Our work has been evaluated with two servers with 4-socket multi-core CPUs and 100 Gbps NICs directly connected with a DAC cable. While we generally focus on trends rather than individual data points, other combinations of end-host network stacks and hardware may exhibit different performance characteristics. All our scripts use `network_setup.sh` to configure the NIC to allow a specific benchmark to be performed. Some of these configurations may be specific to Mellanox NICs (e.g. enabling aRFS).

### Assumptions

The next section assumes that

* you used the instructions in [Section 2](#setup-servers) to setup the servers;
* there is another secondary connection between the two servers through a **separate** NIC and receiver can be reached at the IP address `128.84.155.115` through that interface;
* the IP address of the NIC to be profiled is set to be `192.168.10.114` for the sender, and `192.168.10.115` for the receiver, in accordance with [Section 2.5](#install-ofed-driver-mellanox-nic-and-configure-nics);
* and that the name of the interface of the NIC to be profiled is `enp37s0f1`.

The scripts given below have hardcoded default arguments in accordance with the above assumptions, so that they can be run as is. Please make sure you change the command-lines below to reflect any differences between your setup and the assumptions, refer to [Section 3](#running-an-experiment) on how to do that.

### Running Experiments

All experiments must be run as `sudo`. Run the scripts corresponding to each experiment on the sender and receiver respectively.

```
sudo -s
cd ~/terabit-network-stack-profiling/scripts
```

- Figure 3(a)-3(d) (Single Flow) (~6 minutes)
   - Sender: `bash sender/single-flow.sh`
   - Receiver: `bash receiver/single-flow.sh`

- Figure 3(e)-3(f) (Single Flow) (~11 minutes)
   - Sender: `bash sender/tcp-buffer.sh`
   - Receiver: `bash receiver/tcp-buffer.sh`

- Figure 4(a)-4(b) (One-to-One) (~9 minutes)
   - Sender: `bash sender/one-to-one.sh`
   - Receiver: `bash receiver/one-to-one.sh`

- Figure 5 (Incast) (~10 minutes)
   - Sender: `bash sender/incast.sh`
   - Receiver: `bash receiver/incast.sh`

- Figure 6 (All-to-All) (~10 minutes)
   - Sender: `bash sender/all-to-all.sh`
   - Receiver: `bash receiver/all-to-all.sh`

- Figure 7 (Packet Drops) (~9 minutes)
   - Sender: `bash sender/packet-loss.sh`
   - Receiver: `bash receiver/packet-loss.sh`

- Figure 8(a)-8(b) (Short Flow Incast) (~12 minutes)
   - Sender: `bash sender/short-incast.sh`
   - Receiver: `bash receiver/short-incast.sh`

- Figure 9 (Mixed Flow) (~9 minutes)
   - Sender: `bash sender/mixed.sh`
   - Receiver: `bash receiver/mixed.sh`

- Figure 4(c) and 8(c) (Local vs Remote NUMA) (~4 minutes)
   - Sender: `bash sender/numa.sh`
   - Receiver: `bash receiver/numa.sh`

- Appendix (Outcast) (~9 minutes)
   - Sender: `bash sender/outcast.sh`
   - Receiver: `bash receiver/outcast.sh`

### Interpreting the Results

The results of each experiment will be logged to `stdout` as well as to the directory `~/terabit-network-stack-profiling/results`. This directory will contain files which are named with the format `<experiment_name>_<parameter>_<optimisations>`, where `<experiment_name>` is the name of the experiment (`all-to-all`), `<parameter>` is the value of the parameter that was changed in the experiment (`4` flows, `6400` bytes RPC size), and `<optimisations>` is the set of optimisations enabled for the experiment (`tsogro`, `tsogro+jumbo`, `all-opts`).

The results of the experiment can be pretty printed again by running the command `~/terabit-network-stack-profiling/scripts/parse/<experiment_name>.sh`, where `<experiment_name>` is the file name (without extension) of the script used to run the experiment.

#### A Note on the Evaluation Metrics

We report some or all of the following metrics in our experiments. Each invocation of the `run_experiment_*.py` will log a summary of the results on the sender-side.

* **Throughput**: Unidirectional (sender to receiver) aggregate throughput (in Gbps).
* **Utilisation**: CPU utilisation (in percent (%)) on the sender-side and the receiver-side.
* **Cache Miss:** Cache-miss rate (in percent (%)) on the sender-side and receiver-side.
* **CPU Utilisation Breakdown**: Fraction of CPU cycles taken by various layers of the kernel TCP stack.
* **Cache Miss Breakdown**: Fraction of cache misses that occur in various layers of the kernel TCP stack.
* **Data Copy/Scheduling Latency:** Time (in μs) from the creation of the `skb` to when it's copied to the user buffers.
* **skb Sizes Histogram**: Fraction of `skb`s which, after GRO, have a size (in KB) that lies in the respective range.
* **Throughput per Core**: The aggregate throughput divided by the CPU utilisation of the bottleneck (in Gbps).
    * For outcast experiments, it's throughput divided by sender-side CPU utilisation.
    * For all other experiments, it's throughput divided by receiver-side CPU utilisation.

### Errors

In case of errors, like freezes, crashes, or unexpected error messages, please reboot the servers. That should clear out any erroneous leftover processes and/or bad config and allow you to run the experiments.

## Authors

* Shubham Chaudhary
* Qizhe Cai
