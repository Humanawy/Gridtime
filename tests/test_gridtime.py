# test/test_gridtime.py
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from datetime import datetime, timedelta, date
import gridtime as gt

from gridtime.utils import is_duplicated_hour, is_duplicated_quarter

def test_valid_quarter():
    dt = datetime(2025, 3, 30, 1, 0)
    q = gt.QuarterHour(dt)
    assert q.start_time == dt
    assert q.end_time == dt + timedelta(minutes=15)

def test_missing_quarter():
    dt = datetime(2025, 3, 30, 2, 0)
    with pytest.raises(ValueError):
        gt.QuarterHour(dt)

def test_duplicated_hour_true():
    dt = datetime(2025, 10, 26, 2, 0)
    assert is_duplicated_hour(dt) is True

def test_duplicated_hour_false_day_after():
    dt = datetime(2025, 10, 27, 2, 0)
    assert is_duplicated_hour(dt) is False

def test_duplicated_quarter_true():
    dt = datetime(2025, 10, 26, 2, 30)
    assert is_duplicated_quarter(dt) is True

def test_duplicated_quarter_false():
    dt = datetime(2025, 10, 26, 3, 0)
    assert is_duplicated_quarter(dt) is False

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

def test_count_hours_in_2025():
    year = gt.Year(2025)
    assert year.count("hours")  == 8760

def test_count_hours_in_2024():
    year = gt.Year(2024)
    assert year.count("hours")  == 8784

def test_hours_in_october():
    month = gt.Month(2025, 10)
    assert month.count("hours") == 745, "Październik 2025 powinien mieć 745 dni. 31 dni * 24 godziny + 1 godzina (cofnięta) = 745 godzin"

def test_hours_in_march():
    month = gt.Month(2025, 3)
    assert month.count("hours") == 743, "Marzec 2025 powinien mieć 743 dni. 31 dni * 24 godziny - 1 godzina (cofnięta) = 743 godzin"


# ────────────────────────────────────────────────────────────────────────────────
# 1.  Ogólna własność: shift(n) potem shift(-n) wraca do punktu wyjścia
# ────────────────────────────────────────────────────────────────────────────────
@pytest.mark.parametrize(
    "obj, n",
    [
        (gt.Day(date(2025, 5, 12)),           37),
        (gt.Month(2023, 12),                 -15),
        (gt.Quarter(2024, 3),                  9),
        (gt.Year(2031),                       -4),
        (gt.Week(2025, 20),                  17),
        (gt.Season(2024, "S"),               -7),
    ],
)
def test_inverse_property(obj, n):
    assert obj.shift(n).shift(-n) == obj


# ────────────────────────────────────────────────────────────────────────────────
# 2.  Dni – prosty test kroku
# ────────────────────────────────────────────────────────────────────────────────
def test_day_step_basic():
    d = gt.Day(date(2025, 7, 23))
    assert d.next()      == gt.Day(date(2025, 7, 24))
    assert d.prev()      == gt.Day(date(2025, 7, 22))
    assert d.shift(10)   == gt.Day(date(2025, 8, 2))
    assert d.shift(-15)  == gt.Day(date(2025, 7, 8))


# ────────────────────────────────────────────────────────────────────────────────
# 3.  Miesiące – przejścia przez granice lat, liczby ujemne
# ────────────────────────────────────────────────────────────────────────────────
def test_month_step_cross_years():
    m = gt.Month(2025, 12)
    assert m.next()        == gt.Month(2026, 1)
    assert m.shift(14)     == gt.Month(2027, 2)
    assert m.shift(-25)    == gt.Month(2023, 11)


# ────────────────────────────────────────────────────────────────────────────────
# 4.  Godziny – noc przesunięcia czasu jesienią (duplikat)
#     2025‑10‑26 03:00 CEST → 02:00 CET  (Europa/Warszawa)
# ────────────────────────────────────────────────────────────────────────────────
def test_hour_step_duplicate_fall_back():
    h1 = gt.Hour(datetime(2025, 10, 26, 3, 0))               # ↑1st
    h2 = h1.next()                                        # ↓2nd
    h3 = h2.next()                                        # 03:00‑04:00

    assert h1.is_duplicated and not h1.is_backward
    assert h2.is_duplicated and     h2.is_backward
    assert not h3.is_duplicated

    # wstecz
    assert h3.prev() == h2
    assert h2.prev() == h1


# ────────────────────────────────────────────────────────────────────────────────
# 5.  Godziny – przeskok wiosenny (brak godziny)
#     2025‑03‑30 02:00‑03:00 nie istnieje
# ────────────────────────────────────────────────────────────────────────────────
def test_hour_step_missing_spring_forward():
    h_before = gt.Hour(datetime(2025, 3, 30, 2, 0))          # 01:00‑02:00
    h_after  = h_before.next()   
    print("h_before:", h_before)
    print("h_after :", h_after)
    print("equal   :", h_after == h_before)
    assert h_after.start_time.hour == 3
    # cofając się z powrotem powinno wrócić jeden krok
    assert h_after.prev() == h_before

# ────────────────────────────────────────────────────────────────────────────────
# 6.  Kwadranse – test duplikatu i brakującego kwadransa
# ────────────────────────────────────────────────────────────────────────────────
def test_quarter_hour_step_duplicate_and_missing():
    # duplikat raz jeszcze: 02:00‑02:15 [↑1st]  w jesieni
    q1 = gt.QuarterHour(datetime(2025, 10, 26, 2, 0))        # ↑1st
    q2 = q1.next()                                        # ↓2nd
    q3 = q2.next()                                        # 02:15‑02:30 ↑1st

    assert q1.is_duplicated and not q1.is_backward
    assert q2.is_duplicated and     q2.is_backward

    # brak kwadransa: skok wiosenny 02:00‑03:00
    q_before = gt.QuarterHour(datetime(2025, 3, 30, 1, 45))  # 01:45‑02:00
    q_after  = q_before.next()                            # 03:00‑03:15
    assert q_after.start_time.hour == 3
    assert q_after.prev() == q_before


# ────────────────────────────────────────────────────────────────────────────────
# 7.  Sezony – naprzemienne S/W
# ────────────────────────────────────────────────────────────────────────────────
def test_season_alternation():
    s22 = gt.Season(2022, "S")
    w22 = s22.next()
    s23 = w22.next()
    assert (w22.type, w22.year) == ("W", 2022)
    assert (s23.type, s23.year) == ("S", 2023)
    assert s23.prev() == w22