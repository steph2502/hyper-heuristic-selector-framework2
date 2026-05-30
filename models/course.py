"""Course entity for curriculum-based course timetabling."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Course:
    """A course requiring weekly lecture sessions to be scheduled."""

    course_id: str
    teacher_id: str
    lectures_per_week: int
    min_working_days: int
    students: int
