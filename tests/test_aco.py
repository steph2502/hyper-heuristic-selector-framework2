"""Tests for ant colony optimization."""

from __future__ import annotations

import pytest

from algorithms.aco import run_aco
from algorithms.initializer import generate_initial_solution
from models.course import Course
from models.room import Room
from models.timetable import TimetableState
from parsers.itc_parser import Curriculum, ITCInstance


@pytest.fixture
def small_itc_instance() -> ITCInstance:
    """Synthetic instance: 3 courses, 2 rooms, 3 days, 5 periods."""
    return ITCInstance(
        name="aco_small",
        courses=(
            Course("c1", "t1", 1, 1, 10),
            Course("c2", "t2", 1, 1, 10),
            Course("c3", "t3", 1, 1, 10),
        ),
        rooms=(Room("r1", 50), Room("r2", 50)),
        curricula=(
            Curriculum("cu1", ("c1", "c2")),
            Curriculum("cu2", ("c3",)),
        ),
        unavailability=(),
        nr_days=3,
        periods_per_day=5,
    )


def test_aco_runs(small_itc_instance: ITCInstance) -> None:
    run_aco(small_itc_instance, iterations=5, num_ants=3)


def test_aco_returns_timetable_state(small_itc_instance: ITCInstance) -> None:
    best, history = run_aco(small_itc_instance, iterations=5, num_ants=3)
    assert isinstance(best, TimetableState)
    assert isinstance(history, list)
    assert len(history) == 5
    assert all(isinstance(x, float) for x in history)


def test_aco_fitness_does_not_degrade(small_itc_instance: ITCInstance) -> None:
    initial = generate_initial_solution(small_itc_instance)
    initial_fitness = float(initial.fitness or 0.0)
    best, _ = run_aco(small_itc_instance, iterations=20, num_ants=3)
    best_fitness = float(best.fitness or 0.0)
    assert best_fitness <= initial_fitness
