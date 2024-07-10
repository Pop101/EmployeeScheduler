from dtypes import Timespan, Employee
from dateparser import parse
from datetime import datetime, time, timedelta, date
import pandas as pd

def parse_cell(day:date, cell:str) -> list[Timespan]:
    if cell.casefold() == "all day":
        return [Timespan(datetime.combine(day, time.min), datetime.combine(day, time.max))]
    
    timespans = list()
    timespan_strs = cell.split(",")
    for timespan_str in timespan_strs:
        if '-' not in timespan_str:
            continue
        
        start_str, end_str = timespan_str.split("-")
        if end_str.strip().casefold() in ("midnight", "12am"):
            end_str = "11:59pm"
        start, end = parse(start_str), parse(end_str)
        timespans.append(Timespan(datetime.combine(day, start.time()), datetime.combine(day, end.time())))
    return timespans

def parse_employees(raw_employee_data:pd.DataFrame) -> dict[str, Employee]:
    employees = {}
    for _, row in raw_employee_data.iterrows():
        row = row.where(pd.notna(row), None)
        name = row["Employee"]
        tenure = row["Tenure"]
        preferred_hours = row["Preferred Hours"]
        
        favored_hours = parse_cell(datetime.now().date(), row["Favored Hours"])
        favored_hours = [x.strip_date() for x in favored_hours if x != None]
        
        employees[name] = Employee(tenure=tenure, preferences=favored_hours, preferred_hours=preferred_hours)
    return employees

def parse_availability(raw_availability_data:pd.DataFrame, employees: dict[str, Employee]):
    for _, row in raw_availability_data.iterrows():
        name = row["Employee"]
        if name not in employees:
            continue
        
        availability = set()
        for column in raw_availability_data.columns:
            # If the column is a date, parse. Otherwise skip
            try:
                day = datetime.strptime(column, "%B %d, %Y").date()
            except ValueError:
                continue
            
            if pd.isna(row[column]):
                continue
            
            availability = availability.union(parse_cell(day, row[column]))
        employees[name].availability = availability
        employees[name].positions = set(map(str.strip, row["Positions"].split(",")))

def parse_to_fill(raw_to_fill_data:pd.DataFrame) -> list[tuple[str, Timespan]]:
    to_fill = []
    for _, row in raw_to_fill_data.iterrows():
        position = row["Position"]
        day = datetime.strptime(row["Date"], "%B %d, %Y").date()
        timespans = parse_cell(day, row["Hours"])
        to_fill.extend((position, timespan) for timespan in timespans)
    return to_fill

if __name__ == "__main__":
    employees = parse_employees(pd.read_csv("preferences.csv"))
    parse_availability(pd.read_csv("availability_report.csv"), employees)
    to_fill = parse_to_fill(pd.read_csv("to_fill.csv"))
    
    print(f"Employees: {len(employees)}")
    print(f"To Fill: {len(to_fill)} rows")
    
    import solver
    res = solver.create_schedule(to_fill, employees)
    print(res != None)
    
    print("Done!")