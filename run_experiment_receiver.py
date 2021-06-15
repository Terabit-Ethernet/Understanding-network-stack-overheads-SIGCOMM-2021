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
    parser = argparse.ArgumentParser(description="Run TCP measurement experiments on the receiver.")

    # Add arguments
    parser.add_argument("--flow-type", choices=["long", "short", "mixed"], default="long", help="Type of flow used for the experiment.")
    parser.add_argument("--config", choices=["one-to-one", "incast", "outcast", "all-to-all", "single"], default="single", help="Configuration to run the experiment with.")
    parser.add_argument("--cpus", type=int, nargs="*", help="Which CPUs to use for experiment.")
    parser.add_argument("--affinity", type=int, nargs="*", help="Which CPUs are being used for IRQ processing.")
    parser.add_argument("--num-connections", type=int, default=1, help="Number of connections.")
    parser.add_argument("--arfs", action="store_true", default=False, help="This experiment is run with aRFS.")
    parser.add_argument("--window", type=int, default=None, help="Specify the TCP window size (KB).")
    parser.add_argument("--packet-drop", type=int, default=0, help="Inverse packet drop rate.")
    parser.add_argument("--output", type=str, default=None, help="Write raw output to the directory.")
    parser.add_argument("--throughput", action="store_true", help="Measure throughput.")
    parser.add_argument("--utilisation", action="store_true", help="Measure CPU utilisation.")
    parser.add_argument("--cache-miss", action="store_true", help="Measure LLC miss rate.")
    parser.add_argument("--util-breakdown", action="store_true", help="Calculate CPU utilisation breakdown.")
    parser.add_argument("--cache-breakdown", action="store_true", help="Calculate CPU utilisation breakdown.")
    parser.add_argument("--flame", action="store_true", help="Create a flamegraph from the experiment.")
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
        print("--flow-type mixed can only be combined with --config single.")
        exit(1)

    if not (1 <= args.num_connections <= MAX_CONNECTIONS):
        print("Can't set --num-connections outside of [1, {}].".format(MAX_CONNECTIONS))
        exit(1)

    if args.window is not None and args.flow_type != "long":
        print("Can't set --window for --flow-type short/mixed.")
        exit(1)

    if args.flame and args.output is None:
        print("Please provide --output if using --flame.")
        exit(1)

    # Set CPUs to be used
    if args.cpus is not None:
        if args.config in ["single", "incast"] and len(args.cpus) != 1:
            print("Please provide only 1 --cpus for --config incast/single.")
            exit(1)

        if args.config in ["one-to-one", "outcast", "all-to-all"] and len(args.cpus) != args.num_connections:
            print("Please provide as many --cpus as --num-connections for --config outcast/one-to-one/all-to-all.")
            exit(1)

        if not all(map(lambda c: 0 <= c < MAX_CPUS, args.cpus)):
            print("Can't set --cpus outside of [0, {}].".format(MAX_CPUS))
            exit(1)
    else:
        if args.config in ["incast", "single"]:
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
        if args.config in ["incast", "single"]:
            args.affinity = [1]
        elif args.config in ["outcast", "one-to-one"]:
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


# Need to synchronize with the sender before starting experiment
server = xmlrpc.server.SimpleXMLRPCServer(("0.0.0.0", COMM_PORT), logRequests=False)
server.register_introspection_functions()
server_thread = threading.Thread(target=server.serve_forever, daemon=True)


# Event objects to synchronize sender and receiver
__sender_ready = threading.Event()
__receiver_ready = threading.Event()
__sender_done = threading.Event()


# Stores the results from the receiver
__results = {}


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


def get_results():
    return __results


# Register functions
server.register_function(mark_sender_ready)
server.register_function(is_receiver_ready)
server.register_function(mark_sender_done)
server.register_function(get_results)


# Convenience functions
def clear_processes():
    os.system("pkill iperf")
    os.system("pkill netserver")
    os.system("pkill netperf")
    os.system("pkill perf")
    os.system("pkill sar")


def run_iperf(cpu, port, window):
    if window is None:
        args = ["taskset", "-c", str(cpu), "iperf", "-i", "1", "-s", "-p", str(port)]
    else:
        args = ["taskset", "-c", str(cpu), "iperf", "-s", "-i", "1", "-p", str(port), "-w", str(window / 2) + "K"]

    return subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, universal_newlines=True)


def run_netperf(cpu, port):
    args = ["taskset", "-c", str(cpu), "netserver", "-p", str(port), "-D", "f"]

    return subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, universal_newlines=True)


# We run one iperf server process per flow, and one netserver process per CPU
def run_flows(flow_type, config, num_connections, cpus, window):
    procs = []
    if flow_type == "mixed":
        procs.append(run_iperf(cpus[0], BASE_PORT, window))
        procs.append(run_netperf(cpus[0], ADDITIONAL_BASE_PORT))
    elif flow_type == "long":
        if config == "single":
            procs.append(run_iperf(cpus[0], BASE_PORT, window))
        elif config == "incast":
            procs += [run_iperf(cpus[0], BASE_PORT + n, window) for n in range(num_connections)]
        elif config in ["outcast", "one-to-one"]:
            procs += [run_iperf(cpu, BASE_PORT + n, window) for n, cpu in enumerate(cpus)]
        else:
            for i, sender_cpu in enumerate(cpus):
                for j, receiver_cpu in enumerate(cpus):
                    procs.append(run_iperf(receiver_cpu, BASE_PORT + i * MAX_CONNECTIONS + j, window))
    else:
        if config in ["single", "incast"]:
            procs.append(run_netperf(cpus[0], BASE_PORT))
        else:
            procs += [run_netperf(cpu, BASE_PORT + n) for n, cpu in enumerate(cpus)]

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


def dmesg_clear():
    os.system("dmesg -c > /dev/null 2> /dev/null")


def run_dmesg(level="info"):
    args = ["dmesg", "-c", "-l", level]
    return subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, universal_newlines=True)


def latency_measurement(enabled):
    os.system("echo {} > /sys/module/tcp/parameters/measure_latency_on".format(int(enabled)))


def skb_hist_measurement(enabled):
    os.system("echo {} > /sys/module/ip_input/parameters/skb_size_hist_on".format(int(enabled)))


def set_packet_drop_rate(rate):
    os.system("sysctl -w net.core.packet_loss_gen={}".format(rate))


if __name__ == "__main__":
    # Parse args
    args = parse_args()
    if args.verbose:
        subprocess.enable_logging()

    # Start the XMLRPC server thread
    server_thread.start()

    # Set packet drop rate
    set_packet_drop_rate(args.packet_drop)

    # Print the output directory
    if args.output is not None:
        print("[output] writing results to {}".format(args.output))

    # Run the experiments
    clear_processes()
    header = []
    output = []
    if args.throughput:
        # Wait till sender starts
        is_sender_ready()
        print("[throughput] starting experiment...")

        # Start iperf and/or netperf instances
        procs = run_flows(args.flow_type, args.config, args.num_connections, args.cpus, args.window)

        # Wait till sender is done sending
        mark_receiver_ready()
        is_sender_done()

        # Kill all the processes
        for p in procs:
            p.kill()
        print("[throughput] finished experiment.")

        # Process and write the raw output
        for i, p in enumerate(procs):
            lines = p.stdout.readlines()
            if args.output is not None:
                with open(os.path.join(args.output, "throughput_benchmark_{}.log".format(i)), "w") as f:
                    f.writelines(lines)

    if args.utilisation:
        # Wait till sender starts
        is_sender_ready()
        print("[utilisation] starting experiment...")

        # Start iperf and/or netperf instances
        procs = run_flows(args.flow_type, args.config, args.num_connections, args.cpus, args.window)

        # Start the sar instance
        sar = run_sar(list(set(args.cpus + args.affinity)))

        # Wait till sender is done sending
        mark_receiver_ready()
        is_sender_done()

        # Kill sar
        sar.send_signal(signal.SIGINT)
        sar.wait()

        # Kill all the processes
        for p in procs:
            p.kill()
        print("[utilisation] finished experiment.")

        # Process and write the raw output
        for i, p in enumerate(procs):
            lines = p.stdout.readlines()
            if args.output is not None:
                with open(os.path.join(args.output, "utilisation_benchmark_{}.log".format(i)), "w") as f:
                    f.writelines(lines)

        lines = sar.stdout.readlines()
        cpu_util = sum(process_util_output(lines).values())
        __results["cpu_util"] = cpu_util
        if args.output is not None:
            with open(os.path.join(args.output, "utilisation_sar.log"), "w") as f:
                f.writelines(lines)

        # Print the output
        print("[utilisation] utilisation: {:.3f}".format(cpu_util))
        header.append("receiver utilisation (%)")
        output.append("{:.3f}".format(cpu_util))

    if args.cache_miss:
        # Wait till sender starts
        is_sender_ready()
        print("[cache miss] starting experiment...")

       # Start iperf and/or netperf instances
        procs = run_flows(args.flow_type, args.config, args.num_connections, args.cpus, args.window)

        # Start the perf instance
        perf = run_perf_cache(list(set(args.cpus + args.affinity)))

        # Wait till sender is done sending
        mark_receiver_ready()
        is_sender_done()

        # Kill perf
        perf.send_signal(signal.SIGINT)
        perf.wait()

        # Kill all the processes
        for p in procs:
            p.kill()
        print("[cache miss] finished experiment.")

        # Process and write the raw output
        for i, p in enumerate(procs):
            lines = p.stdout.readlines()
            if args.output is not None:
                with open(os.path.join(args.output, "cache-miss_benchmark_{}.log".format(i)), "w") as f:
                    f.writelines(lines)

        lines = perf.stdout.readlines()
        cache_miss = process_cache_miss_output(lines)
        __results["cache_miss"] = cache_miss
        if args.output is not None:
            with open(os.path.join(args.output, "cache-miss_perf.log"), "w") as f:
                f.writelines(lines)

        # Print the output
        print("[cache miss] cache miss: {:.3f}".format(cache_miss))
        header.append("receiver cache miss (%)")
        output.append("{:.3f}".format(cache_miss))

    if args.util_breakdown:
        # Wait till sender starts
        is_sender_ready()
        print("[util breakdown] starting experiment...")

        # Start iperf and/or netperf instances
        procs = run_flows(args.flow_type, args.config, args.num_connections, args.cpus, args.window)

        # Start the perf instance
        output_dir = tempfile.TemporaryDirectory()
        perf_data_file = os.path.join(output_dir.name, "perf.data")
        perf = run_perf_record_util(list(set(args.cpus + args.affinity)), perf_data_file)

        # Wait till sender is done sending
        mark_receiver_ready()
        is_sender_done()

        # Kill perf
        perf.send_signal(signal.SIGINT)
        perf.wait()

        # Kill all the processes
        for p in procs:
            p.kill()
        print("[util breakdown] finished experiment.")

        # Process and write the raw output
        for i, p in enumerate(procs):
            lines = p.stdout.readlines()
            if args.output is not None:
                with open(os.path.join(args.output, "util-breakdown_benchmark_{}.log".format(i)), "w") as f:
                    f.writelines(lines)

        # Start a perf report instance
        perf = run_perf_report(perf_data_file)
        perf.wait()
        output_dir.cleanup()
        lines = perf.stdout.readlines()
        total_contrib, unaccounted_contrib, util_contibutions, not_found = process_util_breakdown_output(lines)
        __results["util_contibutions"] = util_contibutions
        if args.output is not None:
            with open(os.path.join(args.output, "util-breakdown_perf.log"), "w") as f:
                f.writelines(lines)

        # Print the output
        print("[util breakdown] total contribution: {:.3f}\tunaccounted contribution: {:.3f}".format(total_contrib, unaccounted_contrib))
        if unaccounted_contrib > 5 and args.verbose:
            print("[util breakdown] unknown symbols: {}".format(", ".join(not_found)))

    if args.cache_breakdown:
        # Wait till sender starts
        is_sender_ready()
        print("[cache breakdown] starting experiment...")

        # Start iperf and/or netperf instances
        procs = run_flows(args.flow_type, args.config, args.num_connections, args.cpus, args.window)

        # Start the perf instance
        output_dir = tempfile.TemporaryDirectory()
        perf_data_file = os.path.join(output_dir.name, "perf.data")
        perf = run_perf_record_cache(list(set(args.cpus + args.affinity)), perf_data_file)

        # Wait till sender is done sending
        mark_receiver_ready()
        is_sender_done()

        # Kill perf
        perf.send_signal(signal.SIGINT)
        perf.wait()

        # Kill all the processes
        for p in procs:
            p.kill()
        print("[cache breakdown] finished experiment.")

        # Process and write the raw output
        for i, p in enumerate(procs):
            lines = p.stdout.readlines()
            if args.output is not None:
                with open(os.path.join(args.output, "cache-breakdown_benchmark_{}.log".format(i)), "w") as f:
                    f.writelines(lines)

        # Start a perf report instance
        perf = run_perf_report(perf_data_file)
        perf.wait()
        output_dir.cleanup()
        lines = perf.stdout.readlines()
        total_contrib, unaccounted_contrib, cache_contibutions, not_found = process_util_breakdown_output(lines)
        __results["cache_contibutions"] = cache_contibutions
        if args.output is not None:
            with open(os.path.join(args.output, "cache-breakdown_perf.log"), "w") as f:
                f.writelines(lines)

        # Print the output
        print("[cache breakdown] total contribution: {:.3f}\tunaccounted contribution: {:.3f}".format(total_contrib, unaccounted_contrib))
        if unaccounted_contrib > 5 and not args.verbose:
            print("[cache breakdown] unknown symbols: {}".format(", ".join(not_found)))

    if args.flame:
        # Wait till sender starts
        is_sender_ready()
        print("[flame] starting experiment...")

       # Start iperf and/or netperf instances
        procs = run_flows(args.flow_type, args.config, args.num_connections, args.cpus, args.window)

        # Start the perf instance
        output_dir = tempfile.TemporaryDirectory()
        perf_data_file = os.path.join(output_dir.name, "perf.data")
        perf = run_perf_record_flame(list(set(args.cpus + args.affinity)), perf_data_file)

        # Wait till sender is done sending
        mark_receiver_ready()
        is_sender_done()

        # Kill perf
        perf.send_signal(signal.SIGINT)
        perf.wait()

        # Kill all the processes
        for p in procs:
            p.kill()
        print("[flame] finished experiment.")

        # Process and write the raw output
        for i, p in enumerate(procs):
            lines = p.stdout.readlines()
            if args.output is not None:
                with open(os.path.join(args.output, "flame_benchmark_{}.log".format(i)), "w") as f:
                    f.writelines(lines)

        # Start a perf report instance
        output_svg_file = os.path.join(args.output, "flame.svg")
        run_flamegraph(perf_data_file, output_svg_file)
        output_dir.cleanup()

    if args.latency:
        # Clear dmesg
        dmesg_clear()

        # Enable latency measurement
        latency_measurement(enabled=True)

        # Wait till sender starts
        is_sender_ready()
        print("[latency] starting experiment...")

        # Start iperf and/or netperf instances
        procs = run_flows(args.flow_type, args.config, args.num_connections, args.cpus, args.window)

        # Wait till sender is done sending
        mark_receiver_ready()
        is_sender_done()

        # Kill all the processes
        for p in procs:
            p.kill()
        print("[latency] finished experiment.")

        # Disable latency measurement
        latency_measurement(enabled=False)

        # Process and write the raw output
        for i, p in enumerate(procs):
            lines = p.stdout.readlines()
            if args.output is not None:
                with open(os.path.join(args.output, "latency_benchmark_{}.log".format(i)), "w") as f:
                    f.writelines(lines)

        # Start a dmesg instance to read the kernel logs
        dmesg = run_dmesg()
        lines = []
        while True:
            new_lines = dmesg.stdout.readlines()
            lines += new_lines
            if len(new_lines) == 0 and dmesg.poll() != None:
                break
        avg_latency, tail_latency = process_latency_output(lines)
        __results["avg_latency"] = avg_latency
        __results["tail_latency"] = tail_latency
        if args.output is not None:
            with open(os.path.join(args.output, "latency_dmesg.log"), "w") as f:
                f.writelines(lines)

        # Print the output
        print("[latency] avg. data copy latency: {:.3f}\ttail data copy latency: {}".format(avg_latency, tail_latency))
        header.append("avg. data copy latency (us)")
        output.append("{:.3f}".format(avg_latency))
        header.append("tail data copy latency (us)")
        output.append("{}".format(tail_latency))

    if args.skb_hist:
        # Clear dmesg
        dmesg_clear()

        # Enable skb size histogram measurement
        skb_hist_measurement(enabled=True)

        # Wait till sender starts
        is_sender_ready()
        print("[skb hist] starting experiment...")

        # Start iperf and/or netperf instances
        procs = run_flows(args.flow_type, args.config, args.num_connections, args.cpus, args.window)

        # Wait till sender is done sending
        mark_receiver_ready()
        is_sender_done()

        # Kill all the processes
        for p in procs:
            p.kill()
        print("[skb hist] finished experiment.")

        # Disable skb size histogram measurement
        skb_hist_measurement(enabled=False)

        # Process and write the raw output
        for i, p in enumerate(procs):
            lines = p.stdout.readlines()
            if args.output is not None:
                with open(os.path.join(args.output, "skb-hist_benchmark_{}.log".format(i)), "w") as f:
                    f.writelines(lines)

        # Start a dmesg instance to read the kernel logs
        dmesg = run_dmesg()
        lines = []
        while True:
            new_lines = dmesg.stdout.readlines()
            lines += new_lines
            if len(new_lines) == 0 and dmesg.poll() != None:
                break
        skb_sizes = process_skb_sizes_output(lines)
        __results["skb_sizes"] = skb_sizes
        if args.output is not None:
            with open(os.path.join(args.output, "skb-hist_dmesg.log"), "w") as f:
                f.writelines(lines)

    # Add the headers to the results
    __results["header"] = header
    __results["output"] = output

    # Sync with server again
    mark_receiver_ready()
    is_sender_ready()

    # Close the server
    server.shutdown()
    server_thread.join()

    # Reset packet drop rate
    set_packet_drop_rate(0)
