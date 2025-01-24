from ortools.sat.python import cp_model
from dataclasses import dataclass
from modules.dtypes import Timespan, Employee
from datetime import timedelta, time, datetime, date
import warnings
from streamlit import cache_data
import decimal

def drange(x, y, jump):
    x = decimal.Decimal(x)
    while x < y:
        yield float(x)
        x += decimal.Decimal(jump)
    
def tfloat(time:time) -> float:
    return time.hour + time.minute / 60

def floatt(x:float) -> time:
    return time(int(x), int((x % 1) * 60))

def rfrac(x:float, frac:float):
    if frac < 1:
        frac = 1 / frac
    return round(x * frac) / frac

@cache_data
def create_schedule(
        to_schedule: list[tuple[str, Timespan]],
        employees: dict[str, Employee],
        solver_max_time=10,
        solver_seed=0,
        max_hours_per_week=18,
        shift_lengths=[3, 4],
        min_one_shift_per_employee=False,
        absolute_shift_minimum_length=2.5,
        max_shifts_per_day=1,
        shift_granularity=1
    ) -> list[tuple[str, str, Timespan]] | None:
    """
    May take a while to run if there are many possible shifts.
    Returns a list of tuples containing the employee name, position scheduled, and shift timespan.
    """
    
    model = cp_model.CpModel()
    
    # Create a list of all possible shifts on each position
    all_shifts:list[tuple[tuple[int, str], Timespan]] = []
    for pid, (position, timespan) in enumerate(to_schedule):
        timespan_time = timespan.strip_date()
        # drange(rfrac(tfloat(timespan_time.start), shift_granularity), rfrac(tfloat(timespan_time.end), shift_granularity), shift_granularity):
        for possible_start in range(timespan_time.start.hour, timespan_time.end.hour):
            for length in shift_lengths:
                start_time = time(possible_start)
                
                if start_time < timespan_time.start: start_time = timespan_time.start
                if possible_start + length > 23:     end_time = time(23, 59)
                else:                                end_time = time(possible_start + length)
                if end_time   > timespan_time.end:   end_time = timespan_time.end
                
                start = datetime.combine(timespan.start.date(), start_time)
                end   = datetime.combine(timespan.end.date(), end_time)
                shift = Timespan(start, end)
                
                # Constraints: No shifts shorter than the minimum time
                # This occurs when the shift is at the end of the day
                if shift.length.total_seconds() < absolute_shift_minimum_length * 3600:
                    continue
                if shift.length.total_seconds() > max(shift_lengths) * 3600:
                    continue
                
                # Append shift to list of all shifts
                if shift.strip_date() in timespan_time:
                    all_shifts.append(((pid, position), shift))
    
    if len(all_shifts) == 0:
        print("No shifts to schedule.")
        return None

    # Generate corresponding variables for each shift
    shift_vars:dict[tuple[str, int, Timespan], cp_model.IntVar] = dict()
    for emp_name, emp_data in employees.items():
        for (pid, pname), shift in all_shifts:
            if pname.strip() in emp_data.positions:
                shift_vars[(emp_name, pid, shift)] = model.NewBoolVar(f'shift_e{emp_name}_p{pid}_s{shift}')
    
    # Constraints: Each employee must work at least one shift per scheduling period
    if min_one_shift_per_employee:
        for emp_name, emp_data in employees.items():
            possible_shifts = [shift_vars[(emp_name, pid, shift)] for (pid, _), shift in all_shifts if (emp_name, pid, shift) in shift_vars]
            if len(possible_shifts) > 0:
                model.Add(sum(possible_shifts) >= 1)
            else:
                print(f"Employee {emp_name} has not qualified for any shifts. Quals: {emp_data.positions} Positions: {set(p for p, _ in to_schedule)}")
        
    # Constraints: Ensure every position has exactly 1 employee at all times
    for pid, (position, timespan) in enumerate(to_schedule):
        MINS_PER_CHECK = 5
        current_time = timespan.start
        while current_time <= timespan.end:
            # Get all shifts that overlap with the current time
            shifts_at_time = [shift_vars[(emp_name, pid_s, shift)] for emp_name, pid_s, shift in shift_vars if pid == pid_s and shift.overlaps_with(Timespan(current_time, current_time + timedelta(minutes=MINS_PER_CHECK)))]
            # Add a constraint that there must be exactly 1 employee working at this time
            model.Add(sum(shifts_at_time) == 1)
            current_time += timedelta(minutes=MINS_PER_CHECK)
    
    # Constraints: Ensure no overlapping shifts for the same employee
    for emp_name_1, pid_1, shift_1 in shift_vars:
        for emp_name_2, pid_2, shift_2 in shift_vars:
            if emp_name_1 == emp_name_2 and shift_1.overlaps_with(shift_2) and ((shift_1 != shift_2) or (shift_1 == shift_2 and pid_1 != pid_2)):
                model.Add(shift_vars[(emp_name_1, pid_1, shift_1)] + shift_vars[(emp_name_2, pid_2, shift_2)] <= 1)
    
    # Constraints: Limit the number of shifts each employee can work per day
    for emp_name in employees.keys():
        all_shifts_per_day:dict[int, list[cp_model.IntVar]] = dict() # maps day -> list of shifts
        for pid, (position, timespan) in enumerate(to_schedule):
            day = timespan.start.date().day
            shifts_for_emp = [shift_vars[(emp_name_s, pid, shift)] for emp_name_s, pid_s, shift in shift_vars if emp_name_s == emp_name and pid == pid_s]
            
            if day not in all_shifts_per_day:
                all_shifts_per_day[day] = []
            all_shifts_per_day[day].extend(shifts_for_emp)
        
        for day, shifts in all_shifts_per_day.items():
            model.Add(sum(shifts) <= max_shifts_per_day)
    
    
    # Constraints: Limit the total number of hours each employee can work per week
    # Also: Huertistic to minimize deviation from preferred hours
    # Also: Huertistic to minimize time people work while unavailable
    deviation_terms = []
    for week in set(shift.start.date().isocalendar().week for _, shift in to_schedule):
        for emp_name, emp_data in employees.items():
            total_time_worked = sum(
                int(shift.length.total_seconds()) * shift_vars[(emp_name_s, pid_s, shift)]
                for emp_name_s, pid_s, shift in shift_vars
                if emp_name_s == emp_name and shift.start.date().isocalendar().week == week
            )
            model.Add(total_time_worked <= max_hours_per_week * 3600)
            if emp_data.maximum_hours != None and emp_data.maximum_hours > 0:
                model.Add(total_time_worked <= emp_data.maximum_hours * 3600)
            
            # Hueristic: Minimizing deviation from preferred hours
            # Note: do hueristic here to not create a new varaible for total_time_worked
            
            if emp_data.preferred_hours == None or float(emp_data.preferred_hours) in (0.0, float('inf'), float('-inf'), float('nan')):
                continue
        
            preferred_time = int(emp_data.preferred_hours * 3600)
            preferred_time = max(0, preferred_time)
            preferred_time = min(max_hours_per_week * 3600, preferred_time)
            
            over_preferred = model.NewBoolVar(f'over_preferred_e{emp_name}')
            under_preferred = model.NewBoolVar(f'under_preferred_e{emp_name}')
            model.Add(over_preferred + under_preferred == 1)
            
            deviation_from_preferred = model.NewIntVar(0, 3600*max_hours_per_week, f'deviation_e{emp_name}')
            model.Add(total_time_worked - preferred_time <= deviation_from_preferred).OnlyEnforceIf(over_preferred)
            model.Add(preferred_time - total_time_worked <= deviation_from_preferred).OnlyEnforceIf(under_preferred)
            model.Add(total_time_worked - preferred_time >= 0).OnlyEnforceIf(over_preferred)
            model.Add(total_time_worked - preferred_time <= 0).OnlyEnforceIf(under_preferred)
            
            percent_difference = model.NewIntVar(0, 100, f'percent_diff_e{emp_name}')
            model.AddDivisionEquality(percent_difference, 100 * deviation_from_preferred, preferred_time)
            
            deviation_terms.append(percent_difference * emp_data.deviation_weight * (emp_data.tenure + 1))

    # Constraints: Employees cannot work closing then open the next day
    # for emp_name, emp_data in employees.items():
    #     for pid, (position, timespan) in enumerate(to_schedule):
    #         shifts_for_emp = [ (shift_vars[(emp_name_s, pid_s, shift)], shift) for emp_name_s, pid_s, shift in shift_vars if emp_name_s == emp_name ]
    #         shifts_for_emp.sort(key=lambda x: x[1].start)
            
            
        
    # Hueristic: Maximizing shift preferences
    satisfaction_terms = []
    for emp_name, pid, shift in shift_vars:
        employee = employees[emp_name]
        satisfaction = employee.get_shift_preference(shift)
        satisfaction_terms.append(shift_vars[(emp_name, pid, shift)] * satisfaction * employee.preference_weight * (employee.tenure + 1))
        
    # Hueristic: Minimizing time worked while unavailable
    hours_worked_unavailable_terms = []
    for emp_name, pid, shift in shift_vars:
        employee = employees[emp_name]
        is_available = any(shift in timespan for timespan in employee.availability)
        if not is_available:
            hours_worked_unavailable_terms.append( shift_vars[(emp_name, pid, shift)] * int(shift.length.total_seconds()) )
        
    # Minimize the deviation from preferred hours and maximize satisfaction
    model.Minimize(5 * sum(deviation_terms) - sum(satisfaction_terms) + 10_000_000 * sum(hours_worked_unavailable_terms))

    # Solving the model
    solver = cp_model.CpSolver()
    solver.parameters.random_seed = solver_seed
    # solver.parameters.log_to_stdout = True
    # solver.parameters.log_search_progress = True
    solver.parameters.linearization_level = 2   # Use more aggressive linearization
    #solver.parameters.use_branching_in_lp = True
    solver.parameters.optimize_with_core = True
    
    if solver_max_time > 0: solver.parameters.max_time_in_seconds = solver_max_time
    
    status = solver.Solve(model)

    if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
        schedule = list()
        pid_to_position = {pid: position for pid, (position, _) in enumerate(to_schedule)}
        for (emp_name, pid, shift), var in shift_vars.items():
            if solver.Value(var) == 0: continue
            schedule.append((emp_name, pid_to_position[pid], shift))
        return schedule
    else:
        err_text = "Failed to schedule shifts. Ensure you have enough employees to cover all shifts!\n"
        # for var_index in solver.ResponseProto():
        #     print(var_index, model.VarIndexToVarProto(var_index))
        return None
