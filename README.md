
# Employee Scheduler

Are you a lazy manager? I certainly am. This application allows you to schedule employees based on their availability, preferences, and constraints. It uses hueristics and linear programming to create the best possible schedule where every shift is filled and *most* employees are happy.

# Table of Contents

- [Employee Scheduler](#employee-scheduler)
- [Table of Contents](#table-of-contents)
- [Overview](#overview)
- [Technologies](#technologies)
- [Setup](#setup)
- [Usage](#usage)
  - [Tags](#tags)
  - [Mixins](#mixins)
  - [Downloading Availability](#downloading-availability)
  - [Exporting Schedule](#exporting-schedule)

# Overview

Schedule employees on [TCPHumanity](https://www.humanity.com/app/) based on their availability, preferences, and constraints!

![Employee Scheduler](./github/appshot.png)

Easily export this schedule for quick upload and speedy turnaround time.

# Technologies

To create this, we used:

- [Streamlit](https://streamlit.io): 1.38.0
- [Google OrTools](https://developers.google.com/optimization/): 9.10.4067
- [Pandas](https://pandas.pydata.org/): 2.2.2
- [Dateparser](https://dateparser.readthedocs.io/en/latest/): 1.2.0
- [Streamlit-Calendar](https://discuss.streamlit.io/t/new-component-streamlit-calendar-a-new-way-to-create-calendar-view-in-streamlit/48383): 1.2.0

# Setup

**Poetry**
```bash
poetry install
poetry run streamlit run app.py
```

The website should be available at [localhost:8501](http://localhost:8501). It is also deployed on 

# Usage

First, gather your employee's preferences and save them in a CSV file with the following columns:

| Employee | Tenure                  | Preferred Hours                      | Employee Max Hours               | Morning Shifts                        | Afternoon Shifts                      | Evening Shifts                       | Night Shifts                          | Mixins            | Tags              | Favored Hours                             |
| -------- | ----------------------- | ------------------------------------ | -------------------------------- | ------------------------------------- | ------------------------------------- | ------------------------------------ | ------------------------------------- | ----------------- | ----------------- | ----------------------------------------- |
| <name>   | <weight of preferences> | <number of weekly hours they prefer> | <max weekly hours they can work> | <preference for shifts starting 8-12> | <preference for shifts starting 12-4> | <preference for shifts starting 4-8> | <preference for shifts starting 8-00> | <described below> | <described below> | <comma-separated list of preferred times> |
| John Doe | 3                       | 40                                   | 50                               | 3                                     | 2                                     | 1                                    | 0                                     |                   |                   | 08:00 AM - 09:00 AM, 08:00 PM - 10:00 PM  |

Note that the only required columns are:
- Employee (Name)
- Tenure
- Preferred Hours

The other columns are optional and can be left blank or omitted.

## Tags

There are many predefined tags that allow you to further customize individual employee preferences. These tags are:
- morning: employee prefers morning shifts
- afternoon: employee prefers afternoon shifts
- evening: employee prefers evening shifts
- night: employee prefers night shifts
- closing: employee prefers closing shifts (shifts starting after 8PM)
- opening: employee prefers opening shifts (shifts starting before 9AM)
- weekend: employee prefers weekend shifts
- noweeekend: employee prefers no weekend shifts
- sunday: employee prefers Sunday shifts
- \<weekday\>: employee prefers shifts on a specific day of the week (e.g. monday, tuesday, wednesday, thursday, friday, saturday)

## Mixins

> [!CAUTION]
> Mixins are complex and can easily cause security issues.

Mixins are python functions that will be executed on a specific shift and should return a score representing that employee's weight for that shift.

For usage, see tag definitions in [modules/parse_data.py](https://github.com/Pop101/EmployeeScheduler/blob/main/modules/parse_data.py) and mixin definition in [modules/dtypes.py](https://github.com/Pop101/EmployeeScheduler/blob/main/modules/dtypes.py#L239).

## Downloading Availability

This application is designed to work with [TCPHumanity](https://www.humanity.com/app/). As such, it can easily download and parse the availability reports. To run one, simply open the reports tab in humanity:

![Humanity Reports](./github/availability_report.png)

Then, upload the availability report to the application!

## Exporting Schedule

When you are satisfied with the created schedule, you can download it to a local CSV. To upload this to [TCPHumanity](https://www.humanity.com/app/), simply open the schedule tab and upload the CSV file!

![Uploading the Schedule](./github/import_sched_humanity.png)