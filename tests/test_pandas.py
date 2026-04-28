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

def test_concat_same_type_preserves_dtype():
    """Same-type concat zachowuje dtype gridtime."""
    a1 = HourArray._from_sequence(make_hours()[:1], dtype=HourDtype())
    a2 = HourArray._from_sequence(make_hours()[1:], dtype=HourDtype())
    result = pd.concat([pd.Series(a1), pd.Series(a2)])
    assert str(result.dtype) == "gridtime[hour]"
    assert len(result) == 2


# --- Series repr zawiera gridtime repr --------------------------------------

def test_series_repr_contains_gridtime_repr():
    arr = HourArray._from_sequence(make_hours(), dtype=HourDtype())
    s = pd.Series(arr)
    r = repr(s)
    assert "2025-01-15 12:00-13:00" in r
    assert "gridtime[hour]" in r


# --- pd.NA odrzucone -------------------------------------------------------

def test_from_sequence_rejects_pd_na():
    with pytest.raises(ValueError, match="non-nullable"):
        HourArray._from_sequence([make_hours()[0], pd.NA], dtype=HourDtype())


# --- take z allow_fill=True i ujemnym indeksem ----------------------------

def test_take_allow_fill_negative_raises():
    arr = HourArray._from_sequence(make_hours(), dtype=HourDtype())
    with pytest.raises(ValueError, match="non-nullable"):
        arr.take([-1], allow_fill=True)

def test_take_positive_indices():
    arr = HourArray._from_sequence(make_hours(), dtype=HourDtype())
    result = arr.take([1, 0])
    assert len(result) == 2
    assert result[0] == make_hours()[1]


# --- copy -------------------------------------------------------------------

def test_copy_returns_new_instance():
    arr = HourArray._from_sequence(make_hours(), dtype=HourDtype())
    arr_copy = arr.copy()
    assert isinstance(arr_copy, HourArray)
    assert arr_copy[0] == arr[0]
    assert arr_copy._data is not arr._data


# --- nbytes -----------------------------------------------------------------

def test_nbytes_positive():
    arr = HourArray._from_sequence(make_hours(), dtype=HourDtype())
    assert arr.nbytes > 0


# --- _from_sequence z pd.Timestamp ------------------------------------------

def test_from_sequence_accepts_timestamp_for_hour():
    ts = pd.Timestamp("2025-01-15 12:00")
    arr = HourArray._from_sequence([ts], dtype=HourDtype())
    # timestamp_role="start" → Hour(end=13:00)
    assert arr[0] == Hour(datetime(2025, 1, 15, 13, 0))

def test_from_sequence_accepts_timestamp_for_day():
    ts = pd.Timestamp("2025-01-15")
    arr = DayArray._from_sequence([ts], dtype=DayDtype())
    assert arr[0] == Day(date(2025, 1, 15))

def test_from_sequence_accepts_timestamp_for_quarter_hour():
    ts = pd.Timestamp("2025-01-15 12:00")
    arr = QuarterHourArray._from_sequence([ts], dtype=QuarterHourDtype())
    assert arr[0] == QuarterHour(datetime(2025, 1, 15, 12, 0))


# --- isna dla DayArray i QuarterHourArray -----------------------------------

def test_isna_day_all_false():
    arr = DayArray._from_sequence(make_days(), dtype=DayDtype())
    assert list(arr.isna()) == [False, False]

def test_isna_qh_all_false():
    arr = QuarterHourArray._from_sequence(make_qhs(), dtype=QuarterHourDtype())
    assert list(arr.isna()) == [False, False]


# --- Series repr dla DayArray i QuarterHourArray ----------------------------

def test_series_repr_day():
    arr = DayArray._from_sequence(make_days(), dtype=DayDtype())
    s = pd.Series(arr)
    r = repr(s)
    assert "2025-01-15" in r
    assert "gridtime[day]" in r

def test_series_repr_quarter_hour():
    arr = QuarterHourArray._from_sequence(make_qhs(), dtype=QuarterHourDtype())
    s = pd.Series(arr)
    r = repr(s)
    assert "2025-01-15 12:00-12:15" in r
    assert "gridtime[quarter_hour]" in r


# --- __setitem__ NA i pd.NaT -----------------------------------------------

def test_from_sequence_rejects_nat():
    with pytest.raises(ValueError, match="non-nullable"):
        HourArray._from_sequence([make_hours()[0], pd.NaT], dtype=HourDtype())

def test_setitem_rejects_none():
    arr = HourArray._from_sequence(make_hours(), dtype=HourDtype())
    with pytest.raises(ValueError, match="non-nullable"):
        arr[0] = None


# ===========================================================================
# Task 3: to_gridtime
# ===========================================================================

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
