# gridtime/ranges.py
from datetime import datetime, date, timedelta
from typing import Union, List, Literal
from gridtime.periods import Day, Hour, QuarterHour
from gridtime.factories import create_hours
from gridtime.parsing import parse_date, is_quarter_aligned, parse_hour


def create_hour_range(
    start_hour: Union[int, str],
    start_date: Union[str, date],
    end_hour: Union[int, str],
    end_date: Union[str, date],
    *,
    convention: Literal["0-23", "1-24"] = "0-23",
    interpret: Literal["as_start", "as_end"] = "as_start",
    include_start: bool = True,
    include_end: bool = True,
) -> list["Hour"]:
    """Tworzy listę obiektów Hour w zadanym przedziale godzinowym.

    Args:
        start_hour:    Numer godziny początku (int lub str).
        start_date:    Data początku (obiekt date lub ciąg tekstowy).
        end_hour:      Numer godziny końca (int lub str).
        end_date:      Data końca (obiekt date lub ciąg tekstowy).
        convention:    "0-23" (domyślna) lub "1-24" (energetyczna PSE).
        interpret:     "as_start" (domyślna) lub "as_end".
        include_start: Czy włączyć pierwszą godzinę zakresu (domyślnie True).
        include_end:   Czy włączyć ostatnią godzinę zakresu (domyślnie True).

    DST: godziny brakujące (wiosna) są pomijane automatycznie; duplikowane (jesień)
    są uwzględniane obydwie jako osobne obiekty Hour (↑1st i ↓2nd).
    Granica końcowa domyślnie wskazuje na ↑1st duplikatu – aby włączyć też ↓2nd
    należy użyć parse_hour z backward=True i przekazać wynik do granicy zakresu.
    """
    start = parse_hour(start_hour, start_date, convention=convention, interpret=interpret)
    end   = parse_hour(end_hour,   end_date,   convention=convention, interpret=interpret)

    # start musi być <= end (end_time jako oś czasu; ↑1st < ↓2nd dla tego samego przedziału)
    if start.end_time > end.end_time or (
        start.end_time == end.end_time
        and start.is_backward
        and not end.is_backward
    ):
        raise ValueError(
            f"Godzina początku ({start!r}) musi być wcześniejsza "
            f"lub równa godzinie końca ({end!r})."
        )

    result: list[Hour] = []
    current = start

    while True:
        result.append(current)
        # zatrzymujemy się gdy end_time i is_backward są identyczne
        # (obsługa duplikatów DST: ↑1st != ↓2nd mimo identycznych start/end)
        if current.end_time == end.end_time and current.is_backward == end.is_backward:
            break
        current = current.next()

    if not include_start and result:
        result = result[1:]
    if not include_end and result:
        result = result[:-1]

    return result


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
