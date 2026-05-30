"""Neighborhood operators for local search (ACO/PSO move and swap steps).

All operators return a **new** :class:`TimetableState`; the input ``state`` is never
mutated. Assignment rows are copied with a shallow ``list()`` and only touched
indices are replaced with new :class:`LectureAssignment` instances.
"""

from __future__ import annotations

import random

from algorithms.fitness import evaluate_timetable
from models.timetable import LectureAssignment, TimetableState
from parsers.itc_parser import ITCInstance


def move_lecture(
    state: TimetableState,
    instance: ITCInstance,
    lecture_index: int,
    room_id: str,
    day: int,
    period: int,
) -> TimetableState:
    """Return a new state with lecture ``lecture_index`` placed at ``(room_id, day, period)``.

    Raises:
        IndexError: If ``lecture_index`` is out of range.
        ValueError: If ``room_id`` is unknown or ``day`` / ``period`` are out of bounds.
    """
    if not (0 <= lecture_index < len(state.assignments)):
        raise IndexError(f"lecture_index {lecture_index} out of range for {len(state.assignments)} slots")
    if room_id not in {r.room_id for r in instance.rooms}:
        raise ValueError(f"Unknown room_id {room_id!r}")
    if not (0 <= day < instance.nr_days):
        raise ValueError(f"day {day} out of range [0, {instance.nr_days})")
    if not (0 <= period < instance.periods_per_day):
        raise ValueError(f"period {period} out of range [0, {instance.periods_per_day})")

    assignments = list(state.assignments)
    cur = assignments[lecture_index]
    assignments[lecture_index] = LectureAssignment(cur.course_id, room_id, day, period)
    new_state = TimetableState(assignments=assignments)
    evaluate_timetable(new_state, instance)
    return new_state


def swap_lectures(
    state: TimetableState,
    instance: ITCInstance,
    idx1: int,
    idx2: int,
) -> TimetableState:
    """Return a new state where the time/room packages of two slots are exchanged.

    Each slot keeps its ``course_id``; only ``(room_id, day, period)`` are swapped.
    ``None`` positions are swapped like any other values.

    Raises:
        IndexError: If an index is out of range.
        ValueError: If ``idx1 == idx2``.
    """
    n = len(state.assignments)
    if not (0 <= idx1 < n) or not (0 <= idx2 < n):
        raise IndexError("swap indices out of range")
    if idx1 == idx2:
        raise ValueError("swap_lectures requires two distinct indices")

    assignments = list(state.assignments)
    a, b = assignments[idx1], assignments[idx2]
    assignments[idx1] = LectureAssignment(a.course_id, b.room_id, b.day, b.period)
    assignments[idx2] = LectureAssignment(b.course_id, a.room_id, a.day, a.period)
    new_state = TimetableState(assignments=assignments)
    evaluate_timetable(new_state, instance)
    return new_state


def random_neighbor(state: TimetableState, instance: ITCInstance) -> TimetableState:
    """Apply a random **move** or **swap** (50/50 when at least two slots exist).

    **Move:** uniform random lecture index, random room from the instance, and
    random ``(day, period)`` within timetable dimensions.

    **Swap:** two distinct random lecture indices.

    The returned state is always freshly scored with :func:`evaluate_timetable`.
    """
    n = len(state.assignments)
    if n == 0:
        new_state = TimetableState(assignments=[])
        evaluate_timetable(new_state, instance)
        return new_state

    if n < 2 or random.random() < 0.5:
        room = random.choice(instance.rooms)
        li = random.randrange(n)
        day = random.randrange(instance.nr_days)
        period = random.randrange(instance.periods_per_day)
        return move_lecture(state, instance, li, room.room_id, day, period)

    i, j = random.sample(range(n), 2)
    return swap_lectures(state, instance, i, j)
