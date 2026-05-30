"""Tests for timetable export and visualization utilities."""

from __future__ import annotations

import csv
from pathlib import Path

from algorithms.initializer import generate_initial_solution
from models.timetable import LectureAssignment
from parsers.itc_parser import parse_itc_file
from utils.timetable_output import export_timetable_csv

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def test_export_timetable_csv_creates_file_with_columns(tmp_path: Path) -> None:
    inst = parse_itc_file(FIXTURES / "minimal_itc.txt")
    state = generate_initial_solution(inst)
    out = tmp_path / "results" / "final_timetable.csv"

    saved = export_timetable_csv(state, inst, out)
    assert saved.exists()

    with saved.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []
        assert "course_id" in fieldnames
        assert "room_id" in fieldnames
        assert "day" in fieldnames
        assert "period" in fieldnames
        rows = list(reader)
        assert len(rows) == len(state.assignments)


def test_export_timetable_csv_marks_unscheduled(tmp_path: Path) -> None:
    inst = parse_itc_file(FIXTURES / "minimal_itc.txt")
    state = generate_initial_solution(inst)
    state.assignments[0] = LectureAssignment("c1", None, None, None)
    out = tmp_path / "results" / "final_timetable.csv"

    saved = export_timetable_csv(state, inst, out)
    with saved.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        row = next(reader)
        assert row["room_id"] == "UNSCHEDULED"
        assert row["day"] == "UNSCHEDULED"
        assert row["period"] == "UNSCHEDULED"
