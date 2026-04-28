# gridtime/parsing.py
from datetime import datetime, date, time, timedelta
from typing import Union, Literal
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


def parse_hour(
    hour: Union[int, str],
    date_: Union[str, date, None] = None,
    *,
    convention: Literal["0-23", "1-24"] = "0-23",
    interpret: Literal["as_start", "as_end"] = "as_start",
    backward: bool = False,
) -> "Hour":
    from gridtime.periods import Hour  # lazy import — unika cyklu periods↔parsing
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
