# Reorganizacja struktury plików — gridtime

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rozbić monolityczne `gridtime/gridtime.py` (~950 linii) i `gridtime/utils.py` (~196 linii) na 9 mniejszych modułów o jednej odpowiedzialności każdy, bez zmiany działania żadnej funkcji.

**Architecture:** Czysta reorganizacja — żaden kod domenowy się nie zmienia. Jedynym dopuszczalnym wyjątkiem są lazy importy (`from gridtime.X import Y` wewnątrz ciała funkcji), niezbędne do złamania cykli importów między `periods.py`, `factories.py` i `_steps.py`. Lazy import nie zmienia zachowania funkcji — Python cache'uje moduły w `sys.modules`. Stare pliki (`gridtime.py`, `utils.py`) pozostają nienaruszone aż do Task 12, co gwarantuje że testy przechodzą przez cały proces migracji.

**Tech Stack:** Python 3.12+, pytest

---

## Mapa plików

| Plik | Akcja | Źródło kodu |
|------|-------|-------------|
| `gridtime/_registry.py` | Utwórz | `utils.py` linie 10–60 |
| `gridtime/_dst.py` | Utwórz | `utils.py` linie 140–194 |
| `gridtime/_base.py` | Utwórz | `gridtime.py` linie 216–341 |
| `gridtime/parsing.py` | Utwórz | `utils.py` linie 1–138 + `gridtime.py` linie 592–709 |
| `gridtime/_steps.py` | Utwórz | `gridtime.py` linie 10–214 |
| `gridtime/periods.py` | Utwórz | `gridtime.py` linie 342–528 |
| `gridtime/factories.py` | Utwórz | `gridtime.py` linie 531–590, 771–820 |
| `gridtime/ranges.py` | Utwórz | `gridtime.py` linie 711–769, 822–889 |
| `gridtime/validation.py` | Utwórz | `gridtime.py` linie 891–950 |
| `gridtime/pandas.py` | Utwórz | Nowy, pusty |
| `gridtime/__init__.py` | Zmodyfikuj | Przepisz importy |
| `gridtime/gridtime.py` | Usuń | Po weryfikacji testów |
| `gridtime/utils.py` | Usuń | Po weryfikacji testów |
| `tests/test_periods.py` | Utwórz | `test_gridtime.py` (wybrane testy) |
| `tests/test_parsing.py` | Utwórz | `test_gridtime.py` (wybrane testy) |
| `tests/test_factories.py` | Utwórz | `test_gridtime.py` (wybrane testy) |
| `tests/test_ranges.py` | Utwórz | Nowy, pusty |
| `tests/test_validation.py` | Utwórz | Nowy, pusty |
| `tests/test_gridtime.py` | Usuń | Po weryfikacji testów |

---

## Task 1: Utwórz `gridtime/_registry.py`

**Files:**
- Create: `gridtime/_registry.py`

- [ ] **Krok 1: Utwórz plik z nagłówkiem importów**

```python
# gridtime/_registry.py
from typing import Optional
```

- [ ] **Krok 2: Przenieś kod z `utils.py`**

Przekopiuj verbatim z `gridtime/utils.py` następujące symbole (bez zmian w ciałach):
- `_GRIDTIME_REGISTRY = {}` (linia 10)
- `print_structure_tree` (linie 12–23)
- `register_unit` (linie 25–33)
- `_all_unit_keys` (linie 35–37)
- `_is_reachable` (linie 39–57)
- `list_registered_units` (linie 59–60)

- [ ] **Krok 3: Uruchom testy (stare pliki wciąż istnieją — powinny przejść)**

```
pytest tests/ -q
```

Oczekiwany wynik: wszystkie testy PASS (stare pliki niezmienione).

- [ ] **Krok 4: Commit**

```bash
git add gridtime/_registry.py
git commit -m "refactor: extract _registry.py from utils.py"
```

---

## Task 2: Utwórz `gridtime/_dst.py`

**Files:**
- Create: `gridtime/_dst.py`

- [ ] **Krok 1: Utwórz plik z nagłówkiem importów**

```python
# gridtime/_dst.py
from datetime import datetime, date
from calendar import monthrange
```

- [ ] **Krok 2: Przenieś kod z `utils.py`**

Przekopiuj verbatim z `gridtime/utils.py`:
- `is_missing_hour` (linie 140–163)
- `is_missing_quarter` (linie 165–168)
- `is_duplicated_hour` (linie 170–189)
- `is_duplicated_quarter` (linie 191–194)

- [ ] **Krok 3: Uruchom testy**

```
pytest tests/ -q
```

Oczekiwany wynik: wszystkie testy PASS.

- [ ] **Krok 4: Commit**

```bash
git add gridtime/_dst.py
git commit -m "refactor: extract _dst.py from utils.py"
```

---

## Task 3: Utwórz `gridtime/_base.py`

**Files:**
- Create: `gridtime/_base.py`

- [ ] **Krok 1: Utwórz plik z nagłówkiem importów**

```python
# gridtime/_base.py
from abc import ABC, abstractmethod
from typing import List, Iterator
from collections.abc import Sequence
from gridtime._registry import _GRIDTIME_REGISTRY, _all_unit_keys, _is_reachable
```

- [ ] **Krok 2: Przenieś klasy bazowe z `gridtime.py`**

Przekopiuj verbatim z `gridtime/gridtime.py`:
- `GridtimeLeaf` (linie 216–327)
- `GridtimeStructure` (linie 329–341)

- [ ] **Krok 3: Uruchom testy**

```
pytest tests/ -q
```

Oczekiwany wynik: wszystkie testy PASS.

- [ ] **Krok 4: Commit**

```bash
git add gridtime/_base.py
git commit -m "refactor: extract _base.py from gridtime.py"
```

---

## Task 4: Utwórz `gridtime/parsing.py`

**Files:**
- Create: `gridtime/parsing.py`

- [ ] **Krok 1: Utwórz plik z nagłówkiem importów**

```python
# gridtime/parsing.py
from datetime import datetime, date, time, timedelta
from typing import Union, Literal
import re
import locale

locale.setlocale(locale.LC_TIME, "pl_PL.UTF-8")
```

- [ ] **Krok 2: Przenieś helpery parsowania z `utils.py`**

Przekopiuj verbatim z `gridtime/utils.py`:
- `parse_date` (linie 66–93)
- `is_quarter_aligned` (linie 62–64)
- `_HOUR_REPR_RE` (linie 95–97)
- `_is_hour_repr` (linie 99–101)
- `_parse_hour_repr` (linie 103–138)

- [ ] **Krok 3: Przenieś `parse_hour` z `gridtime.py` z lazy importem**

Przekopiuj `parse_hour` z `gridtime/gridtime.py` (linie 592–709), dodając lazy import jako pierwszą linię ciała funkcji:

```python
def parse_hour(
    hour: Union[int, str],
    date_: Union[str, date, None] = None,
    *,
    convention: Literal["0-23", "1-24"] = "0-23",
    interpret: Literal["as_start", "as_end"] = "as_start",
    backward: bool = False,
) -> "Hour":
    from gridtime.periods import Hour  # lazy import — unika cyklu periods↔parsing
    # reszta ciała funkcji bez zmian (linie 634–709 z gridtime.py)
```

- [ ] **Krok 4: Uruchom testy**

```
pytest tests/ -q
```

Oczekiwany wynik: wszystkie testy PASS.

- [ ] **Krok 5: Commit**

```bash
git add gridtime/parsing.py
git commit -m "refactor: extract parsing.py from utils.py and gridtime.py"
```

---

## Task 5: Utwórz `gridtime/_steps.py`

**Files:**
- Create: `gridtime/_steps.py`

- [ ] **Krok 1: Utwórz plik z nagłówkiem importów**

```python
# gridtime/_steps.py
from datetime import timedelta, date
from gridtime._dst import (
    is_missing_quarter, is_duplicated_quarter,
    is_missing_hour, is_duplicated_hour,
)
```

- [ ] **Krok 2: Przenieś step functions z `gridtime.py` z lazy importami**

Przekopiuj każdą funkcję z `gridtime/gridtime.py` dodając lazy import jako pierwszą linię ciała. Zmodyfikowane sygnatury (ciała bez zmian poza dodaną linią importu):

```python
def quarter_hour_step(obj, steps: int):
    from gridtime.periods import QuarterHour
    # ciało verbatim z linie 21–57 gridtime.py

def hour_step(obj, steps: int):
    from gridtime.periods import Hour
    # ciało verbatim z linie 68–108 gridtime.py

def day_step(obj, steps: int):
    from gridtime.periods import Day
    # ciało verbatim z linie 116–120 gridtime.py

def month_step(obj, steps: int):
    from gridtime.periods import Month
    # ciało verbatim z linie 129–140 gridtime.py

def quarter_step(obj, steps: int):
    from gridtime.periods import Quarter
    # ciało verbatim z linie 147–155 gridtime.py

def year_step(obj, steps: int):
    from gridtime.periods import Year
    # ciało verbatim z linie 161–163 gridtime.py

def week_step(obj, steps: int):
    from gridtime.periods import Week
    # ciało verbatim z linie 169–177 gridtime.py

def season_step(obj, steps: int):
    from gridtime.periods import Season
    # ciało verbatim z linie 185–194 gridtime.py

def month_decade_step(obj, steps: int):
    from gridtime.periods import MonthDecade
    # ciało verbatim z linie 201–214 gridtime.py
```

Zachowaj oryginalne type annotations z `gridtime.py` (np. `obj: "QuarterHour"`, `-> "QuarterHour"`).

- [ ] **Krok 3: Uruchom testy**

```
pytest tests/ -q
```

Oczekiwany wynik: wszystkie testy PASS.

- [ ] **Krok 4: Commit**

```bash
git add gridtime/_steps.py
git commit -m "refactor: extract _steps.py from gridtime.py"
```

---

## Task 6: Utwórz `gridtime/periods.py`

**Files:**
- Create: `gridtime/periods.py`

- [ ] **Krok 1: Utwórz plik z nagłówkiem importów**

```python
# gridtime/periods.py
from datetime import datetime, timedelta, date, time
from typing import Union
from gridtime._registry import register_unit
from gridtime._dst import (
    is_missing_quarter, is_duplicated_quarter,
    is_missing_hour, is_duplicated_hour,
)
from gridtime._base import GridtimeLeaf, GridtimeStructure
from gridtime.parsing import parse_date, _parse_hour_repr, _is_hour_repr
from gridtime._steps import (
    quarter_hour_step, hour_step, day_step, month_step,
    quarter_step, year_step, week_step, season_step, month_decade_step,
)
```

- [ ] **Krok 2: Przenieś klasy z `gridtime.py` — `QuarterHour`**

Przekopiuj `QuarterHour` verbatim (linie 342–367 `gridtime.py`). Brak lazy importów — jest liściem bez dzieci.

- [ ] **Krok 3: Przenieś `Hour` z lazy importem w `_create_children`**

Przekopiuj `Hour` (linie 369–413 `gridtime.py`). Zmodyfikuj wyłącznie metodę `_create_children`:

```python
def _create_children(self) -> list[GridtimeLeaf]:
    from gridtime.factories import create_quarter_hours  # lazy import
    if self.is_duplicated:
        phase = "second" if self.is_backward else "first"
    else:
        phase = "both"
    return create_quarter_hours(self.start_time, phase=phase)
```

- [ ] **Krok 4: Przenieś `Day` z lazy importem w `_create_children`**

Przekopiuj `Day` (linie 415–431 `gridtime.py`). Zmodyfikuj `_create_children`:

```python
def _create_children(self) -> list[GridtimeLeaf]:
    from gridtime.factories import create_hours  # lazy import
    return create_hours(self.date)
```

- [ ] **Krok 5: Przenieś `Month` z lazy importem w `_create_children`**

Przekopiuj `Month` (linie 432–444 `gridtime.py`). Zmodyfikuj `_create_children`:

```python
def _create_children(self) -> list[GridtimeLeaf]:
    from gridtime.factories import create_days  # lazy import
    return create_days(self.year, self.month)
```

- [ ] **Krok 6: Przenieś `Quarter` z lazy importem w `_create_children`**

Przekopiuj `Quarter` (linie 446–460 `gridtime.py`). Zmodyfikuj `_create_children`:

```python
def _create_children(self) -> list[GridtimeLeaf]:
    from gridtime.factories import create_quarter_months  # lazy import
    return create_quarter_months(self.year, self.quarter)
```

- [ ] **Krok 7: Przenieś `Year` z lazy importem w `_create_children`**

Przekopiuj `Year` (linie 462–473 `gridtime.py`). Zmodyfikuj `_create_children`:

```python
def _create_children(self) -> list[GridtimeLeaf]:
    from gridtime.factories import create_quarters  # lazy import
    return create_quarters(self.year, quarters=range(1, 5))
```

- [ ] **Krok 8: Przenieś `Week` z lazy importem w `_create_children`**

Przekopiuj `Week` (linie 475–487 `gridtime.py`). Zmodyfikuj `_create_children`:

```python
def _create_children(self) -> list[GridtimeLeaf]:
    from gridtime.factories import create_week_days  # lazy import
    return create_week_days(self.iso_year, self.iso_week)
```

- [ ] **Krok 9: Przenieś `Season` z lazy importem w `_create_children`**

Przekopiuj `Season` (linie 489–505 `gridtime.py`). Zmodyfikuj `_create_children`:

```python
def _create_children(self) -> list[GridtimeLeaf]:
    from gridtime.factories import create_season_quarters  # lazy import
    return create_season_quarters(self.year, self.type)
```

- [ ] **Krok 10: Przenieś `MonthDecade` z lazy importem w `_create_children`**

Przekopiuj `MonthDecade` (linie 507–528 `gridtime.py`). Zmodyfikuj `_create_children`:

```python
def _create_children(self) -> list[GridtimeLeaf]:
    from gridtime.factories import create_decade_days  # lazy import
    return create_decade_days(self.year, self.month, self.index)
```

- [ ] **Krok 11: Uruchom testy**

```
pytest tests/ -q
```

Oczekiwany wynik: wszystkie testy PASS.

- [ ] **Krok 12: Commit**

```bash
git add gridtime/periods.py
git commit -m "refactor: extract periods.py from gridtime.py"
```

---

## Task 7: Utwórz `gridtime/factories.py`

**Files:**
- Create: `gridtime/factories.py`

- [ ] **Krok 1: Utwórz plik z nagłówkiem importów**

```python
# gridtime/factories.py
from datetime import datetime, date, time, timedelta
from calendar import monthrange
from typing import Union, Optional, List, Literal
from gridtime.periods import (
    QuarterHour, Hour, Day, Month, Quarter, Year, Week, Season, MonthDecade,
)
from gridtime.parsing import parse_date, _is_hour_repr
from gridtime._dst import is_missing_hour, is_duplicated_hour, is_missing_quarter, is_duplicated_quarter
```

- [ ] **Krok 2: Przenieś funkcje z `gridtime.py`**

Przekopiuj verbatim z `gridtime/gridtime.py`:
- `create_days` (linie 531–547)
- `create_months` (linie 549–550)
- `create_quarters` (linie 552–553)
- `create_season_quarters` (linie 555–564)
- `create_week_days` (linie 566–567)
- `create_hours` (linie 569–590)
- `create_quarter_months` (linie 771–773)
- `create_quarter_hours` (linie 775–807)
- `create_decade_days` (linie 809–820)

- [ ] **Krok 3: Uruchom testy**

```
pytest tests/ -q
```

Oczekiwany wynik: wszystkie testy PASS.

- [ ] **Krok 4: Commit**

```bash
git add gridtime/factories.py
git commit -m "refactor: extract factories.py from gridtime.py"
```

---

## Task 8: Utwórz `gridtime/ranges.py`

**Files:**
- Create: `gridtime/ranges.py`

- [ ] **Krok 1: Utwórz plik z nagłówkiem importów**

```python
# gridtime/ranges.py
from datetime import datetime, date, timedelta
from typing import Union, List, Literal
from gridtime.periods import Day, Hour, QuarterHour
from gridtime.factories import create_hours
from gridtime.parsing import parse_date, is_quarter_aligned, parse_hour
```

- [ ] **Krok 2: Przenieś funkcje z `gridtime.py`**

Przekopiuj verbatim z `gridtime/gridtime.py`:
- `create_hour_range` (linie 711–769)
- `create_date_range` (linie 822–889)

- [ ] **Krok 3: Uruchom testy**

```
pytest tests/ -q
```

Oczekiwany wynik: wszystkie testy PASS.

- [ ] **Krok 4: Commit**

```bash
git add gridtime/ranges.py
git commit -m "refactor: extract ranges.py from gridtime.py"
```

---

## Task 9: Utwórz `gridtime/validation.py`

**Files:**
- Create: `gridtime/validation.py`

- [ ] **Krok 1: Utwórz plik z nagłówkiem importów**

```python
# gridtime/validation.py
from gridtime._base import GridtimeLeaf
```

- [ ] **Krok 2: Przenieś funkcję z `gridtime.py`**

Przekopiuj verbatim z `gridtime/gridtime.py`:
- `validate_complete_range` (linie 891–950)

- [ ] **Krok 3: Uruchom testy**

```
pytest tests/ -q
```

Oczekiwany wynik: wszystkie testy PASS.

- [ ] **Krok 4: Commit**

```bash
git add gridtime/validation.py
git commit -m "refactor: extract validation.py from gridtime.py"
```

---

## Task 10: Utwórz `gridtime/pandas.py`

**Files:**
- Create: `gridtime/pandas.py`

- [ ] **Krok 1: Utwórz pusty plik placeholder**

```python
# gridtime/pandas.py
# Dedykowana integracja z pandas — typ kolumny dla jednostek gridtime.
# Moduł w budowie.
```

- [ ] **Krok 2: Commit**

```bash
git add gridtime/pandas.py
git commit -m "refactor: add pandas.py placeholder"
```

---

## Task 11: Zaktualizuj `gridtime/__init__.py`

**Files:**
- Modify: `gridtime/__init__.py`

- [ ] **Krok 1: Zastąp całą zawartość `__init__.py`**

```python
# gridtime/__init__.py
from gridtime.periods import (
    QuarterHour,
    Hour,
    Day,
    Month,
    MonthDecade,
    Quarter,
    Year,
    Week,
    Season,
)
from gridtime.factories import (
    create_hours,
    create_days,
    create_months,
    create_quarters,
    create_quarter_hours,
    create_quarter_months,
    create_season_quarters,
    create_week_days,
    create_decade_days,
)
from gridtime.ranges import create_date_range, create_hour_range
from gridtime.parsing import parse_date, parse_hour, is_quarter_aligned
from gridtime.validation import validate_complete_range
from gridtime._registry import _GRIDTIME_REGISTRY, register_unit, _all_unit_keys, _is_reachable
from gridtime._dst import (
    is_duplicated_hour,
    is_duplicated_quarter,
    is_missing_hour,
    is_missing_quarter,
)

__all__ = [
    "QuarterHour",
    "Hour",
    "Day",
    "Month",
    "Quarter",
    "Year",
    "Week",
    "Season",
    "MonthDecade",
    "create_hours",
    "create_days",
    "create_months",
    "create_quarters",
    "create_quarter_hours",
    "create_quarter_months",
    "create_season_quarters",
    "create_week_days",
    "create_decade_days",
    "create_date_range",
    "create_hour_range",
    "parse_date",
    "parse_hour",
    "is_quarter_aligned",
    "validate_complete_range",
    "register_unit",
    "_GRIDTIME_REGISTRY",
    "_all_unit_keys",
    "_is_reachable",
    "is_duplicated_hour",
    "is_duplicated_quarter",
    "is_missing_hour",
    "is_missing_quarter",
]
```

- [ ] **Krok 2: Uruchom testy — krytyczny checkpoint**

```
pytest tests/ -v
```

Oczekiwany wynik: wszystkie testy PASS. Jeśli któryś nie przechodzi — debuguj przed przejściem dalej (nie usuwaj starych plików).

- [ ] **Krok 3: Commit**

```bash
git add gridtime/__init__.py
git commit -m "refactor: update __init__.py to import from new modules"
```

---

## Task 12: Usuń stare pliki i zweryfikuj

**Files:**
- Delete: `gridtime/gridtime.py`
- Delete: `gridtime/utils.py`

- [ ] **Krok 1: Usuń stare pliki źródłowe**

```bash
rm gridtime/gridtime.py
rm gridtime/utils.py
```

- [ ] **Krok 2: Uruchom pełen zestaw testów — krytyczny checkpoint**

```
pytest tests/ -v
```

Oczekiwany wynik: wszystkie testy PASS. Jeśli cokolwiek nie przechodzi — przywróć pliki (`git checkout gridtime/gridtime.py gridtime/utils.py`) i zdiagnozuj problem.

- [ ] **Krok 3: Commit**

```bash
git add -u
git commit -m "refactor: remove legacy gridtime.py and utils.py"
```

---

## Task 13: Utwórz `tests/test_periods.py`

**Files:**
- Create: `tests/test_periods.py`

- [ ] **Krok 1: Utwórz plik z następującą zawartością**

```python
# tests/test_periods.py
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from datetime import datetime, timedelta, date
import gridtime as gt
from gridtime._dst import is_duplicated_hour, is_duplicated_quarter
```

Następnie przekopiuj verbatim z `tests/test_gridtime.py` następujące funkcje testowe:
- `test_valid_quarter`
- `test_missing_quarter`
- `test_duplicated_hour_true`
- `test_duplicated_hour_false_day_after`
- `test_duplicated_quarter_true`
- `test_duplicated_quarter_false`
- `test_count_hours_in_2025`
- `test_count_hours_in_2024`
- `test_hours_in_october`
- `test_hours_in_march`
- `test_inverse_property` (wraz z dekoratorem `@pytest.mark.parametrize`)
- `test_day_step_basic`
- `test_month_step_cross_years`
- `test_hour_step_duplicate_fall_back`
- `test_hour_step_missing_spring_forward`
- `test_quarter_hour_step_duplicate_and_missing`
- `test_season_alternation`
- `test_quarter_order_in_fall_back_day_walk`

- [ ] **Krok 2: Uruchom tylko nowy plik testów**

```
pytest tests/test_periods.py -v
```

Oczekiwany wynik: wszystkie testy PASS.

- [ ] **Krok 3: Commit**

```bash
git add tests/test_periods.py
git commit -m "refactor: add test_periods.py"
```

---

## Task 14: Utwórz `tests/test_parsing.py`

**Files:**
- Create: `tests/test_parsing.py`

- [ ] **Krok 1: Utwórz plik z następującą zawartością**

```python
# tests/test_parsing.py
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from datetime import datetime, date
import gridtime as gt
from gridtime.parsing import _parse_hour_repr
```

Następnie przekopiuj verbatim z `tests/test_gridtime.py`:
- `test_parse_date_formats` (wraz z `@pytest.mark.parametrize`)
- `test_parse_date_date_passthrough`
- `test_parse_date_datetime_strips_time`
- `test_parse_date_invalid`
- `test_day_from_string` (wraz z `@pytest.mark.parametrize`)
- `test_day_from_date_unchanged`
- `test_parse_hour_repr_normal`
- `test_parse_hour_repr_midnight_crossing`
- `test_parse_hour_repr_dst_roundtrip`
- `test_hour_from_repr_string`
- `test_hour_from_repr_midnight`
- `test_hour_from_repr_dst_roundtrip`
- `test_hour_from_repr_missing_spring_raises`
- `test_parse_hour_repr_mode`
- `test_parse_hour_repr_mode_dst`
- `test_parse_hour_repr_mode_rejects_date_arg`
- `test_parse_hour_number_mode` (wraz z `@pytest.mark.parametrize`)
- `test_parse_hour_string_formats` (wraz z `@pytest.mark.parametrize`)
- `test_parse_hour_requires_date_for_number`
- `test_parse_hour_invalid_combinations` (wraz z `@pytest.mark.parametrize`)
- `test_parse_hour_dst_backward`
- `test_parse_hour_dst_missing_raises`

- [ ] **Krok 2: Uruchom tylko nowy plik testów**

```
pytest tests/test_parsing.py -v
```

Oczekiwany wynik: wszystkie testy PASS.

- [ ] **Krok 3: Commit**

```bash
git add tests/test_parsing.py
git commit -m "refactor: add test_parsing.py"
```

---

## Task 15: Utwórz `tests/test_factories.py`

**Files:**
- Create: `tests/test_factories.py`

- [ ] **Krok 1: Utwórz plik z następującą zawartością**

```python
# tests/test_factories.py
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from datetime import datetime, date
import gridtime as gt
```

Następnie przekopiuj verbatim z `tests/test_gridtime.py`:
- `test_days_in_february_leap_year`
- `test_days_in_february_non_leap_year`
- `test_days_in_january`
- `test_days_in_april`
- `test_days_in_october`
- `test_create_hours_varargs_single`
- `test_create_hours_varargs_multiple`
- `test_create_hours_classic_date_object`
- `test_create_hours_classic_date_string`
- `test_create_hours_classic_dst_spring`
- `test_create_hours_classic_dst_fall`

- [ ] **Krok 2: Uruchom tylko nowy plik testów**

```
pytest tests/test_factories.py -v
```

Oczekiwany wynik: wszystkie testy PASS.

- [ ] **Krok 3: Commit**

```bash
git add tests/test_factories.py
git commit -m "refactor: add test_factories.py"
```

---

## Task 16: Utwórz puste pliki testów dla nowych modułów

**Files:**
- Create: `tests/test_ranges.py`
- Create: `tests/test_validation.py`

- [ ] **Krok 1: Utwórz `tests/test_ranges.py`**

```python
# tests/test_ranges.py
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from datetime import datetime, date
import gridtime as gt
```

- [ ] **Krok 2: Utwórz `tests/test_validation.py`**

```python
# tests/test_validation.py
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
import gridtime as gt
```

- [ ] **Krok 3: Commit**

```bash
git add tests/test_ranges.py tests/test_validation.py
git commit -m "refactor: add empty test_ranges.py and test_validation.py"
```

---

## Task 17: Usuń `tests/test_gridtime.py` i finalna weryfikacja

**Files:**
- Delete: `tests/test_gridtime.py`

- [ ] **Krok 1: Uruchom pełen zestaw testów przed usunięciem**

```
pytest tests/ -v
```

Oczekiwany wynik: wszystkie testy PASS (zarówno stare jak i nowe pliki testów).

- [ ] **Krok 2: Usuń stary plik testów**

```bash
rm tests/test_gridtime.py
```

- [ ] **Krok 3: Uruchom testy po usunięciu — finalna weryfikacja**

```
pytest tests/ -v
```

Oczekiwany wynik: te same testy co poprzednio, wszystkie PASS. Liczba testów musi być identyczna.

- [ ] **Krok 4: Commit końcowy**

```bash
git add -u
git commit -m "refactor: remove legacy test_gridtime.py — reorganizacja struktury plików zakończona"
```
