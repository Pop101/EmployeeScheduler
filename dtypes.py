from datetime import datetime, timedelta, time, date
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Timespan(object):
    """Represents a timespan between two points in time, both inclusive."""
    
    start: datetime | time
    end: datetime | time
    
    def __post_init__(self):
        if type(self.start) != type(self.end):
            raise TypeError("Start and end must be of the same type.")
        if not isinstance(self.start, (datetime, time)):
            raise TypeError("Start and end must be of type datetime or time.")
        if self.start > self.end:
            raise ValueError("Start must be before end.")

    def strip_date(self) -> 'Timespan':
        if isinstance(self.start, datetime):
            start = self.start.time()
        if isinstance(self.end, datetime):
            end = self.end.time()
        return Timespan(start, end)
    
    def with_date(self, day:date) -> 'Timespan':
        if isinstance(self.start, datetime):
            start = datetime.combine(day, self.start.time())
        if isinstance(self.end, datetime):
            end = datetime.combine(day, self.end.time())
        if start > end:
            raise ValueError("Timespan .with_date ill-defined for multi-day timespans.")
        return Timespan(start, end)
    
    def overlaps_with(self, other: 'Timespan') -> bool:
        if not isinstance(other, Timespan):
            raise TypeError("Can only check overlap with another Timespan.")
        
        if type(self.start) != type(other.start):
            my_start = self.start.time() if isinstance(self.start, datetime) else self.start
            other_start = other.start.time() if isinstance(other.start, datetime) else other.start
            
            my_end = self.end.time() if isinstance(self.end, datetime) else self.end
            other_end = other.end.time() if isinstance(other.end, datetime) else other.end
            
            return max(my_start, other_start) < min(my_end, other_end)
        return max(self.start, other.start) < min(self.end, other.end)
    
    @property
    def length(self) -> timedelta:
        if isinstance(self.start, datetime):
            return self.end - self.start
        if isinstance(self.start, time):
            start = datetime.combine(datetime.now(), self.start)
            end = datetime.combine(datetime.now(), self.end)
            return end - start
        
    def __repr__(self):
        return "Timespan(%r, %r)" % (self.start, self.end)

    def __eq__(self, other):
        if not isinstance(other, Timespan):
            return False
        return self.start == other.start and self.end == other.end

    def __ne__(self, other):
        return not self.__eq__(other)
    
    def __contains__(self, other):
        if isinstance(other, Timespan):
            if type(self.start) != type(other.start):
                return False
            return self.start <= other.start and other.end <= self.end
        elif isinstance(other, datetime):
            if not isinstance(self.start, datetime):
                return False
            return self.start <= other and other <= self.end
        elif isinstance(other, time):
            if not isinstance(self.start, time):
                return False
            return self.start <= other and other <= self.end
        else:
            raise TypeError("Cannot check containment with %r." % type(other))
    
    def __lt__(self, other):
        if isinstance(other, Timespan):
            my_start = self.start.time() if isinstance(self.start, datetime) else self.start
            other_start = other.start.time() if isinstance(other.start, datetime) else other.start
            return my_start < other_start
        elif isinstance(other, (datetime, time)):
            my_start = self.start.time() if isinstance(self.start, datetime) else self.start
            other_start = other.time() if isinstance(other.start, datetime) else other
            return my_start < other_start
        else:
            raise TypeError("Cannot compare Timespan with %r." % type(other))
    
    def __gt__(self, other):
        if isinstance(other, Timespan):
            my_end = self.end.time() if isinstance(self.end, datetime) else self.end
            other_end = other.end.time() if isinstance(other.end, datetime) else other.end
            return my_end > other_end
        elif isinstance(other, (datetime, time)):
            my_end = self.end.time() if isinstance(self.end, datetime) else self.end
            other_end = other.time() if isinstance(other, datetime) else other
            return my_end > other_end
        else:
            raise TypeError("Cannot compare Timespan with %r." % type(other))
    
    def __le__(self, other):
        return self.__lt__(other) or self.__eq__(other)
    
    def __ge__(self, other):
        return self.__gt__(other) or self.__eq__(other)
    
    def __add__(self, other):
        if not isinstance(other, (timedelta, datetime, Timespan, time)):
            raise TypeError("Cannot add %r to Timespan." % type(other))
        
        # Shift by timedelta
        if isinstance(other, timedelta):
            if isinstance(self.start, datetime):
                return Timespan(self.start + other, self.end + other)
            if isinstance(self.start, time):
                # addition between time and timedelta is not natively supported
                # cast to datetime then cast back to time
                my_start = datetime.combine(datetime.now(), self.start) + other
                my_end = datetime.combine(datetime.now(), self.end) + other
                return Timespan(my_start.time(), my_end.time())
        
        # Add start and end of timespan
        if isinstance(self.start, Timespan):
            return self.start + other + self.end
        
        # For other dtypes, expand the timeframe to include the other object
        if other in self:
            return self
        
        if isinstance(self.start, datetime):
            if isinstance(other, datetime):
                other_start = other
                other_end = other
            elif isinstance(other, time):
                other_start = datetime.combine(self.start.date(), other)
                other_end = datetime.combine(self.end.date(), other)
            return Timespan(min(self.start, other_start), max(self.end, other_end))
                
        if isinstance(self.start, time):
            if isinstance(other, datetime):
                other_start = other.time()
                other_end = other.time()
            elif isinstance(other, time):
                other_start = other
                other_end = other
            return Timespan(min(self.start, other_start), max(self.end, other_end))
        
        raise TypeError("Cannot add %r to Timespan." % type(other))
    
@dataclass()
class Employee:
    positions: set[str]        = field(default_factory=set)
    availability: set[Timespan]= field(default_factory=set)
    preferences: set[Timespan] = field(default_factory=set)
    preferred_hours: float     = 0.0 # The number of hours the employee prefers to work in a week
    tenure: int                = 0   # A general measure of how likely the employee is to get their preferences
    preference_weight: float   = 1.0 # A multiplier for how much the employee's preferred hours matter
    deviation_weight: float    = 1.0 # A multiplier for how much the employee's deviation from preferred hours matters
    
    def get_shift_preference(self, shift:Timespan):
        satisfaction = 0.0
        is_available = any(shift in timespan for timespan in self.availability)
        is_preferred = any(shift in timespan for timespan in self.preferences)
        
        if not is_available: satisfaction -= 1000
        if is_preferred: satisfaction += 5
        
        # People generally don't like working 2hr blocks
        if shift.length.total_seconds() <= 7200:
            satisfaction -= 1
        
        return satisfaction
    
    def satisfaction_details(self, shifts:list[Timespan]) -> tuple:
        weekly_deviations = list()
        weekly_satisfaction = list()
        for week in set(shift.start.date().isocalendar().week for shift in shifts):
            total_time_worked = sum(
                shift.length.total_seconds()
                for shift in shifts
                if shift.start.date().isocalendar().week == week
            ) / 3600
            
            weekly_deviations   += [abs(total_time_worked - self.preferred_hours)]
            weekly_satisfaction += [sum(self.get_shift_preference(shift) for shift in shifts)]
        
        return (
            self.deviation_weight  * sum(weekly_deviations),
            self.preference_weight * sum(weekly_satisfaction)
        )
    
    def calculate_satisfaction(self, shifts: list[Timespan]):
        """Calculates satisfaction identical to the solver's heuristic."""
        
        deviation, preference = self.satisfaction_details(shifts)
        return -5 * deviation + preference
