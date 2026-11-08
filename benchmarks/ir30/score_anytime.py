#!/usr/bin/env python3
"""Offline IR-30 quality aggregation; requires pre-graded input, not a research grader.

Usage: python benchmarks/ir30/score_anytime.py checkpoints.jsonl
No third-party packages. Every episode must have seven quality checkpoints.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import json
from pathlib import Path
import statistics

CHECKPOINTS = (0, 300, 600, 900, 1200, 1500, 1800)
ARMS = ("A", "B", "C", "D")


def aggregate(rows: list[dict]) -> dict:
    episodes = defaultdict(dict)
    for row in rows:
        case_id, arm, rep = row["case_id"], row["arm"], row["rep"]
        sec = row["elapsed_s"]
        quality = row["quality"]
        if arm not in ARMS:
            raise ValueError(f"Unknown arm: {arm}")
        if sec not in CHECKPOINTS or not isinstance(quality, (float, int)):
            raise ValueError(f"Invalid checkpoint or quality: {row}")
        if not 0 <= quality <= 100:
            raise ValueError(f"Quality not in [0,100]: {quality}")
        key = (case_id, arm, rep)
        if sec in episodes[key]:
            raise ValueError(f"Duplicate checkpoint: {key}@{sec}")
        episodes[key][sec] = row

    if not episodes:
        raise ValueError("No episodes")
    summaries = []
    for (case_id, arm, rep), snapshots in sorted(episodes.items()):
        if tuple(sorted(snapshots)) != CHECKPOINTS:
            raise ValueError(f"Incomplete 30m checkpoints for {case_id}/{arm}/{rep}: {sorted(snapshots)}")
        q = [snapshots[t]["quality"] for t in CHECKPOINTS]
        # Left-step integral: six 5-minute intervals, each carrying quality at its start.
        auc = sum(q[:6]) / 6
        last = snapshots[1800]
        if "usd" not in last or last["usd"] < 0:
            raise ValueError(f"Missing/invalid 30m total USD for {case_id}/{arm}/{rep}")
        summaries.append({
            "case_id": case_id, "arm": arm, "rep": rep,
            "auc_q_30": auc,
            "q30": q[-1],
            "usd": last["usd"],
            "illustrative": any(snapshots[t].get("illustrative", False) for t in CHECKPOINTS)
        })

    by_arm = defaultdict(list)
    for s in summaries:
        by_arm[s["arm"]].append(s)

    arm_summary = {
        arm: {
            "episodes": len(items),
            "mean_auc_q_30": round(statistics.mean(i["auc_q_30"] for i in items), 4),
            "mean_q30": round(statistics.mean(i["q30"] for i in items), 4),
            "mean_usd": round(statistics.mean(i["usd"] for i in items), 4),
        }
        for arm, items in sorted(by_arm.items())
    }

    # Descriptive paired differences only. Proper inference should resample cases,
    # stratified by task family, after averaging per-case repetitions.
    paired = {}
    keys = defaultdict(dict)
    for s in summaries:
        keys[(s["case_id"], s["rep"])][s["arm"]] = s
    for lhs, rhs in (("D", "C"), ("D", "A")):
        diffs = [pair[lhs]["auc_q_30"] - pair[rhs]["auc_q_30"]
                 for pair in keys.values() if lhs in pair and rhs in pair]
        if diffs:
            paired[f"{lhs}_minus_{rhs}"] = {
                "n_paired": len(diffs),
                "mean_auc_difference": round(statistics.mean(diffs), 4)
            }

    return {
        "method": "IR-30 checkpoint left-step AUC; descriptive only",
        "caution": "Scores are supplied input: this script does not grade research, evaluate citations, or run agents.",
        "illustrative_input": any(s["illustrative"] for s in summaries),
        "arms": arm_summary,
        "paired_descriptive": paired,
        "episode_summaries": summaries
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("checkpoints", type=Path)
    args = parser.parse_args()
    rows = [json.loads(line) for line in args.checkpoints.read_text(encoding="utf-8").splitlines() if line.strip()]
    print(json.dumps(aggregate(rows), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
