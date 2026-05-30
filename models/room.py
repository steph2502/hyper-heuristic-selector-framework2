"""Room entity for timetabling."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Room:
    """A teaching room with fixed capacity."""

    room_id: str
    capacity: int
