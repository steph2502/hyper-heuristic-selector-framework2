"""Timetable export and console visualization helpers."""

from __future__ import annotations

import csv
from pathlib import Path

from models.timetable import TimetableState
from parsers.itc_parser import ITCInstance
from utils.timetable_display import (
    BREAK_LABEL,
    BREAK_TIME,
    get_day_name,
    get_time_slot,
)


def export_timetable_csv(
    state: TimetableState,
    instance: ITCInstance,
    output_path: str | Path,
) -> Path:
    """Export the final timetable to CSV."""
    course_meta = {
        course.course_id: {
            "course_title": course.course_id,
            "lecturer_id": course.teacher_id,
        }
        for course in instance.courses
    }
    out_path = Path(output_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "Course Code",
                "Course Title",
                "Lecturer ID",
                "Room",
                "Day",
                "Time Slot",
            ]
        )
        for assignment in state.assignments:
            info = course_meta.get(assignment.course_id, {})
            course_title = info.get("course_title") or assignment.course_id
            lecturer_id = info.get("lecturer_id", "")
            room = assignment.room_id if assignment.room_id is not None else "UNSCHEDULED"
            writer.writerow(
                [
                    assignment.course_id,
                    course_title,
                    lecturer_id,
                    room,
                    get_day_name(assignment.day),
                    get_time_slot(assignment.period),
                ]
            )

    return out_path


def print_timetable(state: TimetableState, instance: ITCInstance) -> None:
    """Print timetable grouped by day and period, plus unscheduled lectures."""
    scheduled: dict[int, dict[int, list[tuple[str, str]]]] = {}
    unscheduled: list[str] = []

    for assignment in state.assignments:
        if (
            assignment.room_id is None
            or assignment.day is None
            or assignment.period is None
        ):
            unscheduled.append(assignment.course_id)
            continue
        day_map = scheduled.setdefault(assignment.day, {})
        day_map.setdefault(assignment.period, []).append(
            (assignment.course_id, assignment.room_id)
        )

    for day in range(instance.nr_days):
        print(f"{get_day_name(day)}")
        print("--------------------------------")
        day_map = scheduled.get(day, {})
        for period in range(instance.periods_per_day):
            print(f"{get_time_slot(period)}")
            entries = day_map.get(period, [])
            if not entries:
                print("  (empty)")
            else:
                for course_id, room_id in sorted(entries):
                    print(f"  {course_id} -> Room {room_id}")
            print()
            if period == 2:
                print(f"{BREAK_LABEL}: {BREAK_TIME}")
                print("  (no lectures)")
                print()

    print("UNSCHEDULED LECTURES")
    if not unscheduled:
        print("  (none)")
    else:
        for course_id in sorted(unscheduled):
            print(f"  {course_id}")
