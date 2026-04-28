# Redesign struktury plików — gridtime

**Data:** 2026-04-28  
**Status:** Zatwierdzona

## Cel

Rozbicie monolitycznych plików `gridtime.py` (~950 linii) i `utils.py` (~196 linii) na mniejsze moduły o jednoznacznej odpowiedzialności. Wyłącznie reorganizacja kodu — żadne funkcje ani klasy nie zmieniają swojego działania.

## Zasada nadrzędna

Tylko przenoszenie kodu między plikami. Żadnych zmian w ciele funkcji ani klasach — jedynym wyjątkiem są lazy importy wewnątrz funkcji (`from gridtime.X import Y`) zastosowane tam, gdzie niezbędne jest złamanie cyklu importów. Lazy import nie zmienia zachowania funkcji.

## Finalna struktura modułu `gridtime/`

```
gridtime/
    __init__.py        # publiczne API — eksporty bez zmian
    _registry.py       # rejestr jednostek czasu
    _dst.py            # wykrywanie zmiany czasu (DST)
    _base.py           # klasy bazowe drzewa
    parsing.py         # parsowanie dat i godzin
    _steps.py          # funkcje kroku dla każdej jednostki
    periods.py         # klasy jednostek czasu
    factories.py       # fabryki pojedynczych obiektów
    ranges.py          # tworzenie zakresów obiektów
    validation.py      # walidatory
    pandas.py          # (nowy, pusty) integracja pandas
```

## Zawartość plików — źródło i cel

### `_registry.py`
**Źródło:** `utils.py`  
Zawartość: `_GRIDTIME_REGISTRY`, `register_unit`, `_all_unit_keys`, `_is_reachable`, `print_structure_tree`

### `_dst.py`
**Źródło:** `utils.py`  
Zawartość: `is_missing_hour`, `is_missing_quarter`, `is_duplicated_hour`, `is_duplicated_quarter`

### `_base.py`
**Źródło:** `gridtime.py`  
Zawartość: `GridtimeLeaf`, `GridtimeStructure`

### `parsing.py`
**Źródło:** `utils.py` + `gridtime.py`  
Zawartość: `parse_date`, `is_quarter_aligned`, `_is_hour_repr`, `_parse_hour_repr`, `parse_hour`  
**Uwaga:** `parse_hour` tworzy obiekty `Hour` — wymaga lazy importu:
```python
def parse_hour(...):
    from gridtime.periods import Hour
    ...
```

### `_steps.py`
**Źródło:** `gridtime.py`  
Zawartość: `quarter_hour_step`, `hour_step`, `day_step`, `month_step`, `quarter_step`, `year_step`, `week_step`, `season_step`, `month_decade_step`  
**Uwaga:** każda funkcja step tworzy instancje klas z `periods.py` — wymagają lazy importów:
```python
def quarter_hour_step(obj, steps):
    from gridtime.periods import QuarterHour
    ...
```

### `periods.py`
**Źródło:** `gridtime.py`  
Zawartość: `QuarterHour`, `Hour`, `Day`, `Month`, `Quarter`, `Year`, `Week`, `Season`, `MonthDecade`

### `factories.py`
**Źródło:** `gridtime.py`  
Zawartość: `create_days`, `create_hours`, `create_months`, `create_quarters`, `create_quarter_hours`, `create_quarter_months`, `create_season_quarters`, `create_week_days`, `create_decade_days`

### `ranges.py`
**Źródło:** `gridtime.py`  
Zawartość: `create_date_range`, `create_hour_range`

### `validation.py`
**Źródło:** `gridtime.py`  
Zawartość: `validate_complete_range`

### `pandas.py`
Nowy plik, początkowo pusty — placeholder dla przyszłego dedykowanego typu kolumny pandas.

## Graf zależności (bez cykli)

```
_registry   ← brak zależności wewnętrznych
_dst        ← brak zależności wewnętrznych
parsing     ← brak zależności wewnętrznych (lazy: periods)
_base       ← _registry, _dst
_steps      ← brak zależności na poziomie modułu (lazy: periods)
periods     ← _registry, _dst, _base, parsing, _steps
factories   ← periods, parsing, _dst
ranges      ← periods, parsing, _dst
validation  ← periods
pandas      ← periods, factories
```

## Struktura testów

Obecny `tests/test_gridtime.py` zostaje podzielony — żadne testy nie są usuwane ani modyfikowane.

```
tests/
    __init__.py
    test_periods.py      # testy klas i step functions
    test_parsing.py      # parse_date, _parse_hour_repr, parse_hour
    test_factories.py    # create_* functions
    test_ranges.py       # create_date_range, create_hour_range
    test_validation.py   # validate_complete_range
    test_pandas.py       # (nowy, pusty)
```

## Publiczne API (`__init__.py`)

Eksporty w `__init__.py` pozostają bez zmian — użytkownicy biblioteki nie odczuwają żadnej różnicy. Zmieniają się tylko źródłowe moduły importów wewnątrz pliku.

## Pliki usuwane po migracji

- `gridtime/gridtime.py` — cała zawartość przeniesiona do nowych modułów
- `gridtime/utils.py` — cała zawartość przeniesiona do nowych modułów
- `tests/test_gridtime.py` — zastąpiony przez podzielone pliki testów

## Kierunki dalszego rozwoju (kontekst)

- `parsing.py` — rozbudowa parsowania jednostek czasu z ciągów tekstowych
- `ranges.py` — rozbudowa tworzenia obiektów z zakresów
- `pandas.py` — dedykowany typ kolumny pandas
- `validation.py` — nowe walidatory zakresu i kompletności danych
