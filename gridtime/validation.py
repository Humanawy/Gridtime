# gridtime/validation.py
from gridtime._base import GridtimeLeaf


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
