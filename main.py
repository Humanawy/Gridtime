from gridtime import gridtime as gt 
from datetime import date, datetime

if __name__ == "__main__":
    day = gt.Day(date(2025, 10, 26))

    for quarters in list(day.walk("quarters15"))[:25]:
        print(quarters)

    
