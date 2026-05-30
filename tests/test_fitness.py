"""Tests for shared fitness evaluation."""

from __future__ import annotations

from pathlib import Path

from algorithms.fitness import HARD_WEIGHT, FitnessResult, evaluate_fitness, evaluate_timetable
from models.timetable import LectureAssignment, TimetableState
from parsers.itc_parser import parse_itc_file

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def _assign_all(
    inst,
    slots: list[tuple[str, str, int, int]],
) -> TimetableState:
    """Build a timetable from parallel (course_id, room_id, day, period) per lecture slot."""
    assigns = [LectureAssignment(c, r, d, p) for c, r, d, p in slots]
    return TimetableState(assignments=assigns)


def test_empty_timetable_counts_all_unscheduled() -> None:
    inst = parse_itc_file(FIXTURES / "minimal_itc.txt")
    state = TimetableState.from_course_list(inst.courses)
    r = evaluate_fitness(inst, state, update_state=False)
    assert r.hard_violations == 1
    assert r.soft_penalty == 0.0
    assert r.total_fitness == HARD_WEIGHT


def test_feasible_single_lecture_zero_hard() -> None:
    inst = parse_itc_file(FIXTURES / "minimal_itc.txt")
    state = _assign_all(inst, [("c1", "r1", 0, 0)])
    out = evaluate_timetable(state, inst)
    assert out is state
    assert state.hard_violations == 0
    assert state.fitness == state.soft_penalty


def test_room_double_booking() -> None:
    inst = parse_itc_file(FIXTURES / "two_courses.txt")
    state = _assign_all(
        inst,
        [
            ("c1", "r1", 0, 0),
            ("c2", "r1", 0, 0),
        ],
    )
    r = evaluate_fitness(inst, state, update_state=False)
    assert r.hard_violations == 1


def test_teacher_double_booking() -> None:
    inst = parse_itc_file(FIXTURES / "two_courses.txt")
    inst2 = type(inst)(
        name=inst.name,
        courses=tuple(
            type(inst.courses[0])(
                course_id=c.course_id,
                teacher_id="t_shared",
                lectures_per_week=c.lectures_per_week,
                min_working_days=c.min_working_days,
                students=c.students,
            )
            for c in inst.courses
        ),
        rooms=inst.rooms,
        curricula=inst.curricula,
        unavailability=inst.unavailability,
        nr_days=inst.nr_days,
        periods_per_day=inst.periods_per_day,
    )
    state = _assign_all(
        inst2,
        [
            ("c1", "r1", 0, 0),
            ("c2", "r1", 0, 0),
        ],
    )
    r = evaluate_fitness(inst2, state, update_state=False)
    assert r.hard_violations == 2  # room + teacher


def test_curriculum_conflict_independent_of_teacher() -> None:
    inst = parse_itc_file(FIXTURES / "shared_curriculum.txt")
    state = _assign_all(
        inst,
        [
            ("c1", "r1", 0, 0),
            ("c2", "r1", 0, 1),
        ],
    )
    r_ok = evaluate_fitness(inst, state, update_state=False)
    assert r_ok.hard_violations == 0

    clash = _assign_all(
        inst,
        [
            ("c1", "r1", 0, 0),
            ("c2", "r1", 0, 0),
        ],
    )
    r_bad = evaluate_fitness(inst, clash, update_state=False)
    assert r_bad.hard_violations == 2  # room + curriculum (two courses same curriculum same slot)


def test_unavailability_violation() -> None:
    from parsers.itc_parser import ITCInstance, Curriculum, UnavailabilityConstraint
    from models.course import Course
    from models.room import Room

    inst = ITCInstance(
        name="u",
        courses=(
            Course("c1", "t1", 1, 1, 10),
        ),
        rooms=(Room("r1", 50),),
        curricula=(Curriculum("cu", ("c1",)),),
        unavailability=(
            UnavailabilityConstraint("c1", ((0, 0),)),
        ),
        nr_days=2,
        periods_per_day=2,
    )
    state = _assign_all(inst, [("c1", "r1", 0, 0)])
    r = evaluate_fitness(inst, state, update_state=False)
    assert r.hard_violations == 1


def test_hard_room_capacity_excess() -> None:
    inst = parse_itc_file(FIXTURES / "minimal_itc.txt")
    # shrink room capacity below students
    inst2 = type(inst)(
        name=inst.name,
        courses=tuple(
            type(inst.courses[0])(
                course_id=c.course_id,
                teacher_id=c.teacher_id,
                lectures_per_week=c.lectures_per_week,
                min_working_days=c.min_working_days,
                students=100,
            )
            for c in inst.courses
        ),
        rooms=tuple(type(inst.rooms[0])(room_id=r.room_id, capacity=30) for r in inst.rooms),
        curricula=inst.curricula,
        unavailability=inst.unavailability,
        nr_days=inst.nr_days,
        periods_per_day=inst.periods_per_day,
    )
    state = _assign_all(inst2, [("c1", "r1", 0, 0)])
    r = evaluate_fitness(inst2, state, update_state=False)
    assert r.hard_violations == 1
    assert r.soft_penalty == 0.0
    assert r.total_fitness == HARD_WEIGHT


def test_soft_min_working_days_and_compactness() -> None:
    txt = FIXTURES / "minimal_itc.txt"
    inst = parse_itc_file(txt)
    inst2 = type(inst)(
        name=inst.name,
        courses=tuple(
            type(inst.courses[0])(
                course_id=c.course_id,
                teacher_id=c.teacher_id,
                lectures_per_week=2,
                min_working_days=2,
                students=c.students,
            )
            for c in inst.courses
        ),
        rooms=inst.rooms,
        curricula=inst.curricula,
        unavailability=inst.unavailability,
        nr_days=inst.nr_days,
        periods_per_day=inst.periods_per_day,
    )
    # same day, periods 0 and 2 -> one working day + one gap of size 1 on day 0 for the curriculum
    state = _assign_all(
        inst2,
        [
            ("c1", "r1", 0, 0),
            ("c1", "r1", 0, 2),
        ],
    )
    r = evaluate_fitness(inst2, state, update_state=False)
    assert r.hard_violations == 0
    assert r.soft_penalty == 5.0 * 1.0 + 2.0 * 1.0  # min days + compactness gap


def test_soft_room_stability(tmp_path: Path) -> None:
    content = "\n".join(
        [
            "Name: stab",
            "Days: 2",
            "Periods_per_day: 2",
            "Courses: 1",
            "Rooms: 2",
            "Curricula: 1",
            "Constraints: 0",
            "",
            "COURSES:",
            "c1 t1 2 2 10",
            "",
            "ROOMS:",
            "r1 50",
            "r2 50",
            "",
            "CURRICULA:",
            "cu 1 c1",
            "",
            "UNAVAILABILITY CONSTRAINTS:",
            "",
        ]
    )
    p = tmp_path / "stab.txt"
    p.write_text(content, encoding="utf-8")
    inst = parse_itc_file(p)
    state = _assign_all(
        inst,
        [
            ("c1", "r1", 0, 0),
            ("c1", "r2", 1, 0),
        ],
    )
    r = evaluate_fitness(inst, state, update_state=False)
    assert r.hard_violations == 0
    assert r.soft_penalty >= 1.0


def test_fitness_result_dataclass() -> None:
    fr = FitnessResult(total_fitness=3.0, hard_violations=0, soft_penalty=3.0)
    assert fr.total_fitness == 3.0
