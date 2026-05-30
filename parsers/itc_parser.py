"""ITC 2007 Track 3 (Curriculum-Based Course Timetabling) TXT instance parser.

File format has two distinct regions that must never be confused:

1. HEADER BLOCK  – key/value metadata lines that appear BEFORE any section marker.
   These use lowercase keys with a colon and a single integer value:
       Name: Fis0506-1
       Courses: 30
       Rooms: 6
       Days: 5
       Periods_per_day: 6
       Curricula: 14
       Constraints: 53

2. SECTION BLOCKS – upper-case markers followed by data lines, e.g.:
       COURSES:
       c0001 t000 6 4 130
       ...
       ROOMS:
       B  200
       ...

The original parser tried to infer section boundaries from a running line counter,
which broke as soon as it hit a header line such as "Rooms: 6" while still inside
the COURSES section.

The new design uses an explicit ``current_section`` state variable that switches on
every upper-case section marker, and parses each data line only according to the
active section.  Header counts are read once in a dedicated first pass and used
only for validation – they do NOT drive loop bounds.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator

from models.course import Course
from models.lecturer import Lecturer
from models.room import Room


# ---------------------------------------------------------------------------
# Domain dataclasses (unchanged from original)
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class Curriculum:
    """A curriculum grouping courses that must not overlap in time."""
    curriculum_id: str
    course_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class UnavailabilityConstraint:
    """A single forbidden (day, period) slot for one course.

    Note: the original design bundled all forbidden slots for one course into a
    single object.  The ITC 2007 file format lists ONE (course, day, period)
    triple per line, so we keep a flat list here and group by course_id after
    parsing.  The public API still exposes one UnavailabilityConstraint per
    course (with multiple forbidden slots) for backwards compatibility.
    """
    course_id: str
    forbidden_slots: tuple[tuple[int, int], ...]


@dataclass(frozen=True, slots=True)
class ITCInstance:
    """Fully parsed ITC 2007 instance with derived timetable dimensions."""
    name: str
    courses: tuple[Course, ...]
    rooms: tuple[Room, ...]
    curricula: tuple[Curriculum, ...]
    unavailability: tuple[UnavailabilityConstraint, ...]
    nr_days: int
    periods_per_day: int

    @property
    def lecturers(self) -> tuple[Lecturer, ...]:
        """Unique lecturers referenced by courses (stable order of first appearance)."""
        seen: dict[str, None] = {}
        for c in self.courses:
            seen.setdefault(c.teacher_id, None)
        return tuple(Lecturer(lecturer_id=lid) for lid in seen)

    def as_dict(self) -> dict[str, Any]:
        """Return a plain dictionary view (useful for logging or JSON serialisation)."""
        return {
            "name": self.name,
            "courses": [c.__dict__ for c in self.courses],
            "rooms": [r.__dict__ for r in self.rooms],
            "curricula": [
                {"curriculum_id": cu.curriculum_id, "course_ids": list(cu.course_ids)}
                for cu in self.curricula
            ],
            "constraints": [
                {
                    "course_id": u.course_id,
                    "forbidden_slots": [list(p) for p in u.forbidden_slots],
                }
                for u in self.unavailability
            ],
            "nr_days": self.nr_days,
            "periods_per_day": self.periods_per_day,
            "lecturers": [lec.lecturer_id for lec in self.lecturers],
        }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

# Matches header lines:  "Name: Fis0506-1"  or  "Periods_per_day: 6"
_HEADER_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_ ]*)\s*:\s*(.+)$")

# Upper-case section markers that appear on their own line, e.g. "COURSES:"
_SECTION_MARKERS: dict[str, str] = {
    "COURSES":                    "COURSES",
    "ROOMS":                      "ROOMS",
    "CURRICULA":                  "CURRICULA",
    "UNAVAILABILITY_CONSTRAINTS": "UNAVAILABILITY",
    "CONSTRAINTS":                "UNAVAILABILITY",   # alias used by some instances
}


def _non_empty_lines(text: str) -> Iterator[str]:
    """Yield stripped, non-blank, non-comment lines."""
    for raw in text.splitlines():
        line = raw.strip()
        if line and not line.startswith("#"):
            yield line


def _is_section_marker(line: str) -> str | None:
    """Return the canonical section name if *line* is a section marker, else None.

    A section marker is an upper-case token optionally followed by a colon,
    standing alone on its line.  Examples that all match COURSES:
        ``COURSES:``   ``COURSES``
    """
    token = line.rstrip(":").strip().upper().replace(" ", "_")
    return _SECTION_MARKERS.get(token)


def _parse_header_block(lines: list[str]) -> dict[str, str]:
    """Extract key→value pairs from the header block (lines before first section marker).

    Stops at the first section marker line and returns the headers seen so far.
    Does NOT consume section markers.
    """
    headers: dict[str, str] = {}
    for line in lines:
        if _is_section_marker(line) is not None:
            break
        m = _HEADER_RE.match(line)
        if m:
            key = m.group(1).strip().lower().replace(" ", "_")
            headers[key] = m.group(2).strip()
    return headers


def _parse_course(parts: list[str]) -> Course:
    if len(parts) < 5:
        raise ValueError(
            f"Course line needs ≥5 fields "
            f"(course_id teacher_id lectures_per_week min_working_days students), "
            f"got {parts!r}"
        )
    return Course(
        course_id=parts[0],
        teacher_id=parts[1],
        lectures_per_week=int(parts[2]),
        min_working_days=int(parts[3]),
        students=int(parts[4]),
    )


def _parse_room(parts: list[str]) -> Room:
    if len(parts) < 2:
        raise ValueError(
            f"Room line needs ≥2 fields (room_id capacity), got {parts!r}"
        )
    return Room(room_id=parts[0], capacity=int(parts[1]))


def _parse_curriculum(parts: list[str]) -> Curriculum:
    if len(parts) < 2:
        raise ValueError(
            f"Curriculum line needs ≥2 fields (curriculum_id n_courses …), got {parts!r}"
        )
    cid = parts[0]
    k = int(parts[1])
    if len(parts) != 2 + k:
        raise ValueError(
            f"Curriculum {cid}: header says {k} courses but found "
            f"{len(parts) - 2} course ids in {parts!r}"
        )
    return Curriculum(curriculum_id=cid, course_ids=tuple(parts[2:]))


def _parse_unavailability_line(parts: list[str]) -> tuple[str, int, int]:
    """Parse one unavailability line:  ``course_id  day  period``"""
    if len(parts) < 3:
        raise ValueError(
            f"Unavailability line needs 3 fields (course_id day period), got {parts!r}"
        )
    return parts[0], int(parts[1]), int(parts[2])


def _group_unavailability(
    raw: list[tuple[str, int, int]]
) -> tuple[UnavailabilityConstraint, ...]:
    """Group flat (course_id, day, period) triples into per-course objects."""
    grouped: dict[str, list[tuple[int, int]]] = {}
    for course_id, day, period in raw:
        grouped.setdefault(course_id, []).append((day, period))
    return tuple(
        UnavailabilityConstraint(
            course_id=cid,
            forbidden_slots=tuple(slots),
        )
        for cid, slots in grouped.items()
    )


# ---------------------------------------------------------------------------
# Public parser
# ---------------------------------------------------------------------------

def parse_itc_file(path: str | Path) -> ITCInstance:
    """Parse an ITC 2007 curriculum-based course timetabling instance file.

    Design
    ------
    The function makes **two passes** over the line list:

    Pass 1 – header extraction
        Reads key/value metadata lines that appear before the first section
        marker.  These lines have the form ``Key: value`` and record counts
        (Courses, Rooms, …) plus optional dimension overrides (Days,
        Periods_per_day).  The counts are used only for post-parse validation;
        they do NOT drive loop bounds.

    Pass 2 – section parsing
        Iterates every line and maintains ``current_section``.  Each line is
        dispatched to the appropriate parser only when the matching section is
        active.  Section markers and ``END.`` are never treated as data.

    Args:
        path: Path to the ``.txt`` instance file.

    Returns:
        A fully-populated :class:`ITCInstance`.

    Raises:
        FileNotFoundError: If *path* does not exist.
        ValueError: On malformed content or count mismatches.
    """
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    lines = list(_non_empty_lines(text))

    if not lines:
        raise ValueError(f"Empty ITC file: {path}")

    # ── Pass 1: read header metadata ──────────────────────────────────────────
    headers = _parse_header_block(lines)

    name = headers.get("name", "")
    if not name:
        raise ValueError("Missing required 'Name:' header")

    # Optional explicit dimensions (may be absent in some instance files)
    explicit_days:    int | None = int(headers["days"])            if "days"            in headers else None
    explicit_periods: int | None = int(headers["periods_per_day"]) if "periods_per_day" in headers else None

    # Header counts used for validation only
    expected_counts: dict[str, int] = {}
    for key in ("courses", "rooms", "curricula", "constraints"):
        if key in headers:
            try:
                expected_counts[key] = int(headers[key])
            except ValueError:
                pass   # non-integer value – skip validation for that field

    # ── Pass 2: state-machine section parser ─────────────────────────────────
    current_section: str | None = None

    courses:      list[Course]                  = []
    rooms:        list[Room]                    = []
    curricula:    list[Curriculum]              = []
    unav_raw:     list[tuple[str, int, int]]    = []   # (course_id, day, period)

    for line in lines:
        # ── Check for section marker first (highest priority) ──────────────
        section = _is_section_marker(line)
        if section is not None:
            current_section = section
            continue

        # ── Stop at END. ───────────────────────────────────────────────────
        if line.upper().startswith("END"):
            break

        # ── Skip header lines that appear before any section marker ────────
        #    (they were already consumed in pass 1)
        if current_section is None:
            continue

        # ── Dispatch to active section ─────────────────────────────────────
        parts = line.split()

        if current_section == "COURSES":
            courses.append(_parse_course(parts))

        elif current_section == "ROOMS":
            rooms.append(_parse_room(parts))

        elif current_section == "CURRICULA":
            curricula.append(_parse_curriculum(parts))

        elif current_section == "UNAVAILABILITY":
            unav_raw.append(_parse_unavailability_line(parts))

    # ── Post-parse validation against header counts ───────────────────────────
    actual = {
        "courses":     len(courses),
        "rooms":       len(rooms),
        "curricula":   len(curricula),
        "constraints": len(unav_raw),
    }
    mismatches = [
        f"{k}: expected {expected_counts[k]}, parsed {actual[k]}"
        for k in expected_counts
        if expected_counts[k] != actual[k]
    ]
    if mismatches:
        raise ValueError(
            "Parsed counts differ from header metadata:\n  "
            + "\n  ".join(mismatches)
        )

    # ── Derive timetable dimensions ───────────────────────────────────────────
    unavailability = _group_unavailability(unav_raw)
    nr_days, periods_per_day = _infer_dimensions(
        unavailability, explicit_days, explicit_periods
    )

    return ITCInstance(
        name=name,
        courses=tuple(courses),
        rooms=tuple(rooms),
        curricula=tuple(curricula),
        unavailability=unavailability,
        nr_days=nr_days,
        periods_per_day=periods_per_day,
    )


def _infer_dimensions(
    unavailability: tuple[UnavailabilityConstraint, ...],
    explicit_days: int | None,
    explicit_periods: int | None,
) -> tuple[int, int]:
    """Derive ``nr_days`` and ``periods_per_day`` from data when not explicit."""
    max_day = -1
    max_period = -1
    for u in unavailability:
        for d, period in u.forbidden_slots:
            max_day    = max(max_day, d)
            max_period = max(max_period, period)

    inferred_days    = max_day    + 1 if max_day    >= 0 else None
    inferred_periods = max_period + 1 if max_period >= 0 else None

    days    = explicit_days    if explicit_days    is not None else inferred_days
    periods = explicit_periods if explicit_periods is not None else inferred_periods

    if days is None or periods is None:
        raise ValueError(
            "Cannot infer timetable dimensions. "
            "Add 'Days:' and 'Periods_per_day:' header lines, "
            "or include at least one unavailability constraint."
        )
    if days <= 0 or periods <= 0:
        raise ValueError(f"Invalid dimensions: days={days}, periods_per_day={periods}")
    return days, periods