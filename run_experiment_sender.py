#!/usr/bin/env python3

import argparse
import os
import shlex
import signal
import subprocess as _sp
import tempfile
import threading
import time
import xmlrpc.client
from constants import *
from process_output import *


# For debugging
class subprocess:
    PIPE = _sp.PIPE
    DEVNULL = _sp.DEVNULL
    STDOUT = _sp.STDOUT
    VERBOSE = False

    @staticmethod
    def enable_logging():
        subprocess.VERBOSE = True

    @staticmethod
    def Popen(*args, **kwargs):
        if subprocess.VERBOSE: print("+ " + " ".join(shlex.quote(s) for s in args[0]))
        return _sp.Popen(*args, **kwargs)


def parse_args():
    parser = argparse.ArgumentParser(description="Run TCP measurement experiments on the sender.")

    # Add arguments
    parser.add_argument("--receiver", required=True, type=str, help="Address of the receiver to communicate metadata.")
    parser.add_argument("--flow-type", choices=["long", "short", "mixed"], default="long", help="Type of flow used for the experiment.")
    parser.add_argument("--addr", required=True, type=str, help="Address of the receiver interface to run experiments on.")
    parser.add_argument("--config", choices=["one-to-one", "incast", "outcast", "all-to-all", "single"], default="single", help="Configuration to run the experiment with.")
    parser.add_argument("--cpus", type=int, nargs="*", help="Which CPUs to use for experiment.")
    parser.add_argument("--affinity", type=int, nargs="*", help="Which CPUs are being used for IRQ processing.")
    parser.add_argument("--num-connections", type=int, default=1, help="Number of connections.")
    parser.add_argument("--rpc-size", type=int, default=4000, help="Size of the RPC for short flows.")
    parser.add_argument("--num-rpcs", type=int, default=0, help="Number of short flows (for mixed flow type).")
    parser.add_argument("--arfs", action="store_true", default=False, help="This experiment is run with aRFS.")
    parser.add_argument("--duration", type=int, default=20, help="Duration of the experiment in seconds.")
    parser.add_argument("--window", type=int, default=None, help="Specify the TCP window size (KB).")
    parser.add_argument("--output", type=str, default=None, help="Write raw output to the directory.")
    parser.add_argument("--throughput", action="store_true", help="Measure throughput.")
    parser.add_argument("--utilisation", action="store_true", help="Measure CPU utilisation.")
    parser.add_argument("--cache-miss", action="store_true", help="Measure LLC miss rate.")
    parser.add_argument("--util-breakdown", action="store_true", help="Calculate CPU utilisation breakdown.")
    parser.add_argument("--cache-breakdown", action="store_true", help="Calculate cache miss breakdown.")
    parser.add_argument("--flame", action="store_true", help="Create a flame graph from the experiment.")
    parser.add_argument("--latency", action="store_true", help="Calculate the average data copy latency for each packet.")
    parser.add_argument("--skb-hist", action="store_true", help="Record the skb sizes histogram.")
    parser.add_argument("--verbose", action="store_true", help="Print extra output.")

    # Parse and verify arguments
    args = parser.parse_args()

    # Report errors
    if args.config == "single" and args.num_connections != 1:
        print("Can't set --num-connections > 1 with --config single.")
        exit(1)

    if args.flow_type == "mixed" and args.config != "single":
        print("Can't set --flow-type mixed without --config single.")
        exit(1)

    if not (1 <= args.num_connections <= MAX_CONNECTIONS):
        print("Can't set --num-connections outside of [1, {}].".format(MAX_CONNECTIONS))
        exit(1)

    if args.flow_type != "mixed" and args.num_rpcs > 0:
        print("Can't set --num-rpcs > 0 without --flow-type mixed.")
        exit(1)

    if args.window is not None and args.flow_type != "long":
        print("Can't set --window for --flow-type short/mixed.")
        exit(1)

    if not (0 <= args.num_rpcs <= MAX_RPCS):
        print("Can't set --num-rpcs outside of [0, {}].".format(MAX_RPCS))
        exit(1)

    if not (0 <= args.num_rpcs <= MAX_RPCS):
        print("Can't set --num-rpcs outside of [0, {}].".format(MAX_RPCS))
        exit(1)

    if not (5 <= args.duration <= 60):
        print("Can't set --duration outside of [5, 60].")
        exit(1)

    if args.flame and args.output is None:
        print("Please provide --output if using --flame.")
        exit(1)

    # Set CPUs to be used
    if args.cpus is not None:
        if args.config in ["single", "outcast"] and len(args.cpus) != 1:
            print("Please provide only 1 --cpus for --config outcast/single.")
            exit(1)

        if args.config in ["one-to-one", "incast", "all-to-all"] and len(args.cpus) != args.num_connections:
            print("Please provide as many --cpus as --num-connections for --config incast/one-to-one/all-to-all.")
            exit(1)

        if not all(map(lambda c: 0 <= c < MAX_CPUS, args.cpus)):
            print("Can't set --cpus outside of [0, {}].".format(MAX_CPUS))
            exit(1)
    else:
        if args.config in ["outcast", "single"]:
            args.cpus = [0]
        else:
            args.cpus = list(range(args.num_connections))

    if args.arfs and args.affinity is not None:
        print("Can't set --affinity with --arfs.")
        exit(0)

    # Set IRQ processing CPUs
    if args.affinity is not None:
        if not all(map(lambda c: 0 <= c < MAX_CPUS, args.affinity)):
            print("Can't set --affinity outside of [0, {}].".format(MAX_CPUS))
            exit(1)
    elif not args.arfs:
        if args.config in ["outcast", "single"]:
            args.affinity = [1]
        elif args.config in ["incast", "one-to-one"]:
            args.affinity = [cpu + 1 for cpu in args.cpus]
        elif args.config == "all-to-all":
            args.affinity = list(range(MAX_CPUS))
    else:
        args.affinity = []

    # Create the directory for writing raw outputs
    if args.output is not None:
        os.makedirs(args.output, exist_ok=True)

    # Return parsed and verified arguments
    return args


# Convenience functions
def clear_processes():
    os.system("pkill iperf")
    os.system("pkill netserver")
    os.system("pkill netperf")
    os.system("pkill perf")
    os.system("pkill sar")


def run_iperf(cpu, addr, port, duration, window):
    if window is None:
        args = ["taskset", "-c", str(cpu), "iperf", "-i", "1", "-c", addr, "-t", str(duration), "-p", str(port)]
    else:
        args = ["taskset", "-c", str(cpu), "iperf", "-i", "1", "-c", addr, "-t", str(duration), "-p", str(port), "-w", str(window / 2) + "K"]

    return subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, universal_newlines=True)


def run_netperf(cpu, addr, port, duration, rpc_size):
    args = ["taskset", "-c", str(cpu), "netperf", "-H", addr, "-t", "TCP_RR", "-l", str(duration), "-p", str(port), "-f", "g", "--", "-r", "{0},{0}".format(rpc_size), "-o", "throughput"]

    return subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, universal_newlines=True)


# We run one iperf client process per flow, and one netperf process per flow
def run_flows(flow_type, config, addr, num_connections, num_rpcs, cpus, duration, window, rpc_size):
    procs = []
    if flow_type == "mixed":
        procs.append(run_iperf(cpus[0], addr, BASE_PORT, duration, window))
        for _ in range(num_rpcs):
            procs.append(run_netperf(cpus[0], addr, ADDITIONAL_BASE_PORT, duration, rpc_size))
    elif flow_type == "long":
        if config == "single":
            procs.append(run_iperf(cpus[0], addr, BASE_PORT, duration, window))
        elif config == "outcast":
            procs += [run_iperf(cpus[0], addr, BASE_PORT + n, duration, window) for n in range(num_connections)]
        elif config in ["incast", "one-to-one"]:
            procs += [run_iperf(cpu, addr, BASE_PORT + n, duration, window) for n, cpu in enumerate(cpus)]
        else:
            for i, sender_cpu in enumerate(cpus):
                for j, receiver_cpu in enumerate(cpus):
                    procs.append(run_iperf(sender_cpu, addr, BASE_PORT + i * MAX_CONNECTIONS + j, duration, window))
    else:
        if config == "single":
            procs.append(run_netperf(cpus[0], addr, BASE_PORT, duration, rpc_size))
        elif config == "incast":
            procs += [run_netperf(cpu, addr, BASE_PORT, duration, rpc_size) for cpu in cpus]
        elif config == "outcast":
            procs += [run_netperf(cpus[0], addr, BASE_PORT + n, duration, rpc_size) for n in range(num_connections)]
        elif config == "one-to-one":
            procs += [run_netperf(cpu, addr, BASE_PORT + n, duration, rpc_size) for n, cpu in enumerate(cpus)]
        else:
            for i, sender_cpu in enumerate(cpus):
                for j, receiver_cpu in enumerate(cpus):
                    procs.append(run_netperf(sender_cpu, addr, BASE_PORT + j, duration, rpc_size))

    return procs


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


if __name__ == "__main__":
    # Parse args
    args = parse_args()
    if args.verbose:
        subprocess.enable_logging()

    # Create the XMLRPC proxy
    receiver = xmlrpc.client.ServerProxy("http://{}:{}".format(args.receiver, COMM_PORT), allow_none=True)

    # Wait till receiver is ready
    while True:
        try:
            receiver.system.listMethods()
            break
        except ConnectionRefusedError:
            time.sleep(1)

    # Print the output directory
    if args.output is not None:
        print("[output] writing results to {}".format(args.output))

    # Run the experiments
    clear_processes()
    header = []
    output = []
    if args.throughput:
        # Wait till receiver starts
        receiver.mark_sender_ready()
        receiver.is_receiver_ready()
        print("[throughput] starting experiment...")

        # Start iperf and/or netperf instances
        procs = run_flows(args.flow_type, args.config, args.addr, args.num_connections, args.num_rpcs, args.cpus, args.duration, args.window, args.rpc_size)

        # Wait till all experiments finish
        for p in procs:
            p.wait()

        # Sender is done sending
        receiver.mark_sender_done()
        print("[throughput] finished experiment.")

        # Process and write the raw output
        total_throughput = 0
        for i, p in enumerate(procs):
            lines = p.stdout.readlines()
            if args.output is not None:
                with open(os.path.join(args.output, "throughput_benchmark_{}.log".format(i)), "w") as f:
                    f.writelines(lines)
            total_throughput += process_throughput_output(lines)

        # Print the output
        print("[throughput] total throughput: {:.3f}".format(total_throughput))
        header.append("throughput (Gbps)")
        output.append("{:.3f}".format(total_throughput))

    if args.utilisation:
        # Wait till receiver starts
        receiver.mark_sender_ready()
        receiver.is_receiver_ready()
        print("[utilisation] starting experiment...")

        # Start iperf and/or netperf instances
        procs = run_flows(args.flow_type, args.config, args.addr, args.num_connections, args.num_rpcs, args.cpus, args.duration, args.window, args.rpc_size)

        # Start the sar instance
        sar = run_sar(list(set(args.cpus + args.affinity)))

        # Wait till all experiments finish
        for p in procs:
            p.wait()

        # Sender is done sending
        receiver.mark_sender_done()

        # Kill the sar instance
        sar.send_signal(signal.SIGINT)
        sar.wait()
        print("[utilisation] finished experiment.")

        # Process and write the raw output
        throughput = 0
        for i, p in enumerate(procs):
            lines = p.stdout.readlines()
            if args.output is not None:
                with open(os.path.join(args.output, "utilisation_benchmark_{}.log".format(i)), "w") as f:
                    f.writelines(lines)
            throughput += process_throughput_output(lines)

        lines = sar.stdout.readlines()
        cpu_util = sum(process_util_output(lines).values())
        if args.output is not None:
            with open(os.path.join(args.output, "utilisation_sar.log"), "w") as f:
                f.writelines(lines)

        # Print the output
        print("[utilisation] total throughput: {:.3f}\tutilisation: {:.3f}".format(throughput, cpu_util))
        header.append("sender utilisation (%)")
        output.append("{:.3f}".format(cpu_util))

    if args.cache_miss:
        # Wait till receiver starts
        receiver.mark_sender_ready()
        receiver.is_receiver_ready()
        print("[cache miss] starting experiment...")

        # Start iperf and/or netperf instances
        procs = run_flows(args.flow_type, args.config, args.addr, args.num_connections, args.num_rpcs, args.cpus, args.duration, args.window, args.rpc_size)

        # Start the perf instance
        perf = run_perf_cache(list(set(args.cpus + args.affinity)))

        # Wait till all experiments finish
        for p in procs:
            p.wait()

        # Sender is done sending
        receiver.mark_sender_done()

        # Kill the perf instance
        perf.send_signal(signal.SIGINT)
        perf.wait()
        print("[cache miss] finished experiment.")

        # Process and write the raw output
        throughput = 0
        for i, p in enumerate(procs):
            lines = p.stdout.readlines()
            if args.output is not None:
                with open(os.path.join(args.output, "cache-miss_benchmark_{}.log".format(i)), "w") as f:
                    f.writelines(lines)
            throughput += process_throughput_output(lines)

        lines = perf.stdout.readlines()
        cache_miss = process_cache_miss_output(lines)
        if args.output is not None:
            with open(os.path.join(args.output, "cache-miss_perf.log"), "w") as f:
                f.writelines(lines)

        # Print the output
        print("[cache miss] total throughput: {:.3f}\tcache miss: {:.3f}".format(throughput, cache_miss))
        header.append("sender cache miss (%)")
        output.append("{:.3f}".format(cache_miss))

    if args.util_breakdown:
        # Wait till receiver starts
        receiver.mark_sender_ready()
        receiver.is_receiver_ready()
        print("[util breakdown] starting experiment...")

        # Start iperf and/or netperf instances
        procs = run_flows(args.flow_type, args.config, args.addr, args.num_connections, args.num_rpcs, args.cpus, args.duration, args.window, args.rpc_size)

        # Start the perf instance
        output_dir = tempfile.TemporaryDirectory()
        perf_data_file = os.path.join(output_dir.name, "perf.data")
        perf = run_perf_record_util(list(set(args.cpus + args.affinity)), perf_data_file)

        # Wait till all experiments finish
        for p in procs:
            p.wait()

        # Sender is done sending
        receiver.mark_sender_done()

        # Kill the perf instance
        perf.send_signal(signal.SIGINT)
        perf.wait()
        print("[util breakdown] finished experiment.")

        # Process and write the raw output
        throughput = 0
        for i, p in enumerate(procs):
            lines = p.stdout.readlines()
            if args.output is not None:
                with open(os.path.join(args.output, "util-breakdown_benchmark_{}.log".format(i)), "w") as f:
                    f.writelines(lines)
            throughput += process_throughput_output(lines)

        # Run a perf report instance
        perf = run_perf_report(perf_data_file)
        lines = []
        while True:
            new_lines =  perf.stdout.readlines()
            lines += new_lines
            if len(new_lines) == 0:
                break
        perf.wait()
        output_dir.cleanup()
        total_contrib, unaccounted_contrib, util_contibutions, not_found = process_util_breakdown_output(lines)
        if args.output is not None:
            with open(os.path.join(args.output, "util-breakdown_perf.log"), "w") as f:
                f.writelines(lines)

        # Print the output
        print("[util breakdown] total throughput: {:.3f}\ttotal contribution: {:.3f}\tunaccounted contribution: {:.3f}".format(throughput, total_contrib, unaccounted_contrib))
        if unaccounted_contrib > 5 and args.verbose:
            print("[util breakdown] unknown symbols: {}".format(", ".join(not_found)))

    if args.cache_breakdown:
        # Wait till receiver starts
        receiver.mark_sender_ready()
        receiver.is_receiver_ready()
        print("[cache breakdown] starting experiment...")

        # Start iperf and/or netperf instances
        procs = run_flows(args.flow_type, args.config, args.addr, args.num_connections, args.num_rpcs, args.cpus, args.duration, args.window, args.rpc_size)

        # Start the perf instance
        output_dir = tempfile.TemporaryDirectory()
        perf_data_file = os.path.join(output_dir.name, "perf.data")
        perf = run_perf_record_cache(list(set(args.cpus + args.affinity)), perf_data_file)

        # Wait till all experiments finish
        for p in procs:
            p.wait()

        # Sender is done sending
        receiver.mark_sender_done()

        # Kill the perf instance
        perf.send_signal(signal.SIGINT)
        perf.wait()
        print("[cache breakdown] finished experiment.")

        # Process and write the raw output
        throughput = 0
        for i, p in enumerate(procs):
            lines = p.stdout.readlines()
            if args.output is not None:
                with open(os.path.join(args.output, "cache-breakdown_benchmark_{}.log".format(i)), "w") as f:
                    f.writelines(lines)
            throughput += process_throughput_output(lines)

        # Run a perf report instance
        perf = run_perf_report(perf_data_file)
        lines = []
        while True:
            new_lines =  perf.stdout.readlines()
            lines += new_lines
            if len(new_lines) == 0:
                break
        perf.wait()
        total_contrib, unaccounted_contrib, cache_contibutions, not_found = process_util_breakdown_output(lines)
        if args.output is not None:
            with open(os.path.join(args.output, "cache-breakdown_perf.log"), "w") as f:
                f.writelines(lines)

        # Print the output
        print("[cache breakdown] total throughput: {:.3f}\ttotal contribution: {:.3f}\tunaccounted contribution: {:.3f}".format(throughput, total_contrib, unaccounted_contrib))
        if unaccounted_contrib > 5 and not args.verbose:
            print("[cache breakdown] unknown symbols: {}".format(", ".join(not_found)))

    if args.flame:
        # Wait till receiver starts
        receiver.mark_sender_ready()
        receiver.is_receiver_ready()
        print("[flame] starting experiment...")

        # Start iperf and/or netperf instances
        procs = run_flows(args.flow_type, args.config, args.addr, args.num_connections, args.num_rpcs, args.cpus, args.duration, args.window, args.rpc_size)

        # Start the perf instance
        output_dir = tempfile.TemporaryDirectory()
        perf_data_file = os.path.join(output_dir.name, "perf.data")
        perf = run_perf_record_flame(list(set(args.cpus + args.affinity)), perf_data_file)

        # Wait till all experiments finish
        for p in procs:
            p.wait()

        # Sender is done sending
        receiver.mark_sender_done()

        # Kill the perf instance
        perf.send_signal(signal.SIGINT)
        perf.wait()
        print("[flame] finished experiment.")

        # Process and write the raw output
        throughput = 0
        for i, p in enumerate(procs):
            lines = p.stdout.readlines()
            if args.output is not None:
                with open(os.path.join(args.output, "flame_benchmark_{}.log".format(i)), "w") as f:
                    f.writelines(lines)
            throughput += process_throughput_output(lines)

        # Run a perf report instance
        output_svg_file = os.path.join(args.output, "flame.svg")
        run_flamegraph(perf_data_file, output_svg_file)
        output_dir.cleanup()

        # Print the output
        print("[flame] total throughput: {:.3f}".format(throughput))

    if args.latency:
        # Wait till receiver starts
        receiver.mark_sender_ready()
        receiver.is_receiver_ready()
        print("[latency] starting experiment...")

        # Start iperf and/or netperf instances
        procs = run_flows(args.flow_type, args.config, args.addr, args.num_connections, args.num_rpcs, args.cpus, args.duration, args.window, args.rpc_size)

        # Wait till all experiments finish
        for p in procs:
            p.wait()

        # Sender is done sending
        receiver.mark_sender_done()
        print("[latency] finished experiment.")

        # Process and write the raw output
        throughput = 0
        for i, p in enumerate(procs):
            lines = p.stdout.readlines()
            if args.output is not None:
                with open(os.path.join(args.output, "latency_benchmark_{}.log".format(i)), "w") as f:
                    f.writelines(lines)
            throughput += process_throughput_output(lines)

        # Print the output
        print("[latency] total throughput: {:.3f}".format(throughput))

    if args.skb_hist:
        # Wait till receiver starts
        receiver.mark_sender_ready()
        receiver.is_receiver_ready()
        print("[skb hist] starting experiment...")

        # Start iperf and/or netperf instances
        procs = run_flows(args.flow_type, args.config, args.addr, args.num_connections, args.num_rpcs, args.cpus, args.duration, args.window, args.rpc_size)

        # Wait till all experiments finish
        for p in procs:
            p.wait()

        # Sender is done sending
        receiver.mark_sender_done()
        print("[skb hist] finished experiment.")

        # Process and write the raw output
        throughput = 0
        for i, p in enumerate(procs):
            lines = p.stdout.readlines()
            if args.output is not None:
                with open(os.path.join(args.output, "skb-hist_benchmark_{}.log".format(i)), "w") as f:
                    f.writelines(lines)
            throughput += process_throughput_output(lines)

        # Print the output
        print("[skb hist] total throughput: {:.3f}".format(throughput))

    # Sync with receiver before exiting
    receiver.is_receiver_ready()

    # Get the results from receiver-side
    receiver_results = receiver.get_results()
    header += receiver_results["header"]
    output += receiver_results["output"]
    if args.throughput and args.utilisation:
        header.append("throughput per core (Gbps)")
        if args.config == "outcast":
            output.append("{:.3f}".format(total_throughput * 100 / cpu_util))
        else:
            output.append("{:.3f}".format(total_throughput * 100 / receiver_results["cpu_util"]))

    # Mark sender as done
    receiver.mark_sender_ready()

    # Sleep before beginning the next experiment
    time.sleep(1)

    # Print final stats
    if len(header) > 0 or args.util_breakdown or args.cache_breakdown:
        print("[summary]")

    if len(header) > 0:
        print("\t".join(header))
        print("\t".join(output))

    # Print utilisation breakdown if required
    if args.util_breakdown:
        keys = sorted(util_contibutions.keys())
        print("[sender utilisation breakdown]")
        print("\t".join(keys))
        print("\t".join(["{:.3f}".format(util_contibutions[k]) for k in keys]))

        util_contibutions = receiver_results["util_contibutions"]
        keys = sorted(util_contibutions.keys())
        print("[receiver utilisation breakdown]")
        print("\t".join(keys))
        print("\t".join(["{:.3f}".format(util_contibutions[k]) for k in keys]))

    # Print cache breakdown if required
    if args.cache_breakdown:
        keys = sorted(cache_contibutions.keys())
        print("[sender cache breakdown]")
        print("\t".join(keys))
        print("\t".join(["{:.3f}".format(cache_contibutions[k]) for k in keys]))

        cache_contibutions = receiver_results["cache_contibutions"]
        keys = sorted(cache_contibutions.keys())
        print("[receiver cache breakdown]")
        print("\t".join(keys))
        print("\t".join(["{:.3f}".format(cache_contibutions[k]) for k in keys]))

    # Print skb sizes histogram
    if args.skb_hist:
        skb_sizes = receiver_results["skb_sizes"]
        keys = ["{}-{}".format(a, b) for a, b in zip(range(0, 65, 5), range(5, 70, 5))]
        print("[skb sizes histogram]")
        print("\t".join(keys))
        print("\t".join(["{:.3f}".format(s) for s in skb_sizes]))

