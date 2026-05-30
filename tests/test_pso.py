"""Tests for discrete particle swarm optimization."""

from __future__ import annotations

import pytest

from algorithms.initializer import generate_initial_solution
from algorithms.pso import run_pso
from models.course import Course
from models.room import Room
from models.timetable import TimetableState
from parsers.itc_parser import Curriculum, ITCInstance


@pytest.fixture
def small_itc_instance() -> ITCInstance:
    """Synthetic instance: 3 courses, 2 rooms, 3 days, 5 periods."""
    return ITCInstance(
        name="pso_small",
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


def test_pso_runs(small_itc_instance: ITCInstance) -> None:
    run_pso(small_itc_instance, iterations=5, num_particles=3)


def test_pso_returns_timetable_state(small_itc_instance: ITCInstance) -> None:
    best, history = run_pso(small_itc_instance, iterations=5, num_particles=3)
    assert isinstance(best, TimetableState)
    assert isinstance(history, list)
    assert len(history) == 5
    assert all(isinstance(x, float) for x in history)


def test_pso_assignments_are_valid_indices(small_itc_instance: ITCInstance) -> None:
    best, _ = run_pso(small_itc_instance, iterations=10, num_particles=3)
    valid_rooms = {r.room_id for r in small_itc_instance.rooms}
    for assignment in best.assignments:
        if assignment.room_id is not None:
            assert assignment.room_id in valid_rooms
        if assignment.day is not None:
            assert isinstance(assignment.day, int)
            assert 0 <= assignment.day < small_itc_instance.nr_days
        if assignment.period is not None:
            assert isinstance(assignment.period, int)
            assert 0 <= assignment.period < small_itc_instance.periods_per_day


def test_pso_fitness_does_not_degrade(small_itc_instance: ITCInstance) -> None:
    initial = generate_initial_solution(small_itc_instance)
    initial_fitness = float(initial.fitness or 0.0)
    best, _ = run_pso(small_itc_instance, iterations=20, num_particles=3)
    best_fitness = float(best.fitness or 0.0)
    assert best_fitness <= initial_fitness
