"""Combine four E02 proof-window summaries from a balanced sequence."""

import argparse
import json
from pathlib import Path
from statistics import median


def summarize(rows):
    times = sorted(row["proof_ms"] for row in rows)
    midpoint = len(times) // 2
    stalls = [row["full_stall_us"] / 1000 for row in rows]
    return {
        "count": len(rows),
        "proof_median_ms": round(median(times), 3),
        "proof_q1_ms": round(median(times[:midpoint]), 3),
        "proof_q3_ms": round(median(times[-midpoint:]), 3),
        "proof_min_ms": times[0],
        "proof_max_ms": times[-1],
        "windows_with_high_events": sum(row["high_events"] > 0 for row in rows),
        "windows_with_full_stall": sum(stall > 0 for stall in stalls),
        "full_stall_median_ms": round(median(stalls), 3),
        "full_stall_total_ms": round(sum(stalls), 3),
        "high_events_total": sum(row["high_events"] for row in rows),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("experiment", type=Path)
    parser.add_argument("--order", choices=("ABBA", "BAAB"), default="ABBA")
    args = parser.parse_args()
    block_names = [f"{args.order}-{index}-{name}" for index, name in enumerate(args.order, 1)]
    groups = {"A": [], "B": []}
    blocks = {}
    verified_count = 0

    for block in block_names:
        data = json.loads((args.experiment / block / "summary.json").read_text())
        rows = data["proof_windows"]
        measured = [row for row in rows if not row["warmup"]]
        if len(rows) != 6 or len(measured) != 5 or not all(row["proof_verified"] for row in rows):
            raise ValueError(f"{block} did not yield one verified warmup and five verified measurements")
        verified_count += len(rows)
        blocks[block] = summarize(measured)
        groups[block[-1]].extend(measured)

    conditions = {name: summarize(rows) for name, rows in groups.items()}
    a, b = (conditions[name]["proof_median_ms"] for name in "AB")
    paired_ratios = []
    for first, second in zip(block_names[::2], block_names[1::2]):
        a_block, b_block = sorted((first, second), key=lambda name: name[-1])
        paired_ratios.append(round(blocks[b_block]["proof_median_ms"] / blocks[a_block]["proof_median_ms"], 5))

    print(json.dumps({
        "verified_including_warmups": verified_count,
        "blocks": blocks,
        "conditions": conditions,
        "median_ratio_b_over_a": round(b / a, 5),
        "median_difference_ms": round(b - a, 3),
        "paired_ratios_b_over_a": paired_ratios,
    }, indent=2))


if __name__ == "__main__":
    main()
