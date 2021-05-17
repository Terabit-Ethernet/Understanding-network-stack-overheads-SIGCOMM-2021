#!/usr/bin/env python3
import argparse
import os
import shlex
import signal
import subprocess as _sp
import tempfile
import threading
import time
import xmlrpc.server
from process_output import *


# For debugging
class subprocess:
    PIPE = _sp.PIPE
    DEVNULL = _sp.DEVNULL
    STDOUT = _sp.STDOUT
    @staticmethod
    def Popen(*args, **kwargs):
        print("+ " + " ".join(shlex.quote(s) for s in args[0]))
        return _sp.Popen(*args, **kwargs)


# Constants
SENDER_COMM_PORT = 8080
IPERF_BASE_PORT = 30000
NETPERF_BASE_PORT = 40000
PERF_PATH = "/home/shubham/bin/perf"
FLAME_PATH = "/home/shubham/utils/FlameGraph"
PERF_DATA = "perf.data"
#CPUS = [0, 4, 8, 12, 2, 6, 10, 14]
CPUS = [ i for i in range(24)]
MAX_CONNECTIONS = len(CPUS)
MAX_RPCS = 16


def parse_args():
    parser = argparse.ArgumentParser(description="Run TCP measurement experiments on the receiver.")

    # Add arguments
    parser.add_argument("--config", choices=["one-to-one", "incast", "outcast", "all-to-all", "single"], default="single", help="Configuration to run the experiment with.")
    parser.add_argument("--num-connections", type=int, default=1, help="Number of connections.")
    parser.add_argument("--num-rpcs", type=int, default=0, help="Number of RPC style connections.")
    parser.add_argument('--arfs', action='store_true', default=False, help='This experiment is run with aRFS.')
    parser.add_argument("--window", type=int, default=None, help="Specify the TCP window size in KiB.")
    parser.add_argument("--output", type=str, default=None, help="Write raw output to the directory.")
    parser.add_argument("--throughput", action="store_true", help="Measure throughput in Gbps.")
    parser.add_argument("--utilisation", action="store_true", help="Measure CPU utilisation in percent.")
    parser.add_argument("--cache-miss", action="store_true", help="Measure LLC miss rate in percent.")
    parser.add_argument("--util-breakdown", action="store_true", help="Calculate CPU utilisation breakdown.")
    parser.add_argument("--cache-breakdown", action="store_true", help="Calculate CPU utilisation breakdown.")
    parser.add_argument("--flame", action="store_true", help="Create a flamegraph from the experiment.")
    parser.add_argument("--latency", action="store_true", help="Calculate the average data copy latency for each packet.")

    # Parse and verify arguments
    args = parser.parse_args()

    if not (1 <= args.num_connections <= MAX_CONNECTIONS):
        print("Can't set --num-connections outside of [1, {}].".format(MAX_CONNECTIONS))
        exit(1)

    if not (0 <= args.num_rpcs <= MAX_RPCS):
        print("Can't set --num-rpcs outside of [0, {}].".format(MAX_RPCS))
        exit(1)

    if args.num_rpcs > 0 and args.num_connections > 1:
        print("Can't use more than 1 --num-connections if using --num-rpcs.")
        exit(1)

    if args.flame and args.output is None:
        print("Please provide --output if using --flame.")
        exit(1)

    # Set CPUs to be used
    if args.config != "incast":
        args.cpus = CPUS[:args.num_connections]
    else:
        args.cpus = CPUS[:1]

    # Set IRQ processing CPUs
    if args.arfs:
        args.affinity = []
    else:
        if args.config in ["one-to-one", "all-to-all"]:
            args.affinity = CPUS
        else:
            args.affinity = [cpu + 1 for cpu in args.cpus]

    # Create the directory for writing raw outputs
    if args.output is not None:
        os.makedirs(args.output, exist_ok=True)

    # Create a list of experiments
    args.experiments = []
    if args.throughput:
        args.experiments.append("throughput")
    if args.utilisation:
        args.experiments.append("utilisation")
    if args.cache_miss:
        args.experiments.append("cache miss")
    if args.util_breakdown:
        args.experiments.append("util breakdown")
    if args.cache_breakdown:
        args.experiments.append("cache breakdown")
    if args.flame:
        args.experiments.append("flame")
    if args.latency:
        args.experiments.append("latency")

    # Return parsed and verified arguments
    return args


# Need to synchronize with the sender before starting experiment
server = xmlrpc.server.SimpleXMLRPCServer(("0.0.0.0", SENDER_COMM_PORT), logRequests=False)
server.register_introspection_functions()
server_thread = threading.Thread(target=server.serve_forever, daemon=True)


# Event objects to synchronize sender and receiver
__sender_ready = threading.Event()
__receiver_ready = threading.Event()
__sender_done = threading.Event()


# Functions to query/set synchronization events
def mark_sender_ready():
    __sender_ready.set()
    return True


def is_receiver_ready():
    __receiver_ready.wait()
    __receiver_ready.clear()
    return True


def mark_receiver_ready():
    __receiver_ready.set()
    return True


def is_sender_ready():
    __sender_ready.wait()
    __sender_ready.clear()
    return True


def mark_sender_done():
    __sender_done.set()
    return True


def is_sender_done():
    __sender_done.wait()
    __sender_done.clear()
    return True


# Register functions
server.register_function(mark_sender_ready)
server.register_function(is_receiver_ready)
server.register_function(mark_sender_done)


# Convenience functions
def clear_processes():
    os.system("pkill iperf")
    os.system("pkill perf")
    os.system("pkill sar")


def run_iperf(cpu, port, window):
    if window is None:
        args = ["taskset", "-c", str(cpu), "iperf", "-i", "1", "-s", "-p", str(port)]
    else:
        args = ["taskset", "-c", str(cpu), "iperf", "-s", "-i", "1", "-p", str(port), "-w", str(window / 2) + "K"]
    return subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, universal_newlines=True)


def run_iperfs(config, num_connections, cpus, window):
    if config in ["one-to-one", "outcast", "single"]:
        iperfs = [run_iperf(cpu, IPERF_BASE_PORT + n, window) for n, cpu in enumerate(cpus)]
    elif config == "incast":
        iperfs = [run_iperf(cpus[0], IPERF_BASE_PORT + n, window) for n in range(num_connections)]
    elif config == "all-to-all":
        iperfs = []
        for i, sender_cpu in enumerate(cpus):
            for j, receiver_cpu in enumerate(cpus):
                iperfs.append(run_iperf(receiver_cpu, IPERF_BASE_PORT + MAX_CONNECTIONS * i + j, window))
    return iperfs


def run_netperf(cpu, port):
    args = ["taskset", "-c", str(cpu), "netserver", "-p", str(port), "-D", "f", "-v", "2"]
    return subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, universal_newlines=True)


def run_netperfs(cpu, num_rpcs):
    return [run_netperf(cpu, NETPERF_BASE_PORT + i) for i in range(num_rpcs)]


def run_perf_cache(cpus):
    args = [PERF_PATH, "stat", "-C", ",".join(map(str, set(cpus))), "-e", "LLC-loads,LLC-load-misses,LLC-stores,LLC-store-misses"]
    return subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, universal_newlines=True)


def run_perf_record_util(cpus, perf_data_file):
    args = [PERF_PATH, "record", "-C", ",".join(map(str, set(cpus))), "-o", str(perf_data_file)]
    return subprocess.Popen(args, stdout=None, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, universal_newlines=True)


def run_perf_record_cache(cpus, perf_data_file):
    args = [PERF_PATH, "record", "-e", "cache-misses", "-C", ",".join(map(str, set(cpus))), "-o", str(perf_data_file)]
    return subprocess.Popen(args, stdout=None, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, universal_newlines=True)


def run_perf_record_flame(cpus, perf_data_file):
    args = [PERF_PATH, "record", "-g", "-F", "99", "-C", ",".join(map(str, set(cpus))), "-o", str(perf_data_file)]
    return subprocess.Popen(args, stdout=None, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, universal_newlines=True)


def run_perf_report(perf_data_file):
    args = ["bash", "-c", "{} report --stdio --stdio-color never --percent-limit 0.01 -i {} | cat".format(PERF_PATH, perf_data_file)]
    return subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, universal_newlines=True)


def run_flamegraph(perf_data_file, output_svg_file):
    os.system("{} script -i {} | {}/stackcollapse-perf.pl > out.perf-folded".format(PERF_PATH, perf_data_file, FLAME_PATH))
    os.system("{}/flamegraph.pl out.perf-folded > {}".format(FLAME_PATH, output_svg_file))


def run_sar(cpus):
    args = ["sar", "-u", "-P", ",".join(map(str, set(cpus))), "1", "1000"]
    return subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, universal_newlines=True)


def dmesg_clear():
    os.system("dmesg -c > /dev/null 2> /dev/null")


def run_dmesg(level="info"):
    args = ["dmesg", "-c", "-l", level]
    return subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, universal_newlines=True)


if __name__ == "__main__":
    # Parse args
    args = parse_args()

    # Start the XMLRPC server thread
    server_thread.start()

    # Run the experiments
    clear_processes()
    header = []
    output = []
    if args.throughput:
        # Wait till sender starts
        is_sender_ready()
        print("[throughput] starting experiment...")

        # Start iperf instances
        iperfs = run_iperfs(args.config, args.num_connections, args.cpus, args.window)

        # Start netperf instances
        netperfs = run_netperfs(args.cpus[0], args.num_rpcs)

        # Wait till sender is done sending
        mark_receiver_ready()
        is_sender_done()

        # Kill all the iperfs
        for p in iperfs + netperfs:
            p.kill()
        for p in iperfs + netperfs:
            p.wait()
        print("[throughput] finished experiment.")

        # Process and write the raw output
        total_throughput = 0
        for i, p in enumerate(iperfs):
            lines = p.stdout.readlines()
            if args.output is not None:
                with open(os.path.join(args.output, "throughput_iperf_{}.log".format(i)), "w") as f:
                    f.writelines(lines)
            total_throughput += process_iperf_output(lines)

        # Print the output
        print("[throughput] total throughput: {:.3f}".format(total_throughput))

    if args.utilisation:
        # Wait till sender starts
        is_sender_ready()
        print("[utilisation] starting experiment...")
        
        # Start iperf instances
        iperfs = run_iperfs(args.config, args.num_connections, args.cpus, args.window)

        # Start netperf instances
        netperfs = run_netperfs(args.cpus[0], args.num_rpcs)

        # Start the sar instance
        sar = run_sar(list(set(args.cpus + args.affinity)))

        # Wait till sender is done sending
        mark_receiver_ready()
        is_sender_done()

        # Kill all the iperfs and sar
        sar.send_signal(signal.SIGINT)
        sar.wait()
        for p in iperfs + netperfs:
            p.kill()
        for p in iperfs + netperfs:
            p.wait()
        print("[utilisation] finished experiment.")

        # Process and write the raw output
        throughput = 0
        for i, p in enumerate(iperfs):
            lines = p.stdout.readlines()
            if args.output is not None:
                with open(os.path.join(args.output, "utilisation_iperf_{}.log".format(i)), "w") as f:
                    f.writelines(lines)
            throughput += process_iperf_output(lines)

        lines = sar.stdout.readlines()
        cpu_util = sum(process_sar_output(lines).values())
        if args.output is not None:
            with open(os.path.join(args.output, "utilisation_sar.log"), "w") as f:
                f.writelines(lines)

        # Print the output
        print("[utilisation] total throughput: {:.3f}\tutilisation: {:.3f}".format(throughput, cpu_util))
        header.append("receiver utilisation (%)")
        output.append("{:.3f}".format(cpu_util))

    if args.cache_miss:
        # Wait till sender starts
        is_sender_ready()
        print("[cache miss] starting experiment...")
        
        # Start iperf instances
        iperfs = run_iperfs(args.config, args.num_connections, args.cpus, args.window)

        # Start netperf instances
        netperfs = run_netperfs(args.cpus[0], args.num_rpcs)

        # Start the perf instance
        perf = run_perf_cache(list(set(args.cpus + args.affinity)))

        # Wait till sender is done sending
        mark_receiver_ready()
        is_sender_done()

        # Kill all the iperfs and perf
        perf.send_signal(signal.SIGINT)
        perf.wait()
        for p in iperfs + netperfs:
            p.kill()
        for p in iperfs + netperfs:
            p.wait()
        print("[cache miss] finished experiment.")

        # Process and write the raw output
        throughput = 0
        for i, p in enumerate(iperfs):
            lines = p.stdout.readlines()
            if args.output is not None:
                with open(os.path.join(args.output, "cache-miss_iperf_{}.log".format(i)), "w") as f:
                    f.writelines(lines)
            throughput += process_iperf_output(lines)

        lines = perf.stdout.readlines()
        cache_miss = process_perf_cache_output(lines)
        if args.output is not None:
            with open(os.path.join(args.output, "cache-miss_perf.log"), "w") as f:
                f.writelines(lines)

        # Print the output
        print("[cache miss] total throughput: {:.3f}\tcache miss: {:.3f}".format(throughput, cache_miss))
        header.append("receiver cache miss (%)")
        output.append("{:.3f}".format(cache_miss))

    if args.util_breakdown:
        # Wait till sender starts
        is_sender_ready()
        print("[util breakdown] starting experiment...")

        # Start iperf instances
        iperfs = run_iperfs(args.config, args.num_connections, args.cpus, args.window)

        # Start netperf instances
        netperfs = run_netperfs(args.cpus[0], args.num_rpcs)

        # Start the perf instance
        output_dir = tempfile.TemporaryDirectory()
        perf_data_file = os.path.join(output_dir.name, PERF_DATA)
        perf = run_perf_record_util(list(set(args.cpus + args.affinity)), perf_data_file)

        # Wait till sender is done sending
        mark_receiver_ready()
        is_sender_done()

        # Kill all the iperfs and perf
        perf.send_signal(signal.SIGINT)
        perf.wait()
        for p in iperfs + netperfs:
            p.kill()
        for p in iperfs + netperfs:
            p.wait()
        print("[util breakdown] finished experiment.")

        # Process and write the raw output
        throughput = 0
        for i, p in enumerate(iperfs):
            lines = p.stdout.readlines()
            if args.output is not None:
                with open(os.path.join(args.output, "util-breakdown_iperf_{}.log".format(i)), "w") as f:
                    f.writelines(lines)
            throughput += process_iperf_output(lines)

        # Start a perf report instance
        perf = run_perf_report(perf_data_file)
        perf.wait()
        output_dir.cleanup()
        lines = perf.stdout.readlines()
        total_contrib, unaccounted_contrib, util_contibutions, not_found = process_perf_report_output(lines)
        if args.output is not None:
            with open(os.path.join(args.output, "util-breakdown_perf.log"), "w") as f:
                f.writelines(lines)

        # Print the output
        print("[util breakdown] total throughput: {:.3f}\ttotal contribution: {:.3f}\tunaccounted contribution: {:.3f}".format(throughput, total_contrib, unaccounted_contrib))
        if unaccounted_contrib > 5:
            print("[util breakdown] unknown symbols: {}".format(", ".join(not_found)))

    if args.cache_breakdown:
        # Wait till sender starts
        is_sender_ready()
        print("[cache breakdown] starting experiment...")

        # Start iperf instances
        iperfs = run_iperfs(args.config, args.num_connections, args.cpus, args.window)

        # Start netperf instances
        netperfs = run_netperfs(args.cpus[0], args.num_rpcs)

        # Start the perf instance
        output_dir = tempfile.TemporaryDirectory()
        perf_data_file = os.path.join(output_dir.name, PERF_DATA)
        perf = run_perf_record_cache(list(set(args.cpus + args.affinity)), perf_data_file)

        # Wait till sender is done sending
        mark_receiver_ready()
        is_sender_done()

        # Kill all the iperfs and perf
        perf.send_signal(signal.SIGINT)
        perf.wait()
        for p in iperfs + netperfs:
            p.kill()
        for p in iperfs + netperfs:
            p.wait()
        print("[cache breakdown] finished experiment.")

        # Process and write the raw output
        throughput = 0
        for i, p in enumerate(iperfs):
            lines = p.stdout.readlines()
            if args.output is not None:
                with open(os.path.join(args.output, "cache-breakdown_iperf_{}.log".format(i)), "w") as f:
                    f.writelines(lines)
            throughput += process_iperf_output(lines)

        # Start a perf report instance
        perf = run_perf_report(perf_data_file)
        perf.wait()
        output_dir.cleanup()
        lines = perf.stdout.readlines()
        total_contrib, unaccounted_contrib, cache_contibutions, not_found = process_perf_report_output(lines)
        if args.output is not None:
            with open(os.path.join(args.output, "cache-breakdown_perf.log"), "w") as f:
                f.writelines(lines)

        # Print the output
        print("[cache breakdown] total throughput: {:.3f}\ttotal contribution: {:.3f}\tunaccounted contribution: {:.3f}".format(throughput, total_contrib, unaccounted_contrib))
        if unaccounted_contrib > 5:
            print("[cache breakdown] unknown symbols: {}".format(", ".join(not_found)))

    if args.flame:
        # Wait till sender starts
        is_sender_ready()
        print("[flame] starting experiment...")

        # Start iperf instances
        iperfs = run_iperfs(args.config, args.num_connections, args.cpus, args.window)

        # Start netperf instances
        netperfs = run_netperfs(args.cpus[0], args.num_rpcs)

        # Start the perf instance
        output_dir = tempfile.TemporaryDirectory()
        perf_data_file = os.path.join(output_dir.name, PERF_DATA)
        perf = run_perf_record_flame(list(set(args.cpus + args.affinity)), perf_data_file)

        # Wait till sender is done sending
        mark_receiver_ready()
        is_sender_done()

        # Kill all the iperfs and perf
        perf.send_signal(signal.SIGINT)
        perf.wait()
        for p in iperfs + netperfs:
            p.kill()
        for p in iperfs + netperfs:
            p.wait()
        print("[flame] finished experiment.")

        # Process and write the raw output
        throughput = 0
        for i, p in enumerate(iperfs):
            lines = p.stdout.readlines()
            if args.output is not None:
                with open(os.path.join(args.output, "flame_iperf_{}.log".format(i)), "w") as f:
                    f.writelines(lines)
            throughput += process_iperf_output(lines)

        # Start a perf report instance
        output_svg_file = os.path.join(args.output, "flame.svg")
        run_flamegraph(perf_data_file, output_svg_file)
        output_dir.cleanup()

        # Print the output
        print("[flame] total throughput: {:.3f}".format(throughput))

    if args.latency:
        # Clear dmesg
        dmesg_clear()

        # Wait till sender starts
        is_sender_ready()
        print("[latency] starting experiment...")

        # Start iperf instances
        iperfs = run_iperfs(args.config, args.num_connections, args.cpus, args.window)

        # Start netperf instances
        netperfs = run_netperfs(args.cpus[0], args.num_rpcs)

        # Wait till sender is done sending
        mark_receiver_ready()
        is_sender_done()

        # Kill all the iperfs and dmesg
        for p in iperfs + netperfs:
            p.kill()
        for p in iperfs + netperfs:
            p.wait()
        print("[latency] finished experiment.")

        # Process and write the raw output
        throughput = 0
        for i, p in enumerate(iperfs):
            lines = p.stdout.readlines()
            if args.output is not None:
                with open(os.path.join(args.output, "latency_iperf_{}.log".format(i)), "w") as f:
                    f.writelines(lines)
            throughput += process_iperf_output(lines)

        # Start a dmesg instance to read the kernel logs
        dmesg = run_dmesg()
        lines = []
        while True:
            new_lines = dmesg.stdout.readlines()
            lines += new_lines
            if len(new_lines) == 0 and dmesg.poll() != None:
                break
        if args.output is not None:
            with open(os.path.join(args.output, "latency_dmesg.log"), "w") as f:
                f.writelines(lines)
        avg_latency, tail_latency = process_dmesg_output(lines)

        # Print the output
        print("[latency] total throughput: {:.3f}\tavg. data copy latency: {:.3f}\ttail data copy latency: {}".format(throughput, avg_latency, tail_latency))
        header.append("avg. data copy latency (us)")
        output.append("{:.3f}".format(avg_latency))
        header.append("tail data copy latency (us)")
        output.append("{}".format(tail_latency))


    # Sync with server again
    mark_receiver_ready()
    is_sender_ready()

    # Close the server
    server.shutdown()
    server_thread.join()

    # Print final stats
    if len(header) > 0:
        print("\t".join(header))
        print("\t".join(output))

    # Print breakdown if required
    if args.util_breakdown:
        keys = sorted(util_contibutions.keys())
        print("\t".join(keys))
        print("\t".join(["{:.3f}".format(util_contibutions[k]) for k in keys]))

    # Print breakdown if required
    if args.cache_breakdown:
        keys = sorted(cache_contibutions.keys())
        print("\t".join(keys))
        print("\t".join(["{:.3f}".format(cache_contibutions[k]) for k in keys]))

    

