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
