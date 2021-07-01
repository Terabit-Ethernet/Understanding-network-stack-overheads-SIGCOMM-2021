#!/usr/bin/env python3

import argparse
import os as _os
from constants import *


# For debugging
class os:
    VERBOSE = False

    @staticmethod
    def enable_logging():
        os.VERBOSE = True

    @staticmethod
    def system(p):
        if os.VERBOSE: print("+ " + p)
        _os.system(p)


def parse_args():
    parser = argparse.ArgumentParser(description="Configure the network interface.")

    # Configuration for setting the IRQ affinity
    parser.add_argument('--sender', action='store_true', default=None, help='This is the sender.')
    parser.add_argument('--receiver', action='store_true', default=None, help='This is the receiver.')
    parser.add_argument("--flow-type", choices=["long", "short", "mixed"], default="long", help="Flow type to run the experiment with.")
    parser.add_argument("--config", choices=["one-to-one", "incast", "outcast", "all-to-all", "single"], default="single", help="Configuration to run the experiment with.")
    parser.add_argument("--affinity", type=int, nargs="*", help="Which CPUs are being used for IRQ processing.")

    # Parse basic parameters
    parser.add_argument('interface', type=str, help='The network device interface to configure.')
    parser.add_argument('--mtu', type=int, default=None, help='MTU of the network interface (in bytes).')
    parser.add_argument('--speed', type=int, default=None, help='Speed of the network interface (in Mbps).')
    parser.add_argument('--sock-size', action='store_true', default=None, help='Increase socket read/write memory limits.')
    parser.add_argument('--dca', type=int, default=None, help='Set the number of cache ways DCA/DDIO can use.')
    parser.add_argument('--ring-buffer', type=int, default=None, help='Set the size of the RX/TX ring buffer.')

    # Parse offload parameters
    parser.add_argument('--gro', action='store_true', default=None, help='Enables GRO.')
    parser.add_argument('--no-gro', dest='gro', action='store_false', default=None, help='Disables GRO.')
    parser.add_argument('--gso', action='store_true', default=None, help='Enables GSO.')
    parser.add_argument('--no-gso', dest='gso', action='store_false', default=None, help='Disables GRO.')
    parser.add_argument('--lro', action='store_true', default=None, help='Enables LRO.')
    parser.add_argument('--no-lro', dest='lro', action='store_false', default=None, help='Disables LRO.')
    parser.add_argument('--tso', action='store_true', default=None, help='Enables TSO.')
    parser.add_argument('--no-tso', dest='tso', action='store_false', default=None, help='Disables TSO.')
    parser.add_argument('--checksum', action='store_true', default=None, help='Enables checksumming offloads.')
    parser.add_argument('--no-checksum', dest='checksum', action='store_false', default=None, help='Disables checksumming offloads.')

    # Parse IRQ/aRFS parameters
    parser.add_argument('--arfs', action='store_true', default=None, help='Enables aRFS.')
    parser.add_argument('--no-arfs', dest='arfs', action='store_false', default=None, help='Disables aRFS.')

    # Logging parameters
    parser.add_argument("--verbose", action="store_true", help="Print extra output.")

    # Actually parse arguments
    args = parser.parse_args()

    # Report errors
    if args.dca is not None and not (1 <= args.dca <= 11):
        print("Can't set --dca values outside of [1, 11].")
        exit(1)

    if args.arfs is not None and args.arfs and args.affinity is not None:
       print("Can't set --affinity with --arfs.")
       exit(0)

    if args.arfs is not None and not args.arfs:
        if args.sender is not None and args.receiver is not None:
            print("Can't set both --sender and --receiver.")
            exit(1)

        if args.sender is None and args.receiver is None:
            print("Must set one of --sender or --receiver with --no-arfs.")
            exit(1)

        if args.flow_type == "mixed" and args.config != "single":
            print("Can't set --flow-type mixed without --config single.")
            exit(1)

        single_cpu_configs = ["single", "incast" if args.receiver else "outcast"]
        multiple_cpu_configs = ["one-to-one", "outcast" if args.receiver else "incast"]

        if args.config == "all-to-all" and args.affinity is not None:
            print("Can't set --affinity with --config all-to-all, uses RSS.")
            exit(0)

        # Set IRQ processing CPUs
        if args.affinity is not None:
            if args.config in single_cpu_configs and len(args.affinity) != 1:
                print("Please provide only 1 --affinity for --config {}cast/single.".format("in" if args.receiver else "out"))
                exit(1)

            if args.config in multiple_cpu_configs and len(args.affinity) != MAX_CPUS:
                print("Please provide {} --affinity for --config {}cast/one-to-one.".format(MAX_CPUS, "out" if args.receiver else "in"))
                exit(1)

            if not all(map(lambda c: 0 <= c < MAX_CPUS, args.affinity)):
                print("Can't set --affinity outside of [0, {}].".format(MAX_CPUS))
                exit(1)
        else:
            if args.config in single_cpu_configs:
                args.affinity = [1]
            elif args.config in multiple_cpu_configs:
                args.affinity = [(cpu + 1) % MAX_CPUS for cpu in CPUS]

    if args.mtu is not None and not (0 < args.mtu <= 9000):
        print("Can't set values of --mtu outside of (0, 9000] bytes.")
        exit(1)

    if args.speed is not None and not (0 < args.speed <= 100000):
        print("Can't set values of --speed outside of (0, 100000] Mbps.")
        exit(1)

    if args.ring_buffer is not None and not (0 < args.ring_buffer <= 8192):
        print("Can't set values of --ring-buffer outside of (0, 1892].")
        exit(1)

    if args.tso is not None and args.checksum is not None and not args.checksum and args.tso:
        print("Can't use --no-checksum with --tso, --no-checksum implies --no-tso.")
        exit(1)

    if args.checksum is not None and not args.checksum:
        args.tso = False

    # Return validated arguments
    return args


# Convenience functions
def on_or_off(state):
    return "on" if state else "off"


def stop_irq_balance():
    os.system("service irqbalance stop")


def manage_ntuple(iface, enabled):
    os.system("ethtool -K {} ntuple {}".format(iface, on_or_off(enabled)))


def manage_rps(iface, enabled):
    num_rps = 32768 if enabled else 0
    os.system("echo {} > /proc/sys/net/core/rps_sock_flow_entries".format(num_rps))
    os.system("for f in /sys/class/net/{}/queues/rx-*/rps_flow_cnt; do echo {} > $f; done".format(iface, num_rps))


def set_irq_affinity(iface):
    os.system("set_irq_affinity.sh {} 2> /dev/null > /dev/null".format(iface))


def ntuple_send_port_to_queue(iface, port, n, loc):
    os.system("ethtool -U {} flow-type tcp4 dst-port {} action {} loc {}".format(iface, port, n, loc))
    os.system("ethtool -U {} flow-type tcp4 src-port {} action {} loc {}".format(iface, port, n, MAX_RULE_LOC - loc))


def ntuple_send_all_traffic_to_queue(iface, n, loc):
    os.system("ethtool -U {} flow-type tcp4 action {} loc {}".format(iface, n, loc))


def ntuple_clear_rules(iface):
    for i in range(MAX_RULE_LOC + 1):
        os.system("ethtool -U {} delete {} 2> /dev/null > /dev/null".format(iface, i))


# Functions to set IRQ mode
def setup_irq_mode_arfs(iface):
    stop_irq_balance()
    manage_rps(iface, True)
    manage_ntuple(iface, True)
    set_irq_affinity(iface)
    ntuple_clear_rules(iface)


def setup_irq_mode_no_arfs_sender(affinity, iface, flow_type, config):
    stop_irq_balance()
    manage_rps(iface, False)
    ntuple_clear_rules(iface)
    set_irq_affinity(iface)

    # For single flow or outcast, we have to send all traffic to core 1;
    # for one-to-one and outcast, we use flow steering to the next core;
    # otherwise we just use RSS
    if config in ["outcast", "single"]:
        manage_ntuple(iface, True)
        ntuple_send_all_traffic_to_queue(iface, CPU_TO_RX_QUEUE_MAP[affinity[0]], 0)
    elif config in ["incast", "one-to-one"]:
        manage_ntuple(iface, True)
        for n, cpu in enumerate(affinity):
            q = CPU_TO_RX_QUEUE_MAP[cpu]
            ntuple_send_port_to_queue(iface, BASE_PORT + n, q, n)
    else:
        manage_ntuple(iface, False)


def setup_irq_mode_no_arfs_receiver(affinity, iface, flow_type, config):
    stop_irq_balance()
    manage_rps(iface, False)
    ntuple_clear_rules(iface)
    set_irq_affinity(iface)

    # For single flow or incast, we have to send all traffic to core 1;
    # for one-to-one and outcast, we use flow steering to next core;
    # otherwise we just use RSS
    if config in ["incast", "single"]:
        manage_ntuple(iface, True)
        ntuple_send_all_traffic_to_queue(iface, CPU_TO_RX_QUEUE_MAP[affinity[0]], 0)
    elif config in ["outcast", "one-to-one"]:
        manage_ntuple(iface, True)
        for n, cpu in enumerate(affinity):
            q = CPU_TO_RX_QUEUE_MAP[cpu]
            ntuple_send_port_to_queue(iface, BASE_PORT + n, q, n)
    else:
        manage_ntuple(iface, False)


def setup_affinity_mode(affinity, iface, arfs, sender, receiver, flow_type, config):
    if arfs is not None:
        if arfs:
            setup_irq_mode_arfs(iface)
        elif sender is not None and sender:
            setup_irq_mode_no_arfs_sender(affinity, iface, flow_type, config)
        elif receiver is not None and receiver:
            setup_irq_mode_no_arfs_receiver(affinity, iface, flow_type, config)


# Set connection speed
def set_speed(iface, speed):
    if speed is not None:
        os.system("ethtool -s {} speed {} autoneg off".format(iface, speed))


# Set MTU
def set_mtu(iface, mtu):
    if mtu is not None:
        os.system("ifconfig {} mtu {}".format(iface, mtu))


# Set RX/RX ring buffer size
def set_ring_buffer_size(iface, size):
    if size is not None:
        os.system("ethtool -G {0} rx {1} tx {1}".format(iface, size))


# Functions to manage offloads
def manage_offloads(iface, lro, tso, gso, gro, checksum):
    offloads = {"lro": lro, "tso": tso, "gso": gso, "gro": gro, "tx": checksum, "rx": checksum}
    args = ["{} {}".format(offload, on_or_off(enabled)) for offload, enabled in offloads.items() if enabled is not None]
    if len(args) > 0:
        os.system("ethtool -K {} {}".format(iface, " ".join(args)))


# Increase socket memory size limit
def increase_sock_size_limit(enabled):
    if enabled is not None:
        if enabled:
            os.system("sysctl -w net.core.wmem_max=12582912 && sysctl -w net.core.rmem_max=12582912")
        else:
            os.system("sysctl -w net.core.wmem_max=212992 && sysctl -w net.core.rmem_max=212992")


# Set DDIO ways
def set_ddio_ways(ways):
    if ways is not None:
        os.system("modprobe msr")
        os.system("wrmsr {} {}".format(DDIO_REG, hex((2 ** ways - 1) << (11 - ways))))


# Run the functions according to parsed arguments
if __name__ == "__main__":
    args = parse_args()
    if args.verbose:
        os.enable_logging()

    # Set offload config
    manage_offloads(args.interface, args.lro, args.tso, args.gso, args.gro, args.checksum)

    # Set IRQ config
    setup_affinity_mode(args.affinity, args.interface, args.arfs, args.sender, args.receiver, args.flow_type, args.config)

    # Setup other config
    set_speed(args.interface, args.speed)
    set_mtu(args.interface, args.mtu)
    increase_sock_size_limit(args.sock_size)
    set_ddio_ways(args.dca)
    set_ring_buffer_size(args.interface, args.ring_buffer)

