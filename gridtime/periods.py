# gridtime/periods.py
from datetime import datetime, timedelta, date, time
from typing import Union
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

        self._children = self._create_children()

    def _create_children(self) -> list[GridtimeLeaf]:
        from gridtime.factories import create_quarter_hours  # lazy import
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


@register_unit("days", children_key="hours", step=day_step)
class Day(GridtimeStructure):
    def __init__(self, day_date: Union[str, date]):
        super().__init__()
        self.date = parse_date(day_date)
        self._children = self._create_children()
        self.hours = self._create_children()

    def _create_children(self) -> list[GridtimeLeaf]:
        from gridtime.factories import create_hours  # lazy import
        return create_hours(self.date)

    def strftime(self, format: str) -> str:
        return self.date.strftime(format)

    def __repr__(self):
        return f"{self.date.strftime('%Y-%m-%d')}"


@register_unit("months", children_key="decades10", step=month_step)
class Month(GridtimeStructure):
    def __init__(self, year: int, month: int):
        super().__init__()
        self.year = year
        self.month = month
        self._children = self._create_children()

    def _create_children(self) -> list[GridtimeLeaf]:
        from gridtime.factories import create_days  # lazy import
        return create_days(self.year, self.month)

    def __repr__(self):
        return f"{self.year}-{self.month:02}"


@register_unit("quarters", children_key="months", step=quarter_step)
class Quarter(GridtimeStructure):
    def __init__(self, year: int, quarter: int):
        super().__init__()
        if quarter not in (1, 2, 3, 4):
            raise ValueError("Kwartał musi być liczbą 1–4")
        self.year = year
        self.quarter = quarter
        self._children = self._create_children()

    def _create_children(self) -> list[GridtimeLeaf]:
        from gridtime.factories import create_quarter_months  # lazy import
        return create_quarter_months(self.year, self.quarter)

    def __repr__(self):
        return f"{self.year}-Q{self.quarter}"


@register_unit("years", children_key="quarters", step=year_step)
class Year(GridtimeStructure):
    def __init__(self, year: int):
        super().__init__()
        self.year = year
        self._children = self._create_children()

    def _create_children(self) -> list[GridtimeLeaf]:
        from gridtime.factories import create_quarters  # lazy import
        return create_quarters(self.year, quarters=range(1, 5))

    def __repr__(self):
        return f"{self.year}"


@register_unit("weeks", children_key="days", step=week_step)
class Week(GridtimeStructure):
    def __init__(self, iso_year: int, iso_week: int):
        super().__init__()
        self.iso_year = iso_year
        self.iso_week = iso_week
        self._children = self._create_children()

    def _create_children(self) -> list[GridtimeLeaf]:
        from gridtime.factories import create_week_days  # lazy import
        return create_week_days(self.iso_year, self.iso_week)

    def __repr__(self):
        return f"W-{self.iso_week}-{self.iso_year}"


@register_unit("seasons", children_key="quarters", step=season_step)
class Season(GridtimeStructure):
    def __init__(self, year: int, type_: str):
        super().__init__()
        if type_ not in ("W", "S"):
            raise ValueError("Sezon musi być 'W' lub 'S'")

        self.year = year
        self.type = type_
        self._children = self._create_children()

    def _create_children(self) -> list[GridtimeLeaf]:
        from gridtime.factories import create_season_quarters  # lazy import
        return create_season_quarters(self.year, self.type)

    def __repr__(self):
        display_year = f"{self.year}/{self.year + 1}" if self.type == "W" else str(self.year)
        return f"S-{self.type}-{display_year}"


@register_unit("decades10", children_key="days", step=month_decade_step)
class MonthDecade(GridtimeStructure):
    """
    Dekada miesięczna (1-3).  Przykład:
        MonthDecade(2025, 7, 2)  →  2025-07 Dekada  2 (11-20 lipca)
    """
    def __init__(self, year: int, month: int, index: int):
        super().__init__()
        if index not in (1, 2, 3):
            raise ValueError("Dekada miesiąca musi być 1, 2 lub 3")
        self.year   = year
        self.month  = month
        self.index  = index
        self._children = self._create_children()
        self.start_date: date = self._children[0].date  # type: ignore
        self.end_date: date = self._children[-1].date  # type: ignore

    def _create_children(self) -> list[GridtimeLeaf]:
        from gridtime.factories import create_decade_days  # lazy import
        return create_decade_days(self.year, self.month, self.index)

    def __repr__(self) -> str:
        return f"{self.year}-{self.month:02} D{self.index} ({self.start_date.day:02}-{self.end_date.day:02})"
