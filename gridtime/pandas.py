# gridtime/pandas.py
from __future__ import annotations

import warnings
import numpy as np
import pandas as pd
from pandas.api.extensions import ExtensionDtype, ExtensionArray, register_extension_dtype
from datetime import timedelta

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
        # HourArray jest zdefiniowane poniżej w tym samym pliku — forward reference.
        # Ta metoda jest wywoływana dopiero w runtime, więc NameError nie wystąpi.
        return HourArray


@register_extension_dtype
class DayDtype(GridtimeDtype):
    name = "gridtime[day]"
    type = Day

    @classmethod
    def construct_array_type(cls):
        # DayArray jest zdefiniowane poniżej w tym samym pliku — forward reference.
        # Ta metoda jest wywoływana dopiero w runtime, więc NameError nie wystąpi.
        return DayArray


@register_extension_dtype
class QuarterHourDtype(GridtimeDtype):
    name = "gridtime[quarter_hour]"
    type = QuarterHour

    @classmethod
    def construct_array_type(cls):
        # QuarterHourArray jest zdefiniowane poniżej w tym samym pliku — forward reference.
        # Ta metoda jest wywoływana dopiero w runtime, więc NameError nie wystąpi.
        return QuarterHourArray


class GridtimeArray(ExtensionArray):
    # --- Podklasy muszą nadpisać te atrybuty --------------------------------
    dtype: GridtimeDtype = None
    _gridtime_type: type = None
    _default_timestamp_role: str = "start"

    def __init__(self, data: np.ndarray) -> None:
        self._data = data

    def __getitem__(self, key):
        result = self._data[key]
        if isinstance(result, np.ndarray):
            return self.__class__(result)
        return result

    def __setitem__(self, key, value):
        # Sprawdź NA przed typem — kolumna jest non-nullable
        is_na = value is None
        if not is_na:
            try:
                is_na = bool(pd.isna(value))
            except (TypeError, ValueError):
                is_na = False
        if is_na:
            raise ValueError(
                f"Kolumna {self.dtype.name} jest non-nullable — "
                f"nie można wstawiać wartości NA."
            )
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

    def copy(self) -> "GridtimeArray":
        return self.__class__(self._data.copy())

    @classmethod
    def _concat_same_type(cls, to_concat):
        return cls(np.concatenate([arr._data for arr in to_concat]))

    @classmethod
    def _from_sequence(cls, scalars, *, dtype=None, copy: bool = False):
        result = []
        for s in scalars:
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
            if isinstance(s, cls._gridtime_type):
                result.append(s)
            elif isinstance(s, pd.Timestamp):
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
        end_time = dt + timedelta(hours=1)
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
        return QuarterHour(dt)


# ===========================================================================
# to_gridtime — konwersja pandas Series na Series z typem gridtime
# ===========================================================================

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
    missing = [start for start, end in pairs if is_missing_hour(start)]
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
            f"duplikowanego kwadransa.\n"
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
