"""Small controller weight sensitivity test runner."""

from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from algorithms.controller import (
    reset_controller_score_weights,
    run_hyper_heuristic,
    set_controller_score_weights,
)
from algorithms.fitness import evaluate_timetable
from parsers.itc_parser import parse_itc_file

OUTPUT_PATH = Path("results") / "controller_weight_sensitivity_dataset1.csv"
FIELDNAMES = [
    "config_name",
    "final_fitness",
    "hard_violations",
    "soft_penalty",
    "runtime_seconds",
    "selected_heuristics",
    "aco_usage_count",
    "pso_usage_count",
]

CONFIGS: list[dict[str, Any]] = [
    {
        "config_name": "CONFIG A",
        "aco": (0.4, 0.3, 0.3),
        "pso": (0.5, 0.3, 0.2),
    },
    {
        "config_name": "CONFIG B",
        "aco": (0.3, 0.3, 0.4),
        "pso": (0.3, 0.5, 0.2),
    },
    {
        "config_name": "CONFIG C",
        "aco": (0.3, 0.5, 0.2),
        "pso": (0.4, 0.3, 0.3),
    },
]


def _rank_key(row: dict[str, Any]) -> tuple[int, float, float]:
    return (
        int(row["hard_violations"]),
        float(row["final_fitness"]),
        float(row["runtime_seconds"]),
    )


def run_sensitivity(datasets: list[str | Path], runs: int) -> list[dict[str, Any]]:
    if runs <= 0:
        raise ValueError("runs must be >= 1")
    if len(datasets) != 1:
        raise ValueError("This script supports exactly one dataset path.")

    dataset_path = Path(datasets[0])
    instance = parse_itc_file(dataset_path)
    rows: list[dict[str, Any]] = []

    try:
        for config in CONFIGS:
            name = str(config["config_name"])
            aco_w = config["aco"]
            pso_w = config["pso"]
            set_controller_score_weights(
                aco_conflict_density=aco_w[0],
                aco_normalized_hard_violations=aco_w[1],
                aco_infeasibility=aco_w[2],
                pso_search_stagnation=pso_w[0],
                pso_feasibility_ratio=pso_w[1],
                pso_low_conflict_density=pso_w[2],
            )

            for run_idx in range(1, runs + 1):
                print(f"Running {name} on {instance.name} (run {run_idx}/{runs})")
                started = time.perf_counter()
                state, _, stats = run_hyper_heuristic(instance)
                runtime = time.perf_counter() - started
                evaluate_timetable(state, instance)
                selected = list(stats["selection_history"])
                row = {
                    "config_name": name,
                    "final_fitness": float(state.fitness or 0.0),
                    "hard_violations": int(state.hard_violations or 0),
                    "soft_penalty": float(state.soft_penalty or 0.0),
                    "runtime_seconds": runtime,
                    "selected_heuristics": json.dumps(selected),
                    "aco_usage_count": sum(1 for h in selected if h == "ACO"),
                    "pso_usage_count": sum(1 for h in selected if h == "PSO"),
                }
                rows.append(row)
    finally:
        reset_controller_score_weights()

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)

    ranked = sorted(rows, key=_rank_key)
    print("\nRanked results (hard_violations, final_fitness, runtime_seconds):")
    print(
        "config_name | final_fitness | hard_violations | soft_penalty | "
        "runtime_seconds | aco_usage_count | pso_usage_count | selected_heuristics"
    )
    print("-" * 130)
    for row in ranked:
        print(
            f"{row['config_name']} | {float(row['final_fitness']):.2f} | "
            f"{int(row['hard_violations'])} | {float(row['soft_penalty']):.2f} | "
            f"{float(row['runtime_seconds']):.2f} | {int(row['aco_usage_count'])} | "
            f"{int(row['pso_usage_count'])} | {row['selected_heuristics']}"
        )

    return ranked


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Controller weight sensitivity (Dataset 1)")
    parser.add_argument(
        "--datasets",
        nargs="+",
        required=True,
        help="Exactly one dataset path, e.g. data/itc/Dataset 1.txt",
    )
    parser.add_argument("--runs", type=int, default=1, help="Runs per configuration")
    args = parser.parse_args(argv)

    ranked = run_sensitivity(args.datasets, args.runs)
    best = ranked[0]
    baseline = next(row for row in ranked if str(row["config_name"]) == "CONFIG A")

    improved = _rank_key(best) < _rank_key(baseline)
    print("\nBest configuration:", best["config_name"])
    print("Improves over baseline CONFIG A:", "yes" if improved else "no")
    print(f"Saved sensitivity CSV: {OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
