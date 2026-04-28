# tests/test_periods.py
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from datetime import datetime, timedelta, date
import gridtime as gt
from gridtime._dst import is_duplicated_hour, is_duplicated_quarter

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


def test_day_step_basic():
    d = gt.Day(date(2025, 7, 23))
    assert d.next()      == gt.Day(date(2025, 7, 24))
    assert d.prev()      == gt.Day(date(2025, 7, 22))
    assert d.shift(10)   == gt.Day(date(2025, 8, 2))
    assert d.shift(-15)  == gt.Day(date(2025, 7, 8))


def test_month_step_cross_years():
    m = gt.Month(2025, 12)
    assert m.next()        == gt.Month(2026, 1)
    assert m.shift(14)     == gt.Month(2027, 2)
    assert m.shift(-25)    == gt.Month(2023, 11)


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


def test_hour_step_missing_spring_forward():
    h_before = gt.Hour(datetime(2025, 3, 30, 2, 0))          # 01:00‑02:00
    h_after  = h_before.next()
    print("h_before:", h_before)
    print("h_after :", h_after)
    print("equal   :", h_after == h_before)
    assert h_after.start_time.hour == 3
    # cofając się z powrotem powinno wrócić jeden krok
    assert h_after.prev() == h_before

def test_quarter_hour_step_duplicate_and_missing():
    # duplikat raz jeszcze: 02:00‑02:15 [↑1st]  w jesieni
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


def test_season_alternation():
    s22 = gt.Season(2022, "S")
    w22 = s22.next()
    s23 = w22.next()
    assert (w22.type, w22.year) == ("W", 2022)
    assert (s23.type, s23.year) == ("S", 2023)
    assert s23.prev() == w22

def test_quarter_order_in_fall_back_day_walk():
    """
    W dniu cofnięcia czasu (2025-10-26, Europa/Warszawa) iterator walk("quarters15")
    powinien zwrócić kwadranse między 02:00 a 03:00 w kolejności:
      1) najpierw wszystkie '↑1st' (is_duplicated=True, is_backward=False)
         dla minut: 0, 15, 30, 45
      2) następnie wszystkie '↓2nd' (is_duplicated=True, is_backward=True)
         dla minut: 0, 15, 30, 45

    Dodatkowe asercje:
      - przed sekwencją jest 01:45–02:00
      - po sekwencji jest 03:00–03:15
      - dokładnie 8 kwadransów w zakresie 02:00–03:00
    """
    day = gt.Day(date(2025, 10, 26))
    quarters = list(day.walk("quarters15"))

    idx_in_2h = [i for i, q in enumerate(quarters) if q.start_time.hour == 2]
    assert len(idx_in_2h) == 8, f"Spodziewano 8 kwadransów 02:00–03:00, jest {len(idx_in_2h)}"

    seq_2h = [quarters[i] for i in idx_in_2h]
    expected_minutes = [0, 15, 30, 45]

    first_half  = seq_2h[:4]
    second_half = seq_2h[4:]

    # 1) Pierwsza połowa: ↑1st
    assert all(q.is_duplicated for q in first_half), "Pierwsza połowa musi być duplikowana (↑1st)"
    assert all(not q.is_backward for q in first_half), "Pierwsza połowa musi być ↑1st (is_backward=False)"
    assert [q.start_time.minute for q in first_half] == expected_minutes

    # 2) Druga połowa: ↓2nd
    assert all(q.is_duplicated for q in second_half), "Druga połowa musi być duplikowana (↓2nd)"
    assert all(q.is_backward for q in second_half), "Druga połowa musi być ↓2nd (is_backward=True)"
    assert [q.start_time.minute for q in second_half] == expected_minutes

    # Kontekst: element przed i po
    first_idx = idx_in_2h[0]
    last_idx  = idx_in_2h[-1]

    assert first_idx > 0
    prev_q = quarters[first_idx - 1]
    assert prev_q.start_time.hour == 1 and prev_q.start_time.minute == 45
    assert prev_q.end_time.hour   == 2 and prev_q.end_time.minute   == 0

    assert last_idx + 1 < len(quarters)
    next_q = quarters[last_idx + 1]
    assert next_q.start_time.hour == 3 and next_q.start_time.minute == 0
    assert next_q.end_time.hour   == 3 and next_q.end_time.minute   == 15
