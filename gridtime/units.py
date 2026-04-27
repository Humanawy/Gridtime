# units.py – funkcje kroku, klasy bazowe, klasy domenowe, wewnętrzne fabryki DST
from datetime import datetime, timedelta, date, time
from calendar import monthrange
from abc import ABC, abstractmethod
from typing import List, Iterator, Literal, Union, Optional
from collections.abc import Sequence

from gridtime.utils import (
    _GRIDTIME_REGISTRY, register_unit, _all_unit_keys, _is_reachable,
    is_duplicated_hour, is_duplicated_quarter,
    is_missing_hour, is_missing_quarter,
    parse_date, is_quarter_aligned,
    _parse_hour_repr, _is_hour_repr,
)


# ─────────────────────────────────────────────────────────────────────────────
# Funkcje kroku
# ─────────────────────────────────────────────────────────────────────────────

def quarter_hour_step(obj: "QuarterHour", steps: int) -> "QuarterHour":
    if steps == 0:
        return obj

    direction = 1 if steps > 0 else -1
    current   = obj

    for _ in range(abs(steps)):
        if direction > 0 and current.is_duplicated and not current.is_backward:
            current = QuarterHour(current.start_time, is_backward=True)
            continue
        if direction < 0 and current.is_duplicated and current.is_backward:
            current = QuarterHour(current.start_time, is_backward=False)
            continue

        cand_start = current.start_time + timedelta(minutes=15 * direction)
        while is_missing_quarter(cand_start):
            cand_start += timedelta(minutes=15 * direction)

        is_back = direction < 0 if is_duplicated_quarter(cand_start) else False
        if is_duplicated_quarter(cand_start):
            current = QuarterHour(cand_start, is_backward=is_back)
        else:
            current = QuarterHour(cand_start)

    return current


def hour_step(obj: "Hour", steps: int) -> "Hour":
    if steps == 0:
        return obj

    direction = 1 if steps > 0 else -1
    current   = obj

    for _ in range(abs(steps)):
        if direction > 0 and current.is_duplicated and not current.is_backward:
            current = Hour(current.end_time, is_backward=True)
            continue
        if direction < 0 and current.is_duplicated and current.is_backward:
            current = Hour(current.end_time, is_backward=False)
            continue

        cand_end = current.end_time + timedelta(hours=direction)
        while True:
            cand_start = cand_end - timedelta(hours=1)
            if is_missing_hour(cand_start):
                cand_end += timedelta(hours=direction)
                continue
            break

        if is_duplicated_hour(cand_start):
            is_back = direction < 0
            current = Hour(cand_end, is_backward=is_back)
        else:
            current = Hour(cand_end)

    return current


def day_step(obj: "Day", steps: int) -> "Day":
    if steps == 0:
        return obj
    return Day(obj.date + timedelta(days=steps))


def month_step(obj: "Month", steps: int) -> "Month":
    if steps == 0:
        return obj
    current_index = obj.year * 12 + (obj.month - 1)
    target_index  = current_index + steps
    new_year, new_month_zero = divmod(target_index, 12)
    return Month(new_year, new_month_zero + 1)


def quarter_step(obj: "Quarter", steps: int) -> "Quarter":
    if steps == 0:
        return obj
    current_idx = obj.year * 4 + (obj.quarter - 1)
    target_idx  = current_idx + steps
    new_year, new_q_zero = divmod(target_idx, 4)
    return Quarter(new_year, new_q_zero + 1)


def year_step(obj: "Year", steps: int) -> "Year":
    if steps == 0:
        return obj
    return Year(obj.year + steps)


def week_step(obj: "Week", steps: int) -> "Week":
    if steps == 0:
        return obj
    current_monday = date.fromisocalendar(obj.iso_year, obj.iso_week, 1)
    target_monday  = current_monday + timedelta(weeks=steps)
    new_iso_year, new_iso_week, _ = target_monday.isocalendar()
    return Week(new_iso_year, new_iso_week)


def season_step(obj: "Season", steps: int) -> "Season":
    if steps == 0:
        return obj
    current_idx = obj.year * 2 + (0 if obj.type == "S" else 1)
    target_idx  = current_idx + steps
    new_year, mod = divmod(target_idx, 2)
    return Season(new_year, "S" if mod == 0 else "W")


def month_decade_step(obj: "MonthDecade", steps: int) -> "MonthDecade":
    if steps == 0:
        return obj
    current_idx = (obj.year * 12 + (obj.month - 1)) * 3 + (obj.index - 1)
    target_idx  = current_idx + steps
    month_block, new_idx_zero = divmod(target_idx, 3)
    new_year, new_month_zero  = divmod(month_block, 12)
    return MonthDecade(new_year, new_month_zero + 1, new_idx_zero + 1)


# ─────────────────────────────────────────────────────────────────────────────
# Klasy bazowe
# ─────────────────────────────────────────────────────────────────────────────

class GridtimeLeaf(ABC):
    def _structure_name(self) -> str:
        return self.__class__.__name__

    def unit_key(self) -> str:
        return _GRIDTIME_REGISTRY[self.__class__]["unit_key"]

    @abstractmethod
    def __repr__(self) -> str:
        pass

    def shift(self, steps: int = 1) -> "GridtimeLeaf":
        info = _GRIDTIME_REGISTRY[self.__class__]
        if "step" not in info:
            raise NotImplementedError(f"Brak klucza 'step' dla {self.__class__.__name__}")
        return info["step"](self, steps)

    def next(self): return self.shift(+1)
    def prev(self): return self.shift(-1)
    def __next__(self): return self.next()

    def _iter_children(self) -> Iterator["GridtimeLeaf"]:
        return iter(())

    def children_key(self) -> str | None:
        return _GRIDTIME_REGISTRY[self.__class__].get("children_key")

    def _validate_unit(self, unit: str) -> None:
        if unit not in _all_unit_keys():
            raise ValueError(
                f"Nieznana jednostka '{unit}'. Dostępne: {sorted(_all_unit_keys())}"
            )
        if not _is_reachable(self.__class__, unit):
            raise ValueError(
                f"Jednostka '{unit}' nie występuje w gałęzi drzewa z korzeniem "
                f"{self._structure_name()} ('{self.unit_key()}')."
            )

    def __iter__(self) -> Iterator["GridtimeLeaf"]:
        return self._iter_children()

    def __len__(self) -> int:
        return sum(1 for _ in self._iter_children())

    def __contains__(self, other: object) -> bool:
        if not isinstance(other, GridtimeLeaf):
            return False
        return any(node == other for node in self.walk(other.unit_key()))

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, self.__class__)
            and getattr(self, "start_time", None) == getattr(other, "start_time", None)
            and getattr(self, "end_time", None)   == getattr(other, "end_time", None)
        )

    def __hash__(self) -> int:
        return hash((self.__class__, getattr(self, "start_time", None), getattr(self, "end_time", None)))

    def count(self, unit: str) -> int:
        self._validate_unit(unit)
        if self.unit_key() == unit:
            return 1
        if self.children_key() is None:
            return 0
        return sum(child.count(unit) for child in self._iter_children())

    def get(self, unit: str) -> List["GridtimeLeaf"]:
        self._validate_unit(unit)
        if self.unit_key() == unit:
            return [self]
        if self.children_key() is None:
            return []
        out: List["GridtimeLeaf"] = []
        for child in self._iter_children():
            out.extend(child.get(unit))
        return out

    def walk(self, unit: str) -> Iterator["GridtimeLeaf"]:
        self._validate_unit(unit)
        if self.unit_key() == unit:
            yield self
        elif self.children_key() is not None:
            for child in self._iter_children():
                yield from child.walk(unit)

    def tree(
        self,
        unit_stop: str | None = None,
        show_root: bool = True,
        _prefix: str = "",
        _is_last: bool = True,
    ) -> str:
        lines: list[str] = []
        if show_root:
            connector = "└── " if _is_last else "├── "
            lines.append(f"{_prefix}{connector}{repr(self)}")
            _prefix += "    " if _is_last else "│   "

        if (unit_stop is not None and self.unit_key() == unit_stop) \
                or self.children_key() is None:
            return "\n".join(lines)

        children = list(self._iter_children())
        for idx, child in enumerate(children):
            is_last = idx == len(children) - 1
            lines.append(child.tree(unit_stop, True, _prefix, is_last))
        return "\n".join(lines)

    def print_tree(self, **kwargs):
        print(self.tree(**kwargs))


class GridtimeStructure(GridtimeLeaf):
    def __init__(self):
        self._children: Sequence[GridtimeLeaf] | None = None

    @abstractmethod
    def _create_children(self) -> list[GridtimeLeaf]:
        ...

    def _iter_children(self) -> Iterator[GridtimeLeaf]:
        if self._children is None:
            self._children = self._create_children()
        return iter(self._children)


# ─────────────────────────────────────────────────────────────────────────────
# Wewnętrzne fabryki DST (wymagane przez _create_children klas Hour i Day)
# ─────────────────────────────────────────────────────────────────────────────

def create_quarter_hours(
    start_time: datetime,
    *,
    phase: Literal["first", "second", "both"] = "both",
) -> list["QuarterHour"]:
    """Zwraca kwadranse w obrębie godziny zaczynającej się o `start_time`.

    phase:
        "first"  – tylko ↑1st
        "second" – tylko ↓2nd
        "both"   – ↑1st i ↓2nd dla duplikatów DST
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
            else:
                quarters.append(QuarterHour(dt, is_backward=False))
                quarters.append(QuarterHour(dt, is_backward=True))
        else:
            quarters.append(QuarterHour(dt))
    return quarters


def create_hours(date_or_repr: Union[str, date], *more_reprs: str, hour_range=range(1, 25)) -> list["Hour"]:
    """Tworzy listę obiektów Hour dla podanej daty lub z repr stringów.

    Tryb repr (jeden lub więcej ciągów 'YYYY-MM-DD HH:MM-HH:MM'):
        create_hours("2026-01-01 21:00-22:00", "2026-01-01 22:00-23:00")

    Tryb klasyczny (data lub string daty):
        create_hours(date(2027, 1, 1))
        create_hours("2027-01-01")
    """
    if more_reprs or (isinstance(date_or_repr, str) and _is_hour_repr(date_or_repr)):
        return [Hour(r) for r in (date_or_repr, *more_reprs)]

    date_ = parse_date(date_or_repr)
    hours: list[Hour] = []
    for hour in hour_range:
        dt_end     = datetime.combine(date_, time(0)) + timedelta(hours=hour)
        start_time = dt_end - timedelta(hours=1)
        if is_missing_hour(start_time):
            continue
        if is_duplicated_hour(start_time):
            hours.append(Hour(dt_end, is_backward=False))
            hours.append(Hour(dt_end, is_backward=True))
        else:
            hours.append(Hour(dt_end))
    return hours


# ─────────────────────────────────────────────────────────────────────────────
# Klasy domenowe
# ─────────────────────────────────────────────────────────────────────────────

@register_unit("quarters15", step=quarter_hour_step)
class QuarterHour(GridtimeLeaf):
    def __init__(self, start_time: datetime, *, is_backward: bool = False):
        super().__init__()
        self.start_time = start_time
        self.end_time   = start_time + timedelta(minutes=15)

        if is_missing_quarter(self.start_time):
            raise ValueError(
                f"Nie można utworzyć kwadransu dla "
                f"{self.start_time:%Y-%m-%d %H:%M}-{self.end_time:%H:%M}"
            )

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
        self.end_time   = reference_time
        self.start_time = self.end_time - timedelta(hours=1)

        if is_missing_hour(self.start_time):
            raise ValueError(
                f"Nie można utworzyć godziny dla {reference_time:%Y-%m-%d %H:%M}"
            )

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
        phase = "both"
        if self.is_duplicated:
            phase = "second" if self.is_backward else "first"
        return create_quarter_hours(self.start_time, phase=phase)

    def strftime(self, fmt: str) -> str:
        return self.start_time.strftime(fmt)

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
        self.hours = self._children

    def _create_children(self) -> list[GridtimeLeaf]:
        return create_hours(self.date)

    def strftime(self, fmt: str) -> str:
        return self.date.strftime(fmt)

    def __repr__(self):
        return f"{self.date:%Y-%m-%d}"


@register_unit("months", children_key="decades10", step=month_step)
class Month(GridtimeStructure):
    def __init__(self, year: int, month: int):
        super().__init__()
        self.year  = year
        self.month = month
        self._children = self._create_children()

    def _create_children(self) -> list[GridtimeLeaf]:
        num_days = monthrange(self.year, self.month)[1]
        return [Day(date(self.year, self.month, d)) for d in range(1, num_days + 1)]

    def __repr__(self):
        return f"{self.year}-{self.month:02}"


@register_unit("quarters", children_key="months", step=quarter_step)
class Quarter(GridtimeStructure):
    def __init__(self, year: int, quarter: int):
        super().__init__()
        if quarter not in (1, 2, 3, 4):
            raise ValueError("Kwartał musi być liczbą 1–4")
        self.year    = year
        self.quarter = quarter
        self._children = self._create_children()

    def _create_children(self) -> list[GridtimeLeaf]:
        start_month = 1 + (self.quarter - 1) * 3
        return [Month(self.year, m) for m in range(start_month, start_month + 3)]

    def __repr__(self):
        return f"{self.year}-Q{self.quarter}"


@register_unit("years", children_key="quarters", step=year_step)
class Year(GridtimeStructure):
    def __init__(self, year: int):
        super().__init__()
        self.year = year
        self._children = self._create_children()

    def _create_children(self) -> list[GridtimeLeaf]:
        return [Quarter(self.year, q) for q in range(1, 5)]

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
        return [Day(date.fromisocalendar(self.iso_year, self.iso_week, i)) for i in range(1, 8)]

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
        if self.type == "W":
            return [Quarter(self.year, 4), Quarter(self.year + 1, 1)]
        return [Quarter(self.year, 2), Quarter(self.year, 3)]

    def __repr__(self):
        display_year = f"{self.year}/{self.year + 1}" if self.type == "W" else str(self.year)
        return f"S-{self.type}-{display_year}"


@register_unit("decades10", children_key="days", step=month_decade_step)
class MonthDecade(GridtimeStructure):
    def __init__(self, year: int, month: int, index: int):
        super().__init__()
        if index not in (1, 2, 3):
            raise ValueError("Dekada miesiąca musi być 1, 2 lub 3")
        self.year  = year
        self.month = month
        self.index = index
        self._children = self._create_children()
        self.start_date: date = self._children[0].date   # type: ignore
        self.end_date:   date = self._children[-1].date  # type: ignore

    def _create_children(self) -> list[GridtimeLeaf]:
        start_day = 1 + (self.index - 1) * 10
        end_day   = start_day + 9 if self.index < 3 else monthrange(self.year, self.month)[1]
        return [Day(date(self.year, self.month, d)) for d in range(start_day, end_day + 1)]

    def __repr__(self) -> str:
        return f"{self.year}-{self.month:02} D{self.index} ({self.start_date.day:02}-{self.end_date.day:02})"
