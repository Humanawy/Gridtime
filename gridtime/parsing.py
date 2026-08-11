# gridtime/parsing.py
from datetime import datetime, date, time, timedelta
from typing import Union
import re
import locale

locale.setlocale(locale.LC_TIME, "pl_PL.UTF-8")


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


def _parse_hour_repr(s: str) -> tuple:
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
