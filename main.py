from gridtime import gridtime as gt 
from datetime import date, datetime

if __name__ == "__main__":
    # day = gt.Day(date(2025, 10, 26))

    # for quarters in list(day.walk("quarters15"))[:25]:
    #     print(quarters)

    hours = gt.Year(2025).get("hours")
    res = gt.validate_complete_range(hours)
    print(res)

