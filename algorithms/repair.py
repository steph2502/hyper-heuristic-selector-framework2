"""Conflict detection and repair operators for timetable states."""

from __future__ import annotations

import random
from collections import defaultdict
from dataclasses import dataclass
from typing import Any

from algorithms.fitness import evaluate_timetable
from algorithms.neighborhood import move_lecture
from models.course import Course
from models.room import Room
from models.timetable import LectureAssignment, TimetableState
from parsers.itc_parser import ITCInstance

MAX_CANDIDATE_SLOTS_PER_LECTURE = 28
_CONTEXT_CACHE: dict[tuple[Any, ...], "_RepairContext"] = {}


@dataclass(frozen=True, slots=True)
class _RepairContext:
    course_by_id: dict[str, Course]
    room_by_id: dict[str, Room]
    forbidden: dict[str, frozenset[tuple[int, int]]]
    course_to_curr: dict[str, tuple[str, ...]]
    feasible_slots_by_course: dict[str, tuple[tuple[str, int, int], ...]]


def get_conflicting_lectures(state: TimetableState, instance: ITCInstance) -> set[int]:
    """Return lecture indices that contribute to any hard-constraint violation."""
    ctx = _context(instance)
    conflicts: set[int] = set()

    room_slot_to_indices: dict[tuple[str, int, int], list[int]] = defaultdict(list)
    teacher_slot_to_indices: dict[tuple[str, int, int], list[int]] = defaultdict(list)
    curr_slot_to_indices: dict[tuple[str, int, int], list[int]] = defaultdict(list)

    for idx, assignment in enumerate(state.assignments):
        course = ctx.course_by_id.get(assignment.course_id)
        if course is None:
            conflicts.add(idx)
            continue

        if not _is_valid_placement(assignment, ctx.room_by_id, instance):
            conflicts.add(idx)
            continue

        rid = assignment.room_id
        day = assignment.day
        period = assignment.period
        assert rid is not None and day is not None and period is not None

        room = ctx.room_by_id[rid]
        if course.students > room.capacity:
            conflicts.add(idx)
        if (day, period) in ctx.forbidden.get(course.course_id, frozenset()):
            conflicts.add(idx)

        room_slot_to_indices[(rid, day, period)].append(idx)
        teacher_slot_to_indices[(course.teacher_id, day, period)].append(idx)
        for cur_id in ctx.course_to_curr.get(course.course_id, ()):
            curr_slot_to_indices[(cur_id, day, period)].append(idx)

    for idxs in room_slot_to_indices.values():
        if len(idxs) > 1:
            conflicts.update(idxs)
    for idxs in teacher_slot_to_indices.values():
        if len(idxs) > 1:
            conflicts.update(idxs)
    for idxs in curr_slot_to_indices.values():
        if len(idxs) > 1:
            conflicts.update(idxs)

    return conflicts


def repair_conflicts(
    state: TimetableState,
    instance: ITCInstance,
    max_attempts: int = 50,
) -> TimetableState:
    """Repair hard violations using bounded first-improvement search."""
    if state.fitness is None:
        evaluate_timetable(state, instance)

    ctx = _context(instance)
    current = state
    attempts = 0

    while attempts < max_attempts:
        conflicts = list(get_conflicting_lectures(current, instance))
        if not conflicts or int(current.hard_violations or 0) == 0:
            break
        random.shuffle(conflicts)

        improved = False
        for lecture_index in conflicts:
            if attempts >= max_attempts:
                break
            attempts += 1

            assignment = current.assignments[lecture_index]
            baseline_hard = int(current.hard_violations or 0)
            baseline_soft = float(current.soft_penalty or 0.0)

            slots = list(ctx.feasible_slots_by_course.get(assignment.course_id, ()))
            if not slots:
                continue
            random.shuffle(slots)
            if len(slots) > MAX_CANDIDATE_SLOTS_PER_LECTURE:
                slots = slots[:MAX_CANDIDATE_SLOTS_PER_LECTURE]

            for room_id, day, period in slots:
                if (
                    assignment.room_id == room_id
                    and assignment.day == day
                    and assignment.period == period
                ):
                    continue
                candidate = move_lecture(current, instance, lecture_index, room_id, day, period)
                cand_hard = int(candidate.hard_violations or 0)
                cand_soft = float(candidate.soft_penalty or 0.0)
                if cand_hard < baseline_hard or (
                    cand_hard == baseline_hard and cand_soft < baseline_soft
                ):
                    current = candidate
                    improved = True
                    break

            if improved:
                if int(current.hard_violations or 0) == 0:
                    return current
                break

        if not improved:
            break

    return current


def ruin_and_recreate(
    state: TimetableState,
    instance: ITCInstance,
    *,
    lectures_to_ruin: int = 8,
    repair_attempts: int = 30,
) -> TimetableState:
    """Unschedule a subset of lectures then greedily repair conflicts."""
    if not state.assignments:
        return state
    if state.fitness is None:
        evaluate_timetable(state, instance)

    conflicts = list(get_conflicting_lectures(state, instance))
    pool = conflicts if conflicts else list(range(len(state.assignments)))
    random.shuffle(pool)
    k = min(max(1, lectures_to_ruin), len(pool))
    chosen = set(pool[:k])

    new_assignments = list(state.assignments)
    for idx in chosen:
        a = new_assignments[idx]
        new_assignments[idx] = LectureAssignment(a.course_id, None, None, None)

    ruined = TimetableState(assignments=new_assignments)
    evaluate_timetable(ruined, instance)
    return repair_conflicts(ruined, instance, max_attempts=repair_attempts)


def feasible_slots_by_course(
    instance: ITCInstance,
) -> dict[str, tuple[tuple[str, int, int], ...]]:
    """Return cached feasible slots by course (capacity + unavailability only)."""
    return _context(instance).feasible_slots_by_course


def _context(instance: ITCInstance) -> _RepairContext:
    key = _instance_cache_key(instance)
    cached = _CONTEXT_CACHE.get(key)
    if cached is not None:
        return cached

    course_by_id: dict[str, Course] = {c.course_id: c for c in instance.courses}
    room_by_id: dict[str, Room] = {r.room_id: r for r in instance.rooms}
    forbidden = _forbidden_by_course(instance)
    course_to_curr = _course_to_curricula(instance)
    slots = _build_feasible_slots(instance, course_by_id, forbidden)
    ctx = _RepairContext(
        course_by_id=course_by_id,
        room_by_id=room_by_id,
        forbidden=forbidden,
        course_to_curr=course_to_curr,
        feasible_slots_by_course=slots,
    )
    _CONTEXT_CACHE[key] = ctx
    return ctx


def _instance_cache_key(instance: ITCInstance) -> tuple[Any, ...]:
    courses = tuple(
        (
            c.course_id,
            c.teacher_id,
            c.lectures_per_week,
            c.min_working_days,
            c.students,
        )
        for c in instance.courses
    )
    rooms = tuple((r.room_id, r.capacity) for r in instance.rooms)
    curricula = tuple((cu.curriculum_id, tuple(cu.course_ids)) for cu in instance.curricula)
    unavailability = tuple(
        (u.course_id, tuple(u.forbidden_slots)) for u in instance.unavailability
    )
    return (
        instance.nr_days,
        instance.periods_per_day,
        courses,
        rooms,
        curricula,
        unavailability,
    )


def _build_feasible_slots(
    instance: ITCInstance,
    course_by_id: dict[str, Course],
    forbidden: dict[str, frozenset[tuple[int, int]]],
) -> dict[str, tuple[tuple[str, int, int], ...]]:
    out: dict[str, tuple[tuple[str, int, int], ...]] = {}
    for cid, course in course_by_id.items():
        slots: list[tuple[str, int, int]] = []
        blocked = forbidden.get(cid, frozenset())
        for room in instance.rooms:
            if course.students > room.capacity:
                continue
            for day in range(instance.nr_days):
                for period in range(instance.periods_per_day):
                    if (day, period) in blocked:
                        continue
                    slots.append((room.room_id, day, period))
        out[cid] = tuple(slots)
    return out


def _forbidden_by_course(instance: ITCInstance) -> dict[str, frozenset[tuple[int, int]]]:
    out: dict[str, set[tuple[int, int]]] = {}
    for u in instance.unavailability:
        out.setdefault(u.course_id, set()).update(u.forbidden_slots)
    return {k: frozenset(v) for k, v in out.items()}


def _course_to_curricula(instance: ITCInstance) -> dict[str, tuple[str, ...]]:
    out: dict[str, list[str]] = defaultdict(list)
    for cu in instance.curricula:
        for cid in cu.course_ids:
            out[cid].append(cu.curriculum_id)
    return {k: tuple(v) for k, v in out.items()}


def _is_valid_placement(
    assignment: LectureAssignment,
    room_by_id: dict[str, Room],
    instance: ITCInstance,
) -> bool:
    if assignment.room_id is None or assignment.day is None or assignment.period is None:
        return False
    if assignment.room_id not in room_by_id:
        return False
    return 0 <= assignment.day < instance.nr_days and 0 <= assignment.period < instance.periods_per_day
