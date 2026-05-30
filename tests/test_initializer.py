"""Smoke tests for greedy initial solution generation."""

from __future__ import annotations

from pathlib import Path

from algorithms.initializer import count_scheduled_lectures, generate_initial_solution
from parsers.itc_parser import parse_itc_file

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def test_generate_initial_runs_and_counts() -> None:
    inst = parse_itc_file(FIXTURES / "minimal_itc.txt")
    state = generate_initial_solution(inst)
    assert state.fitness is not None
    assert state.hard_violations is not None
    sch, tot = count_scheduled_lectures(state)
    assert tot == 1
    assert sch == 1
    assert state.hard_violations == 0
