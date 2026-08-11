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

# Każda klasa poniżej jest poprzedzona funkcją `create_*`, która buduje jej
# dzieci, i funkcją `*_step`, która oblicza przesunięcie w czasie (next/prev).
# Obie muszą być zdefiniowane przed klasą, bo `*_step` jest przekazywana jako
# argument dekoratora `@register_unit(...)`, a dekorator wykonuje się w
# momencie definicji klasy. `create_*` jest wołana dopiero z wnętrza metody,
# więc formalnie mogłaby stać za klasą — zostawiam ją obok `*_step`, żeby cała
# logika budowy/nawigacji danej jednostki czasu była w jednym miejscu.
# Obie funkcje są też publicznym API (re-eksportowanym w `gridtime/__init__.py`).


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
            #   • przy kroku -1 – 2-gi (bo jest „bliżej" w czasie wstecz)
            is_back = direction < 0
            current = Hour(cand_end, is_backward=is_back)
        else:
            current = Hour(cand_end)

    return current


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


def parse_hour(
    hour: Union[int, str],
    date_: Union[str, date, None] = None,
    *,
    convention: Literal["0-23", "1-24"] = "0-23",
    interpret: Literal["as_start", "as_end"] = "as_start",
    backward: bool = False,
) -> "Hour":
    """Parsuje godzinę do obiektu Hour.

    Dwa tryby użycia (analogicznie do parse_date):

    1) Repr string (jeden argument):
         parse_hour("2026-01-01 21:00-22:00")
         parse_hour("2026-01-01 02:00-03:00 [↓2nd]")

    2) Numer godziny + data:
         parse_hour(21, "2026-01-01")
         parse_hour("21", date(2026, 1, 1))
         parse_hour(1, "2026-01-01", convention="1-24", interpret="as_end")

    Args:
        hour:       Repr string YYYY-MM-DD HH:MM-HH:MM lub numer godziny (int/str).
        date_:      Data dnia – wymagana gdy hour jest numerem; None dla trybu repr.
        convention: "0-23" (domyślna) lub "1-24" (energetyczna PSE).
        interpret:  "as_start" (domyślna) lub "as_end".
        backward:   Dla duplikowanych godzin DST: False = ↑1st, True = ↓2nd.
                    Ignorowany gdy hour jest repr stringiem z tagiem DST.

    Tabela zakresów (tryb numer + data):
        convention  interpret   wejście   zakres
        0-23        as_start    0         00:00-01:00
        0-23        as_start    1         01:00-02:00
        0-23        as_start    23        23:00-00:00+1d
        0-23        as_end      1         00:00-01:00
        0-23        as_end      23        22:00-23:00
        0-23        as_end      0         ValueError
        1-24        as_end      1         00:00-01:00
        1-24        as_end      24        23:00-00:00+1d
        1-24        as_start    1         01:00-02:00
        1-24        as_start    24        ValueError
    """
    # --- tryb repr string ---
    if isinstance(hour, str) and _is_hour_repr(hour):
        if date_ is not None:
            raise ValueError(
                "Gdy hour jest repr stringiem (np. '2026-01-01 21:00-22:00'), "
                "nie należy podawać argumentu date_."
            )
        return Hour(hour)

    # --- tryb numer godziny + data ---
    if date_ is None:
        raise ValueError(
            "Argument date_ jest wymagany gdy hour jest numerem godziny."
        )

    # --- parsowanie liczby godziny ---
    if isinstance(hour, str):
        hour = hour.strip()
        if ":" in hour:
            parts = hour.split(":")
            if len(parts) != 2:
                raise ValueError(f"Nieprawidłowy format godziny: '{hour}'.")
            h_str, m_str = parts
            if not m_str.isdigit() or int(m_str) != 0:
                raise ValueError(
                    f"parse_hour oczekuje pełnych godzin (minuty = 00). Otrzymano: '{hour}'."
                )
            hour = int(h_str)
        else:
            if not hour.isdigit():
                raise ValueError(f"Nieprawidłowa wartość godziny: '{hour}'.")
            hour = int(hour)

    # --- walidacja zakresu dla danej konwencji ---
    if convention == "0-23":
        if not (0 <= hour <= 23):
            raise ValueError(
                f"Konwencja '0-23': godzina musi być w zakresie 0–23. Otrzymano: {hour}."
            )
    elif convention == "1-24":
        if not (1 <= hour <= 24):
            raise ValueError(
                f"Konwencja '1-24': godzina musi być w zakresie 1–24. Otrzymano: {hour}."
            )
    else:
        raise ValueError(f"Nieznana konwencja: '{convention}'. Dozwolone: '0-23', '1-24'.")

    # --- wyznaczenie end_time (Hour przyjmuje reference_time jako end_time) ---
    date_obj = parse_date(date_)
    base = datetime.combine(date_obj, time(0, 0))

    if convention == "0-23":
        if interpret == "as_start":
            end_time = base + timedelta(hours=hour + 1)
        elif interpret == "as_end":
            if hour == 0:
                raise ValueError(
                    "Konwencja '0-23', interpret='as_end': godzina 0 jest nieprawidłowa "
                    "(żadna godzina nie kończy się o 00:00)."
                )
            end_time = base + timedelta(hours=hour)
        else:
            raise ValueError(f"Nieznany interpret: '{interpret}'. Dozwolone: 'as_start', 'as_end'.")
    else:  # 1-24
        if interpret == "as_end":
            end_time = base + timedelta(hours=hour)
        elif interpret == "as_start":
            if hour == 24:
                raise ValueError(
                    "Konwencja '1-24', interpret='as_start': godzina 24 jako start jest nieprawidłowa."
                )
            end_time = base + timedelta(hours=hour + 1)
        else:
            raise ValueError(f"Nieznany interpret: '{interpret}'. Dozwolone: 'as_start', 'as_end'.")

    return Hour(end_time, is_backward=backward)


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


def month_step(obj: "Month", steps: int) -> "Month":
    """
    Zwraca instancję Month przesuniętą o `steps` miesięcy.

      • steps > 0  – przyszłość
      • steps < 0  – przeszłość
      • steps == 0 – ten sam miesiąc
    """
    if steps == 0:
        return obj

    # liczba miesięcy od „epochy" (rok 0, styczeń = 0)
    current_index = obj.year * 12 + (obj.month - 1)
    target_index  = current_index + steps

    new_year, new_month_zero = divmod(target_index, 12)  # divmod działa poprawnie z liczbami < 0
    new_month = new_month_zero + 1                       # 0-based → 1-based

    return Month(new_year, new_month)


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


def year_step(obj: "Year", steps: int) -> "Year":
    """
    Przesuń Year o `steps` lat.
    """
    if steps == 0:
        return obj
    return Year(obj.year + steps)


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
