# Pandas ExtensionArray dla gridtime — Plan Implementacji

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Dodać do `gridtime/pandas.py` pełną integrację z pandas: typy kolumn `HourArray`, `DayArray`, `QuarterHourArray` oraz funkcję `to_gridtime` z obsługą DST.

**Architecture:** Wspólna baza `GridtimeDtype(ExtensionDtype)` + `GridtimeArray(ExtensionArray)`, każda podklasa deklaruje tylko 3 atrybuty. Konwersja przez `to_gridtime(series, dtype, *, timestamp_role, dst_ambiguous)` — opakowuje `pd.to_datetime` i buduje gridtime-obiekty z auto-detekcją DST wg kolejności.

**Tech Stack:** Python 3.11+, pandas ≥ 2.0, numpy, pytest. Brak nowych zależności — gridtime już je ma.

---

## Mapa plików

| Plik | Akcja | Odpowiedzialność |
|------|-------|-----------------|
| `gridtime/pandas.py` | Modify (zastąp placeholder) | `GridtimeDSTWarning`, `GridtimeDtype`, `HourDtype/DayDtype/QuarterHourDtype`, `GridtimeArray`, `HourArray/DayArray/QuarterHourArray`, `to_gridtime` |
| `tests/test_pandas.py` | Create | Wszystkie testy integracji pandas |

---

## Task 1: Dtype infrastructure — `GridtimeDSTWarning`, `GridtimeDtype`, subklasy dtype

**Files:**
- Modify: `gridtime/pandas.py`
- Create: `tests/test_pandas.py`

- [ ] **Step 1: Napisz testy dtype**

```python
# tests/test_pandas.py
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
import pandas as pd
from gridtime.pandas import HourDtype, DayDtype, QuarterHourDtype, GridtimeDSTWarning
from gridtime import Hour, Day, QuarterHour


def test_hour_dtype_name():
    assert HourDtype.name == "gridtime[hour]"

def test_day_dtype_name():
    assert DayDtype.name == "gridtime[day]"

def test_quarter_hour_dtype_name():
    assert QuarterHourDtype.name == "gridtime[quarter_hour]"

def test_hour_dtype_type():
    assert HourDtype.type is Hour

def test_day_dtype_type():
    assert DayDtype.type is Day

def test_quarter_hour_dtype_type():
    assert QuarterHourDtype.type is QuarterHour

def test_dtype_registered_hour():
    dtype = pd.api.types.pandas_dtype("gridtime[hour]")
    assert isinstance(dtype, HourDtype)

def test_dtype_registered_day():
    dtype = pd.api.types.pandas_dtype("gridtime[day]")
    assert isinstance(dtype, DayDtype)

def test_dtype_registered_quarter_hour():
    dtype = pd.api.types.pandas_dtype("gridtime[quarter_hour]")
    assert isinstance(dtype, QuarterHourDtype)

def test_dst_warning_is_user_warning():
    assert issubclass(GridtimeDSTWarning, UserWarning)
```

- [ ] **Step 2: Uruchom testy — muszą failować**

```
pytest tests/test_pandas.py -v
```
Oczekiwane: `ImportError: cannot import name 'HourDtype' from 'gridtime.pandas'`

- [ ] **Step 3: Zaimplementuj dtype infrastructure w `gridtime/pandas.py`**

```python
# gridtime/pandas.py
from __future__ import annotations

import warnings
import numpy as np
import pandas as pd
from pandas.api.extensions import ExtensionDtype, register_extension_dtype

from gridtime.periods import Hour, Day, QuarterHour


class GridtimeDSTWarning(UserWarning):
    pass


class GridtimeDtype(ExtensionDtype):
    kind = "O"
    na_value = pd.NA

    @classmethod
    def construct_from_string(cls, string: str) -> GridtimeDtype:
        if not isinstance(string, str):
            raise TypeError
        if string == cls.name:
            return cls()
        raise TypeError(f"Cannot construct a '{cls.__name__}' from '{string}'")

    def __repr__(self) -> str:
        return self.name


@register_extension_dtype
class HourDtype(GridtimeDtype):
    name = "gridtime[hour]"
    type = Hour

    @classmethod
    def construct_array_type(cls):
        return HourArray


@register_extension_dtype
class DayDtype(GridtimeDtype):
    name = "gridtime[day]"
    type = Day

    @classmethod
    def construct_array_type(cls):
        return DayArray


@register_extension_dtype
class QuarterHourDtype(GridtimeDtype):
    name = "gridtime[quarter_hour]"
    type = QuarterHour

    @classmethod
    def construct_array_type(cls):
        return QuarterHourArray
```

- [ ] **Step 4: Uruchom testy — muszą przechodzić**

```
pytest tests/test_pandas.py -v
```
Oczekiwane: `9 passed` (testy dtype i warning).  
Uwaga: `HourArray`, `DayArray`, `QuarterHourArray` jeszcze nie istnieją — `construct_array_type` zwraca forward reference. Testy dtype nie wywołują tej metody, więc przejdą.

- [ ] **Step 5: Commit**

```bash
git add gridtime/pandas.py tests/test_pandas.py
git commit -m "feat(pandas): dodaj dtype infrastructure — HourDtype, DayDtype, QuarterHourDtype"
```

---

## Task 2: `GridtimeArray` — baza i podklasy

**Files:**
- Modify: `gridtime/pandas.py` — dopisz po dtype definitions
- Modify: `tests/test_pandas.py` — dopisz testy array

- [ ] **Step 1: Napisz testy GridtimeArray**

Dopisz do `tests/test_pandas.py`:

```python
from datetime import datetime, date
from gridtime.pandas import HourArray, DayArray, QuarterHourArray


# --- Helpers ----------------------------------------------------------------

def make_hours():
    return [
        Hour(datetime(2025, 1, 15, 13, 0)),   # 12:00-13:00
        Hour(datetime(2025, 1, 15, 14, 0)),   # 13:00-14:00
    ]

def make_days():
    return [Day(date(2025, 1, 15)), Day(date(2025, 1, 16))]

def make_qhs():
    return [
        QuarterHour(datetime(2025, 1, 15, 12, 0)),
        QuarterHour(datetime(2025, 1, 15, 12, 15)),
    ]


# --- Tworzenie ---------------------------------------------------------------

def test_hour_array_from_list():
    arr = HourArray._from_sequence(make_hours(), dtype=HourDtype())
    assert isinstance(arr, HourArray)
    assert len(arr) == 2

def test_day_array_from_list():
    arr = DayArray._from_sequence(make_days(), dtype=DayDtype())
    assert len(arr) == 2

def test_quarter_hour_array_from_list():
    arr = QuarterHourArray._from_sequence(make_qhs(), dtype=QuarterHourDtype())
    assert len(arr) == 2


# --- dtype ------------------------------------------------------------------

def test_hour_array_dtype():
    arr = HourArray._from_sequence(make_hours(), dtype=HourDtype())
    assert isinstance(arr.dtype, HourDtype)
    assert str(arr.dtype) == "gridtime[hour]"


# --- isna zawsze False ------------------------------------------------------

def test_isna_all_false():
    arr = HourArray._from_sequence(make_hours(), dtype=HourDtype())
    result = arr.isna()
    assert list(result) == [False, False]


# --- Non-nullable: odrzucenie None/NaN --------------------------------------

def test_from_sequence_rejects_none():
    with pytest.raises(ValueError, match="non-nullable"):
        HourArray._from_sequence([make_hours()[0], None], dtype=HourDtype())

def test_from_sequence_rejects_nan():
    import numpy as np
    with pytest.raises(ValueError, match="non-nullable"):
        HourArray._from_sequence([make_hours()[0], np.nan], dtype=HourDtype())


# --- Walidacja typu ---------------------------------------------------------

def test_from_sequence_rejects_wrong_type():
    with pytest.raises(TypeError):
        HourArray._from_sequence([Day(date(2025, 1, 1))], dtype=HourDtype())


# --- __getitem__ ------------------------------------------------------------

def test_getitem_scalar():
    arr = HourArray._from_sequence(make_hours(), dtype=HourDtype())
    assert arr[0] == make_hours()[0]

def test_getitem_slice():
    arr = HourArray._from_sequence(make_hours(), dtype=HourDtype())
    sliced = arr[0:1]
    assert isinstance(sliced, HourArray)
    assert len(sliced) == 1


# --- pd.concat --------------------------------------------------------------

def test_concat_same_type():
    a1 = HourArray._from_sequence(make_hours()[:1], dtype=HourDtype())
    a2 = HourArray._from_sequence(make_hours()[1:], dtype=HourDtype())
    s1 = pd.Series(a1)
    s2 = pd.Series(a2)
    result = pd.concat([s1, s2])
    assert str(result.dtype) == "gridtime[hour]"
    assert len(result) == 2

def test_concat_different_types_raises():
    s_hour = pd.Series(HourArray._from_sequence(make_hours(), dtype=HourDtype()))
    s_day = pd.Series(DayArray._from_sequence(make_days(), dtype=DayDtype()))
    with pytest.raises(TypeError):
        pd.concat([s_hour, s_day])


# --- Series repr zawiera gridtime repr --------------------------------------

def test_series_repr_contains_gridtime_repr():
    arr = HourArray._from_sequence(make_hours(), dtype=HourDtype())
    s = pd.Series(arr)
    r = repr(s)
    assert "2025-01-15 12:00-13:00" in r
    assert "gridtime[hour]" in r
```

- [ ] **Step 2: Uruchom testy — muszą failować**

```
pytest tests/test_pandas.py -k "array or isna or nan or getitem or concat or repr" -v
```
Oczekiwane: `ImportError: cannot import name 'HourArray'`

- [ ] **Step 3: Zaimplementuj `GridtimeArray` i podklasy**

Dopisz do `gridtime/pandas.py` (po dtype definitions):

```python
from pandas.api.extensions import ExtensionArray
from datetime import timedelta


class GridtimeArray(ExtensionArray):
    # --- Podklasy muszą nadpisać te atrybuty --------------------------------
    dtype: GridtimeDtype = None          # instancja dtype (klasa)
    _gridtime_type: type = None          # Hour | Day | QuarterHour
    _default_timestamp_role: str = "start"

    # --- Inicjalizacja ------------------------------------------------------

    def __init__(self, data: np.ndarray) -> None:
        # data: np.ndarray(dtype=object) z gridtime-obiektami
        self._data = data

    # --- Wymagane przez ExtensionArray ABC ----------------------------------

    def __getitem__(self, key):
        result = self._data[key]
        if isinstance(result, np.ndarray):
            return self.__class__(result)
        return result

    def __setitem__(self, key, value):
        if isinstance(value, self.__class__):
            self._data[key] = value._data
        elif isinstance(value, self._gridtime_type):
            self._data[key] = value
        else:
            raise TypeError(
                f"Oczekiwano {self._gridtime_type.__name__}, "
                f"otrzymano {type(value).__name__}"
            )

    def __len__(self) -> int:
        return len(self._data)

    def isna(self) -> np.ndarray:
        return np.zeros(len(self), dtype=bool)

    def take(self, indices, *, allow_fill: bool = False, fill_value=None):
        indices = np.asarray(indices, dtype=np.intp)
        if allow_fill and np.any(indices < 0):
            raise ValueError(
                f"Kolumna {self.dtype.name} jest non-nullable — "
                f"nie można wstawiać wartości NA."
            )
        return self.__class__(self._data.take(indices))

    def copy(self) -> GridtimeArray:
        return self.__class__(self._data.copy())

    @classmethod
    def _concat_same_type(cls, to_concat):
        return cls(np.concatenate([arr._data for arr in to_concat]))

    @classmethod
    def _from_sequence(cls, scalars, *, dtype=None, copy: bool = False):
        result = []
        for s in scalars:
            # Sprawdź NA
            is_na = s is None
            if not is_na:
                try:
                    is_na = bool(pd.isna(s))
                except (TypeError, ValueError):
                    is_na = False
            if is_na:
                raise ValueError(
                    f"GridtimeArray nie obsługuje wartości None/NaN. "
                    f"Kolumna {cls.dtype.name} jest non-nullable."
                )
            # Akceptuj gridtime-obiekt lub pd.Timestamp (konwertuj z domyślami)
            if isinstance(s, cls._gridtime_type):
                result.append(s)
            elif isinstance(s, (pd.Timestamp,)):
                result.append(cls._convert_timestamp(s))
            else:
                raise TypeError(
                    f"Oczekiwano {cls._gridtime_type.__name__} lub pd.Timestamp, "
                    f"otrzymano {type(s).__name__}"
                )
        data = np.array(result, dtype=object)
        return cls(data)

    @classmethod
    def _from_factorized(cls, values, original):
        return cls._from_sequence(values, dtype=original.dtype)

    @classmethod
    def _convert_timestamp(cls, ts: pd.Timestamp):
        raise NotImplementedError(
            f"_convert_timestamp nie jest zaimplementowane dla {cls.__name__}"
        )

    @property
    def nbytes(self) -> int:
        return self._data.nbytes


class HourArray(GridtimeArray):
    dtype = HourDtype()
    _gridtime_type = Hour
    _default_timestamp_role = "start"

    @classmethod
    def _convert_timestamp(cls, ts: pd.Timestamp):
        dt = ts.to_pydatetime().replace(tzinfo=None)
        end_time = dt + timedelta(hours=1)   # timestamp_role="start" default
        return Hour(end_time)


class DayArray(GridtimeArray):
    dtype = DayDtype()
    _gridtime_type = Day
    _default_timestamp_role = "start"

    @classmethod
    def _convert_timestamp(cls, ts: pd.Timestamp):
        return Day(ts.date())


class QuarterHourArray(GridtimeArray):
    dtype = QuarterHourDtype()
    _gridtime_type = QuarterHour
    _default_timestamp_role = "start"

    @classmethod
    def _convert_timestamp(cls, ts: pd.Timestamp):
        dt = ts.to_pydatetime().replace(tzinfo=None)
        return QuarterHour(dt)   # timestamp_role="start" default
```

- [ ] **Step 4: Uruchom testy — muszą przechodzić**

```
pytest tests/test_pandas.py -v
```
Oczekiwane: wszystkie testy z Task 1 i Task 2 przechodzą (`~25 passed`).

- [ ] **Step 5: Commit**

```bash
git add gridtime/pandas.py tests/test_pandas.py
git commit -m "feat(pandas): dodaj GridtimeArray bazę i podklasy HourArray/DayArray/QuarterHourArray"
```

---

## Task 3: `to_gridtime` — podstawowa konwersja (Day, Hour, QuarterHour, bez DST)

**Files:**
- Modify: `gridtime/pandas.py` — dopisz `to_gridtime` i funkcje pomocnicze
- Modify: `tests/test_pandas.py` — dopisz testy konwersji

- [ ] **Step 1: Napisz testy konwersji bez DST**

Dopisz do `tests/test_pandas.py`:

```python
from gridtime.pandas import to_gridtime


# --- Day --------------------------------------------------------------------

def test_to_gridtime_day_from_string():
    s = pd.Series(["2025-01-15", "2025-01-16"])
    result = to_gridtime(s, "gridtime[day]")
    assert str(result.dtype) == "gridtime[day]"
    assert result.iloc[0] == Day(date(2025, 1, 15))
    assert result.iloc[1] == Day(date(2025, 1, 16))

def test_to_gridtime_day_from_timestamps():
    s = pd.Series(pd.to_datetime(["2025-03-01", "2025-03-02"]))
    result = to_gridtime(s, "gridtime[day]")
    assert result.iloc[0] == Day(date(2025, 3, 1))

def test_to_gridtime_day_dtype_instance():
    s = pd.Series(["2025-06-01"])
    result = to_gridtime(s, DayDtype())
    assert isinstance(result.dtype, DayDtype)


# --- Hour, timestamp_role="start" (domyślne) --------------------------------

def test_to_gridtime_hour_start_role():
    # ts=12:00 jako start → Hour(end=13:00), czyli godzina 12:00-13:00
    s = pd.Series(["2025-01-15 12:00", "2025-01-15 13:00"])
    result = to_gridtime(s, "gridtime[hour]")
    assert str(result.dtype) == "gridtime[hour]"
    assert result.iloc[0] == Hour(datetime(2025, 1, 15, 13, 0))
    assert result.iloc[1] == Hour(datetime(2025, 1, 15, 14, 0))

def test_to_gridtime_hour_explicit_start():
    s = pd.Series(["2025-01-15 12:00"])
    result = to_gridtime(s, "gridtime[hour]", timestamp_role="start")
    assert result.iloc[0] == Hour(datetime(2025, 1, 15, 13, 0))


# --- Hour, timestamp_role="end" ---------------------------------------------

def test_to_gridtime_hour_end_role():
    # ts=13:00 jako end → Hour(end=13:00), czyli godzina 12:00-13:00
    s = pd.Series(["2025-01-15 13:00"])
    result = to_gridtime(s, "gridtime[hour]", timestamp_role="end")
    assert result.iloc[0] == Hour(datetime(2025, 1, 15, 13, 0))


# --- QuarterHour ------------------------------------------------------------

def test_to_gridtime_quarter_hour():
    s = pd.Series(["2025-07-10 00:00", "2025-07-10 00:15"])
    result = to_gridtime(s, "gridtime[quarter_hour]")
    assert str(result.dtype) == "gridtime[quarter_hour]"
    assert result.iloc[0] == QuarterHour(datetime(2025, 7, 10, 0, 0))
    assert result.iloc[1] == QuarterHour(datetime(2025, 7, 10, 0, 15))


# --- kwargs → pd.to_datetime ------------------------------------------------

def test_to_gridtime_passes_kwargs_to_datetime():
    s = pd.Series(["15/01/2025"])
    result = to_gridtime(s, "gridtime[day]", dayfirst=True)
    assert result.iloc[0] == Day(date(2025, 1, 15))


# --- astype -----------------------------------------------------------------

def test_astype_hour():
    s = pd.Series(pd.to_datetime(["2025-06-01 08:00", "2025-06-01 09:00"]))
    result = s.astype("gridtime[hour]")
    assert str(result.dtype) == "gridtime[hour]"
    assert result.iloc[0] == Hour(datetime(2025, 6, 1, 9, 0))

def test_astype_day():
    s = pd.Series(pd.to_datetime(["2025-06-01", "2025-06-02"]))
    result = s.astype("gridtime[day]")
    assert str(result.dtype) == "gridtime[day]"
    assert result.iloc[0] == Day(date(2025, 6, 1))
```

- [ ] **Step 2: Uruchom testy — muszą failować**

```
pytest tests/test_pandas.py -k "to_gridtime or astype" -v
```
Oczekiwane: `ImportError: cannot import name 'to_gridtime'`

- [ ] **Step 3: Zaimplementuj `to_gridtime` i funkcje pomocnicze**

Dopisz do `gridtime/pandas.py` (po klasach array, przed `__all__`):

```python
from gridtime._dst import is_missing_hour, is_missing_quarter
from gridtime._dst import is_duplicated_hour, is_duplicated_quarter
from datetime import datetime


def _resolve_array_class(dtype) -> type:
    """Zamienia dtype string/instancję/klasę na klasę GridtimeArray."""
    if isinstance(dtype, str):
        dtype = pd.api.types.pandas_dtype(dtype)
    if isinstance(dtype, type) and issubclass(dtype, GridtimeArray):
        return dtype
    if isinstance(dtype, GridtimeDtype):
        return dtype.construct_array_type()
    raise TypeError(f"Nieobsługiwany dtype: {dtype!r}")


def _ts_to_naive_dt(ts: pd.Timestamp) -> datetime:
    """Zamienia pd.Timestamp na naive datetime (bez strefy czasowej)."""
    return ts.to_pydatetime().replace(tzinfo=None)


def _build_day_objects(timestamps) -> list:
    return [Day(ts.date()) for ts in timestamps]


def _build_hour_objects(timestamps, timestamp_role: str, dst_ambiguous) -> list:
    """Buduje listę Hour-obiektów z obsługą DST."""
    # Oblicz start_time i end_time dla każdego timestamp
    pairs = []
    for ts in timestamps:
        dt = _ts_to_naive_dt(ts)
        if timestamp_role == "start":
            start_time = dt
            end_time = dt + timedelta(hours=1)
        else:  # "end"
            end_time = dt
            start_time = dt - timedelta(hours=1)
        pairs.append((start_time, end_time))

    # Sprawdź brakujące godziny DST (marzec) → ValueError
    missing = [end for start, end in pairs if is_missing_hour(start)]
    if missing:
        formatted = ", ".join(str(dt) for dt in missing)
        raise ValueError(
            f"Następujące timestamps nie istnieją z powodu zmiany czasu (DST):\n"
            f"  {formatted}\n"
            f"Usuń lub popraw te wartości przed konwersją."
        )

    # Buduj obiekty z obsługą DST
    if dst_ambiguous in ("first", "second"):
        is_backward = dst_ambiguous == "second"
        return [
            Hour(end, is_backward=is_backward) if is_duplicated_hour(start) else Hour(end)
            for start, end in pairs
        ]

    # dst_ambiguous=None → auto-detect na podstawie kolejności
    seen_dst: dict[datetime, int] = {}
    objects = []
    for start, end in pairs:
        if is_duplicated_hour(start):
            count = seen_dst.get(start, 0)
            if count >= 2:
                raise ValueError(
                    f"Timestamp DST {start} pojawia się więcej niż 2 razy w serii."
                )
            objects.append(Hour(end, is_backward=(count == 1)))
            seen_dst[start] = count + 1
        else:
            objects.append(Hour(end))

    # Ostrzeż o pojedynczych wystąpieniach (niekompletne dane)
    single = [str(st) for st, count in seen_dst.items() if count == 1]
    if single:
        warnings.warn(
            f"Nie można wywnioskować kolejności dla timestampów DST\n"
            f"({', '.join(single)}). Dane zawierają tylko jedno wystąpienie "
            f"duplikowanej godziny.\n"
            f"Wybrano domyślnie 'first'. Podaj dst_ambiguous='first' lub 'second'\n"
            f"aby jawnie wskazać które to wystąpienie i wyciszyć to ostrzeżenie.",
            GridtimeDSTWarning,
            stacklevel=4,
        )
    return objects


def _build_quarter_hour_objects(timestamps, timestamp_role: str, dst_ambiguous) -> list:
    """Buduje listę QuarterHour-obiektów z obsługą DST."""
    start_times = []
    for ts in timestamps:
        dt = _ts_to_naive_dt(ts)
        # QuarterHour constructor przyjmuje start_time
        if timestamp_role == "start":
            start_times.append(dt)
        else:  # "end"
            start_times.append(dt - timedelta(minutes=15))

    # Sprawdź brakujące kwadranse (marzec)
    missing = [st for st in start_times if is_missing_quarter(st)]
    if missing:
        formatted = ", ".join(str(dt) for dt in missing)
        raise ValueError(
            f"Następujące timestamps nie istnieją z powodu zmiany czasu (DST):\n"
            f"  {formatted}\n"
            f"Usuń lub popraw te wartości przed konwersją."
        )

    if dst_ambiguous in ("first", "second"):
        is_backward = dst_ambiguous == "second"
        return [
            QuarterHour(st, is_backward=is_backward) if is_duplicated_quarter(st) else QuarterHour(st)
            for st in start_times
        ]

    # Auto-detect
    seen_dst: dict[datetime, int] = {}
    objects = []
    for st in start_times:
        if is_duplicated_quarter(st):
            count = seen_dst.get(st, 0)
            if count >= 2:
                raise ValueError(
                    f"Timestamp DST {st} pojawia się więcej niż 2 razy w serii."
                )
            objects.append(QuarterHour(st, is_backward=(count == 1)))
            seen_dst[st] = count + 1
        else:
            objects.append(QuarterHour(st))

    single = [str(st) for st, count in seen_dst.items() if count == 1]
    if single:
        warnings.warn(
            f"Nie można wywnioskować kolejności dla timestampów DST\n"
            f"({', '.join(single)}). Dane zawierają tylko jedno wystąpienie "
            f"duplikowanej kwadransa.\n"
            f"Wybrano domyślnie 'first'. Podaj dst_ambiguous='first' lub 'second'\n"
            f"aby jawnie wskazać które to wystąpienie i wyciszyć to ostrzeżenie.",
            GridtimeDSTWarning,
            stacklevel=4,
        )
    return objects


def to_gridtime(
    series,
    dtype,
    *,
    timestamp_role: str = "start",
    dst_ambiguous=None,
    **kwargs,
) -> pd.Series:
    """Konwertuje pandas Series na Series z kolumną gridtime.

    Args:
        series: Wejściowe dane (stringi, daty, pd.Timestamp, datetime64).
        dtype:  Docelowy typ gridtime: "gridtime[hour]" | "gridtime[day]" |
                "gridtime[quarter_hour]" | instancja dtype | klasa Array.
        timestamp_role: "start" (domyślne) lub "end" — jak interpretować
                        timestamp dla Hour i QuarterHour.
        dst_ambiguous:  None (auto-detect wg kolejności) | "first" | "second".
        **kwargs:       Przekazywane do pd.to_datetime().
    """
    array_class = _resolve_array_class(dtype)
    timestamps = pd.to_datetime(series, **kwargs)

    gt_type = array_class._gridtime_type

    if gt_type is Day:
        objects = _build_day_objects(timestamps)
    elif gt_type is Hour:
        objects = _build_hour_objects(timestamps, timestamp_role, dst_ambiguous)
    elif gt_type is QuarterHour:
        objects = _build_quarter_hour_objects(timestamps, timestamp_role, dst_ambiguous)
    else:
        raise TypeError(f"Nieobsługiwany typ gridtime: {gt_type}")

    data = np.array(objects, dtype=object)
    return pd.Series(array_class(data))
```

- [ ] **Step 4: Uruchom testy — muszą przechodzić**

```
pytest tests/test_pandas.py -v
```
Oczekiwane: wszystkie testy do tej pory przechodzą (`~38 passed`).

- [ ] **Step 5: Commit**

```bash
git add gridtime/pandas.py tests/test_pandas.py
git commit -m "feat(pandas): dodaj to_gridtime — konwersja Day, Hour, QuarterHour"
```

---

## Task 4: DST — brakująca godzina marca (`ValueError`)

**Files:**
- Modify: `tests/test_pandas.py`

Logika brakujących godzin jest już zaimplementowana w `_build_hour_objects` i `_build_quarter_hour_objects`. Ten task weryfikuje ją testami.

- [ ] **Step 1: Napisz testy brakujących godzin DST**

Dopisz do `tests/test_pandas.py`:

```python
# --- DST: brakująca godzina (marzec 2025-03-30) ----------------------------

def test_missing_hour_raises_value_error():
    # 30 marca 2025 godzina 02:00 nie istnieje (zmiana na czas letni)
    s = pd.Series(["2025-03-30 01:00", "2025-03-30 02:00", "2025-03-30 03:00"])
    with pytest.raises(ValueError, match="nie istnieją z powodu zmiany czasu"):
        to_gridtime(s, "gridtime[hour]")

def test_missing_hour_error_lists_timestamp():
    s = pd.Series(["2025-03-30 02:00"])
    with pytest.raises(ValueError, match="2025-03-30"):
        to_gridtime(s, "gridtime[hour]")

def test_missing_quarter_raises_value_error():
    # 30 marca 2025 kwadranse 02:00-02:15, 02:15-02:30 itd. nie istnieją
    s = pd.Series(["2025-03-30 01:45", "2025-03-30 02:00"])
    with pytest.raises(ValueError, match="nie istnieją z powodu zmiany czasu"):
        to_gridtime(s, "gridtime[quarter_hour]")

def test_valid_hours_around_spring_dst_ok():
    # Godziny tuż przed i po luce DST są prawidłowe
    s = pd.Series(["2025-03-30 01:00", "2025-03-30 03:00"])
    result = to_gridtime(s, "gridtime[hour]")
    assert len(result) == 2
```

- [ ] **Step 2: Uruchom testy — muszą przechodzić**

```
pytest tests/test_pandas.py -k "missing" -v
```
Oczekiwane: `4 passed` (logika jest już w `_build_hour_objects` z Task 3).

- [ ] **Step 3: Commit**

```bash
git add tests/test_pandas.py
git commit -m "test(pandas): testy DST brakującej godziny marca"
```

---

## Task 5: DST — duplikowana godzina (auto-detect i jawne `first`/`second`)

**Files:**
- Modify: `tests/test_pandas.py`

Logika auto-detect i jawnych trybów jest już w `_build_hour_objects` i `_build_quarter_hour_objects`. Ten task weryfikuje ją testami.

- [ ] **Step 1: Napisz testy DST duplikowanej godziny**

Dopisz do `tests/test_pandas.py`:

```python
# --- DST: duplikowana godzina (październik 2025-10-26) ----------------------

DST_DAY = "2025-10-26"  # ostatnia niedziela października 2025


def test_complete_dst_hours_no_warning():
    # Dwa wystąpienia 02:00 → auto-detect, brak ostrzeżeń
    s = pd.Series([
        f"{DST_DAY} 01:00",
        f"{DST_DAY} 02:00",   # ← pierwsze → ↑1st
        f"{DST_DAY} 02:00",   # ← drugie  → ↓2nd
        f"{DST_DAY} 03:00",
    ])
    import warnings as _warnings
    with _warnings.catch_warnings():
        _warnings.simplefilter("error", GridtimeDSTWarning)
        result = to_gridtime(s, "gridtime[hour]")

    assert str(result.dtype) == "gridtime[hour]"
    h1st = result.iloc[1]
    h2nd = result.iloc[2]
    assert h1st.is_duplicated is True
    assert h1st.is_backward is False    # ↑1st
    assert h2nd.is_duplicated is True
    assert h2nd.is_backward is True     # ↓2nd


def test_incomplete_dst_hour_warns():
    # Jedno wystąpienie 02:00 → GridtimeDSTWarning
    s = pd.Series([f"{DST_DAY} 01:00", f"{DST_DAY} 02:00", f"{DST_DAY} 03:00"])
    with pytest.warns(GridtimeDSTWarning, match="jedno wystąpienie"):
        result = to_gridtime(s, "gridtime[hour]")
    # Domyślnie wybiera ↑1st
    assert result.iloc[1].is_backward is False


def test_dst_explicit_first_no_warning():
    s = pd.Series([f"{DST_DAY} 01:00", f"{DST_DAY} 02:00", f"{DST_DAY} 03:00"])
    import warnings as _warnings
    with _warnings.catch_warnings():
        _warnings.simplefilter("error", GridtimeDSTWarning)
        result = to_gridtime(s, "gridtime[hour]", dst_ambiguous="first")
    assert result.iloc[1].is_backward is False   # ↑1st


def test_dst_explicit_second_no_warning():
    s = pd.Series([f"{DST_DAY} 01:00", f"{DST_DAY} 02:00", f"{DST_DAY} 03:00"])
    import warnings as _warnings
    with _warnings.catch_warnings():
        _warnings.simplefilter("error", GridtimeDSTWarning)
        result = to_gridtime(s, "gridtime[hour]", dst_ambiguous="second")
    assert result.iloc[1].is_backward is True    # ↓2nd


# --- DST: kwadranse ---------------------------------------------------------

def test_complete_dst_quarter_hours_no_warning():
    # 8 kwadransów (4×↑1st + 4×↓2nd) → auto-detect, brak ostrzeżeń
    s = pd.Series([
        f"{DST_DAY} 01:45",
        f"{DST_DAY} 02:00",   # ← pierwsze 02:00 → ↑1st
        f"{DST_DAY} 02:15",   # ← pierwsze 02:15 → ↑1st
        f"{DST_DAY} 02:30",   # ← pierwsze 02:30 → ↑1st
        f"{DST_DAY} 02:45",   # ← pierwsze 02:45 → ↑1st
        f"{DST_DAY} 02:00",   # ← drugie 02:00  → ↓2nd
        f"{DST_DAY} 02:15",   # ← drugie 02:15  → ↓2nd
        f"{DST_DAY} 02:30",   # ← drugie 02:30  → ↓2nd
        f"{DST_DAY} 02:45",   # ← drugie 02:45  → ↓2nd
        f"{DST_DAY} 03:00",
    ])
    import warnings as _warnings
    with _warnings.catch_warnings():
        _warnings.simplefilter("error", GridtimeDSTWarning)
        result = to_gridtime(s, "gridtime[quarter_hour]")

    assert str(result.dtype) == "gridtime[quarter_hour]"
    assert result.iloc[1].is_backward is False   # ↑1st
    assert result.iloc[4].is_backward is False   # ↑1st (02:45)
    assert result.iloc[5].is_backward is True    # ↓2nd (02:00)
    assert result.iloc[8].is_backward is True    # ↓2nd (02:45)


def test_incomplete_dst_quarter_warns():
    s = pd.Series([f"{DST_DAY} 02:00"])
    with pytest.warns(GridtimeDSTWarning):
        result = to_gridtime(s, "gridtime[quarter_hour]")
    assert result.iloc[0].is_backward is False


def test_three_occurrences_dst_raises():
    s = pd.Series([
        f"{DST_DAY} 02:00",
        f"{DST_DAY} 02:00",
        f"{DST_DAY} 02:00",   # trzecie wystąpienie → błąd
    ])
    with pytest.raises(ValueError, match="więcej niż 2 razy"):
        to_gridtime(s, "gridtime[hour]")
```

- [ ] **Step 2: Uruchom testy — muszą przechodzić**

```
pytest tests/test_pandas.py -k "dst" -v
```
Oczekiwane: `~11 passed`.

- [ ] **Step 3: Commit**

```bash
git add tests/test_pandas.py
git commit -m "test(pandas): testy DST duplikowanej godziny — auto-detect i first/second"
```

---

## Task 6: Eksport publiczny i pełny przebieg testów

**Files:**
- Modify: `gridtime/pandas.py` — dodaj `__all__`
- Modify: `tests/test_pandas.py` — finalny smoke test

- [ ] **Step 1: Napisz smoke test integracyjny**

Dopisz do `tests/test_pandas.py`:

```python
# --- Smoke test: pełny DataFrame workflow -----------------------------------

def test_full_dataframe_workflow():
    """Symuluje wczytanie danych z CSV i konwersję na gridtime."""
    df = pd.DataFrame({
        "ts": ["2025-01-15 08:00", "2025-01-15 09:00", "2025-01-15 10:00"],
        "value": [100.0, 110.0, 95.0],
    })
    df["hour"] = to_gridtime(df["ts"], "gridtime[hour]")
    df["day"] = to_gridtime(df["ts"], "gridtime[day]")

    assert str(df["hour"].dtype) == "gridtime[hour]"
    assert str(df["day"].dtype) == "gridtime[day]"
    assert df["hour"].iloc[0] == Hour(datetime(2025, 1, 15, 9, 0))
    assert df["day"].iloc[0] == Day(date(2025, 1, 15))
    # dtypes w DataFrame
    assert "gridtime[hour]" in str(df.dtypes["hour"])
    assert "gridtime[day]" in str(df.dtypes["day"])
```

- [ ] **Step 2: Uruchom — musi przechodzić**

```
pytest tests/test_pandas.py -k "workflow" -v
```
Oczekiwane: `1 passed`.

- [ ] **Step 3: Dodaj `__all__` do `gridtime/pandas.py`**

Dopisz na końcu pliku:

```python
__all__ = [
    "GridtimeDSTWarning",
    "HourDtype",
    "DayDtype",
    "QuarterHourDtype",
    "HourArray",
    "DayArray",
    "QuarterHourArray",
    "to_gridtime",
]
```

- [ ] **Step 4: Uruchom pełną suite testów**

```
pytest tests/test_pandas.py -v
```
Oczekiwane: wszystkie testy przechodzą. Sprawdź też że reszta projektu nie jest zepsuta:
```
pytest tests/ -v
```
Oczekiwane: wszystkie testy przechodzą.

- [ ] **Step 5: Commit finalny**

```bash
git add gridtime/pandas.py tests/test_pandas.py
git commit -m "feat(pandas): dodaj __all__ i smoke test — integracja pandas kompletna"
```

---

## Self-Review

### 1. Pokrycie specyfikacji

| Wymaganie ze specyfikacji | Task |
|--------------------------|------|
| `HourDtype`, `DayDtype`, `QuarterHourDtype` z `@register_extension_dtype` | Task 1 |
| `pd.api.types.pandas_dtype("gridtime[hour]")` działa | Task 1 |
| `GridtimeArray` non-nullable — `isna()` zawsze False | Task 2 |
| `_from_sequence` rzuca ValueError przy None/NaN | Task 2 |
| `pd.concat` zachowuje dtype, różne typy → TypeError | Task 2 |
| `__repr__` pokazuje gridtime repr | Task 2 |
| `to_gridtime` — Day, Hour (start/end), QuarterHour | Task 3 |
| `astype("gridtime[hour]")` | Task 3 |
| `**kwargs` do `pd.to_datetime` | Task 3 |
| Brakująca godzina marca → `ValueError` | Task 4 |
| Duplikowana godzina — auto-detect bez ostrzeżeń (kompletne dane) | Task 5 |
| Duplikowana godzina — ostrzeżenie dla niekompletnych danych | Task 5 |
| `dst_ambiguous="first"` / `"second"` — jawne, bez ostrzeżeń | Task 5 |
| Kwadranse DST — auto-detect | Task 5 |
| `__all__` eksport publiczny | Task 6 |

### 2. Spójność typów i nazw

- `_build_hour_objects` i `_build_quarter_hour_objects` używają `GridtimeDSTWarning` zdefiniowanego w Task 1 ✓
- `_resolve_array_class` używa `GridtimeArray` i `GridtimeDtype` zdefiniowanych w Task 2 i Task 1 ✓
- Testy importują `to_gridtime`, `HourArray`, `DayArray`, `QuarterHourArray` z `gridtime.pandas` — wszystkie zdefiniowane ✓
- `Hour(end_time, is_backward=...)` — zgodne z konstruktorem w `periods.py` ✓
- `QuarterHour(start_time, is_backward=...)` — zgodne z konstruktorem w `periods.py` ✓
- `is_duplicated_hour`, `is_missing_hour` z `gridtime._dst` ✓

### 3. Brak placeholderów

Każdy step zawiera kompletny kod. Brak TBD/TODO. ✓
