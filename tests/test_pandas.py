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

def test_construct_from_string_wrong_name():
    with pytest.raises(TypeError):
        HourDtype.construct_from_string("gridtime[day]")

def test_construct_from_string_non_string():
    with pytest.raises(TypeError):
        HourDtype.construct_from_string(123)

def test_hour_dtype_repr():
    assert repr(HourDtype()) == "gridtime[hour]"

def test_day_dtype_repr():
    assert repr(DayDtype()) == "gridtime[day]"

def test_quarter_hour_dtype_repr():
    assert repr(QuarterHourDtype()) == "gridtime[quarter_hour]"


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
