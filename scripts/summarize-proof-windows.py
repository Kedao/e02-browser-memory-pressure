"""Summarize cgroup counter changes strictly inside browser proof windows."""

import argparse
import csv
import json
from pathlib import Path
from statistics import median


GUARD_NS = 10_000_000
COUNTERS = ("high_events", "max_events", "oom_events", "oom_kill_events", "some_stall_us", "full_stall_us")


def deltas(first, last):
    changes = {key: last[key] - first[key] for key in COUNTERS}
    if any(change < 0 for change in changes.values()):
        raise ValueError("cgroup counters went backwards")
    return changes


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("samples", type=Path)
    parser.add_argument("marks", type=Path)
    parser.add_argument("proof", type=Path)
    args = parser.parse_args()

    with args.samples.open() as source:
        samples = [{key: int(value) for key, value in row.items()} for row in csv.DictReader(source)]
    timing = json.loads(args.marks.read_text())
    proof = json.loads(args.proof.read_text())
    marks = {entry["name"]: entry["startTime"] for entry in timing["marks"]}
    origin = timing["timeOrigin"]

    offsets = [sample["begin_epoch_ns"] - sample["begin_monotonic_ns"] for sample in samples]
    offset_range = max(offsets) - min(offsets)
    if abs(timing["clockOffsetMs"]) > 2 or offset_range > 2_000_000:
        raise ValueError("clock check failed")

    windows = []
    for round_number, row in enumerate(proof, 1):
        start = marks[f"E02 proof {round_number} start"]
        end = marks[f"E02 proof {round_number} end"]
        if abs(end - start - row["proveTimeMs"]) > 0.01:
            raise ValueError(f"proof timing mismatch in round {round_number}")
        start_ns = round((origin + start) * 1_000_000)
        end_ns = round((origin + end) * 1_000_000)
        inside = [sample for sample in samples if start_ns + GUARD_NS <= sample["begin_epoch_ns"]
                  and sample["end_epoch_ns"] <= end_ns - GUARD_NS]
        if len(inside) < 2:
            raise ValueError(f"fewer than two interior samples in round {round_number}")
        first, last = inside[0], inside[-1]
        windows.append({
            "round": round_number,
            "warmup": row["warmup"],
            "proof_verified": row["proofVerified"],
            "proof_ms": row["proveTimeMs"],
            "samples": len(inside),
            "leading_gap_ms": round((first["end_epoch_ns"] - start_ns) / 1_000_000, 3),
            "trailing_gap_ms": round((end_ns - last["begin_epoch_ns"]) / 1_000_000, 3),
            "peak_sampled_mib": round(max(sample["current_bytes"] for sample in inside) / 2**20, 3),
            **deltas(first, last),
        })

    print(json.dumps({
        "browser_wall_clock_offset_ms": timing["clockOffsetMs"],
        "host_clock_offset_range_ms": round(offset_range / 1_000_000, 4),
        "guard_each_edge_ms": GUARD_NS / 1_000_000,
        "median_sample_interval_ms": round(median(
            (last["begin_monotonic_ns"] - first["begin_monotonic_ns"]) / 1_000_000
            for first, last in zip(samples, samples[1:])
        ), 3),
        "whole_capture": deltas(samples[0], samples[-1]),
        "proof_windows": windows,
    }, indent=2))


if __name__ == "__main__":
    main()
