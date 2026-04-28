# gridtime/_dst.py
from datetime import datetime, date
from calendar import monthrange


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
