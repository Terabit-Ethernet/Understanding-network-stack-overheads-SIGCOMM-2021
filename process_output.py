import os
import re


# Constants
SYMBOL_MAP_FILE = os.path.join(os.path.split(os.path.realpath(__file__))[0], "symbol_mapping.tsv")


def process_iperf_output(lines):
    throughput = 0.
    num_samples = 0
    for line in lines:
        elements = line.split()
        if len(elements) > 2 and elements[-1] == "Gbits/sec":
            throughput += float(elements[-2])
            num_samples += 1
        elif len(elements) > 2 and elements[-1] == "Mbits/sec":
            throughput += float(elements[-2]) / 1000
            num_samples += 1
    return throughput / num_samples


def process_sar_output(lines):
    cpu_util = {}
    num_samples = {}
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
    for cpu in cpu_util:
        cpu_util[cpu] /= num_samples[cpu]
    return cpu_util


def process_perf_cache_output(lines):
    for line in lines:
        elements = line.split()
        if len(elements) == 9 and elements[1] == "LLC-load-misses":
            cache_miss = float(elements[3][:-1])
            break
    return cache_miss


def process_perf_report_output(lines):
    contributions = {}
    not_found = []
    symbol_map = {}
    total_contrib = 0.
    unaccounted_contrib = 0.
    with open(SYMBOL_MAP_FILE, "r") as f:
        for line in f.readlines():
            comps = line.split()
            if len(comps) == 2:
                symbol, typ = line.split()
                symbol_map[symbol] = typ
                if typ not in contributions:
                    contributions[typ] = 0.
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


def process_dmesg_output(lines):
    samples = []
    for line in lines:
        try:
            samples.append(int(re.match(r"^.*latency=([0-9]+)\.$", line).group(1)))
        except:
            pass
    samples.sort()
    return sum(samples) / len(samples), samples[round(0.99 * len(samples) + 0.5)]
