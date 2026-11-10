"""Recompute and check the E02 candidate package using only Python's standard library."""

import json
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
BATCHES = ("depth7-384mib-abba", "depth7-320mib-abba", "depth7-320mib-baab")
PILOTS = ("no-limit-aligned", "pressure-384mib", "pressure-352mib", "pressure-320mib")


def recompute(script, expected, *arguments):
    result = subprocess.check_output([sys.executable, SCRIPTS / script, *arguments])
    if result != expected.read_bytes():
        raise ValueError(f"recomputation differs from {expected.relative_to(ROOT)}")
    return json.loads(result)


def check_windows(folder):
    return recompute("summarize-proof-windows.py", folder / "summary.json",
                     folder / "samples.csv", folder / "marks.json", folder / "proof.json")


def check_gate(folder, summary):
    rows = summary["proof_windows"]
    formal = [row for row in rows if not row["warmup"]]
    stalls = [row["full_stall_us"] for row in formal]
    covered = sum(stall > 0 for stall in stalls)
    verified = len(rows) == 6 and all(row["proof_verified"] for row in rows)
    event_lines = (folder / "cgroup.txt").read_text().split("events-final\n", 1)[1].split("\n\n", 1)[0]
    events = {key: int(value) for key, value in (line.split() for line in event_lines.splitlines())}
    oom = {name: events[name] for name in ("oom", "oom_kill", "oom_group_kill")}
    expected = json.loads((folder / "gate.json").read_text())
    actual = {
        "passed": len(formal) == 5 and covered >= 4 and verified and not any(oom.values()),
        "formal_rows": len(formal),
        "formal_windows_with_full_stall": covered,
        "full_stall_us_by_formal_round": stalls,
        "all_verified_including_warmup": verified,
        "final_cgroup_oom_events": oom,
    }
    if actual != expected:
        raise ValueError(f"gate recomputation differs for {folder.name}")
    return covered


def main():
    for name in BATCHES:
        folder = ROOT / "data" / "formal" / name
        order = name.rsplit("-", 1)[-1].upper()
        for index, arm in enumerate(order, 1):
            check_windows(folder / f"{order}-{index}-{arm}")
        batch = recompute("summarize-abba.py", folder / "aggregate.json", folder, "--order", order)
        a, b = (batch["conditions"][arm] for arm in "AB")
        change = (batch["median_ratio_b_over_a"] - 1) * 100
        print(f"{name}: {a['proof_median_ms']:.3f} / {b['proof_median_ms']:.3f} ms, {change:+.2f}%, "
              f"B full stalls {b['windows_with_full_stall']}/{b['count']}")

    for name in PILOTS:
        folder = ROOT / "data" / "smoke" / name
        summary = check_windows(folder)
        if (folder / "gate.json").is_file():
            print(f"{name}: {check_gate(folder, summary)}/5 measured proof windows with full stalls")

    print("All 16 aligned blocks, 3 formal summaries and 2 pilot gates match the archived results.")


if __name__ == "__main__":
    main()
