"""Lecturer (teacher) entity."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Lecturer:
    """A lecturer identified by a stable identifier."""

    lecturer_id: str
