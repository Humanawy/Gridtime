# Gridtime – struktury czasu z obsługą DST i drzewiastym API

`Gridtime` to zaawansowany system reprezentacji jednostek czasu w Pythonie – z obsługą zmian czasu (DST), strukturą drzewa (rok → kwartał → miesiąc → dekada → dzień → godzina → kwadrans) i intuicyjnym API do iteracji, nawigacji i agregacji.

## Cel

Narzędzie zostało stworzone **z myślą o zastosowaniach w polskiej branży energetycznej**, w szczególności:

- przetwarzaniu danych dobowo-godzinowych oraz 15-minutowych (kwadransowych),
- zachowaniu pełnej zgodności ze specyfiką czasową PSE i OSD (zmiana czasu, powtarzające się i brakujące godziny),
- zapewnieniu **jednoznacznego przypisania każdego rekordu do przedziału czasowego**, nawet przy przesunięciu zegarowym.

---

## Spis treści

1. [Jednostki czasu](#1-jednostki-czasu)
2. [Nawigacja – next, prev, shift](#2-nawigacja--next-prev-shift)
3. [Drzewo – walk, get, count, tree](#3-drzewo--walk-get-count-tree)
4. [Fabryki obiektów – create_*](#4-fabryki-obiektów--create_)
5. [Zakresy – create_date_range, create_hour_range](#5-zakresy--create_date_range-create_hour_range)
6. [Parsowanie – parse_date, parse_hour](#6-parsowanie--parse_date-parse_hour)
7. [Obsługa DST](#7-obsługa-dst)
8. [Walidacja – validate_complete_range](#8-walidacja--validate_complete_range)

---

## 1. Jednostki czasu

```python
from datetime import date, datetime
import gridtime as gt

# Kwadrans godzinowy (15 minut)
q = gt.QuarterHour(datetime(2025, 6, 15, 14, 0))
print(q)          # 2025-06-15 14:00-14:15

# Godzina (identyfikowana przez czas końca)
h = gt.Hour(datetime(2025, 6, 15, 15, 0))
print(h)          # 2025-06-15 14:00-15:00

# Dzień
d = gt.Day(date(2025, 6, 15))
print(d)          # 2025-06-15

# Miesiąc
m = gt.Month(2025, 6)
print(m)          # 2025-06

# Dekada miesięczna (1–3)
dec = gt.MonthDecade(2025, 7, 2)
print(dec)        # 2025-07 D2 (11-20)

# Kwartał
q4 = gt.Quarter(2025, 4)
print(q4)         # 2025-Q4

# Rok
y = gt.Year(2025)
print(y)          # 2025

# Tydzień ISO
w = gt.Week(2025, 20)
print(w)          # W-20-2025

# Sezon (W = zimowy, S = letni)
s_w = gt.Season(2024, "W")
s_s = gt.Season(2025, "S")
print(s_w)        # S-W-2024/2025
print(s_s)        # S-S-2025
```

---

## 2. Nawigacja – next, prev, shift

```python
from datetime import date
import gridtime as gt

# --- Dzień ---
d = gt.Day(date(2025, 12, 31))
print(d.next())        # 2026-01-01
print(d.prev())        # 2025-12-30
print(d.shift(10))     # 2026-01-10
print(d.shift(-5))     # 2025-12-26

# --- Miesiąc (przekroczenie roku) ---
m = gt.Month(2025, 12)
print(m.next())        # 2026-01
print(m.shift(14))     # 2027-02
print(m.shift(-25))    # 2023-11

# --- Kwartał ---
q = gt.Quarter(2025, 4)
print(q.next())        # 2026-Q1
print(q.shift(-3))     # 2025-Q1

# --- Tydzień ---
w = gt.Week(2025, 52)
print(w.next())        # W-1-2026

# --- Sezon (przemiana S/W) ---
s = gt.Season(2025, "S")
print(s.next())        # S-W-2025/2026
print(s.next().next()) # S-S-2026

# --- Własność odwracalności: shift(n).shift(-n) == oryginał ---
d = gt.Day(date(2025, 5, 12))
assert d.shift(37).shift(-37) == d
```

---

## 3. Drzewo – walk, get, count, tree

### Liczenie jednostek

```python
import gridtime as gt

# Rok przestępny vs. zwykły
print(gt.Year(2024).count("hours"))   # 8784  (366 dni × 24 + 1 za DST jesień - 1 za DST wiosna)
print(gt.Year(2025).count("hours"))   # 8760

# Październik 2025 – zmiana czasu na zimowy (25 godzin × 1 dzień)
print(gt.Month(2025, 10).count("hours"))     # 745
# Marzec 2025 – zmiana czasu na letni (23 godziny × 1 dzień)
print(gt.Month(2025, 3).count("hours"))      # 743

# Kwadranse w kwartale
print(gt.Quarter(2025, 1).count("quarters15"))  # 8640  (= 90 dni × 24 h × 4 q)

# Dni w tygodniu
print(gt.Week(2025, 20).count("days"))       # 7
```

### walk – leniwy iterator

```python
from datetime import date
import gridtime as gt

# Wszystkie godziny w dniu – iteracja
day = gt.Day(date(2025, 6, 15))
for hour in day.walk("hours"):
    print(hour)
# 2025-06-15 00:00-01:00
# 2025-06-15 01:00-02:00
# ...
# 2025-06-15 23:00-00:00

# Wyfiltruj nocne godziny
night = [h for h in day.walk("hours") if h.start_time.hour >= 22 or h.start_time.hour < 6]

# Kwadranse w całym kwartale
q1 = gt.Quarter(2025, 1)
quarters_list = list(q1.walk("quarters15"))
print(len(quarters_list))   # 8640
```

### get – lista węzłów

```python
import gridtime as gt

month = gt.Month(2025, 3)

# Wszystkie dni marca
days = month.get("days")
print(len(days))          # 31

# Wszystkie godziny (jako lista)
hours = month.get("hours")
print(len(hours))         # 743  (marzec ze zmianą czasu)
```

### tree / print_tree – wizualizacja

```python
from datetime import date
import gridtime as gt

# Drzewo kwartału zatrzymane na poziomie miesięcy
q = gt.Quarter(2025, 1)
q.print_tree(unit_stop="months")
# └── 2025-Q1
#     ├── 2025-01
#     ├── 2025-02
#     └── 2025-03

# Drzewo dnia ze zmianą czasu do poziomu godzin
gt.Day(date(2025, 10, 26)).print_tree(unit_stop="hours")
# └── 2025-10-26
#     ├── 2025-10-26 00:00-01:00
#     ├── 2025-10-26 01:00-02:00
#     ├── 2025-10-26 02:00-03:00 [↑1st]
#     ├── 2025-10-26 02:00-03:00 [↓2nd]
#     ├── 2025-10-26 03:00-04:00
#     ...
#     └── 2025-10-26 23:00-00:00

# Zwróć drzewo jako string (np. do logowania)
tree_str = gt.Quarter(2025, 2).tree(unit_stop="months")
```

### Operator in

```python
from datetime import date, datetime
import gridtime as gt

day = gt.Day(date(2025, 6, 15))
hour = gt.Hour(datetime(2025, 6, 15, 15, 0))

print(hour in day)                        # True
print(gt.Hour(datetime(2025, 6, 16, 1, 0)) in day)  # False

month = gt.Month(2025, 6)
print(day in month)                       # True
```

---

## 4. Fabryki obiektów – create_*

### Dni miesiąca

```python
import gridtime as gt

# Wszystkie dni marca 2025
days = gt.create_days(2025, 3)
print(len(days))        # 31

# Dni z ciągu tekstowego daty (pobiera rok i miesiąc)
days = gt.create_days("2025-06-01")
print(len(days))        # 30

# Podzbiór dni (parzysty zakres)
from datetime import date
days = gt.create_days(2025, 1, day_range=range(1, 16))
print(len(days))        # 15
```

### Godziny dnia

```python
from datetime import date
import gridtime as gt

# Wszystkie godziny zwykłego dnia
hours = gt.create_hours(date(2027, 1, 1))
print(len(hours))        # 24

# Dzień z przesuniętym czasem – wiosna (brakująca godzina)
hours = gt.create_hours(date(2025, 3, 30))
print(len(hours))        # 23

# Dzień z przesuniętym czasem – jesień (dodatkowa godzina)
hours = gt.create_hours(date(2025, 10, 26))
print(len(hours))        # 25

# Tryb repr – wybrane godziny po repr-stringu
hours = gt.create_hours(
    "2026-01-01 21:00-22:00",
    "2026-01-01 22:00-23:00",
    "2026-01-01 23:00-00:00",
)
print(len(hours))        # 3
```

### Kwadranse godziny

```python
from datetime import datetime
import gridtime as gt

# Zwykła godzina (4 kwadranse)
qs = gt.create_quarter_hours(datetime(2025, 6, 15, 14, 0))
print(len(qs))           # 4

# Godzina duplikowana – tylko pierwsza faza (↑1st)
qs_first = gt.create_quarter_hours(datetime(2025, 10, 26, 2, 0), phase="first")
print(len(qs_first))     # 4

# Obie fazy (↑1st + ↓2nd) = 8 kwadransów
qs_both = gt.create_quarter_hours(datetime(2025, 10, 26, 2, 0), phase="both")
print(len(qs_both))      # 8
```

### Miesiące, kwartały, sezony

```python
import gridtime as gt

# Wybrane miesiące roku
months = gt.create_months(2025, [1, 4, 7, 10])   # styczeń, kwiecień, lipiec, październik

# Wszystkie kwartały roku
quarters = gt.create_quarters(2025)
print(len(quarters))     # 4

# Kwartały sezonu zimowego 2024/2025 (Q4/2024 + Q1/2025)
winter_qs = gt.create_season_quarters(2024, "W")
print(winter_qs)         # [2024-Q4, 2025-Q1]

# Kwartały sezonu letniego 2025 (Q2 + Q3)
summer_qs = gt.create_season_quarters(2025, "S")
print(summer_qs)         # [2025-Q2, 2025-Q3]

# Dni tygodnia ISO
days = gt.create_week_days(2025, 20)
print(len(days))         # 7

# Dni dekady
dec_days = gt.create_decade_days(2025, 7, 2)    # 11–20 lipca
print(len(dec_days))     # 10
dec_days = gt.create_decade_days(2025, 2, 3)    # 21–28 lutego
print(len(dec_days))     # 8
```

---

## 5. Zakresy – create_date_range, create_hour_range

### Zakres dni

```python
import gridtime as gt

# Tydzień jako lista dni
days = gt.create_date_range("2025-06-09", "2025-06-15")
print(len(days))         # 7

# Ten sam zakres bez pierwszego i ostatniego dnia
days = gt.create_date_range("2025-06-09", "2025-06-15", include_start=False, include_end=False)
print(len(days))         # 5

# Zakres godzin (granularity="hours") – z obsługą DST
hours = gt.create_date_range("2025-10-25", "2025-10-26", granularity="hours")
print(len(hours))        # 49  (24 + 25, dzień ze zmianą czasu)

# Zakres kwadransów
qs = gt.create_date_range("2025-01-01", "2025-01-02", granularity="quarters15")
print(len(qs))           # 96  (2 dni × 24 h × 4 q)

# Formaty daty są dowolne
days = gt.create_date_range("01.01.2025", "31.01.2025")
print(len(days))         # 31
```

### Zakres godzin

```python
from datetime import date
import gridtime as gt

# Godziny 8:00–16:00 jednego dnia (konwencja 0-23, as_start)
hours = gt.create_hour_range(8, "2025-06-15", 16, "2025-06-15")
print(len(hours))        # 9  (8, 9, 10, 11, 12, 13, 14, 15, 16)

# Ten sam zakres bez pierwszej i ostatniej
hours = gt.create_hour_range(8, "2025-06-15", 16, "2025-06-15",
                             include_start=False, include_end=False)
print(len(hours))        # 7

# Konwencja energetyczna 1-24, as_end (godzina 1 = 00:00-01:00)
hours = gt.create_hour_range(1, "2025-06-15", 24, "2025-06-15",
                             convention="1-24", interpret="as_end")
print(len(hours))        # 24  (cała doba)

# Zakres wielodniowy
hours = gt.create_hour_range(20, "2025-06-14", 4, "2025-06-15")
print(len(hours))        # 9  (20:00→04:00)
```

---

## 6. Parsowanie – parse_date, parse_hour

### parse_date

```python
from datetime import date, datetime
import gridtime as gt

# Różne formaty tekstowe
print(gt.parse_date("01.01.2027"))    # 2027-01-01
print(gt.parse_date("01/06/2027"))    # 2027-06-01
print(gt.parse_date("2027-03-15"))    # 2027-03-15

# Obiekty date/datetime są przepuszczane bez zmian
d = date(2027, 5, 20)
assert gt.parse_date(d) is d         # ten sam obiekt

dt = datetime(2027, 1, 1, 20, 3)
print(gt.parse_date(dt))             # 2027-01-01  (czas jest odcinany)
```

### parse_hour

```python
from datetime import date
import gridtime as gt

# --- Tryb repr (jeden argument) ---
h = gt.parse_hour("2026-01-01 21:00-22:00")
print(h.start_time)     # 2026-01-01 21:00
print(h.end_time)       # 2026-01-01 22:00

# --- Tryb numer + data (konwencja 0-23, domyślna) ---
h = gt.parse_hour(14, date(2025, 6, 15))
print(h)                # 2025-06-15 14:00-15:00

# Numer jako string lub z minutami
h = gt.parse_hour("08", date(2025, 6, 15))
h = gt.parse_hour("08:00", date(2025, 6, 15))
print(h)                # 2025-06-15 08:00-09:00

# --- Konwencja energetyczna 1-24 (as_end) ---
# Godzina 1  = 00:00-01:00, godzina 24 = 23:00-00:00
h1  = gt.parse_hour(1,  date(2025, 6, 15), convention="1-24", interpret="as_end")
h24 = gt.parse_hour(24, date(2025, 6, 15), convention="1-24", interpret="as_end")
print(h1)               # 2025-06-15 00:00-01:00
print(h24)              # 2025-06-15 23:00-00:00

# --- DST – godzina duplikowana (jesień) ---
h_fwd = gt.parse_hour(2, date(2025, 10, 26))                  # ↑1st
h_bwd = gt.parse_hour(2, date(2025, 10, 26), backward=True)   # ↓2nd
print(h_fwd.is_backward)   # False
print(h_bwd.is_backward)   # True
```

---

## 7. Obsługa DST

Gridtime obsługuje **obie strony zmiany czasu** stosowanej w Polsce (strefa Europa/Warszawa):

| Zdarzenie | Data 2025 | Skutek |
|---|---|---|
| Zmiana na letni (wiosna) | 30 marca | Godzina `02:00–03:00` nie istnieje |
| Zmiana na zimowy (jesień) | 26 października | Godzina `02:00–03:00` powtarza się |

### Brakująca godzina (wiosna)

```python
from datetime import datetime, date
import gridtime as gt

# Godzina 02:00–03:00 nie istnieje – próba utworzenia rzuca wyjątek
try:
    gt.Hour(datetime(2025, 3, 30, 3, 0))   # end_time = 03:00 → start = 02:00
except ValueError as e:
    print(e)   # Nie można utworzyć godziny dla 2025-03-30 03:00

# create_hours automatycznie pomija brakującą godzinę
hours = gt.create_hours(date(2025, 3, 30))
print(len(hours))        # 23

# Nawigacja omija brakującą godzinę
h_before = gt.Hour(datetime(2025, 3, 30, 2, 0))   # 01:00-02:00
h_after  = h_before.next()
print(h_after)           # 2025-03-30 03:00-04:00  (przeskok przez 02:00-03:00)
assert h_after.prev() == h_before
```

### Duplikowana godzina (jesień)

```python
from datetime import datetime, date
import gridtime as gt

# Dzień ze zmianą czasu ma 25 godzin
day = gt.Day(date(2025, 10, 26))
print(len(day))                              # 25
print(day.count("hours"))                   # 25

# Dwie osobne instancje godziny 02:00-03:00
h1 = gt.Hour(datetime(2025, 10, 26, 3, 0), is_backward=False)  # ↑1st (CEST)
h2 = gt.Hour(datetime(2025, 10, 26, 3, 0), is_backward=True)   # ↓2nd (CET)
print(h1)                   # 2025-10-26 02:00-03:00 [↑1st]
print(h2)                   # 2025-10-26 02:00-03:00 [↓2nd]
print(h1 == h2)             # False  (różne obiekty)
print(h1.is_duplicated)     # True
print(h2.is_backward)       # True

# Nawigacja przez duplikat
h_next = h1.next()
print(h_next)               # 2025-10-26 02:00-03:00 [↓2nd]
print(h_next.next())        # 2025-10-26 03:00-04:00

# Wyodrębnienie duplikatów z dnia
duplicated = [h for h in day.walk("hours") if h.is_duplicated]
print(len(duplicated))      # 2  (↑1st i ↓2nd)
```

### Duplikowane kwadranse (jesień)

```python
from datetime import datetime, date
import gridtime as gt

# W dniu 2025-10-26 między 02:00 a 03:00 jest 8 kwadransów (4 ↑1st + 4 ↓2nd)
day = gt.Day(date(2025, 10, 26))
qs_in_2h = [q for q in day.walk("quarters15") if q.start_time.hour == 2]
print(len(qs_in_2h))        # 8

first_phase  = [q for q in qs_in_2h if not q.is_backward]
second_phase = [q for q in qs_in_2h if q.is_backward]
print([str(q) for q in first_phase])
# ['2025-10-26 02:00-02:15 [↑1st]', '...02:15-02:30 [↑1st]', ...]
```

### Wykrywanie DST

```python
from datetime import datetime
from gridtime import is_duplicated_hour, is_missing_hour, is_duplicated_quarter, is_missing_quarter

print(is_duplicated_hour(datetime(2025, 10, 26, 2, 0)))     # True
print(is_duplicated_hour(datetime(2025, 10, 27, 2, 0)))     # False
print(is_missing_hour(datetime(2025, 3, 30, 2, 0)))          # True
print(is_missing_quarter(datetime(2025, 3, 30, 2, 15)))      # True
print(is_duplicated_quarter(datetime(2025, 10, 26, 2, 30))) # True
```

---

## 8. Walidacja – validate_complete_range

```python
from datetime import date
import gridtime as gt

# Kompletny zakres – brak błędu
hours = gt.create_date_range("2025-06-01", "2025-06-30", granularity="hours")
gt.validate_complete_range(hours)   # True

# Brakujący element – błąd
days = gt.create_date_range("2025-01-01", "2025-01-31")
incomplete = days[:10] + days[12:]   # brakuje 11 i 12 stycznia
try:
    gt.validate_complete_range(incomplete)
except ValueError as e:
    print(e)   # Zakres niekompletny – brak elementów, np.: ...

# Duplikat (niezwiązany z DST) – błąd
from datetime import datetime
hours = gt.create_hours(date(2025, 6, 15))
duplicate_hours = hours + [hours[5]]   # ten sam element dwa razy
try:
    gt.validate_complete_range(duplicate_hours)
except ValueError as e:
    print(e)   # Nielogiczne duplikaty w danych, np.: ...

# DST: zakres z duplikatem godziny przechodzi walidację
hours_dst = gt.create_date_range("2025-10-26", "2025-10-26", granularity="hours")
print(len(hours_dst))               # 25
gt.validate_complete_range(hours_dst)   # True – duplikat DST jest ignorowany
```

---

## Rejestr jednostek

```python
import gridtime as gt

# Sprawdź zarejestrowane jednostki
from gridtime import _GRIDTIME_REGISTRY, list_registered_units
print(list_registered_units())
# {'QuarterHour': 'quarters15', 'Hour': 'hours', 'Day': 'days', ...}

# Sprawdź, czy jednostka jest osiągalna z danego węzła
from gridtime import _is_reachable
print(_is_reachable(gt.Year, "quarters15"))   # True
print(_is_reachable(gt.Month, "weeks"))       # False
```
