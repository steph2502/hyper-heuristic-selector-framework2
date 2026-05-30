"""Timetable state: assignments and cached evaluation fields."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

from models.course import Course


@dataclass(frozen=True, slots=True)
class LectureAssignment:
    """One scheduled lecture of a course (one weekly occurrence)."""

    course_id: str
    room_id: str | None
    day: int | None
    period: int | None


@dataclass(slots=True)
class TimetableState:
    """Mutable search state for a weekly timetable.

    Assignments are stored as one entry per required lecture for each course.
    ``None`` room/day/period denotes an unscheduled lecture (hard violation).
    """

    assignments: list[LectureAssignment] = field(default_factory=list)
    fitness: float | None = None
    hard_violations: int | None = None
    soft_penalty: float | None = None

    @classmethod
    def from_course_list(cls, courses: Iterable[Course]) -> TimetableState:
        """Create an empty state with the correct number of lecture slots."""
        slots: list[LectureAssignment] = []
        for c in courses:
            for _ in range(c.lectures_per_week):
                slots.append(LectureAssignment(c.course_id, None, None, None))
        return cls(assignments=slots)

    def copy(self) -> TimetableState:
        """Return a shallow copy suitable for local search moves."""
        return TimetableState(
            assignments=list(self.assignments),
            fitness=self.fitness,
            hard_violations=self.hard_violations,
            soft_penalty=self.soft_penalty,
        )
