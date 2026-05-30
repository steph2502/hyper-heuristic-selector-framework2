"""Tests for neighborhood move/swap operators."""

from __future__ import annotations

from pathlib import Path

import pytest

from algorithms.fitness import evaluate_timetable
from algorithms.neighborhood import move_lecture, random_neighbor, swap_lectures
from models.timetable import LectureAssignment, TimetableState
from parsers.itc_parser import parse_itc_file

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def _two_lecture_feasible_state(inst):
    """Two courses, one lecture each, non-overlapping slots."""
    return TimetableState(
        assignments=[
            LectureAssignment("c1", "r1", 0, 0),
            LectureAssignment("c2", "r1", 0, 1),
        ]
    )


def test_move_lecture_changes_exactly_one_slot() -> None:
    inst = parse_itc_file(FIXTURES / "two_courses.txt")
    state = _two_lecture_feasible_state(inst)
    evaluate_timetable(state, inst)

    new_state = move_lecture(state, inst, 1, "r1", 1, 0)

    assert new_state is not state
    assert new_state.assignments is not state.assignments
    assert new_state.assignments[0] == state.assignments[0]
    assert new_state.assignments[1] != state.assignments[1]
    assert new_state.assignments[1] == LectureAssignment("c2", "r1", 1, 0)


def test_swap_lectures_exchanges_time_room_only() -> None:
    inst = parse_itc_file(FIXTURES / "two_courses.txt")
    state = TimetableState(
        assignments=[
            LectureAssignment("c1", "r1", 0, 0),
            LectureAssignment("c2", "r1", 1, 1),
        ]
    )
    evaluate_timetable(state, inst)

    new_state = swap_lectures(state, inst, 0, 1)

    assert new_state.assignments[0] == LectureAssignment("c1", "r1", 1, 1)
    assert new_state.assignments[1] == LectureAssignment("c2", "r1", 0, 0)
    assert state.assignments[0].room_id == "r1" and state.assignments[0].day == 0


def test_operators_do_not_mutate_original_state() -> None:
    inst = parse_itc_file(FIXTURES / "two_courses.txt")
    state = _two_lecture_feasible_state(inst)
    evaluate_timetable(state, inst)
    frozen_before = [LectureAssignment(a.course_id, a.room_id, a.day, a.period) for a in state.assignments]

    _ = move_lecture(state, inst, 0, "r1", 1, 1)
    assert [LectureAssignment(a.course_id, a.room_id, a.day, a.period) for a in state.assignments] == frozen_before

    s2 = _two_lecture_feasible_state(inst)
    evaluate_timetable(s2, inst)
    fb2 = [LectureAssignment(a.course_id, a.room_id, a.day, a.period) for a in s2.assignments]
    _ = swap_lectures(s2, inst, 0, 1)
    assert [LectureAssignment(a.course_id, a.room_id, a.day, a.period) for a in s2.assignments] == fb2


def test_returned_state_fitness_is_recomputed_not_stale_copy() -> None:
    inst = parse_itc_file(FIXTURES / "two_courses.txt")
    state = _two_lecture_feasible_state(inst)
    evaluate_timetable(state, inst)
    assert state.hard_violations == 0

    # Force room double-booking: both lectures same slot — hard violations must rise.
    conflicted = move_lecture(state, inst, 1, "r1", 0, 0)
    assert conflicted.hard_violations > 0
    assert conflicted.fitness is not None
    assert conflicted.fitness != state.fitness

    # Sanity: explicit re-evaluation of the same assignment list matches returned scores.
    probe = TimetableState(assignments=list(conflicted.assignments))
    evaluate_timetable(probe, inst)
    assert probe.hard_violations == conflicted.hard_violations
    assert probe.soft_penalty == conflicted.soft_penalty
    assert probe.fitness == conflicted.fitness


def _slot_tuple(a: LectureAssignment) -> tuple:
    return (a.course_id, a.room_id, a.day, a.period)


def test_random_neighbor_is_deterministic_with_seed() -> None:
    inst = parse_itc_file(FIXTURES / "two_courses.txt")
    state = _two_lecture_feasible_state(inst)
    evaluate_timetable(state, inst)
    import random

    random.seed(42)
    a = random_neighbor(state, inst)
    random.seed(42)
    b = random_neighbor(state, inst)
    assert [_slot_tuple(x) for x in a.assignments] == [_slot_tuple(x) for x in b.assignments]
    assert a.fitness == b.fitness


def test_swap_distinct_indices_required() -> None:
    inst = parse_itc_file(FIXTURES / "minimal_itc.txt")
    state = TimetableState.from_course_list(inst.courses)
    with pytest.raises(ValueError, match="distinct"):
        swap_lectures(state, inst, 0, 0)
