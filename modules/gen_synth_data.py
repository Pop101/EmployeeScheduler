import random
import pandas as pd
from itertools import chain
from datetime import datetime, time, timedelta, date

names = [
    "Liam", "Emma", "Noah", "Olivia", "William", "Ava", "James", "Isabella", 
    "Benjamin", "Sophia", "Lucas", "Mia", "Henry", "Amelia", "Alexander", 
    "Harper", "Jackson", "Evelyn", "Sebastian", "Abigail", "Aiden", "Emily", 
    # "Matthew", "Ella", "Elijah", "Madison", "Daniel", "Scarlett", "Mason", "Victoria",
    # "Michael", "Aria", "Logan", "Grace", "David", "Chloe", "Oliver", "Camila",
    # "Joseph", "Penelope", "Gabriel", "Riley", "Samuel", "Layla", "Carter", "Lillian",
    # "Anthony", "Nora", "John", "Zoey", "Dylan", "Mila", "Luke", "Avery", "Christopher",
]

positions = [
    "The MILL Maker Desk", "The MILL Maker Rover"
]

def choices(itr, min_count=1):
    itr = list(itr)
    assert min_count <= len(itr)
    return random.sample(itr, k=random.randint(min_count, len(itr)))

def generate_data(
        start_date: date = None,
        end_date: date = None,
        names: list[str] = names,
        seed: int = None
    ) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Generates synthetic data for the scheduling problem.
    random.seed is based on the current day
    Returns 'availability_report', 'to_fill', 'preferences'
    """
    
    if not start_date: start_date = datetime.now().date()
    random.seed(seed or start_date.toordinal())
    
    if not end_date: end_date = start_date + timedelta(weeks=1)
    
    dates = list(
        map(lambda d: d.strftime("%B %d, %Y"), 
            pd.date_range(start=start_date, end=end_date, freq='D')
        )
    )
    
    times = list(
        chain(
            map(lambda x: x.time(), pd.date_range(start='2022-01-01 08:00:00', end='2022-01-01 11:00:00', freq='h')),
            [time(23, 59)]
        )
    )            

    availability_report = pd.DataFrame(columns=["Employee", "Positions"] + dates)
    to_fill = pd.DataFrame(columns=["Position", "Date", "Hours"])
    preferences = pd.DataFrame(columns=["Employee", "Tenure", "Preferred Hours", "Morning Shifts", "Afternoon Shifts", "Evening Shifts", "Favored Hours"])

    for i, name in enumerate(names):
        # Assign qualifications
        positions_assigned = choices(positions, min_count=1)
        
        # Assign availability
        availability = list()
        for date in dates:
            today_times = sorted(choices(times, min_count=0))
            if len(today_times) % 2 == 1: today_times = today_times[:-1]
            
            date_times_list = list()
            it = map(lambda t: t.strftime("%I:%M %p"), today_times)
            for start, end in zip(it, it):
                date_times_list.append(f'{start} - {end}')
            availability += ', '.join(date_times_list),
        
        # Assign preferred hours
        favored_hours = list()
        for date in dates:
            today_times = sorted(choices(times, min_count=2))
            if len(today_times) % 2 == 1: today_times = today_times[:-1]
            
            date_times_list = list()
            it = map(lambda t: t.strftime("%I:%M %p"), today_times)
            for start, end in zip(it, it):
                date_times_list.append(f'{start} - {end}')
            favored_hours += ', '.join(date_times_list),
        
        # Assign tenure & preferred hours
        tenure = random.randint(0, 5)
        preferred_hours = random.randint(5, 20)
        
        # Add rows
        availability_report.loc[i] = [name, ', '.join(positions_assigned)] + availability
        preferences.loc[i] = [
            name,
            tenure,
            preferred_hours,
            random.randint(0, 10),   # Morning Shifts
            random.randint(0, 10),   # Afternoon Shifts
            random.randint(0, 10),   # Evening Shifts
            ', '.join(favored_hours) # Favored Hours
        ]
        
    # Fill in the positions to fill
    for date in dates:
        for position in positions:
            if position == "The MILL Maker Desk":
                start_time = time(8, 15).strftime("%I:%M %p")
                end_time = time(23, 59).strftime("%I:%M %p")
            elif position == "The MILL Maker Rover":
                start_time = time(11, 00).strftime("%I:%M %p")
                end_time = time(23, 59).strftime("%I:%M %p")
            if datetime.strptime(date, "%B %d, %Y").weekday() >= 5:
                start_time = time(12, 45).strftime("%I:%M %p")
                
            to_fill.loc[len(to_fill)] = [position, date, f'{start_time} - {end_time}']

    return availability_report, to_fill, preferences

if __name__ == "__main__":
    availability_report, to_fill, preferences = generate_data()
        
    availability_report.to_csv("availability_report.csv", index=False)
    to_fill.to_csv("to_fill.csv", index=False)
    preferences.to_csv("preferences.csv", index=False)