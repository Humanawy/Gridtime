# tests/test_parsing.py
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from datetime import datetime, date
import gridtime as gt
from gridtime.parsing import _parse_hour_repr


# ────────────────────────────────────────────────────────────────────────────────
# parse_date – parsowanie ciągów tekstowych dat
# ────────────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("s, expected", [
    ("01.01.2027", date(2027, 1, 1)),
    ("01/06/2027", date(2027, 6, 1)),
    ("01-10-2027", date(2027, 10, 1)),
    ("2027-03-15", date(2027, 3, 15)),
])
def test_parse_date_formats(s, expected):
    assert gt.parse_date(s) == expected

def test_parse_date_date_passthrough():
    d = date(2027, 5, 20)
    assert gt.parse_date(d) is d

def test_parse_date_datetime_strips_time():
    dt = datetime(2027, 1, 1, 20, 3)
    result = gt.parse_date(dt)
    assert result == date(2027, 1, 1)
    assert type(result) is date

def test_parse_date_invalid():
    with pytest.raises(ValueError):
        gt.parse_date("not-a-date")


# ────────────────────────────────────────────────────────────────────────────────
# Day – tworzenie z ciągu tekstowego
# ────────────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("s", [
    "2026-01-01",
    "01.01.2026",
    "01/01/2026",
    "01-01-2026",
])
def test_day_from_string(s):
    day = gt.Day(s)
    assert day.date == date(2026, 1, 1)

def test_day_from_date_unchanged():
    d = date(2026, 6, 15)
    assert gt.Day(d).date == d


# ────────────────────────────────────────────────────────────────────────────────
# _parse_hour_repr – wewnętrzna funkcja parsowania repr godziny
# ────────────────────────────────────────────────────────────────────────────────

def test_parse_hour_repr_normal():
    end_time, is_backward = _parse_hour_repr("2026-01-01 21:00-22:00")
    assert end_time == datetime(2026, 1, 1, 22, 0)
    assert is_backward is False

def test_parse_hour_repr_midnight_crossing():
    end_time, is_backward = _parse_hour_repr("2026-01-01 23:00-00:00")
    assert end_time == datetime(2026, 1, 2, 0, 0)
    assert is_backward is False

def test_parse_hour_repr_dst_roundtrip():
    h1 = gt.Hour(datetime(2025, 10, 26, 3, 0), is_backward=False)
    h2 = gt.Hour(datetime(2025, 10, 26, 3, 0), is_backward=True)
    end1, bw1 = _parse_hour_repr(repr(h1))
    end2, bw2 = _parse_hour_repr(repr(h2))
    assert end1 == datetime(2025, 10, 26, 3, 0) and bw1 is False
    assert end2 == datetime(2025, 10, 26, 3, 0) and bw2 is True


# ────────────────────────────────────────────────────────────────────────────────
# Hour – tworzenie z ciągu tekstowego (repr)
# ────────────────────────────────────────────────────────────────────────────────

def test_hour_from_repr_string():
    h = gt.Hour("2026-01-01 21:00-22:00")
    assert h.start_time == datetime(2026, 1, 1, 21, 0)
    assert h.end_time   == datetime(2026, 1, 1, 22, 0)
    assert h.is_backward is False

def test_hour_from_repr_midnight():
    h = gt.Hour("2026-01-01 23:00-00:00")
    assert h.start_time == datetime(2026, 1, 1, 23, 0)
    assert h.end_time   == datetime(2026, 1, 2,  0, 0)

def test_hour_from_repr_dst_roundtrip():
    h1 = gt.Hour(datetime(2025, 10, 26, 3, 0), is_backward=False)
    h2 = gt.Hour(datetime(2025, 10, 26, 3, 0), is_backward=True)
    assert gt.Hour(repr(h1)).is_backward is False
    assert gt.Hour(repr(h2)).is_backward is True

def test_hour_from_repr_missing_spring_raises():
    with pytest.raises(ValueError):
        gt.Hour("2025-03-30 02:00-03:00")


# ────────────────────────────────────────────────────────────────────────────────
# parse_hour – tryb repr string (jeden argument)
# ────────────────────────────────────────────────────────────────────────────────

def test_parse_hour_repr_mode():
    h = gt.parse_hour("2026-01-01 21:00-22:00")
    assert h.start_time == datetime(2026, 1, 1, 21, 0)
    assert h.end_time   == datetime(2026, 1, 1, 22, 0)

def test_parse_hour_repr_mode_dst():
    h_orig = gt.Hour(datetime(2025, 10, 26, 3, 0), is_backward=True)
    h = gt.parse_hour(repr(h_orig))
    assert h.is_backward is True

def test_parse_hour_repr_mode_rejects_date_arg():
    with pytest.raises(ValueError):
        gt.parse_hour("2026-01-01 21:00-22:00", "2026-01-01")


# ────────────────────────────────────────────────────────────────────────────────
# parse_hour – tryb numer + data
# ────────────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("hour, conv, interp, exp_start, exp_end", [
    (0,  "0-23", "as_start", datetime(2027,6,15, 0,0), datetime(2027,6,15, 1,0)),
    (1,  "0-23", "as_start", datetime(2027,6,15, 1,0), datetime(2027,6,15, 2,0)),
    (23, "0-23", "as_start", datetime(2027,6,15,23,0), datetime(2027,6,16, 0,0)),
    (1,  "0-23", "as_end",   datetime(2027,6,15, 0,0), datetime(2027,6,15, 1,0)),
    (1,  "1-24", "as_end",   datetime(2027,6,15, 0,0), datetime(2027,6,15, 1,0)),
    (24, "1-24", "as_end",   datetime(2027,6,15,23,0), datetime(2027,6,16, 0,0)),
])
def test_parse_hour_number_mode(hour, conv, interp, exp_start, exp_end):
    h = gt.parse_hour(hour, date(2027, 6, 15), convention=conv, interpret=interp)
    assert h.start_time == exp_start
    assert h.end_time   == exp_end

@pytest.mark.parametrize("hour_str", ["1", "01", "01:00", "1:00"])
def test_parse_hour_string_formats(hour_str):
    h = gt.parse_hour(hour_str, date(2027, 6, 15))
    assert h.start_time == datetime(2027, 6, 15, 1, 0)

def test_parse_hour_requires_date_for_number():
    with pytest.raises(ValueError):
        gt.parse_hour(5)

@pytest.mark.parametrize("hour, conv, interp", [
    (0,  "0-23", "as_end"),
    (24, "0-23", "as_start"),
    (0,  "1-24", "as_end"),
    (24, "1-24", "as_start"),
])
def test_parse_hour_invalid_combinations(hour, conv, interp):
    with pytest.raises(ValueError):
        gt.parse_hour(hour, date(2027, 6, 15), convention=conv, interpret=interp)

def test_parse_hour_dst_backward():
    h = gt.parse_hour(2, date(2025, 10, 26), backward=True)
    assert h.is_duplicated is True
    assert h.is_backward   is True

def test_parse_hour_dst_missing_raises():
    with pytest.raises(ValueError):
        gt.parse_hour(2, date(2025, 3, 30))
