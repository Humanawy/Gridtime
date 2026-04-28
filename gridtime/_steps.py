# gridtime/_steps.py
from datetime import timedelta, date
from gridtime._dst import (
    is_missing_quarter, is_duplicated_quarter,
    is_missing_hour, is_duplicated_hour,
)


def quarter_hour_step(obj: "QuarterHour", steps: int) -> "QuarterHour":
    """
    Zwraca instancję QuarterHour przesuniętą o `steps` kwadransów.

    • steps > 0  – w przyszłość
    • steps < 0  – w przeszłość

    Uwzględnia:
      • duplikaty kwadransów (is_duplicated_quarter / is_backward)
      • brakujące kwadranse (is_missing_quarter)
    """
    from gridtime.periods import QuarterHour  # lazy import
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
    from gridtime.periods import Hour  # lazy import
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


def day_step(obj: "Day", steps: int) -> "Day":
    """
    Zwraca instancję Day przesuniętą o `steps` dni.
      • steps > 0  – przyszłość
      • steps < 0  – przeszłość
      • steps == 0 – ten sam dzień
    """
    from gridtime.periods import Day  # lazy import
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
    from gridtime.periods import Month  # lazy import
    if steps == 0:
        return obj

    # liczba miesięcy od „epochy" (rok 0, styczeń = 0)
    current_index = obj.year * 12 + (obj.month - 1)
    target_index  = current_index + steps

    new_year, new_month_zero = divmod(target_index, 12)  # divmod działa poprawnie z liczbami < 0
    new_month = new_month_zero + 1                       # 0-based → 1-based

    return Month(new_year, new_month)


def quarter_step(obj: "Quarter", steps: int) -> "Quarter":
    """
    Przesuń Quarter o `steps` kwartałów (dodatnie ➜ przyszłość, ujemne ➜ przeszłość).
    """
    from gridtime.periods import Quarter  # lazy import
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
    from gridtime.periods import Year  # lazy import
    if steps == 0:
        return obj
    return Year(obj.year + steps)


def week_step(obj: "Week", steps: int) -> "Week":
    """
    Przesuń Week o `steps` tygodni według kalendarza ISO-8601.
    """
    from gridtime.periods import Week  # lazy import
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
    from gridtime.periods import Season  # lazy import
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
    from gridtime.periods import MonthDecade  # lazy import
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
