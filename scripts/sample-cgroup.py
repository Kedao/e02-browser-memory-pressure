"""Write timestamped cgroup v2 memory readings to CSV until stopped."""

import argparse
import csv
from pathlib import Path
import sys
import time


def read_events(path):
    return {key: int(value) for key, value in (line.split() for line in path.read_text().splitlines())}


def read_pressure(path):
    totals = {}
    for line in path.read_text().splitlines():
        kind, *fields = line.split()
        totals[kind] = int(dict(field.split("=") for field in fields)["total"])
    return totals


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("cgroup", type=Path)
    args = parser.parse_args()
    cgroup = args.cgroup

    sys.stdout.reconfigure(line_buffering=True)
    output = csv.writer(sys.stdout)
    output.writerow([
        "begin_epoch_ns", "end_epoch_ns", "begin_monotonic_ns", "end_monotonic_ns",
        "current_bytes", "high_events", "max_events", "oom_events", "oom_kill_events",
        "some_stall_us", "full_stall_us",
    ])

    while True:
        begin_monotonic = time.monotonic_ns()
        begin_epoch = time.time_ns()
        current = int((cgroup / "memory.current").read_text())
        events = read_events(cgroup / "memory.events.local")
        pressure = read_pressure(cgroup / "memory.pressure")
        end_epoch = time.time_ns()
        end_monotonic = time.monotonic_ns()
        output.writerow([
            begin_epoch, end_epoch, begin_monotonic, end_monotonic, current,
            events["high"], events["max"], events["oom"], events["oom_kill"],
            pressure["some"], pressure["full"],
        ])
        time.sleep(0.05)


if __name__ == "__main__":
    main()
