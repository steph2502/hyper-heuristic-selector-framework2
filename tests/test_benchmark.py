"""Tests for experiment benchmark runner."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from experiments.benchmark import run_benchmarks

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def test_run_benchmarks_writes_outputs(tmp_path: Path) -> None:
    dataset = FIXTURES / "minimal_itc.txt"
    rows, entries = run_benchmarks([dataset], runs=1, output_dir=tmp_path / "results")
    assert rows
    assert entries

    csv_path = tmp_path / "results" / "benchmark_results.csv"
    json_path = tmp_path / "results" / "convergence_histories.json"
    summary_path = tmp_path / "results" / "final_benchmark_summary.csv"
    notes_path = tmp_path / "results" / "benchmark_notes.txt"
    timetable_csv = (
        tmp_path
        / "results"
        / "generated_timetables"
        / "tiny_ok"
        / "controller_run_1.csv"
    )
    timetable_txt = (
        tmp_path
        / "results"
        / "generated_timetables"
        / "tiny_ok"
        / "controller_run_1.txt"
    )
    assert csv_path.exists()
    assert json_path.exists()
    assert summary_path.exists()
    assert notes_path.exists()
    assert timetable_csv.exists()
    assert timetable_txt.exists()

    with csv_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []
        for expected in (
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
        ):
            assert expected in fieldnames
        all_rows = list(reader)
        assert len(all_rows) == 4

    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert "entries" in payload
    assert len(payload["entries"]) == 4

    notes = notes_path.read_text(encoding="utf-8")
    assert "PSO may outperform the controller on some datasets." in notes


def test_run_benchmarks_quick_skips_aco(tmp_path: Path) -> None:
    dataset = FIXTURES / "minimal_itc.txt"
    rows, _ = run_benchmarks(
        [dataset],
        runs=3,
        output_dir=tmp_path / "results_quick",
        quick=True,
    )
    methods = {str(r["method"]) for r in rows}
    assert methods == {"Greedy", "PSO", "Controller"}
    assert len(rows) == 3


def test_run_benchmarks_seed_is_recorded(tmp_path: Path) -> None:
    dataset = FIXTURES / "minimal_itc.txt"
    rows, entries = run_benchmarks(
        [dataset],
        runs=2,
        output_dir=tmp_path / "results_seeded",
        seed=123,
    )
    assert len(rows) == 8
    seeds = [row["seed"] for row in rows]
    assert 123 in seeds
    assert 124 in seeds
    assert entries
