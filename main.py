from gridtime import gridtime as gt 
from datetime import date, datetime

if __name__ == "__main__":
    # day = gt.Day(date(2025, 10, 26))

    # for quarters in list(day.walk("quarters15"))[:25]:
    #     print(quarters)

    day = gt.Day("2026-01-01") 
    hour = gt.Hour("2026-01-01 21:00-22:00") 

    hours = gt.create_hours("2026-01-01 21:00-22:00", "2026-01-01 22:00-23:00")

    print(hour) # 2026-01-01 21:00-22:00
    print(day) # 2026-01-01
    print(hours) # [2026-01-01 21:00-22:00, 2026-01-01 22:00-23:00]

