import streamlit as st
from datetime import datetime, date, timedelta
import pandas as pd
from streamlit_calendar import calendar

from modules.gen_synth_data import generate_data
import modules.parse_data as parse_data
import modules.solver as solver
from modules.streamlit_utils import load_css

import re
import random


# Inject style
load_css("./.streamlit/style.css")

# Initialize session state
seed = datetime.now().toordinal()
if 'seed' not in st.session_state:
    st.session_state.seed = seed

# Start & End Date
if 'start_date' not in st.session_state or date.today() - st.session_state.start_date > timedelta(days=7):
    # Set to most recent monday
    st.session_state.start_date = date.today() - timedelta(days=date.today().weekday())
if 'end_date' not in st.session_state or date.today() - st.session_state.start_date > timedelta(days=7):
    st.session_state.end_date = st.session_state.start_date + timedelta(weeks=1)

# Generate synthetic data
synthetic_data = generate_data(seed=st.session_state.seed, start_date=st.session_state.start_date, end_date=st.session_state.end_date)
if 'availability_report' not in st.session_state:
    st.session_state.availability_report = synthetic_data[0]
if 'to_fill' not in st.session_state:
    st.session_state.to_fill = synthetic_data[1]
if 'preferences' not in st.session_state:
    st.session_state.preferences = synthetic_data[2]
del synthetic_data

# Calendar
st.title("Employee Scheduling")

left, mid, right = st.columns(3)

# Create file uploader dialog
@st.dialog("Upload CSV")
def file_dialog():
    st.write("Upload your CSV file")
    st.write("Ensure data matches the shown data formats")
    files = st.file_uploader("Upload CSV", type=['csv'], accept_multiple_files=True)
    for file in files:
        name = re.sub(r"\.*", "", file.name).strip()
        name = re.sub(r"\s+", "_", name).casefold()
        if name == "availability_report":
            st.session_state.availability_report = pd.read_csv(file)
        elif name == "to_fill":
            st.session_state.to_fill = pd.read_csv(file)
        elif name == "preferences":
            st.session_state.preferences = pd.read_csv(file)
        else:
            file_label = st.selectbox(
                f"Please label {file.name}:",
                ("None", "Availability Report", "To Fill", "Preferences"),
                key=file.name+str(file.size)
            )
            if file_label == "Availability Report":
                st.session_state.availability_report = pd.read_csv(file)
            elif file_label == "To Fill":
                st.session_state.to_fill = pd.read_csv(file)
            elif file_label == "Preferences":
                st.session_state.preferences = pd.read_csv(file)
    st.write(f"Read {len(files)} files")
    
    apply = st.button("Apply Changes")
    if apply: st.rerun()

if st.button("Upload CSV"):
    file_dialog()
    
# Input start day and end day

start_date      = left.date_input("Start Date", st.session_state.start_date)
end_date        = mid.date_input("End Date",    st.session_state.end_date)
regenerate_data = right.button("Regenerate Shifts")

if regenerate_data:
    synthetic_data = generate_data(seed=st.session_state.seed, start_date=start_date, end_date=end_date)
    st.session_state.to_fill = synthetic_data[1]
    del synthetic_data
    
if start_date > end_date:
    st.error("Start date must be before end date")
else:
    st.session_state.start_date = start_date
    st.session_state.end_date = end_date

# Settings
with st.expander("Settings"):
    min_one_shift = st.checkbox("Require at least one shift per employee", value=False)
    max_hours     = st.number_input("Max hours per week", min_value=0, max_value=40, value=18)
    
# Display data
with st.expander("Employees and Preferences"):
    st.session_state.preferences = st.data_editor(
        st.session_state.preferences.reset_index(drop=True),
        hide_index = True,
        num_rows="dynamic",
        use_container_width = True
    )

with st.expander("Availability Report"):
    st.session_state.availability_report = st.data_editor(
        st.session_state.availability_report.reset_index(drop=True),
        hide_index = True,
        num_rows="dynamic",
        use_container_width = True
    )

with st.expander("To Fill"):
    st.session_state.to_fill = st.data_editor(
        st.session_state.to_fill.reset_index(drop=True),
        hide_index = True,
        num_rows="dynamic",
        use_container_width = True
    )

# Schedule shifts
def reseed():
    st.session_state.seed = random.randint(0, 365)
    
left, right = st.columns(2)
should_reschedule = left.button("Schedule Shifts")
should_reseed     = right.button("Reseed & Schedule")

if should_reseed:
    st.session_state.seed = random.randint(0, 365) + st.session_state.seed
    
if should_reschedule or should_reseed:
    st.write(f"Seed: {st.session_state.seed}")
    
    employees = parse_data.parse_employees(st.session_state.preferences)
    parse_data.parse_availability(st.session_state.availability_report, employees)
    shifts_to_fill = parse_data.parse_to_fill(st.session_state.to_fill)
    weeks = set(shift.start.isocalendar().week for _, shift in shifts_to_fill)

    # Create a None-Employee who will ensure we can always generate a schedule
    # but has no availability
    #employees[None] = solver.Employee(tenure=0, preferences=solver.AveragePreference(), preferred_hours=None)
    
    # Schedule shifts
    schedule = solver.create_schedule(
        shifts_to_fill,
        employees,
        min_one_shift_per_employee=bool(min_one_shift),
        max_hours_per_week=max_hours,
        solver_seed=st.session_state.seed
    )

    if schedule == None:
        st.write("Failed to schedule shifts. Ensure you have enough employees to cover all shifts!")
    else:
        schedule_json = [
            {
                "title": f'{emp_name} - {position}',
                "start": timespan.start.isoformat(),
                "end": timespan.end.isoformat(),
                "resourceId": position,
            }    
            for emp_name, position, timespan in schedule
        ]
        
        calendar(events=schedule_json, callbacks=[], options={
            #"selectable": "true",
            "initialView": "resourceTimeGridDay", # Ideally resourceTimeGridDay
            "resourceGroupField": "building",
            #"datesAboveResources": True,
            "initialDate": st.session_state.start_date.isoformat(),
            "validRange": {
                "start": st.session_state.start_date.isoformat(),
                "end": st.session_state.end_date.isoformat()
            },
            "resources": list(
                {"id": position, "title": position, "building": position}
                for position in set(position for _, position, _ in schedule)
            ),
        })

        # Display employee Dissatisfaction
        get_emp_times = lambda emp_name: [shift for name_s, _, shift in schedule if name_s == emp_name]
        get_tot_hours = lambda emp_name: sum(shift.length.total_seconds() / 3600 for shift in get_emp_times(emp_name))
        emp_sats = pd.DataFrame(
            [
                (emp_name, emp.tenure, get_tot_hours(emp_name), *emp.satisfaction_details(get_emp_times(emp_name)), emp.calculate_satisfaction(get_emp_times(emp_name)))
                for emp_name, emp in employees.items()
            ],
            columns=["Employee", "Tenure", "Hours Scheduled", "Deviation", "Preference", "Dissatisfaction"]
        )

        # Normalize the Dissatisfaction values
        emp_sats["Deviation"] = emp_sats["Deviation"].fillna(0.0) / len(weeks)
        max_deviation = emp_sats["Deviation"].max()
        
        emp_sats["Preference"] = emp_sats["Preference"].apply(abs)
        emp_sats["Preference"] = (emp_sats["Preference"] - emp_sats["Preference"].min()) / emp_sats["Preference"].max()
        emp_sats["Preference"] = emp_sats["Preference"].fillna(1.0) if emp_sats["Preference"].max() == 0 else emp_sats["Preference"].fillna(0.0)
        
        emp_sats["Dissatisfaction"] = emp_sats["Dissatisfaction"].apply(abs)
        emp_sats["Dissatisfaction"] = (emp_sats["Dissatisfaction"] - emp_sats["Dissatisfaction"].min()) / emp_sats["Dissatisfaction"].max()
        emp_sats["Dissatisfaction"] = emp_sats["Dissatisfaction"].fillna(1.0) if emp_sats["Dissatisfaction"].max() == 0 else emp_sats["Dissatisfaction"].fillna(0.0)
        
        # Display the Dissatisfaction values
        st.dataframe(emp_sats, hide_index=True, use_container_width = True, column_config={
            "Employee": st.column_config.TextColumn("Employee Name"),
            "Tenure": st.column_config.NumberColumn("Employee Tenure"),
            "Hours Scheduled": st.column_config.NumberColumn("Hours Scheduled", format="%.1f hr"),
            "Deviation": st.column_config.ProgressColumn("Deviation from Preferred Hours", help="More is worse", format="%.1f hr", min_value=0.0, max_value=max_deviation),
            "Preference": st.column_config.ProgressColumn("Shift Preference", format="%.2f%%", min_value=0.0, max_value=1.0),
            "Dissatisfaction": st.column_config.ProgressColumn("Dissatisfaction", format="%.2f%%", min_value=0.0, max_value=1.0),
        })