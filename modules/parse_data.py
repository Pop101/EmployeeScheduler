from modules.dtypes import Timespan, Employee, AveragePreference, RelativeTODPreference, SpecificTODPreference, MixinPreference, MaxPreference
from dateparser import parse
from datetime import datetime, time, timedelta, date
import pandas as pd

TAG_DEFINITIONS = {
    'morning': 'return shift.end.time() < time(12, 0)',
    'afternoon': 'return shift.start.time() >= time(12, 0) and shift.end.time() <= time(18, 0)',
    'evening': 'return shift.start.time() >= time(17, 0) and shift.end.time() <= time(21, 0)',
    'night': 'return shift.start.time() >= time(20, 0) or shift.end.time() <= time(6, 0)',
    
    'closing': 'return shift.end.time() >= time(20, 0)',
    'noclosing': 'return shift.end.time() < time(20, 0)',
    
    'opening': 'return shift.start.time() < time(9, 0)',
    'noopening': 'return shift.start.time() >= time(9, 00)',
    
    'weekend': 'return shift.start.weekday() >= 5',
    'noweekend': 'return shift.start.weekday() < 5',
    
    'sunday': 'return shift.start.weekday() == 6',
    'monday': 'return shift.start.weekday() == 0',
    'tuesday': 'return shift.start.weekday() == 1',
    'wednesday': 'return shift.start.weekday() == 2',
    'thursday': 'return shift.start.weekday() == 3',
    'friday': 'return shift.start.weekday() == 4',
}
def parse_cell(day:date, cell:str) -> list[Timespan]:
    if cell.casefold() == "all day":
        return [Timespan(datetime.combine(day, time.min), datetime.combine(day, time.max))]
    
    timespans = list()
    timespan_strs = cell.split(",")
    for timespan_str in timespan_strs:
        if '-' not in timespan_str:
            continue
        
        start_str, end_str = timespan_str.split("-")
        if end_str.strip().casefold() in ("midnight", "12am", "12:00am"):
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
        
        # Parse per-employee max hours
        try:
            max_hours = float(row.get("Employee Max Hours", None))
        except (ValueError, TypeError):
            max_hours = None
        
        # Favored Hours Preferences
        preferences = AveragePreference()
        if 'Favored Hours' in row:
            favored_hours = parse_cell(datetime.now().date(), row["Favored Hours"])
            favored_hours = [x.strip_date() for x in favored_hours if x != None]
            preferences.append(SpecificTODPreference(favored_hours))

        # Relative Time of Day Preferences (Morning, Afternoon, Evening)
        morning_preferences = row.get("Morning Shifts", 0)
        afternoon_shifts    = row.get("Afternoon Shifts", 0)
        evening_shifts      = row.get("Evening Shifts", 0)
        night_shifts        = row.get("Night Shifts", 0)
        if morning_preferences or afternoon_shifts or evening_shifts or night_shifts:
            preferences.append(RelativeTODPreference(morning_preferences, afternoon_shifts, evening_shifts, night_shifts))
        
        # Shift mixins
        if 'Mixins' in row:
            preferences.append(MixinPreference(row["Mixins"]))
        
        # Tags are pre-defined mixins
        if 'Tags' in row and row['Tags'] != None:
            tag_preferences = list()
            for tag in row.get('Tags', '').split(','):
                tag = tag.strip().casefold()
                if tag in TAG_DEFINITIONS: tag_preferences.append(MixinPreference(TAG_DEFINITIONS[tag]))
            if tag_preferences:
                preferences.append(MaxPreference(tag_preferences), 7)       
            
        # Add employee to dictionary
        employees[name] = Employee(tenure=tenure, preferences=preferences, preferred_hours=preferred_hours, maximum_hours=max_hours)
    return employees

def parse_availability(raw_availability_data:pd.DataFrame, employees: dict[str, Employee]):
    for _, row in raw_availability_data.iterrows():
        name = row["Employee"]
        if name not in employees:
            continue
        
        availability = set()
        for column in raw_availability_data.columns:
            # If the column is a date, parse. Otherwise skip
            day = None
            
            try:
                day = datetime.strptime(column, "%B %d, %Y").date()
            except ValueError:
                pass
            
            try:
                day = datetime.strptime(column, "%b %d, %Y").date()
            except ValueError:
                pass
            
            if pd.isna(row[column]) or day == None:
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
    
    import modules.solver as solver
    res = solver.create_schedule(to_fill, employees)
    print(res != None)
    
    print("Done!")