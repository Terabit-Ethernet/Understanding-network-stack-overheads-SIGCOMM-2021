import os
import re


# Path to the symbols map file
SYMBOL_MAP_FILE = os.path.join(os.path.split(os.path.realpath(__file__))[0], "symbol_mapping.tsv")


def process_throughput_output(lines):
    # Check whether the output is coming from netperf
    if len(lines) == 3 and lines[1] == "Throughput\n":
        return float(lines[2]) / 2

    # The output must be from iperf
    throughput = 0.
    num_samples = 0

    # Get last 10 secs throughput (exclude the last second)
    lines = lines[-12:-2]
    for line in lines:
        elements = line.split()
        if len(elements) > 2 and elements[-1] == "Gbits/sec":
            throughput += float(elements[-2])
            num_samples += 1
        elif len(elements) > 2 and elements[-1] == "Mbits/sec":
            throughput += float(elements[-2]) / 1000
            num_samples += 1

    # Return the average throughput
    return 0 if num_samples == 0 else throughput / num_samples


def process_util_output(lines):
    cpu_util = {}
    num_samples = {}

    # Get the utilisation for each core
    for line in lines[::-1]:
        elements = line.split()
        if len(elements) == 9 and elements[2] != "CPU":
            cpu = int(elements[2])
            util = float(elements[8])
            if cpu not in cpu_util:
                cpu_util[cpu] = (100 - util)
                num_samples[cpu] = 1
            else:
                cpu_util[cpu] += (100 - util)
                num_samples[cpu] += 1

    # Average the utilisation
    for cpu in cpu_util:
        if num_samples[cpu] != 0:
            cpu_util[cpu] /= num_samples[cpu]

    return cpu_util


def process_cache_miss_output(lines):
    cache_miss = 0.

    # Find the cache miss rate
    for line in lines:
        elements = line.split()
        if len(elements) == 9 and elements[1] == "LLC-load-misses":
            cache_miss = float(elements[3][:-1])
            break

    return cache_miss


def process_util_breakdown_output(lines):
    contributions = {}
    not_found = []
    symbol_map = {}
    total_contrib = 0.
    unaccounted_contrib = 0.

    # Read the symbols map file
    with open(SYMBOL_MAP_FILE, "r") as f:
        for line in f.readlines():
            comps = line.split()
            if len(comps) == 2:
                symbol, typ = line.split()
                symbol_map[symbol] = typ
                if typ not in contributions:
                    contributions[typ] = 0.

    # Process the perf output to calculate breakdown
    for line in lines:
        if total_contrib < 95:
            comps = line.split()
            if len(comps) == 5 and comps[3] == "[k]":
                func = comps[4].split(".")[0]
                contrib = float(comps[0][:-1])
                total_contrib += contrib
                if func in symbol_map:
                    typ = symbol_map[func]
                    contributions[typ] += contrib
                else:
                    if contrib > 0.01:
                        not_found.append(func)
                    unaccounted_contrib += contrib
        else:
            break

    return total_contrib, unaccounted_contrib, contributions, not_found


def process_latency_output(lines):
    samples = []

    # Try to parse the latecy from dmesg output
    for line in lines:
        try:
            samples.append(int(re.match(r"^.*\[data-copy-latency\] latency=(.*)$", line).group(1)))
        except:
            pass

    # Sort and get average and tail
    samples.sort()
    num_samples = len(samples)
    avg_latency = (sum(samples) / num_samples) / 1000
    tail_latency = samples[max(num_samples - 1, round(0.99 * num_samples + 0.5))] / 1000

    return avg_latency, tail_latency


def process_skb_sizes_output(lines):
    skb_sizes = [0 for _ in range(13)]

    # Try to parse the histogram from dmesg output
    for line in lines:
        counts = re.match(r"^.*\[skb-sizes\] (.*)$", line)
        if counts is not None:
            for idx, c in enumerate(counts.group(1).split()):
                skb_sizes[idx] += int(c)
    total = sum(skb_sizes)

    # Get the fraction of packets
    if total == 0:
        return skb_sizes
    else:
        return [s / total for s in skb_sizes]

