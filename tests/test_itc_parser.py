"""Tests for ITC 2007 TXT parsing."""

from __future__ import annotations

from pathlib import Path

import pytest

from parsers.itc_parser import parse_itc_file

FIXTURES = Path(__file__).resolve().parent / "fixtures"
DATA_ITC = Path(__file__).resolve().parents[1] / "data" / "itc"


def test_parse_minimal_instance() -> None:
    inst = parse_itc_file(FIXTURES / "minimal_itc.txt")
    assert inst.name == "tiny_ok"
    assert len(inst.courses) == 1
    assert inst.courses[0].course_id == "c1"
    assert inst.courses[0].lectures_per_week == 1
    assert inst.nr_days == 3
    assert inst.periods_per_day == 4
    assert len(inst.rooms) == 1
    assert len(inst.curricula) == 1
    assert inst.curricula[0].course_ids == ("c1",)
    assert inst.unavailability == ()


def test_infer_dimensions_from_unavailability_only(tmp_path: Path) -> None:
    txt = tmp_path / "infer.txt"
    txt.write_text(
        "\n".join(
            [
                "Name: infer",
                "Courses: 1",
                "Rooms: 1",
                "Curricula: 1",
                "Constraints: 1",
                "",
                "COURSES:",
                "c1 t1 1 1 10",
                "",
                "ROOMS:",
                "r1 50",
                "",
                "CURRICULA:",
                "cu 1 c1",
                "",
                "UNAVAILABILITY CONSTRAINTS:",
                "c1 4 7",
                "",
            ]
        ),
        encoding="utf-8",
    )
    inst = parse_itc_file(txt)
    assert inst.nr_days == 5
    assert inst.periods_per_day == 8


@pytest.mark.skipif(not (DATA_ITC / "Fis0506-1.txt").is_file(), reason="Fis0506-1.txt not present under data/itc")
def test_parse_fis0506_1_real_file() -> None:
    inst = parse_itc_file(DATA_ITC / "Fis0506-1.txt")
    assert inst.name
    assert len(inst.courses) > 0
    assert len(inst.rooms) > 0
    assert inst.nr_days >= 1
    assert inst.periods_per_day >= 1
    assert len(inst.curricula) > 0
