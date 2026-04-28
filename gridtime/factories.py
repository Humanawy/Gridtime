# gridtime/factories.py
from datetime import datetime, date, time, timedelta
from calendar import monthrange
from typing import Union, Optional, List, Literal
from gridtime.periods import (
    QuarterHour, Hour, Day, Month, Quarter, Year, Week, Season, MonthDecade,
)
from gridtime.parsing import parse_date, _is_hour_repr
from gridtime._dst import is_missing_hour, is_duplicated_hour, is_missing_quarter, is_duplicated_quarter


def create_days(
    year_or_date: Union[str, date, int],
    month: Optional[int] = None,
    day_range=None,
) -> list["Day"]:
    if isinstance(year_or_date, (str, date)):
        d = parse_date(year_or_date)
        year, month = d.year, d.month
    else:
        if month is None:
            raise ValueError("Parametr 'month' jest wymagany gdy 'year_or_date' jest liczbą całkowitą.")
        year = year_or_date

    num_days = monthrange(year, month)[1]
    if day_range is None:
        day_range = range(1, num_days + 1)
    return [Day(date(year, month, d)) for d in day_range]

def create_months(year: int, months: list[int]) -> list[Month]:
    return [Month(year, m) for m in months]

def create_quarters(year: int, quarters=range(1, 5)) -> list[Quarter]:
    return [Quarter(year, q) for q in quarters]

def create_season_quarters(year: int, type_: str) -> list[Quarter]:
    if type_ not in ("W", "S"):
        raise ValueError("Sezon musi być 'W' (zimowy) lub 'S' (letni)")

    if type_ == "W":
        # Zimowy sezon np. 2024 = Q4/2024 + Q1/2025
        return [Quarter(year, 4), Quarter(year + 1, 1)]
    else:  # type_ == "S"
        # Letni sezon np. 2024 = Q2 + Q3 roku 2024
        return [Quarter(year, 2), Quarter(year, 3)]

def create_week_days(iso_year: int, iso_week: int) -> list[Day]:
    return [Day(date.fromisocalendar(iso_year, iso_week, i)) for i in range(1, 8)]

def create_hours(date_or_repr: Union[str, date], *more_reprs: str, hour_range=range(1, 25)) -> list[Hour]:
    # Tryb repr: jeden lub więcej ciągów w formacie "YYYY-MM-DD HH:MM-HH:MM"
    if more_reprs or (isinstance(date_or_repr, str) and _is_hour_repr(date_or_repr)):
        return [Hour(r) for r in (date_or_repr, *more_reprs)]

    # Tryb klasyczny: data dnia → wszystkie godziny (z obsługą DST)
    date_ = parse_date(date_or_repr)
    hours: list[Hour] = []
    for hour in hour_range:
        dt_end = datetime.combine(date_, time(0)) + timedelta(hours=hour)
        start_time = dt_end - timedelta(hours=1)

        if is_missing_hour(start_time):
            continue

        if is_duplicated_hour(start_time):
            hours.append(Hour(dt_end, is_backward=False))
            hours.append(Hour(dt_end, is_backward=True))
        else:
            hours.append(Hour(dt_end))

    return hours

def create_quarter_months(year: int, quarter: int) -> list[Month]:
    start_month = 1 + (quarter - 1) * 3
    return create_months(year, list(range(start_month, start_month + 3)))

def create_quarter_hours(
    start_time: datetime,
    *,
    phase: Literal["first", "second", "both"] = "both"
) -> list[QuarterHour]:
    """
    Zwraca kwadranse w obrębie godziny zaczynającej się o `start_time`.
    Parametr `phase` steruje kolejnością/zakresem dla godzin duplikowanych:
      - "first"  → zwracaj tylko ↑1st
      - "second" → zwracaj tylko ↓2nd
      - "both"   → zwracaj ↑1st, potem ↓2nd dla każdego duplikowanego kwadransa
                   (zachowanie wsteczne dla godzin nieduplikowanych)
    """
    quarters: list[QuarterHour] = []

    for i in range(4):
        dt = start_time + timedelta(minutes=15 * i)

        if is_missing_quarter(dt):
            continue

        if is_duplicated_quarter(dt):
            if phase == "first":
                quarters.append(QuarterHour(dt, is_backward=False))
            elif phase == "second":
                quarters.append(QuarterHour(dt, is_backward=True))
            else:  # phase == "both"
                quarters.append(QuarterHour(dt, is_backward=False))
                quarters.append(QuarterHour(dt, is_backward=True))
        else:
            quarters.append(QuarterHour(dt))

    return quarters

def create_decade_days(year: int, month: int, index: int) -> list["Day"]:
    """Zwraca listę obiektów Day w danej dekadzie (1-3) danego miesiąca."""
    if index not in (1, 2, 3):
        raise ValueError("index dekady musi być 1, 2 lub 3")

    start_day = 1 + (index - 1) * 10
    if index < 3:
        end_day = start_day + 9
    else:
        end_day = monthrange(year, month)[1]            # ostatni dzień miesiąca

    return [Day(date(year, month, d)) for d in range(start_day, end_day + 1)]
