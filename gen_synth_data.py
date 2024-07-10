import random
import pandas as pd
from itertools import chain
from datetime import datetime, time, timedelta

names = [
    "Liam", "Emma", "Noah", "Olivia", "William", "Ava", "James", "Isabella", 
    "Benjamin", "Sophia", "Lucas", "Mia", "Henry", "Amelia", "Alexander", 
    "Harper", "Jackson", "Evelyn", "Sebastian", "Abigail", "Aiden", "Emily", 
    "Matthew", "Ella", "Elijah", "Madison", "Daniel", "Scarlett", "Mason", "Victoria",
    "Michael", "Aria", "Logan", "Grace", "David", "Chloe", "Oliver", "Camila",
    "Joseph", "Penelope", "Gabriel", "Riley", "Samuel", "Layla", "Carter", "Lillian",
]

positions = [
    "The MILL Maker Desk", "The MILL Maker Rover"
]

def choices(itr, min_count=1):
    itr = list(itr)
    assert min_count <= len(itr)
    return random.sample(itr, k=random.randint(min_count, len(itr)))

def generate_data() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Generates synthetic data for the scheduling problem.
    random.seed is based on the current day
    Returns 'availability_report', 'to_fill', 'preferences'
    """
    today = datetime.now().date()
    random.seed(today.day)
    
    dates = list(
        map(lambda d: d.strftime("%B %d, %Y"), 
            pd.date_range(start=today, end=today + timedelta(weeks=1), freq='D')
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
    preferences = pd.DataFrame(columns=["Employee", "Tenure", "Preferred Hours", "Favored Hours"])

    for i, name in enumerate(names):
        # Assign qualifications
        positions_assigned = choices(positions, min_count=1)
        
        # Assign availability
        availability = list()
        for date in dates:
            today_times = sorted(choices(times, min_count=4))
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
        preferences.loc[i] = [name, tenure, preferred_hours, ', '.join(favored_hours)]
        
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
                start_time = time(12, 00).strftime("%I:%M %p")
                
            to_fill.loc[len(to_fill)] = [position, date, f'{start_time} - {end_time}']

    return availability_report, to_fill, preferences

if __name__ == "__main__":
    availability_report, to_fill, preferences = generate_data()
        
    availability_report.to_csv("availability_report.csv", index=False)
    to_fill.to_csv("to_fill.csv", index=False)
    preferences.to_csv("preferences.csv", index=False)