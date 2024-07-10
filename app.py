import streamlit as st
from datetime import datetime
import pandas as pd
from streamlit_calendar import calendar
from gen_synth_data import generate_data
import re
import parse_data
import solver

# Initialize session state
synthetic_data = generate_data()
if 'availability_report' not in st.session_state:
    st.session_state.availability_report = synthetic_data[0]
if 'to_fill' not in st.session_state:
    st.session_state.to_fill = synthetic_data[1]
if 'preferences' not in st.session_state:
    st.session_state.preferences = synthetic_data[2]
del synthetic_data

# Calendar
st.title("Employee Scheduling")

# Create file uploader dialog
@st.experimental_dialog("Upload CSV")
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

if st.button("Upload CSV"):
    file_dialog()
    
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

employees = parse_data.parse_employees(st.session_state.preferences)
parse_data.parse_availability(st.session_state.availability_report, employees)
shifts_to_fill = parse_data.parse_to_fill(st.session_state.to_fill)
weeks = set(shift.start.isocalendar().week for _, shift in shifts_to_fill)

# Schedule shifts
schedule = solver.create_schedule(shifts_to_fill, employees)

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
        "resources": list(
            {"id": position, "title": position, "building": position}
            for position in set(position for _, position, _ in schedule)
        ),
    })

    # Display employee satisfaction
    get_emp_times = lambda emp_name: [shift for name_s, _, shift in schedule if name_s == emp_name]
    get_tot_hours = lambda emp_name: sum(shift.length.total_seconds() / 3600 for shift in get_emp_times(emp_name))
    emp_sats = pd.DataFrame(
        [
            (emp_name, emp.tenure, get_tot_hours(emp_name), *emp.satisfaction_details(get_emp_times(emp_name)), emp.calculate_satisfaction(get_emp_times(emp_name)))
            for emp_name, emp in employees.items()
        ],
        columns=["Employee", "Tenure", "Hours Scheduled", "Deviation", "Preference", "Satisfaction"]
    )

    # Normalize the satisfaction values
    emp_sats["Deviation"] = emp_sats["Deviation"].fillna(0.0) / len(weeks)
    max_deviation = emp_sats["Deviation"].max()
    
    emp_sats["Preference"] = (emp_sats["Preference"] - emp_sats["Preference"].min()) / emp_sats["Preference"].max()
    emp_sats["Preference"] = emp_sats["Preference"].fillna(1.0) if emp_sats["Preference"].max() == 0 else emp_sats["Preference"].fillna(0.0)
    
    emp_sats["Satisfaction"] = (emp_sats["Satisfaction"] - emp_sats["Satisfaction"].min()) / emp_sats["Satisfaction"].max()
    emp_sats["Satisfaction"] = emp_sats["Satisfaction"].fillna(1.0) if emp_sats["Satisfaction"].max() == 0 else emp_sats["Satisfaction"].fillna(0.0)
    
    # Display the satisfaction values
    st.dataframe(emp_sats, hide_index=True, use_container_width = True, column_config={
        "Employee": st.column_config.TextColumn("Employee Name"),
        "Tenure": st.column_config.NumberColumn("Employee Tenure"),
        "Hours Scheduled": st.column_config.NumberColumn("Hours Scheduled", format="%.1f hr"),
        "Deviation": st.column_config.ProgressColumn("Deviation from Preferred Hours", help="More is worse", format="%.1f hr", min_value=0.0, max_value=max_deviation),
        "Preference": st.column_config.ProgressColumn("Shift Preference", format="%.2f%%", min_value=0.0, max_value=1.0),
        "Satisfaction": st.column_config.ProgressColumn("Satisfaction", format="%.2f%%", min_value=0.0, max_value=1.0),
    })