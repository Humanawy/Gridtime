import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

import warnings
import pandas as pd
from gridtime import Hour
from gridtime.pandas import to_gridtime, HourArray, GridtimeDSTWarning


# ===========================================================================
# Scenariusz 1 — timestamp jako POCZĄTEK godziny (timestamp_role="start")
# CSV/baza zwraca "12:00" = początek godziny 12:00-13:00
# ===========================================================================

df = pd.DataFrame({
    "timestamp": ["2025-01-15 12:00", "2025-01-15 13:00", "2025-01-15 14:00"],
    "produkcja_mw": [423.5, 418.0, 431.2],
})

df["hour"] = to_gridtime(df["timestamp"], "gridtime[hour]")

print("=== Scenariusz 1: timestamp_role='start' (domyślne) ===")
print(df[["timestamp", "hour"]])
print(df.dtypes)


# ===========================================================================
# Scenariusz 2 — timestamp jako KONIEC godziny (timestamp_role="end")
# System SCADA zapisuje "13:00" = koniec godziny 12:00-13:00
# ===========================================================================

df2 = pd.DataFrame({
    "ts": ["2025-01-15 13:00", "2025-01-15 14:00"],
    "cena": [280.5, 275.0],
})

df2["hour"] = to_gridtime(df2["ts"], "gridtime[hour]", timestamp_role="end")

print("\n=== Scenariusz 2: timestamp_role='end' ===")
print(df2[["ts", "hour"]])


# ===========================================================================
# Scenariusz 3 — istniejąca kolumna datetime64 -> DayArray
# ===========================================================================

df3 = pd.DataFrame({
    "date": pd.to_datetime(["2025-03-01", "2025-03-02", "2025-03-03"]),
    "wolumen": [1200, 1350, 1100],
})

df3["day"] = to_gridtime(df3["date"], "gridtime[day]")

print("\n=== Scenariusz 3: datetime64 -> gridtime[day] ===")
print(df3)
print(df3.dtypes)


# ===========================================================================
# Scenariusz 4 — dane kwadransowe z rozdzielczością 15 min
# ===========================================================================

df4 = pd.DataFrame({
    "ts": ["2025-07-10 00:00", "2025-07-10 00:15", "2025-07-10 00:30", "2025-07-10 00:45"],
    "moc_mw": [312.0, 318.5, 321.0, 315.5],
})

df4["qh"] = to_gridtime(df4["ts"], "gridtime[quarter_hour]")

print("\n=== Scenariusz 4: dane kwadransowe ===")
print(df4[["ts", "qh"]])
print(df4.dtypes)


# ===========================================================================
# Scenariusz 5 — kompletne dane DST (dwa wystąpienia 02:00)
# Domyślny dst_ambiguous=None -> auto-detect wg kolejności, brak ostrzeżeń
# ===========================================================================

df5 = pd.DataFrame({
    "ts": [
        "2025-10-26 01:00",
        "2025-10-26 02:00",   # pierwsze -> ↑1st
        "2025-10-26 02:00",   # drugie  -> ↓2nd
        "2025-10-26 03:00",
    ],
    "cena": [210.0, 195.0, 198.0, 205.0],
})

with warnings.catch_warnings():
    warnings.simplefilter("error", GridtimeDSTWarning)
    df5["hour"] = to_gridtime(df5["ts"], "gridtime[hour]")

print("\n=== Scenariusz 5: kompletne dane DST (brak ostrzeżeń) ===")
print(df5[["ts", "hour"]])


# ===========================================================================
# Scenariusz 6 — niekompletne dane DST (jedno wystąpienie 02:00)
# dst_ambiguous=None -> GridtimeDSTWarning, domyślnie ↑1st
# ===========================================================================

df6 = pd.DataFrame({
    "ts": ["2025-10-26 01:00", "2025-10-26 02:00", "2025-10-26 03:00"],
    "cena": [210.0, 195.0, 205.0],
})

print("\n=== Scenariusz 6: niekompletne dane DST -> ostrzeżenie ===")
with warnings.catch_warnings(record=True) as caught:
    warnings.simplefilter("always", GridtimeDSTWarning)
    df6["hour"] = to_gridtime(df6["ts"], "gridtime[hour]")

print(df6[["ts", "hour"]])
if caught:
    print(f"Ostrzeżenie: {caught[0].message}")


# ===========================================================================
# Scenariusz 7 — jawne dst_ambiguous="second", brak ostrzeżeń
# ===========================================================================

df7 = df6.copy()
df7["hour"] = to_gridtime(df7["ts"], "gridtime[hour]", dst_ambiguous="second")

print("\n=== Scenariusz 7: dst_ambiguous='second' (brak ostrzeżeń) ===")
print(df7[["ts", "hour"]])


# ===========================================================================
# Scenariusz 8 — brakująca godzina marca -> ValueError
# ===========================================================================

df8 = pd.DataFrame({
    "ts": ["2025-03-30 01:00", "2025-03-30 02:00", "2025-03-30 03:00"],
})

print("\n=== Scenariusz 8: brakująca godzina DST (marzec) -> ValueError ===")
try:
    to_gridtime(df8["ts"], "gridtime[hour]")
except ValueError as e:
    print(f"ValueError: {e}")


# ===========================================================================
# Scenariusz 9 — astype po rejestracji dtype
# ===========================================================================

s = pd.Series(pd.to_datetime(["2025-06-01 08:00", "2025-06-01 09:00"]))
s_hour = s.astype("gridtime[hour]")

print("\n=== Scenariusz 9: astype('gridtime[hour]') ===")
print(s_hour)


# ===========================================================================
# Scenariusz 10 — pd.concat zachowuje dtype
# ===========================================================================

df10a = pd.DataFrame({"hour": to_gridtime(pd.Series(["2025-01-01 00:00", "2025-01-01 01:00"]), "gridtime[hour]")})
df10b = pd.DataFrame({"hour": to_gridtime(pd.Series(["2025-01-02 00:00"]), "gridtime[hour]")})

result = pd.concat([df10a, df10b], ignore_index=True)

print("\n=== Scenariusz 10: pd.concat zachowuje dtype ===")
print(result)
print(f"dtype po concat: {result['hour'].dtype}")


# ===========================================================================
# Scenariusz 11 — kompletne dane kwadransowe DST (4×↑ + 4×↓)
# ===========================================================================

df11 = pd.DataFrame({
    "ts": [
        "2025-10-26 01:45",
        "2025-10-26 02:00",   # pierwsze 02:00 -> ↑1st
        "2025-10-26 02:15",   # pierwsze 02:15 -> ↑1st
        "2025-10-26 02:30",   # pierwsze 02:30 -> ↑1st
        "2025-10-26 02:45",   # pierwsze 02:45 -> ↑1st
        "2025-10-26 02:00",   # drugie 02:00  -> ↓2nd
        "2025-10-26 02:15",   # drugie 02:15  -> ↓2nd
        "2025-10-26 02:30",   # drugie 02:30  -> ↓2nd
        "2025-10-26 02:45",   # drugie 02:45  -> ↓2nd
        "2025-10-26 03:00",
    ],
})

with warnings.catch_warnings():
    warnings.simplefilter("error", GridtimeDSTWarning)
    df11["qh"] = to_gridtime(df11["ts"], "gridtime[quarter_hour]")

print("\n=== Scenariusz 11: kompletne kwadranse DST (brak ostrzeżeń) ===")
print(df11[["ts", "qh"]])
