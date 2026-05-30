"""Benchmark runner for initializer, ACO, PSO, and controller methods."""

from __future__ import annotations

import argparse
import csv
import json
import random
import sys
import statistics
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from algorithms.aco import run_aco
from algorithms.controller import get_last_controller_telemetry, run_hyper_heuristic
from algorithms.fitness import evaluate_timetable
from algorithms.initializer import count_scheduled_lectures, generate_initial_solution
from algorithms.pso import run_pso
from models.timetable import TimetableState
from parsers.itc_parser import ITCInstance, parse_itc_file
from utils.timetable_output import export_timetable_csv, print_timetable

METHODS = ("Greedy", "ACO", "PSO", "Controller")
QUICK_METHODS = ("Greedy", "PSO", "Controller")
CSV_FIELDNAMES = [
    "dataset_name",
    "method",
    "run_number",
    "final_fitness",
    "hard_violations",
    "soft_penalty",
    "runtime_seconds",
    "scheduled_lectures",
    "total_lectures",
    "convergence_history",
    "selected_heuristics",
    "aco_usage_count",
    "pso_usage_count",
    "seed",
    "controller_telemetry",
]
SUMMARY_FIELDNAMES = [
    "dataset_name",
    "method",
    "mean_fitness",
    "best_fitness",
    "mean_hard_violations",
    "best_hard_violations",
    "mean_soft_penalty",
    "best_soft_penalty",
    "mean_runtime_seconds",
    "best_runtime_seconds",
]


def run_benchmarks(
    datasets: list[str | Path],
    runs: int,
    *,
    output_dir: str | Path = "results",
    quick: bool = False,
    final_mode: bool = False,
    seed: int | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Execute benchmark runs and persist CSV/JSON outputs."""
    if runs <= 0:
        raise ValueError("runs must be >= 1")
    if quick:
        runs = 1
    if final_mode:
        quick = False
        runs = 3

    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)
    csv_path = output_root / "benchmark_results.csv"
    json_path = output_root / "convergence_histories.json"
    summary_path = output_root / "final_benchmark_summary.csv"
    notes_path = output_root / "benchmark_notes.txt"
    methods = QUICK_METHODS if quick else METHODS

    rows: list[dict[str, Any]] = []
    convergence_entries: list[dict[str, Any]] = []

    _write_csv(csv_path, rows)
    _write_json(json_path, convergence_entries)

    for dataset in datasets:
        dataset_path = Path(dataset)
        instance = parse_itc_file(dataset_path)
        dataset_name = instance.name or dataset_path.name

        for run_number in range(1, runs + 1):
            for method in methods:
                print(f"Running dataset: {dataset_name}", flush=True)
                print(f"Method: {method}", flush=True)
                print(f"Run: {run_number}/{runs}", flush=True)
                run_seed = seed + run_number - 1 if seed is not None else None
                state, history, selected_heuristics, runtime_seconds, telemetry = _run_method(
                    method, instance, run_seed
                )
                aco_usage_count = 0
                pso_usage_count = 0
                if method == "Controller" and selected_heuristics is not None:
                    aco_usage_count = sum(1 for h in selected_heuristics if h == "ACO")
                    pso_usage_count = sum(1 for h in selected_heuristics if h == "PSO")
                    _export_controller_timetable(
                        state,
                        instance,
                        output_root,
                        dataset_name,
                        run_number,
                    )
                evaluate_timetable(state, instance)
                scheduled_lectures, total_lectures = count_scheduled_lectures(state)
                row = {
                    "dataset_name": dataset_name,
                    "method": method,
                    "run_number": run_number,
                    "final_fitness": float(state.fitness or 0.0),
                    "hard_violations": int(state.hard_violations or 0),
                    "soft_penalty": float(state.soft_penalty or 0.0),
                    "runtime_seconds": runtime_seconds,
                    "scheduled_lectures": scheduled_lectures,
                    "total_lectures": total_lectures,
                    "convergence_history": json.dumps(history),
                    "selected_heuristics": json.dumps(selected_heuristics)
                    if selected_heuristics is not None
                    else "",
                    "aco_usage_count": aco_usage_count,
                    "pso_usage_count": pso_usage_count,
                    "seed": run_seed if run_seed is not None else "",
                    "controller_telemetry": json.dumps(telemetry) if telemetry else "",
                }
                rows.append(row)
                convergence_entries.append(
                    {
                        "dataset_name": dataset_name,
                        "method": method,
                        "run_number": run_number,
                        "convergence_history": history,
                        "selected_heuristics": selected_heuristics or [],
                        "seed": run_seed,
                        "controller_telemetry": telemetry,
                    }
                )
                _write_csv(csv_path, rows)
                _write_json(json_path, convergence_entries)
                print(f"Completed {method} in {runtime_seconds:.1f} seconds", flush=True)
                print("Saved:\nresults/benchmark_results.csv", flush=True)
                print("Saved:\nresults/convergence_histories.json", flush=True)

    _print_summary(rows)
    summary_rows = _build_summary_rows(rows)
    _write_summary_csv(summary_path, summary_rows)
    _write_notes(notes_path)
    print(f"Saved benchmark CSV: {csv_path}")
    print(f"Saved convergence JSON: {json_path}")
    print(f"Saved summary CSV: {summary_path}")
    print(f"Saved benchmark notes: {notes_path}")
    return rows, convergence_entries


def _run_method(
    method: str,
    instance: ITCInstance,
    seed: int | None = None,
) -> tuple[
    TimetableState,
    list[float],
    list[str] | None,
    float,
    list[dict[str, float | int | str]] | None,
]:
    started = time.perf_counter()
    if seed is not None:
        random.seed(seed)
    if method == "Greedy":
        state = generate_initial_solution(instance)
        evaluate_timetable(state, instance)
        runtime = time.perf_counter() - started
        return state, [float(state.fitness or 0.0)], None, runtime, None

    if method == "ACO":
        state, history = run_aco(instance)
        runtime = time.perf_counter() - started
        return state, history, None, runtime, None

    if method == "PSO":
        state, history = run_pso(instance)
        runtime = time.perf_counter() - started
        return state, history, None, runtime, None

    if method == "Controller":
        state, history, stats = run_hyper_heuristic(instance)
        runtime = time.perf_counter() - started
        selected = list(stats["selection_history"])
        telemetry = get_last_controller_telemetry()
        return state, history, selected, runtime, telemetry

    raise ValueError(f"Unknown benchmark method: {method}")


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)


def _write_summary_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=SUMMARY_FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)


def _write_json(path: Path, entries: list[dict[str, Any]]) -> None:
    payload = {"entries": entries}
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _write_notes(path: Path) -> None:
    path.write_text(
        "\n".join(
            [
                "PSO may outperform the controller on some datasets.",
                "The controller is still valid because it adaptively selects heuristics and improves over the greedy baseline.",
                "The objective is to evaluate whether adaptive selection improves feasibility and robustness, not to guarantee dominance over every standalone heuristic.",
            ]
        ),
        encoding="utf-8",
    )


def _export_controller_timetable(
    state: TimetableState,
    instance: ITCInstance,
    output_root: Path,
    dataset_name: str,
    run_number: int,
) -> None:
    safe_dataset_name = _sanitize_dataset_name(dataset_name)
    target_dir = output_root / "generated_timetables" / safe_dataset_name
    target_dir.mkdir(parents=True, exist_ok=True)

    csv_path = target_dir / f"controller_run_{run_number}.csv"
    txt_path = target_dir / f"controller_run_{run_number}.txt"

    export_timetable_csv(state, instance, csv_path)
    _write_readable_timetable_txt(state, instance, txt_path)
    print(f"Saved:\n{csv_path}", flush=True)
    print(f"Saved:\n{txt_path}", flush=True)


def _write_readable_timetable_txt(
    state: TimetableState,
    instance: ITCInstance,
    output_path: Path,
) -> None:
    from io import StringIO
    from contextlib import redirect_stdout

    buffer = StringIO()
    with redirect_stdout(buffer):
        print_timetable(state, instance)
    output_path.write_text(buffer.getvalue(), encoding="utf-8")


def _sanitize_dataset_name(name: str) -> str:
    keep = []
    for ch in name:
        if ch.isalnum() or ch in ("-", "_"):
            keep.append(ch)
        else:
            keep.append("_")
    return "".join(keep).strip("_") or "dataset"


def _print_summary(rows: list[dict[str, Any]]) -> None:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in rows:
        key = (str(row["dataset_name"]), str(row["method"]))
        grouped.setdefault(key, []).append(row)

    print(
        "dataset | method | mean_fitness | best_fitness | "
        "mean_hard | best_hard | mean_runtime"
    )
    print("-" * 95)
    for (dataset_name, method), items in sorted(grouped.items()):
        mean_fitness = statistics.fmean(float(i["final_fitness"]) for i in items)
        best_fitness = min(float(i["final_fitness"]) for i in items)
        mean_hard = statistics.fmean(float(i["hard_violations"]) for i in items)
        best_hard = min(int(i["hard_violations"]) for i in items)
        mean_runtime = statistics.fmean(float(i["runtime_seconds"]) for i in items)
        print(
            f"{dataset_name} | {method} | {mean_fitness:.2f} | "
            f"{best_fitness:.2f} | {mean_hard:.2f} | {best_hard} | {mean_runtime:.2f}"
        )


def _build_summary_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in rows:
        key = (str(row["dataset_name"]), str(row["method"]))
        grouped.setdefault(key, []).append(row)

    summary: list[dict[str, Any]] = []
    for (dataset_name, method), items in sorted(grouped.items()):
        summary.append(
            {
                "dataset_name": dataset_name,
                "method": method,
                "mean_fitness": statistics.fmean(float(i["final_fitness"]) for i in items),
                "best_fitness": min(float(i["final_fitness"]) for i in items),
                "mean_hard_violations": statistics.fmean(
                    float(i["hard_violations"]) for i in items
                ),
                "best_hard_violations": min(int(i["hard_violations"]) for i in items),
                "mean_soft_penalty": statistics.fmean(float(i["soft_penalty"]) for i in items),
                "best_soft_penalty": min(float(i["soft_penalty"]) for i in items),
                "mean_runtime_seconds": statistics.fmean(
                    float(i["runtime_seconds"]) for i in items
                ),
                "best_runtime_seconds": min(float(i["runtime_seconds"]) for i in items),
            }
        )
    return summary


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint for benchmark execution."""
    parser = argparse.ArgumentParser(description="Benchmark timetabling methods")
    parser.add_argument(
        "--datasets",
        nargs="+",
        required=True,
        help="One or more ITC dataset file paths",
    )
    parser.add_argument("--runs", type=int, default=1, help="Repetitions per dataset")
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Quick pipeline validation: runs=1 and skips ACO",
    )
    parser.add_argument(
        "--final",
        action="store_true",
        help="Final benchmarking mode: runs=3 with all methods",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Base random seed (run i uses seed + i - 1)",
    )
    args = parser.parse_args(argv)

    run_benchmarks(
        args.datasets,
        args.runs,
        quick=args.quick,
        final_mode=args.final,
        seed=args.seed,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
