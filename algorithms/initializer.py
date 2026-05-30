"""Greedy construction of a starting timetable (baseline for meta-heuristics)."""

from __future__ import annotations

from algorithms.fitness import evaluate_timetable
from models.course import Course
from models.timetable import LectureAssignment, TimetableState
from parsers.itc_parser import ITCInstance


def generate_initial_solution(instance: ITCInstance) -> TimetableState:
    """Build a timetable by placing lectures one-by-one in a greedy order.

    Lecture slots are sorted by descending **difficulty** (``lectures_per_week``,
    then ``students``) so constrained courses are placed first.

    For each slot, every feasible-shaped candidate (room, day, period) is tried.
    Candidates that cannot satisfy capacity or static unavailability for that
    course are skipped without a full evaluation. For the remainder,
    :func:`algorithms.fitness.evaluate_timetable` scores the full state so new
    clashes with already-placed lectures are accounted for.

    The candidate with the lowest ``hard_violations`` is kept; ``soft_penalty``
    breaks ties, then lexicographic ``(room_id, day, period)`` for determinism.

    If **every** candidate yields **strictly greater** ``hard_violations`` than
    leaving the slot empty, the lecture stays unscheduled (``None`` room/day/period).

    The returned state has been evaluated with :func:`evaluate_timetable` after
    each lecture decision (final pass included).

    Args:
        instance: Parsed ITC instance.

    Returns:
        Populated :class:`TimetableState` (partially feasible in general).
    """
    state = TimetableState.from_course_list(instance.courses)
    course_by_id: dict[str, Course] = {c.course_id: c for c in instance.courses}
    forbidden = _forbidden_by_course(instance)

    order = _lecture_indices_by_difficulty(state, course_by_id)

    for idx in order:
        current = state.assignments[idx]
        cid = current.course_id
        course = course_by_id[cid]

        state.assignments[idx] = LectureAssignment(cid, None, None, None)
        evaluate_timetable(state, instance)
        baseline_hard = int(state.hard_violations or 0)

        best: tuple[int, float, str, int, int] | None = None
        # best = (hard, soft, room_id, day, period) — minimized lexicographically

        for room in instance.rooms:
            if course.students > room.capacity:
                continue
            for day in range(instance.nr_days):
                for period in range(instance.periods_per_day):
                    if (day, period) in forbidden.get(cid, frozenset()):
                        continue
                    rid = room.room_id
                    state.assignments[idx] = LectureAssignment(cid, rid, day, period)
                    evaluate_timetable(state, instance)
                    h = int(state.hard_violations or 0)
                    s = float(state.soft_penalty or 0.0)
                    cand = (h, s, rid, day, period)
                    if best is None or cand < best:
                        best = cand
                    state.assignments[idx] = LectureAssignment(cid, None, None, None)

        if best is None or best[0] > baseline_hard:
            state.assignments[idx] = LectureAssignment(cid, None, None, None)
        else:
            _, _, rid, day, period = best
            state.assignments[idx] = LectureAssignment(cid, rid, day, period)

        evaluate_timetable(state, instance)
    return state


def _forbidden_by_course(instance: ITCInstance) -> dict[str, frozenset[tuple[int, int]]]:
    out: dict[str, set[tuple[int, int]]] = {}
    for u in instance.unavailability:
        out.setdefault(u.course_id, set()).update(u.forbidden_slots)
    return {k: frozenset(v) for k, v in out.items()}


def _lecture_indices_by_difficulty(
    state: TimetableState,
    course_by_id: dict[str, Course],
) -> list[int]:
    """Indices sorted hardest-first for greedy placement."""

    def key(idx: int) -> tuple[int, int, str, int]:
        c = course_by_id[state.assignments[idx].course_id]
        return (-c.lectures_per_week, -c.students, c.course_id, idx)

    return sorted(range(len(state.assignments)), key=key)


def count_scheduled_lectures(state: TimetableState) -> tuple[int, int]:
    """Return ``(scheduled_count, total_slots)``."""
    total = len(state.assignments)
    scheduled = sum(
        1
        for a in state.assignments
        if a.room_id is not None and a.day is not None and a.period is not None
    )
    return scheduled, total
