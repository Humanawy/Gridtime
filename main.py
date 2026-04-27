from datetime import date, datetime
from gridtime import Day, Hour

# Dzień zmiany czasu z letniego na zimowy – 26 października 2025
dst_day = Day(date(2025, 10, 26))

# Wypisz wszystkie godziny w tej dobie
for hour in dst_day:
    print(hour)

# Weryfikacja zduplikowanych godzin
print("Liczba godzin:", len(dst_day))  # ➜ 25
duplicated_hours = [h for h in dst_day if h.is_duplicated]

# Sprawdź drzewo struktury
print("\nStruktura drzewa:")
dst_day.print_tree(unit_stop="hours")