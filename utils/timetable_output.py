"""Timetable export and console visualization helpers."""

from __future__ import annotations

import csv
from pathlib import Path

from models.timetable import TimetableState
from parsers.itc_parser import ITCInstance


def export_timetable_csv(
    state: TimetableState,
    instance: ITCInstance,
    output_path: str | Path,
) -> Path:
    """Export the final timetable to CSV."""
    del instance  # kept for API symmetry and future validation hooks
    out_path = Path(output_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["course_id", "room_id", "day", "period"])
        for assignment in state.assignments:
            room = assignment.room_id if assignment.room_id is not None else "UNSCHEDULED"
            day = assignment.day if assignment.day is not None else "UNSCHEDULED"
            period = assignment.period if assignment.period is not None else "UNSCHEDULED"
            writer.writerow([assignment.course_id, room, day, period])

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
        print(f"DAY {day}")
        print("--------------------------------")
        day_map = scheduled.get(day, {})
        for period in range(instance.periods_per_day):
            print(f"Period {period}")
            entries = day_map.get(period, [])
            if not entries:
                print("  (empty)")
            else:
                for course_id, room_id in sorted(entries):
                    print(f"  {course_id} -> Room {room_id}")
            print()

    print("UNSCHEDULED LECTURES")
    if not unscheduled:
        print("  (none)")
    else:
        for course_id in sorted(unscheduled):
            print(f"  {course_id}")
