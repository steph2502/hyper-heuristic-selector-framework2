"""Domain models for curriculum-based course timetabling."""

from models.course import Course
from models.lecturer import Lecturer
from models.room import Room
from models.timetable import LectureAssignment, TimetableState

__all__ = [
    "Course",
    "Lecturer",
    "Room",
    "LectureAssignment",
    "TimetableState",
]
