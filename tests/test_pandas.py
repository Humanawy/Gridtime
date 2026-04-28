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
