# tests/test_factories.py
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from datetime import datetime, date
import gridtime as gt

def test_days_in_february_leap_year():
    days = gt.create_days(2024, 2)
    assert len(days) == 29, "Luty 2024 powinien mieć 29 dni"

def test_days_in_february_non_leap_year():
    days = gt.create_days(2023, 2)
    assert len(days) == 28, "Luty 2023 powinien mieć 28 dni"

def test_days_in_january():
    days = gt.create_days(2025, 1)
    assert len(days) == 31, "Styczeń 2025 powinien mieć 31 dni"

def test_days_in_april():
    days = gt.create_days(2025, 4)
    assert len(days) == 30, "Kwiecień 2025 powinien mieć 30 dni"

def test_days_in_october():
    days = gt.create_days(2025, 10)
    assert len(days) == 31, "Październik 2025 powinien mieć 31 dni"

def test_create_hours_varargs_single():
    hours = gt.create_hours("2026-01-01 21:00-22:00")
    assert len(hours) == 1
    assert hours[0].start_time == datetime(2026, 1, 1, 21, 0)

def test_create_hours_varargs_multiple():
    hours = gt.create_hours(
        "2026-01-01 21:00-22:00",
        "2026-01-01 22:00-23:00",
        "2026-01-01 23:00-00:00",
    )
    assert len(hours) == 3
    assert hours[0].start_time == datetime(2026, 1, 1, 21, 0)
    assert hours[2].end_time   == datetime(2026, 1, 2,  0, 0)

def test_create_hours_classic_date_object():
    hours = gt.create_hours(date(2027, 1, 1))
    assert len(hours) == 24

def test_create_hours_classic_date_string():
    hours = gt.create_hours("2027-01-01")
    assert len(hours) == 24

def test_create_hours_classic_dst_spring():
    hours = gt.create_hours(date(2025, 3, 30))
    assert len(hours) == 23

def test_create_hours_classic_dst_fall():
    hours = gt.create_hours(date(2025, 10, 26))
    assert len(hours) == 25
