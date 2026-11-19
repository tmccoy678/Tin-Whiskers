#!/usr/bin/env python3
"""Prepare state metadata for an adaptive 0..N timeline from metrics and actions."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--metrics", required=True, type=Path)
    parser.add_argument("--actions", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    with args.metrics.open(newline="") as handle:
        metrics = list(csv.DictReader(handle, delimiter="\t"))
    actions = json.loads(args.actions.read_text())
    if len(metrics) != len(actions) + 1:
        raise RuntimeError("adaptive metrics must contain one more state than actions")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "epoch",
                "connected",
                "upper_probe",
                "lower_probe",
                "applied_action_index",
            ],
            delimiter="\t",
        )
        writer.writeheader()
        for state, metric in enumerate(metrics):
            action_index = state - 1
            if action_index >= 0:
                action = actions[action_index]
                upper = float(action["upper_fraction"])
                lower = float(action["lower_fraction"])
            else:
                upper = 0.0
                lower = 0.0
            writer.writerow(
                {
                    "epoch": int(metric["epoch"]),
                    "connected": -1,
                    "upper_probe": upper,
                    "lower_probe": lower,
                    "applied_action_index": action_index,
                }
            )
    print(f"PASS adaptive metadata states={len(metrics)} output={args.output}")


if __name__ == "__main__":
    main()
