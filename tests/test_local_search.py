"""Tests for hill-climbing local search."""

from __future__ import annotations

from pathlib import Path

from algorithms.fitness import evaluate_timetable
from algorithms.local_search import hill_climb
from models.timetable import TimetableState
from parsers.itc_parser import parse_itc_file

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def test_hill_climb_records_history_and_runs() -> None:
    inst = parse_itc_file(FIXTURES / "minimal_itc.txt")
    initial = TimetableState.from_course_list(inst.courses)
    evaluate_timetable(initial, inst)
    best, hist = hill_climb(initial, inst, max_iterations=5, feasible_soft_refinement_iters=0)
    assert len(hist) == 5
    assert all(isinstance(x, float) for x in hist)
    assert best.fitness is not None
