# Design: Integracja gridtime z pandas — typ kolumny ExtensionArray

**Data:** 2026-04-28  
**Status:** Zatwierdzony  
**Plik implementacji:** `gridtime/pandas.py`  
**Testy:** `tests/test_pandas.py`

---

## 1. Cel

Dodanie do biblioteki gridtime dedykowanego typu kolumny pandas, który:
- pozwala przechowywać obiekty gridtime (`Hour`, `Day`, `QuarterHour`) w kolumnach DataFrame
- daje wizualną reprezentację zgodną z `__repr__` obiektów gridtime
- umożliwia płynną konwersję z domyślnych typów dat pandas (`pd.Timestamp`, `datetime64`)
- obsługuje specyficzne przypadki DST (duplikowane/brakujące godziny) z ostrzeżeniami zamiast błędów krytycznych

---

## 2. Zakres pierwszej implementacji

Obsługiwane typy gridtime: **`Hour`**, **`Day`**, **`QuarterHour`**.  
Pozostałe typy (`Month`, `Quarter`, `Year`, `Week`, `Season`, `MonthDecade`) będą dodane ręcznie w przyszłości, korzystając z tej samej bazy.

---

## 3. Architektura

Cały kod w `gridtime/pandas.py`. Struktura:

```
GridtimeDtype(ExtensionDtype)        ← wspólna baza dtype
    HourDtype          name="gridtime[hour]"         type=Hour
    DayDtype           name="gridtime[day]"          type=Day
    QuarterHourDtype   name="gridtime[quarter_hour]" type=QuarterHour

GridtimeArray(ExtensionArray)        ← wspólna baza array
    HourArray          dtype=HourDtype()         _default_timestamp_role="start"
    DayArray           dtype=DayDtype()          _default_timestamp_role="start"
    QuarterHourArray   dtype=QuarterHourDtype()  _default_timestamp_role="start"

to_gridtime(series, dtype, *, timestamp_role, dst_ambiguous, **kwargs)
```

---

## 4. GridtimeDtype

Wspólna baza dtype implementuje:
- `kind = "O"` (object storage)
- `na_value = pd.NA` (formalnie wymagane przez pandas, nigdy nie wystąpi w kolumnie)
- `construct_array_type()` → odpowiedni `GridtimeArray`
- `__from_dtype_string__` → parsuje `"gridtime[hour]"` itd.

Każda podklasa deklaruje `name` i `type` oraz jest dekorowana `@register_extension_dtype`, co umożliwia:

```python
df["col"].astype("gridtime[hour]")
df.dtypes  # → gridtime[hour]
pd.array([...], dtype="gridtime[hour]")
```

---

## 5. GridtimeArray

Przechowuje dane jako `np.ndarray(dtype=object)` zawierający wyłącznie obiekty gridtime.

**Kolumna jest non-nullable** — brak NaN z definicji:
- `isna()` zawsze zwraca `np.zeros(len(self), dtype=bool)`
- `_from_sequence` rzuca `ValueError` przy napotkaniu `None` lub `NaN`

Implementowane metody pandas ExtensionArray API:
- `__getitem__`, `__setitem__`, `__len__`
- `isna`, `take`, `copy`, `_concat_same_type`
- `_from_sequence`, `_from_factorized`
- `_validate_scalar` — sprawdza zgodność typu z `_gridtime_type`
- `__repr__` — deleguje do `repr()` każdego obiektu gridtime

Podklasy deklarują tylko:
```python
class HourArray(GridtimeArray):
    dtype = HourDtype()
    _gridtime_type = Hour
    _default_timestamp_role = "start"
```

---

## 6. Konwencje timestamp dla każdego typu

| Typ           | Konstruktor gridtime          | Domyślny `timestamp_role` | Interpretacja                        |
|---------------|-------------------------------|---------------------------|--------------------------------------|
| `Hour`        | `Hour(end_time)`              | `"start"`                 | `"start"`: `end_time = ts + 1h`      |
|               |                               |                           | `"end"`: `end_time = ts`             |
| `QuarterHour` | `QuarterHour(start_time)`     | `"start"`                 | `"start"`: `start_time = ts`         |
| `Day`         | `Day(date)`                   | nieistotne                | zawsze `ts.date()`                   |

---

## 7. Funkcja `to_gridtime`

```python
def to_gridtime(
    series,
    dtype,                     # "gridtime[hour]" | HourDtype() | type HourArray
    *,
    timestamp_role="start",    # "start" | "end"  (dla Hour i QuarterHour)
    dst_ambiguous=None,        # None | "first" | "second" | "infer"
    **kwargs,                  # przekazywane do pd.to_datetime(series, **kwargs)
) -> pd.Series:
```

**Przepływ:**
1. `pd.to_datetime(series, **kwargs)` — normalizacja do `pd.Timestamp`
2. Dla każdego `pd.Timestamp`:
   - Czy timestamp trafia na duplikowaną godzinę DST?
     - `dst_ambiguous=None` → `warnings.warn(GridtimeDSTWarning)` + wybierz `"first"`
     - `dst_ambiguous="first"` → `is_backward=False`, brak ostrzeżenia
     - `dst_ambiguous="second"` → `is_backward=True`, brak ostrzeżenia
     - `dst_ambiguous="infer"` → patrz niżej
   - Czy timestamp trafia na brakującą godzinę DST (marzec)? → `ValueError` z listą nieprawidłowych timestamps
   - Zbuduj obiekt gridtime zgodnie z `timestamp_role`
3. Zwróć `pd.Series(GridtimeArray(...))`

**Tryb `dst_ambiguous="infer"` — automatyczne wykrywanie na podstawie kolejności:**

Gdy dane zawierają naturalną sekwencję z oboma wystąpieniami duplikowanej godziny (tj. ten sam timestamp pojawia się dwukrotnie pod rząd w miejscu zmiany czasu), `"infer"` przypisuje je automatycznie — pierwsze wystąpienie to `↑1st`, drugie to `↓2nd`. Dla kwadransów: pierwsza czwórka identycznych timestampów to `↑1st`, druga czwórka to `↓2nd`.

Algorytm przegląda serię od lewej do prawej. Gdy napotka duplikowany timestamp DST:
- jeśli poprzednie wystąpienie tego samego timestampa DST w sesji było `↑1st` → przypisz `↓2nd`
- w przeciwnym razie → przypisz `↑1st`

Brak ostrzeżeń w trybie `"infer"` — zakłada się że użytkownik świadomie przekazał kompletne dane.

**Ostrzeżenie DST** (`GridtimeDSTWarning`, tylko dla `dst_ambiguous=None`) zawiera listę timestamps których dotyczyło:
```
GridtimeDSTWarning: 2 timestamps trafia na duplikowaną godzinę DST
(2025-10-26 02:00, 2025-10-26 02:15). Wybrano 'first'.
Podaj dst_ambiguous='first', 'second' lub 'infer' aby wyciszyć to ostrzeżenie.
```

---

## 8. Eksport publiczny

`to_gridtime`, `HourArray`, `DayArray`, `QuarterHourArray`, `HourDtype`, `DayDtype`, `QuarterHourDtype` oraz `GridtimeDSTWarning` będą eksportowane z `gridtime/pandas.py`. Klasy `GridtimeDtype` i `GridtimeArray` są szczegółem implementacyjnym — nie są eksportowane publicznie.  
`gridtime/__init__.py` nie importuje automatycznie modułu pandas — użytkownik importuje go jawnie:

```python
from gridtime.pandas import to_gridtime, HourArray
```

---

## 9. Scenariusze zachowania

Konkretne przykłady pokazujące oczekiwane wejście i wyjście w typowych sytuacjach.

---

### Scenariusz 1 — Wczytanie danych z CSV i konwersja na godziny

Plik CSV zawiera kolumnę `timestamp` z początkami godzin jako stringi.  
`timestamp_role="start"` (domyślne) oznacza że `"2025-01-15 12:00"` to początek godziny 12:00–13:00.

```python
df = pd.read_csv("produkcja.csv")
# df["timestamp"]:
# 0    2025-01-15 12:00
# 1    2025-01-15 13:00
# 2    2025-01-15 14:00
# dtype: object

df["hour"] = to_gridtime(df["timestamp"], "gridtime[hour]")
# df["hour"]:
# 0    2025-01-15 12:00-13:00
# 1    2025-01-15 13:00-14:00
# 2    2025-01-15 14:00-15:00
# dtype: gridtime[hour]
```

---

### Scenariusz 2 — Dane z bazy danych gdzie timestamp oznacza koniec godziny

System SCADA zapisuje `timestamp` jako koniec okresu rozliczeniowego — `13:00` to godzina 12:00–13:00.  
Wymaga jawnego `timestamp_role="end"`.

```python
df["hour"] = to_gridtime(df["timestamp"], "gridtime[hour]", timestamp_role="end")
# Timestamp "2025-01-15 13:00" → Hour(end_time=13:00) → 2025-01-15 12:00-13:00
#
# df["hour"]:
# 0    2025-01-15 12:00-13:00
# 1    2025-01-15 13:00-14:00
# dtype: gridtime[hour]
```

---

### Scenariusz 3 — Konwersja istniejącej kolumny datetime pandas na DayArray

Kolumna `datetime64[ns]` z pandas — typowy wynik `pd.read_excel` lub `pd.read_sql`.

```python
df["date"] = pd.to_datetime(["2025-03-01", "2025-03-02", "2025-03-03"])
# dtype: datetime64[ns]

df["day"] = to_gridtime(df["date"], "gridtime[day]")
# df["day"]:
# 0    2025-03-01
# 1    2025-03-02
# 2    2025-03-03
# dtype: gridtime[day]

df.dtypes
# date    datetime64[ns]
# day     gridtime[day]
```

---

### Scenariusz 4 — Dane kwadransowe z pliku Excel

Kolumna z początkami kwadransów. `QuarterHour(start_time)` — `timestamp_role="start"` domyślne i naturalne.

```python
df = pd.read_excel("pwr_15min.xlsx")
# df["ts"]:
# 0    2025-07-10 00:00
# 1    2025-07-10 00:15
# 2    2025-07-10 00:30
# 3    2025-07-10 00:45

df["qh"] = to_gridtime(df["ts"], "gridtime[quarter_hour]")
# df["qh"]:
# 0    2025-07-10 00:00-00:15
# 1    2025-07-10 00:15-00:30
# 2    2025-07-10 00:30-00:45
# 3    2025-07-10 00:45-01:00
# dtype: gridtime[quarter_hour]
```

---

### Scenariusz 5 — Duplikowana godzina DST, brak `dst_ambiguous` → ostrzeżenie

26 października 2025 godzina 02:00–03:00 wystąpi dwa razy (zmiana czasu z letniego na zimowy).  
Dane wejściowe zawierają obie wartości `02:00` bez rozróżnienia.

```python
df["ts"] = pd.to_datetime([
    "2025-10-26 01:00",
    "2025-10-26 02:00",   # ← duplikowana!
    "2025-10-26 03:00",
])

df["hour"] = to_gridtime(df["ts"], "gridtime[hour]")
# GridtimeDSTWarning: 1 timestamp trafia na duplikowaną godzinę DST
# (2025-10-26 02:00). Wybrano 'first'.
# Podaj dst_ambiguous='first' lub 'second' aby wyciszyć to ostrzeżenie.
#
# df["hour"]:
# 0    2025-10-26 01:00-02:00
# 1    2025-10-26 02:00-03:00 [↑1st]
# 2    2025-10-26 03:00-04:00
# dtype: gridtime[hour]
```

---

### Scenariusz 6 — Duplikowana godzina DST z jawnym `dst_ambiguous`

Użytkownik wie że dane dotyczą drugiego (cofniętego) wystąpienia godziny — brak ostrzeżenia.

```python
df["hour"] = to_gridtime(
    df["ts"], "gridtime[hour]",
    dst_ambiguous="second"
)
# Brak ostrzeżeń.
#
# df["hour"]:
# 0    2025-10-26 01:00-02:00
# 1    2025-10-26 02:00-03:00 [↓2nd]
# 2    2025-10-26 03:00-04:00
# dtype: gridtime[hour]
```

---

### Scenariusz 7 — Brakująca godzina DST (marzec) → `ValueError`

30 marca 2025 godzina 02:00–03:00 nie istnieje (zmiana czasu z zimowego na letnie).  
W gridtime nie można zbudować `Hour` dla nieistniejącej godziny — to zawsze błąd twardy.

```python
df["ts"] = pd.to_datetime([
    "2025-03-30 01:00",
    "2025-03-30 02:00",   # ← nie istnieje!
    "2025-03-30 03:00",
])

df["hour"] = to_gridtime(df["ts"], "gridtime[hour]")
# ValueError: Następujące timestamps nie istnieją z powodu zmiany czasu (DST):
#   - 2025-03-30 02:00
# Usuń lub popraw te wartości przed konwersją.
```

---

### Scenariusz 8 — Próba wstawienia `None` do istniejącej kolumny → `ValueError`

Kolumna gridtime jest non-nullable. Wstawianie `None` lub `NaN` jest niedozwolone.

```python
arr = HourArray._from_sequence([Hour("2025-01-15 12:00"), None])
# ValueError: GridtimeArray nie obsługuje wartości None/NaN.
# Kolumna gridtime[hour] jest non-nullable.
```

---

### Scenariusz 9 — `astype` na istniejącej kolumnie datetime pandas

Po zarejestrowaniu dtype można używać standardowego `astype` pandas.  
Domyślna rola timestampa to `"start"` — działa jak `to_gridtime` bez dodatkowych parametrów.

```python
s = pd.Series(pd.to_datetime(["2025-06-01 08:00", "2025-06-01 09:00"]))
s_hour = s.astype("gridtime[hour]")
# 0    2025-06-01 08:00-09:00
# 1    2025-06-01 09:00-10:00
# dtype: gridtime[hour]
```

Uwaga: `astype` nie przekazuje `timestamp_role` ani `dst_ambiguous` — do konwersji z niestandardowymi parametrami należy używać `to_gridtime`.

---

### Scenariusz 10 — Łączenie dwóch DataFrame z kolumnami gridtime

`pd.concat` zachowuje typ kolumny gdy obie mają ten sam dtype.

```python
df1["hour"]:
# 0    2025-01-01 00:00-01:00
# 1    2025-01-01 01:00-02:00
# dtype: gridtime[hour]

df2["hour"]:
# 0    2025-01-02 00:00-01:00
# dtype: gridtime[hour]

pd.concat([df1, df2])["hour"]:
# 0    2025-01-01 00:00-01:00
# 1    2025-01-01 01:00-02:00
# 0    2025-01-02 00:00-01:00
# dtype: gridtime[hour]   ← dtype zachowany
```

Próba `pd.concat` kolumn różnych typów gridtime (np. `gridtime[hour]` z `gridtime[day]`) rzuci `TypeError`.

---

### Scenariusz 11 — Dwie identyczne godziny DST w danych → `dst_ambiguous="infer"` (godziny)

System eksportuje pełną dobę z uwzględnieniem obu wystąpień godziny 02:00–03:00.  
Dane zawierają ją dwukrotnie — raz jako `↑1st`, raz jako `↓2nd` — w naturalnej kolejności.  
`"infer"` wykrywa to automatycznie na podstawie pozycji w serii — bez ostrzeżeń.

```python
df["ts"] = pd.to_datetime([
    "2025-10-26 01:00",
    "2025-10-26 02:00",   # ← pierwsze wystąpienie → ↑1st
    "2025-10-26 02:00",   # ← drugie wystąpienie  → ↓2nd
    "2025-10-26 03:00",
])

df["hour"] = to_gridtime(df["ts"], "gridtime[hour]", dst_ambiguous="infer")
# Brak ostrzeżeń.
#
# df["hour"]:
# 0    2025-10-26 01:00-02:00
# 1    2025-10-26 02:00-03:00 [↑1st]
# 2    2025-10-26 02:00-03:00 [↓2nd]
# 3    2025-10-26 03:00-04:00
# dtype: gridtime[hour]
```

---

### Scenariusz 12 — Dwie identyczne godziny DST w danych → `dst_ambiguous="infer"` (kwadranse)

Dla danych kwadransowych pełna doba z październikową zmianą czasu zawiera 8 kwadransów  
z zakresu 02:00–03:00: cztery `↑1st` i cztery `↓2nd` w naturalnej kolejności.  
`"infer"` śledzi każdy unikalny timestamp osobno — pierwsze pojawienie się to `↑1st`, drugie to `↓2nd`.

```python
df["ts"] = pd.to_datetime([
    "2025-10-26 01:45",
    "2025-10-26 02:00",   # ← ↑1st (pierwsze wystąpienie 02:00)
    "2025-10-26 02:15",   # ← ↑1st (pierwsze wystąpienie 02:15)
    "2025-10-26 02:30",   # ← ↑1st (pierwsze wystąpienie 02:30)
    "2025-10-26 02:45",   # ← ↑1st (pierwsze wystąpienie 02:45)
    "2025-10-26 02:00",   # ← ↓2nd (drugie wystąpienie 02:00)
    "2025-10-26 02:15",   # ← ↓2nd (drugie wystąpienie 02:15)
    "2025-10-26 02:30",   # ← ↓2nd (drugie wystąpienie 02:30)
    "2025-10-26 02:45",   # ← ↓2nd (drugie wystąpienie 02:45)
    "2025-10-26 03:00",
])

df["qh"] = to_gridtime(df["ts"], "gridtime[quarter_hour]", dst_ambiguous="infer")
# Brak ostrzeżeń.
#
# df["qh"]:
# 0    2025-10-26 01:45-02:00
# 1    2025-10-26 02:00-02:15 [↑1st]
# 2    2025-10-26 02:15-02:30 [↑1st]
# 3    2025-10-26 02:30-02:45 [↑1st]
# 4    2025-10-26 02:45-03:00 [↑1st]
# 5    2025-10-26 02:00-02:15 [↓2nd]
# 6    2025-10-26 02:15-02:30 [↓2nd]
# 7    2025-10-26 02:30-02:45 [↓2nd]
# 8    2025-10-26 02:45-03:00 [↓2nd]
# 9    2025-10-26 03:00-03:15
# dtype: gridtime[quarter_hour]
```

---

## 10. Testowanie

Plik: `tests/test_pandas.py`

### Array i dtype
- Tworzenie `HourArray`, `DayArray`, `QuarterHourArray` z listy obiektów gridtime
- `__repr__` kolumny pokazuje reprezentację gridtime każdego elementu
- `df.dtypes` zwraca `"gridtime[hour]"` / `"gridtime[day]"` / `"gridtime[quarter_hour]"`
- `isna()` zawsze zwraca `False` dla wszystkich elementów
- `_from_sequence` rzuca `ValueError` przy `None` lub `NaN`
- `pd.concat` działa między kolumnami tego samego typu

### Konwersja `to_gridtime`
- String / `pd.Timestamp` / `date` → `Hour` z `timestamp_role="start"`
- String / `pd.Timestamp` / `date` → `Hour` z `timestamp_role="end"`
- Konwersja → `Day`
- Konwersja → `QuarterHour`
- `astype("gridtime[hour]")` działa po rejestracji dtype

### DST
- Duplikowana godzina + `dst_ambiguous=None` → `GridtimeDSTWarning` + `↑1st`
- Duplikowana godzina + `dst_ambiguous="first"` → brak ostrzeżenia, `↑1st`
- Duplikowana godzina + `dst_ambiguous="second"` → brak ostrzeżenia, `↓2nd`
- Dwie identyczne godziny DST w serii + `dst_ambiguous="infer"` → `↑1st` i `↓2nd` wg kolejności, brak ostrzeżenia
- Osiem kwadransów DST (4×↑ + 4×↓) + `dst_ambiguous="infer"` → prawidłowe przypisanie wg kolejności
- Brakująca godzina (marzec) → `ValueError` z listą timestamps
- `**kwargs` z `pd.to_datetime` (np. `format=`, `utc=`) są przekazywane dalej
