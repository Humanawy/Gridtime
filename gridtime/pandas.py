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


from pandas.api.extensions import ExtensionArray
from datetime import timedelta


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

    def astype(self, dtype, copy: bool = True):
        from pandas.api.types import pandas_dtype as _pandas_dtype
        dtype = _pandas_dtype(dtype)
        if dtype == self.dtype:
            return self.copy() if copy else self
        if isinstance(dtype, GridtimeDtype):
            raise TypeError(
                f"Nie można konwertować {self.dtype.name} na {dtype.name}. "
                f"Typy gridtime nie są kompatybilne."
            )
        if dtype == np.dtype("object"):
            raise TypeError(
                f"Nie można konwertować {self.dtype.name} na dtype object. "
                f"Użyj pd.concat tylko z seriami tego samego typu gridtime."
            )
        return super().astype(dtype, copy=copy)

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
