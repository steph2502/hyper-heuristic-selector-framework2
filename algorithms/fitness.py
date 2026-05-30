"""Shared fitness evaluation for timetabling search algorithms.

Designed for high call volume (ACO/PSO): one linear scan over assignments plus
linear aggregation over hash buckets (no all-pairs comparisons). NumPy is not
used here; dict/set grouping is typically faster than array materialization per
call for sparse timetables.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from models.course import Course
from models.room import Room
from models.timetable import LectureAssignment, TimetableState
from parsers.itc_parser import ITCInstance

HARD_WEIGHT = 1000


@dataclass(frozen=True, slots=True)
class FitnessResult:
    """Outcome of evaluating a timetable state."""

    total_fitness: float
    hard_violations: int
    soft_penalty: float


def evaluate_timetable(state: TimetableState, instance: ITCInstance) -> TimetableState:
    """Compute fitness and write ``hard_violations``, ``soft_penalty``, and ``fitness`` on ``state``.

    ``fitness = hard_violations * HARD_WEIGHT + soft_penalty`` (lower is better).

    Hard constraints (each violation unit increments ``hard_violations``):

    - Lecture count / unknown course alignment with the instance
    - Unscheduled or out-of-bounds / invalid room placement
    - Room double-booking, lecturer overlap, curriculum overlap
    - Unavailability (blocked day/period)
    - Room capacity (students must not exceed room capacity)

    Soft penalties: room stability, minimum working days, curriculum compactness.

    Returns:
        The same ``state`` object, for chaining.
    """
    hard, soft, total = _compute_fitness_values(state.assignments, instance)
    state.hard_violations = hard
    state.soft_penalty = soft
    state.fitness = total
    return state


def evaluate_fitness(
    instance: ITCInstance,
    state: TimetableState,
    *,
    update_state: bool = True,
) -> FitnessResult:
    """Backward-compatible wrapper around :func:`evaluate_timetable` (argument order legacy)."""
    hard, soft, total = _compute_fitness_values(state.assignments, instance)
    if update_state:
        state.hard_violations = hard
        state.soft_penalty = soft
        state.fitness = total
    return FitnessResult(total_fitness=total, hard_violations=hard, soft_penalty=soft)


def _compute_fitness_values(
    assignments: list[LectureAssignment],
    instance: ITCInstance,
) -> tuple[int, float, float]:
    """Return ``(hard_violations, soft_penalty, total_fitness)``."""
    course_by_id: dict[str, Course] = {c.course_id: c for c in instance.courses}
    room_by_id: dict[str, Room] = {r.room_id: r for r in instance.rooms}
    expected = {c.course_id: c.lectures_per_week for c in instance.courses}
    forbidden = _build_forbidden_map(instance)
    course_to_curr = _course_to_curriculum_ids(instance)

    actual: dict[str, int] = defaultdict(int)
    hard = 0

    # Buckets for O(n) clash detection (keys only for placed lectures).
    room_slot_counts: dict[tuple[str, int, int], int] = defaultdict(int)
    teacher_slot_counts: dict[tuple[str, int, int], int] = defaultdict(int)
    curr_slot_courses: dict[tuple[str, int, int], set[str]] = defaultdict(set)

    # Soft: populated only for placed lectures with known course.
    days_used: dict[str, set[int]] = defaultdict(set)
    rooms_used: dict[str, set[str]] = defaultdict(set)
    # (curriculum_id, day) -> period list for compactness
    curr_day_periods: dict[tuple[str, int], list[int]] = defaultdict(list)

    empty_forbidden: set[tuple[int, int]] = set()

    for a in assignments:
        if a.course_id not in expected:
            hard += 1
            continue
        actual[a.course_id] += 1

        placed = _is_placed(a, room_by_id, instance.nr_days, instance.periods_per_day)
        if not placed:
            hard += 1
            continue

        course = course_by_id[a.course_id]
        rid = a.room_id
        day, period = a.day, a.period
        room = room_by_id[rid]

        if course.students > room.capacity:
            hard += 1

        if (day, period) in forbidden.get(a.course_id, empty_forbidden):
            hard += 1

        key_rp = (rid, day, period)
        room_slot_counts[key_rp] += 1
        teacher_slot_counts[(course.teacher_id, day, period)] += 1

        for cur_id in course_to_curr.get(a.course_id, ()):
            curr_slot_courses[(cur_id, day, period)].add(a.course_id)
            curr_day_periods[(cur_id, day)].append(period)

        days_used[a.course_id].add(day)
        rooms_used[a.course_id].add(rid)

    for cid, need in expected.items():
        got = actual.get(cid, 0)
        if got != need:
            hard += abs(need - got)

    for cnt in room_slot_counts.values():
        if cnt > 1:
            hard += cnt - 1
    for cnt in teacher_slot_counts.values():
        if cnt > 1:
            hard += cnt - 1
    for courses in curr_slot_courses.values():
        if len(courses) > 1:
            hard += len(courses) - 1

    soft = _soft_penalties(
        course_by_id,
        days_used,
        rooms_used,
        curr_day_periods,
    )

    total = hard * HARD_WEIGHT + soft
    return hard, soft, total


def _is_placed(
    a: LectureAssignment,
    room_by_id: dict[str, Room],
    nr_days: int,
    periods_per_day: int,
) -> bool:
    if a.room_id is None or a.day is None or a.period is None:
        return False
    if a.room_id not in room_by_id:
        return False
    return 0 <= a.day < nr_days and 0 <= a.period < periods_per_day


def _build_forbidden_map(instance: ITCInstance) -> dict[str, set[tuple[int, int]]]:
    out: dict[str, set[tuple[int, int]]] = defaultdict(set)
    for u in instance.unavailability:
        for slot in u.forbidden_slots:
            out[u.course_id].add(slot)
    return out


def _course_to_curriculum_ids(instance: ITCInstance) -> dict[str, tuple[str, ...]]:
    """Map each course to curriculum ids (small tuples; built once per evaluation)."""
    m: dict[str, list[str]] = defaultdict(list)
    for cu in instance.curricula:
        for cid in cu.course_ids:
            m[cid].append(cu.curriculum_id)
    return {k: tuple(v) for k, v in m.items()}


def _soft_penalties(
    course_by_id: dict[str, Course],
    days_used: dict[str, set[int]],
    rooms_used: dict[str, set[str]],
    curr_day_periods: dict[tuple[str, int], list[int]],
    *,
    day_weight: int = 5,
    gap_weight: int = 2,
    extra_room_weight: int = 1,
) -> float:
    pen = 0.0

    for cid, c in course_by_id.items():
        used_days = len(days_used.get(cid, ()))
        if used_days > 0 and used_days < c.min_working_days:
            pen += day_weight * float(c.min_working_days - used_days)

        if c.lectures_per_week > 1:
            rset = rooms_used.get(cid, set())
            if len(rset) > 1:
                pen += extra_room_weight * float(len(rset) - 1)

    for periods in curr_day_periods.values():
        if len(periods) < 2:
            continue
        ps = sorted(periods)
        for i in range(len(ps) - 1):
            gap = ps[i + 1] - ps[i] - 1
            if gap > 0:
                pen += gap_weight * float(gap)

    return pen
