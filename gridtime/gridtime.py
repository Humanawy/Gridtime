# gridtime.py
from datetime import datetime, timedelta, date, time
from calendar import monthrange
from abc import ABC, abstractmethod
from typing import List, Iterator, Literal, Union, Optional
from gridtime.utils import _GRIDTIME_REGISTRY, register_unit, _all_unit_keys, _is_reachable, is_duplicated_hour, is_duplicated_quarter, is_missing_hour, is_missing_quarter, parse_date, is_quarter_aligned
from collections.abc import Sequence
from datetime import timedelta

def quarter_hour_step(obj: "QuarterHour", steps: int) -> "QuarterHour":
    """
    Zwraca instancję QuarterHour przesuniętą o `steps` kwadransów.

    • steps > 0  – w przyszłość
    • steps < 0  – w przeszłość

    Uwzględnia:
      • duplikaty kwadransów (is_duplicated_quarter / is_backward)
      • brakujące kwadranse (is_missing_quarter)
    """
    if steps == 0:
        return obj

    direction = 1 if steps > 0 else -1    # +1 → przód, -1 → tył
    current   = obj

    for _ in range(abs(steps)):

        # ── 1. Druga kopia w duplikacie ────────────────────────────────────
        if direction > 0 and current.is_duplicated and not current.is_backward:
            # ↑1st → ↓2nd
            current = QuarterHour(current.start_time, is_backward=True)
            continue

        if direction < 0 and current.is_duplicated and current.is_backward:
            # ↓2nd → ↑1st
            current = QuarterHour(current.start_time, is_backward=False)
            continue

        # ── 2. Przejście do kolejnego / poprzedniego kwadransa ─────────────
        cand_start = current.start_time + timedelta(minutes=15 * direction)

        # pomijamy brakujące kwadranse (wiosenna zmiana czasu)
        while is_missing_quarter(cand_start):
            cand_start += timedelta(minutes=15 * direction)

        # ── 3. Tworzymy instancję dla cand_start ───────────────────────────
        if is_duplicated_quarter(cand_start):
            # jeżeli duplikat:
            #   • przy kroku +1 – pierwszy egzemplarz
            #   • przy kroku -1 – drugi (bliższy wstecz)
            is_back = direction < 0
            current = QuarterHour(cand_start, is_backward=is_back)
        else:
            current = QuarterHour(cand_start)

    return current

def hour_step(obj: "Hour", steps: int) -> "Hour":
    """
    Zwraca instancję Hour przesuniętą o `steps` okresów.
    *  steps  > 0  – w przyszłość
    *  steps  < 0  – w przeszłość
    Obsługa:
      • duplikatów (is_duplicated / is_backward)
      • brakujących godzin (is_missing_hour)
    """
    if steps == 0:
        return obj

    direction = 1 if steps > 0 else -1
    current   = obj

    for _ in range(abs(steps)):

        # ── 1. Druga kopia w duplikacie ──────────────────────────────────────
        if direction > 0 and current.is_duplicated and not current.is_backward:
            #   ↑1st  →  ↓2nd
            current = Hour(current.end_time, is_backward=True)
            continue

        if direction < 0 and current.is_duplicated and current.is_backward:
            #   ↓2nd  →  ↑1st
            current = Hour(current.end_time, is_backward=False)
            continue

        # ── 2. Przejście do kolejnej / poprzedniej godziny ──────────────────
        cand_end = current.end_time + timedelta(hours=direction)

        # pomijamy brakującą godzinę (wiosenna zmiana czasu)
        while True:
            cand_start = cand_end - timedelta(hours=1)
            if is_missing_hour(cand_start):
                cand_end += timedelta(hours=direction)
                continue
            break

        # ── 3. Tworzymy instancję dla cand_end ──────────────────────────────
        if is_duplicated_hour(cand_start):
            # jeżeli duplikat:
            #   • przy kroku +1 wybieramy 1-szy egzemplarz
            #   • przy kroku -1 – 2-gi (bo jest „bliżej” w czasie wstecz)
            is_back = direction < 0
            current = Hour(cand_end, is_backward=is_back)
        else:
            current = Hour(cand_end)

    return current

def day_step(obj: "Day", steps: int) -> "Day":
    """
    Zwraca instancję Day przesuniętą o `steps` dni.
      • steps > 0  – przyszłość
      • steps < 0  – przeszłość
      • steps == 0 – ten sam dzień
    """
    if steps == 0:
        return obj
    new_date = obj.date + timedelta(days=steps)
    return Day(new_date)

def month_step(obj: "Month", steps: int) -> "Month":
    """
    Zwraca instancję Month przesuniętą o `steps` miesięcy.

      • steps > 0  – przyszłość
      • steps < 0  – przeszłość
      • steps == 0 – ten sam miesiąc
    """
    if steps == 0:
        return obj

    # liczba miesięcy od „epochy” (rok 0, styczeń = 0)
    current_index = obj.year * 12 + (obj.month - 1)
    target_index  = current_index + steps

    new_year, new_month_zero = divmod(target_index, 12)  # divmod działa poprawnie z liczbami < 0
    new_month = new_month_zero + 1                       # 0-based → 1-based

    return Month(new_year, new_month)

def quarter_step(obj: "Quarter", steps: int) -> "Quarter":
    """
    Przesuń Quarter o `steps` kwartałów (dodatnie ➜ przyszłość, ujemne ➜ przeszłość).
    """
    if steps == 0:
        return obj

    current_idx = obj.year * 4 + (obj.quarter - 1)   # 0-based indeks globalny
    target_idx  = current_idx + steps

    new_year, new_q_zero = divmod(target_idx, 4)
    new_quarter = new_q_zero + 1                     # 1–4

    return Quarter(new_year, new_quarter)

def year_step(obj: "Year", steps: int) -> "Year":
    """
    Przesuń Year o `steps` lat.
    """
    if steps == 0:
        return obj
    return Year(obj.year + steps)

def week_step(obj: "Week", steps: int) -> "Week":
    """
    Przesuń Week o `steps` tygodni według kalendarza ISO-8601.
    """
    if steps == 0:
        return obj

    # poniedziałek danego tygodnia
    current_monday = date.fromisocalendar(obj.iso_year, obj.iso_week, 1)
    target_monday  = current_monday + timedelta(weeks=steps)

    new_iso_year, new_iso_week, _ = target_monday.isocalendar()
    return Week(new_iso_year, new_iso_week)

def season_step(obj: "Season", steps: int) -> "Season":
    """
    Zwraca instancję Season przesuniętą o `steps` sezonów
    (dodatnie ➜ przyszłość, ujemne ➜ przeszłość).
    """
    if steps == 0:
        return obj

    # 0-based, rosnący wraz z  chronologią
    current_idx = obj.year * 2 + (0 if obj.type == "S" else 1)
    target_idx  = current_idx + steps

    new_year, mod = divmod(target_idx, 2)     # mod ∈ {0, 1}
    new_type = "S" if mod == 0 else "W"

    return Season(new_year, new_type)

def month_decade_step(obj: "MonthDecade", steps: int) -> "MonthDecade":
    """
    Przesuń MonthDecade o `steps` dekad (10-dniowych okresów).
    Kroki +/-1 przechodzą kolejno: 1→2→3→(następny miesiąc, dekada 1) itd.
    """
    if steps == 0:
        return obj

    # globalny indeks: każdy miesiąc ma 3 dekady
    current_idx = (obj.year * 12 + (obj.month - 1)) * 3 + (obj.index - 1)
    target_idx  = current_idx + steps

    # dekodujemy z powrotem
    month_block, new_idx_zero = divmod(target_idx, 3)   # 0..2
    new_year, new_month_zero  = divmod(month_block, 12)
    new_month  = new_month_zero + 1
    new_index  = new_idx_zero + 1                       # 1..3

    return MonthDecade(new_year, new_month, new_index)

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
    def __init__(self, reference_time: datetime, *, is_backward: bool = False):
        super().__init__()
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
        # Jeśli godzina jest duplikowana, to:
        #   - dla ↑1st zwróć tylko kwadranse ↑
        #   - dla ↓2nd zwróć tylko kwadranse ↓
        if self.is_duplicated:
            phase = "second" if self.is_backward else "first"
        else:
            phase = "both"  # zwykłe godziny

        return create_quarter_hours(self.start_time, phase=phase)  # type: ignore

    
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
    def __init__(self, day_date: date):
        super().__init__()
        self.date = day_date
        self._children = self._create_children()
        self.hours = self._create_children()

    def _create_children(self) -> list[GridtimeLeaf]:
        return create_hours(self.date) # type: ignore
    
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
        return create_days(self.year, self.month) # type: ignore
    
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
        return create_quarter_months(self.year, self.quarter) # type: ignore
    
    def __repr__(self):
        return f"{self.year}-Q{self.quarter}"
    
@register_unit("years", children_key="quarters", step=year_step)    
class Year(GridtimeStructure):
    def __init__(self, year: int):
        super().__init__()
        self.year = year
        self._children = self._create_children()

    def _create_children(self) -> list[GridtimeLeaf]:
        return create_quarters(self.year, quarters=range(1, 5))  #type: ignore
    
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
        return create_week_days(self.iso_year, self.iso_week)  #type: ignore

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
        return create_season_quarters(self.year, self.type) #type: ignore
    
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
        return create_decade_days(self.year, self.month, self.index)  # type: ignore
    
    def __repr__(self) -> str:
        return f"{self.year}-{self.month:02} D{self.index} ({self.start_date.day:02}-{self.end_date.day:02})"


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

def create_hours(date_: date, hour_range=range(1, 25)) -> list[Hour]:
    hours: list[Hour] = []

    for hour in hour_range:
        dt_end = datetime.combine(date_, time(0)) + timedelta(hours=hour)
        start_time = dt_end - timedelta(hours=1)

        # brakująca (wiosenna) godzina – pomijamy
        if is_missing_hour(start_time):
            continue

        # podwójna godzina przy cofnięciu czasu
        if is_duplicated_hour(start_time):
            hours.append(Hour(dt_end, is_backward=False))  # 1. przed cofnięciem
            hours.append(Hour(dt_end, is_backward=True))   # 2. po cofnięciu
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

def create_date_range(
    start: Union[str, date],
    end: Union[str, date],
    granularity: Literal["days", "hours", "quarters15"] = "days",
    *,
    include_start: bool = True,
    include_end: bool = True,
) -> Union[list["Day"], list["Hour"], list["QuarterHour"]]:
    """Tworzy listę jednostek czasu w zadanym przedziale dat.

    Args:
        start:         Data początku – obiekt date lub ciąg tekstowy
                       (DD.MM.YYYY / DD/MM/YYYY / DD-MM-YYYY / YYYY-MM-DD).
        end:           Data końca – ten sam format co start.
        granularity:   Granulacja zwracanych jednostek:
                         "days"       – obiekty Day (jeden na dobę)
                         "hours"      – obiekty Hour (z obsługą DST)
                         "quarters15" – obiekty QuarterHour (z obsługą DST)
        include_start: Czy włączyć pierwszą jednostkę zakresu (domyślnie True).
        include_end:   Czy włączyć ostatnią jednostkę zakresu (domyślnie True).
    """
    if granularity == "quarters15":
        for label, val in (("start", start), ("end", end)):
            if isinstance(val, datetime) and not is_quarter_aligned(val):
                raise ValueError(
                    f"Dla granulacji 'quarters15' data {label} musi być wyrównana do granicy "
                    f"kwadransa (minuty: 0, 15, 30 lub 45, sekundy: 0). "
                    f"Otrzymano: {val:%H:%M:%S}."
                )

    start_date = parse_date(start)
    end_date   = parse_date(end)

    if start_date > end_date:
        raise ValueError(
            f"Data początku ({start_date}) musi być wcześniejsza lub równa dacie końca ({end_date})."
        )

    result: list = []
    current = start_date

    if granularity == "days":
        while current <= end_date:
            result.append(Day(current))
            current += timedelta(days=1)

    elif granularity == "hours":
        while current <= end_date:
            result.extend(create_hours(current))
            current += timedelta(days=1)

    elif granularity == "quarters15":
        while current <= end_date:
            for hour in create_hours(current):
                result.extend(list(hour))
            current += timedelta(days=1)

    else:
        raise ValueError(
            f"Nieznana granulacja: '{granularity}'. Dozwolone: 'days', 'hours', 'quarters15'."
        )

    if not include_start and result:
        result = result[1:]
    if not include_end and result:
        result = result[:-1]

    return result

def validate_complete_range(items: list[GridtimeLeaf]) -> bool:
    """
    Waliduje, czy lista `items` zawiera pełny zakres jednostek czasu.
    Ignoruje naturalne duplikaty z DST (is_duplicated=True).
    Zwraca True jeśli OK, w przeciwnym razie rzuca ValueError.
    """

    if not items:
        raise ValueError("Lista jest pusta.")

    cls = items[0].__class__

    # wszystkie elementy tego samego typu
    if any(type(e) is not cls for e in items):
        raise ValueError("Lista zawiera elementy różnych typów jednostek.")

    start = items[0]
    end   = items[-1]

    # generujemy idealny zakres
    cur = start
    expected = []
    while True:
        expected.append(cur)
        if cur == end:
            break
        cur = cur.next()

    set_items = set(items)
    set_expected = set(expected)

    # --- brakujące
    missing = sorted(set_expected - set_items, key=lambda x: repr(x))
    if missing:
        raise ValueError(
            f"Zakres niekompletny – brak elementów, np.: {missing[0]!r}"
        )

    # --- prawdziwe duplikaty
    duplicates = []
    seen = set()

    for obj in items:
        key = (obj.start_time, obj.end_time)

        # jeśli jest to naturalny duplikat przy DST → ignorujemy
        if getattr(obj, "is_duplicated", False):
            continue

        if key in seen:
            duplicates.append(obj)
        else:
            seen.add(key)

    if duplicates:
        raise ValueError(
            f"Nielogiczne duplikaty w danych, np.: {duplicates[0]!r}"
        )

    return True