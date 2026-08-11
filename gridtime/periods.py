# gridtime/periods.py
from datetime import datetime, timedelta, date, time
from calendar import monthrange
from typing import Union, Optional, Literal
from gridtime._registry import register_unit
from gridtime._dst import (
    is_missing_quarter, is_duplicated_quarter,
    is_missing_hour, is_duplicated_hour,
)
from gridtime._base import GridtimeLeaf, GridtimeStructure
from gridtime.parsing import parse_date, _parse_hour_repr, _is_hour_repr
from gridtime._steps import (
    quarter_hour_step, hour_step, day_step, month_step,
    quarter_step, year_step, week_step, season_step, month_decade_step,
)

# Każda klasa poniżej jest poprzedzona funkcją `create_*`, która buduje jej
# dzieci. Klasa woła tę funkcję bezpośrednio z `_create_children`, a funkcja
# jest też publicznym punktem wejścia (re-eksportowanym w `gridtime/__init__.py`)
# dla kogoś, kto chce dostać samą listę bez tworzenia obiektu nadrzędnego.


@register_unit("quarters15", step=quarter_hour_step)
class QuarterHour(GridtimeLeaf):
    def __init__(self, start_time: datetime, *, is_backward: bool = False):
        super().__init__()
        self.start_time = start_time
        self.end_time = start_time + timedelta(minutes=15)

        if is_missing_quarter(self.start_time):
            raise ValueError(
                f"Nie można utworzyć kwadransu dla {self.start_time.strftime('%Y-%m-%d %H:%M')} - {self.end_time.strftime('%H:%M')}")

        self.is_duplicated: bool = is_duplicated_quarter(self.start_time)
        self.is_backward:   bool = is_backward

        if self.is_backward and not self.is_duplicated:
            raise ValueError(
                f"Kwadrans {self.start_time:%Y-%m-%d %H:%M} nie jest duplikowany, "
                f"nie można utworzyć 'cofniętej' instancji (is_backward=True)."
            )

    def __repr__(self):
        base = f"{self.start_time:%Y-%m-%d %H:%M}-{self.end_time:%H:%M}"
        if self.is_duplicated:
            tag = "↓2nd" if self.is_backward else "↑1st"
            return f"{base} [{tag}]"
        return base


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


@register_unit("hours", children_key="quarters15", step=hour_step)
class Hour(GridtimeStructure):
    def __init__(self, reference_time: Union[str, datetime], *, is_backward: bool = False):
        super().__init__()
        if isinstance(reference_time, str):
            reference_time, is_backward = _parse_hour_repr(reference_time)
        self.end_time = reference_time
        self.start_time = self.end_time - timedelta(hours=1)

        if is_missing_hour(self.start_time):
            raise ValueError(f"Nie można utworzyć godziny dla {reference_time.strftime('%Y-%m-%d %H:%M')}")

        self.is_duplicated: bool = is_duplicated_hour(self.start_time)
        self.is_backward:   bool = is_backward

        if self.is_backward and not self.is_duplicated:
            raise ValueError(
                f"Godzina {self.start_time:%Y-%m-%d %H:%M}-{self.end_time:%H:%M} "
                f"nie jest duplikowana, nie można utworzyć 'cofniętej' instancji "
                f"(is_backward=True)."
            )

    def _create_children(self) -> list[GridtimeLeaf]:
        # Jeśli godzina jest duplikowana, to:
        #   - dla ↑1st zwróć tylko kwadranse ↑
        #   - dla ↓2nd zwróć tylko kwadranse ↓
        if self.is_duplicated:
            phase = "second" if self.is_backward else "first"
        else:
            phase = "both"  # zwykłe godziny

        return create_quarter_hours(self.start_time, phase=phase)

    def strftime(self, format: str) -> str:
        return self.start_time.strftime(format)

    def __repr__(self):
        base = f"{self.start_time:%Y-%m-%d %H:%M}-{self.end_time:%H:%M}"
        if self.is_duplicated:
            tag = "↓2nd" if self.is_backward else "↑1st"
            return f"{base} [{tag}]"
        return base


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


@register_unit("days", children_key="hours", step=day_step)
class Day(GridtimeStructure):
    def __init__(self, day_date: Union[str, date]):
        super().__init__()
        self.date = parse_date(day_date)

    def _create_children(self) -> list[GridtimeLeaf]:
        return create_hours(self.date)

    @property
    def hours(self) -> list["Hour"]:
        """Godziny tego dnia (budowane leniwie, cache'owane po pierwszym dostępie)."""
        return list(self)

    def strftime(self, format: str) -> str:
        return self.date.strftime(format)

    def __repr__(self):
        return f"{self.date.strftime('%Y-%m-%d')}"


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


@register_unit("months", children_key="decades10", step=month_step)
class Month(GridtimeStructure):
    def __init__(self, year: int, month: int):
        super().__init__()
        self.year = year
        self.month = month

    def _create_children(self) -> list[GridtimeLeaf]:
        return create_days(self.year, self.month)

    def __repr__(self):
        return f"{self.year}-{self.month:02}"


def create_months(year: int, months: list[int]) -> list[Month]:
    return [Month(year, m) for m in months]


def create_quarter_months(year: int, quarter: int) -> list[Month]:
    start_month = 1 + (quarter - 1) * 3
    return create_months(year, list(range(start_month, start_month + 3)))


@register_unit("quarters", children_key="months", step=quarter_step)
class Quarter(GridtimeStructure):
    def __init__(self, year: int, quarter: int):
        super().__init__()
        if quarter not in (1, 2, 3, 4):
            raise ValueError("Kwartał musi być liczbą 1–4")
        self.year = year
        self.quarter = quarter

    def _create_children(self) -> list[GridtimeLeaf]:
        return create_quarter_months(self.year, self.quarter)

    def __repr__(self):
        return f"{self.year}-Q{self.quarter}"


def create_quarters(year: int, quarters=range(1, 5)) -> list[Quarter]:
    return [Quarter(year, q) for q in quarters]


@register_unit("years", children_key="quarters", step=year_step)
class Year(GridtimeStructure):
    def __init__(self, year: int):
        super().__init__()
        self.year = year

    def _create_children(self) -> list[GridtimeLeaf]:
        return create_quarters(self.year, quarters=range(1, 5))

    def __repr__(self):
        return f"{self.year}"


def create_week_days(iso_year: int, iso_week: int) -> list[Day]:
    return [Day(date.fromisocalendar(iso_year, iso_week, i)) for i in range(1, 8)]


@register_unit("weeks", children_key="days", step=week_step)
class Week(GridtimeStructure):
    def __init__(self, iso_year: int, iso_week: int):
        super().__init__()
        self.iso_year = iso_year
        self.iso_week = iso_week

    def _create_children(self) -> list[GridtimeLeaf]:
        return create_week_days(self.iso_year, self.iso_week)

    def __repr__(self):
        return f"W-{self.iso_week}-{self.iso_year}"


def create_season_quarters(year: int, type_: str) -> list[Quarter]:
    if type_ not in ("W", "S"):
        raise ValueError("Sezon musi być 'W' (zimowy) lub 'S' (letni)")

    if type_ == "W":
        # Zimowy sezon np. 2024 = Q4/2024 + Q1/2025
        return [Quarter(year, 4), Quarter(year + 1, 1)]
    else:  # type_ == "S"
        # Letni sezon np. 2024 = Q2 + Q3 roku 2024
        return [Quarter(year, 2), Quarter(year, 3)]


@register_unit("seasons", children_key="quarters", step=season_step)
class Season(GridtimeStructure):
    def __init__(self, year: int, type_: str):
        super().__init__()
        if type_ not in ("W", "S"):
            raise ValueError("Sezon musi być 'W' lub 'S'")

        self.year = year
        self.type = type_

    def _create_children(self) -> list[GridtimeLeaf]:
        return create_season_quarters(self.year, self.type)

    def __repr__(self):
        display_year = f"{self.year}/{self.year + 1}" if self.type == "W" else str(self.year)
        return f"S-{self.type}-{display_year}"


def decade_day_bounds(year: int, month: int, index: int) -> tuple[int, int]:
    """Zwraca (start_day, end_day) dekady `index` (1-3) danego miesiąca.

    Dzielona przez `MonthDecade` i `create_decade_days`, żeby granice dekady
    dało się policzyć bez materializowania obiektów `Day`.
    """
    if index not in (1, 2, 3):
        raise ValueError("index dekady musi być 1, 2 lub 3")
    start_day = 1 + (index - 1) * 10
    end_day = start_day + 9 if index < 3 else monthrange(year, month)[1]
    return start_day, end_day


def create_decade_days(year: int, month: int, index: int) -> list["Day"]:
    """Zwraca listę obiektów Day w danej dekadzie (1-3) danego miesiąca."""
    start_day, end_day = decade_day_bounds(year, month, index)
    return [Day(date(year, month, d)) for d in range(start_day, end_day + 1)]


@register_unit("decades10", children_key="days", step=month_decade_step)
class MonthDecade(GridtimeStructure):
    """
    Dekada miesięczna (1-3).  Przykład:
        MonthDecade(2025, 7, 2)  →  2025-07 Dekada  2 (11-20 lipca)
    """
    def __init__(self, year: int, month: int, index: int):
        super().__init__()
        start_day, end_day = decade_day_bounds(year, month, index)
        self.year   = year
        self.month  = month
        self.index  = index
        self.start_date: date = date(year, month, start_day)
        self.end_date: date = date(year, month, end_day)

    def _create_children(self) -> list[GridtimeLeaf]:
        return create_decade_days(self.year, self.month, self.index)

    def __repr__(self) -> str:
        return f"{self.year}-{self.month:02} D{self.index} ({self.start_date.day:02}-{self.end_date.day:02})"
