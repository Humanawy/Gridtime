# utils.py
from datetime import datetime, date, time, timedelta
from calendar import monthrange
from typing import Optional, Union
import re
import locale

locale.setlocale(locale.LC_TIME, "pl_PL.UTF-8") 

_GRIDTIME_REGISTRY = {}

def print_structure_tree(cls: type, indent: str = ""):
    unit_key = _GRIDTIME_REGISTRY.get(cls, {}).get("unit_key", cls.__name__)
    print(f"{indent}{cls.__name__} [{unit_key}]")

    child_key = _GRIDTIME_REGISTRY.get(cls, {}).get("children_key")
    if child_key:
        child_classes = [
            child_cls for child_cls, props in _GRIDTIME_REGISTRY.items()
            if props["unit_key"] == child_key
        ]
        for child_cls in child_classes:
            print_structure_tree(child_cls, indent + "  ")

def register_unit(unit_key: str, children_key: Optional[str] = None, step: Optional[str] = None):
    def decorator(cls):
        _GRIDTIME_REGISTRY[cls] = {
            "unit_key": unit_key,
            "children_key": children_key,
            "step": step,     
        }
        return cls
    return decorator

def _all_unit_keys() -> set[str]:
    """Zwraca zbiór wszystkich zarejestrowanych unit_key‑ów."""
    return {props["unit_key"] for props in _GRIDTIME_REGISTRY.values()}

def _is_reachable(cls: type, target_unit: str) -> bool:
    """
    Czy z danej klasy istnieje ścieżka do jednostki `target_unit`
    (włącznie z nią samą)?
    """
    props = _GRIDTIME_REGISTRY.get(cls, {})
    if props.get("unit_key") == target_unit:
        return True

    child_key = props.get("children_key")
    if child_key is None:
        return False

    # wszystkie klasy, które reprezentują dziecko o podanym key‑u
    child_classes = [
        c for c, p in _GRIDTIME_REGISTRY.items()
        if p["unit_key"] == child_key
    ]
    return any(_is_reachable(c, target_unit) for c in child_classes)

def list_registered_units():
    return {cls.__name__: props["unit_key"] for cls, props in _GRIDTIME_REGISTRY.items()}

def is_quarter_aligned(dt: datetime) -> bool:
    """Sprawdza, czy datetime jest wyrównany do granicy kwadransa (minuty: 0, 15, 30 lub 45)."""
    return dt.minute in (0, 15, 30, 45) and dt.second == 0 and dt.microsecond == 0

def parse_date(value: Union[str, date]) -> date:
    """Parsuje ciąg tekstowy daty lub obiekt date/datetime do obiektu date.

    Obsługiwane formaty tekstowe:
        DD.MM.YYYY  →  01.01.2027
        DD/MM/YYYY  →  01/01/2027
        DD-MM-YYYY  →  01-01-2027
        YYYY-MM-DD  →  2027-01-01
    """
    if isinstance(value, datetime):   # datetime jest podklasą date – sprawdź pierwszy
        return value.date()
    if isinstance(value, date):
        return value
    formats = [
        "%d.%m.%Y",
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%Y-%m-%d",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    raise ValueError(
        f"Nierozpoznany format daty: '{value}'. "
        "Obsługiwane formaty: DD.MM.YYYY, DD/MM/YYYY, DD-MM-YYYY, YYYY-MM-DD"
    )

_HOUR_REPR_RE = re.compile(
    r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}-\d{2}:\d{2}(\s+\[.+\])?$'
)

def _is_hour_repr(s: str) -> bool:
    """Sprawdza, czy ciąg tekstowy jest repr-em obiektu Hour (np. '2026-01-01 21:00-22:00')."""
    return bool(_HOUR_REPR_RE.match(s.strip()))

def parse_hour_repr(s: str) -> tuple:
    """Parsuje repr godziny do (end_time: datetime, is_backward: bool).

    Obsługiwane formaty:
        YYYY-MM-DD HH:MM-HH:MM
        YYYY-MM-DD HH:MM-HH:MM [↑1st]
        YYYY-MM-DD HH:MM-HH:MM [↓2nd]
    """
    s = s.strip()
    is_backward = False

    if s.endswith(']'):
        bracket = s.rfind('[')
        tag = s[bracket + 1:-1].strip()
        is_backward = (tag == '↓2nd')
        s = s[:bracket].strip()

    parts = s.split(' ')
    if len(parts) != 2:
        raise ValueError(f"Nieprawidłowy format repr godziny: '{s}'.")

    date_str, time_range = parts
    time_parts = time_range.split('-')
    if len(time_parts) != 2:
        raise ValueError(f"Nieprawidłowy zakres czasu w repr godziny: '{time_range}'.")

    start_str, _ = time_parts
    try:
        d = datetime.strptime(date_str, '%Y-%m-%d').date()
        sh, sm = map(int, start_str.split(':'))
    except (ValueError, AttributeError):
        raise ValueError(f"Nieprawidłowy format repr godziny: '{s}'.")

    start_dt = datetime.combine(d, time(sh, sm))
    end_dt = start_dt + timedelta(hours=1)
    return end_dt, is_backward

def is_missing_hour(start: datetime) -> bool:
    # 1. Czy miesiąc to marzec?
    if start.month != 3:
        return False

    # 2. Czy to niedziela?
    if start.weekday() != 6:  # 6 = niedziela
        return False

    # 3. Czy to ostatnia niedziela marca?
    last_day = monthrange(start.year, 3)[1]
    last_sunday = max(
        day for day in range(last_day - 6, last_day + 1)
        if date(start.year, 3, day).weekday() == 6
    )
    if start.day != last_sunday:
        return False

    # 4. Czy godzina to 02:00?
    if start.hour == 2:
        return True

    # Jeśli nie spełnia warunków zmiany czasu – godzina istnieje
    return False

def is_missing_quarter(start: datetime) -> bool:
    if is_missing_hour(start):
        return True
    return False

def is_duplicated_hour(start: datetime) -> bool:
    # 1. Czy miesiąc to październik?
    if start.month != 10:
        return False
    # 2. Czy to niedziela?
    if start.weekday() != 6:  # 6 = niedziela
        return False
    # 3. Czy to ostatnia niedziela października?
    last_day = monthrange(start.year, 10)[1]
    last_sunday = max(
        day for day in range(last_day - 6, last_day + 1)
        if date(start.year, 10, day).weekday() == 6
    )
    if start.day != last_sunday:
        return False
    # 4. Czy godzina to 02:00?
    if start.hour == 2:
        return True
    # Jeśli nie spełnia warunków zmiany czasu – godzina nie jest podwójna
    return False

def is_duplicated_quarter(start: datetime) -> bool:
    if is_duplicated_hour(start):
        return True
    return False

