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
    dst_ambiguous=None,        # None | "first" | "second"
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
   - Czy timestamp trafia na brakującą godzinę DST (marzec)? → `ValueError` z listą nieprawidłowych timestamps
   - Zbuduj obiekt gridtime zgodnie z `timestamp_role`
3. Zwróć `pd.Series(GridtimeArray(...))`

**Ostrzeżenie DST** (`GridtimeDSTWarning`) zawiera listę timestamps których dotyczyło:
```
GridtimeDSTWarning: 2 timestamps trafia na duplikowaną godzinę DST
(2025-10-26 02:00, 2025-10-26 02:15). Wybrano 'first'.
Podaj dst_ambiguous='first' lub 'second' aby wyciszyć to ostrzeżenie.
```

---

## 8. Eksport publiczny

`to_gridtime`, `HourArray`, `DayArray`, `QuarterHourArray`, `HourDtype`, `DayDtype`, `QuarterHourDtype` oraz `GridtimeDSTWarning` będą eksportowane z `gridtime/pandas.py`. Klasy `GridtimeDtype` i `GridtimeArray` są szczegółem implementacyjnym — nie są eksportowane publicznie.  
`gridtime/__init__.py` nie importuje automatycznie modułu pandas — użytkownik importuje go jawnie:

```python
from gridtime.pandas import to_gridtime, HourArray
```

---

## 9. Testowanie

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
- Brakująca godzina (marzec) → `ValueError` z listą timestamps
- `**kwargs` z `pd.to_datetime` (np. `format=`, `utc=`) są przekazywane dalej
