# test/test_gridtime.py
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from datetime import datetime, timedelta, date
import gridtime as gt

from gridtime.utils import is_duplicated_hour, is_duplicated_quarter, _parse_hour_repr

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


# ────────────────────────────────────────────────────────────────────────────────
# create_hours – tryb varargs (repr stringi)
# ────────────────────────────────────────────────────────────────────────────────

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