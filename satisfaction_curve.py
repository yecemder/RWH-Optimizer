from constants import *

class Satisfaction:
    def __init__(self, 
                 weight: float, 
                 min: float,
                 min_is_req: bool,
                 max: float,
                 max_is_req: bool,
                 is_increasing: bool):
        self.weight = weight
        self.min = min
        self.min_is_req = min_is_req  # True if values below min are not acceptable, False if they are acceptable but less satisfying
        self.max = max
        self.max_is_req = max_is_req  # True if values above max are not acceptable, False if they are acceptable but less satisfying
        self.is_increasing = is_increasing  # True if higher values are better, False if lower values are better
    
    # Calculate satisfaction based on the value and the defined curve
    # Returns a value between 0 and 1, or None if the value is outside the required range
    def calculate_satisfaction(self, value: float) -> float | None:
        if self.min_is_req and value < self.min:
            return None
        if self.max_is_req and value > self.max:
            return None
        
        if self.is_increasing:
            if value <= self.min:
                return 0.0
            elif value >= self.max:
                return 1.0
            else:
                return 0.5 * (1 - cos(pi * (value - self.min) / (self.max - self.min)))
        else:
            if value <= self.min:
                return 1.0
            elif value >= self.max:
                return 0.0
            else:
                return 0.5 * (1 + cos(pi * (value - self.min) / (self.max - self.min)))
    
    # Calculate the weighted satisfaction by multiplying the satisfaction by the weight
    def calculate_weighted_satisfaction(self, value: float) -> float | None:
        satisfaction = self.calculate_satisfaction(value)
        if satisfaction is None:
            return None
        return satisfaction * self.weight
    
    def __repr__(self):
        return f"Satisfaction(weight={self.weight}, min={self.min}, min_is_req={self.min_is_req}, max={self.max}, max_is_req={self.max_is_req}, is_increasing={self.is_increasing})"
    

# Order: weight, min, min_is_req, max, max_is_req, is_increasing
CONSUMPTION = Satisfaction(
    CONSUMPTION_WEIGHT,
    125,
    True,
    745,
    False,
    True
)

REL_COST = Satisfaction(
    RELATIVE_COST_WEIGHT,
    0.3,
    False,
    1.15,
    True,
    False
)

HEALTH_RISK = Satisfaction(
    HEALTH_RISK_WEIGHT,
    1,
    False,
    24,
    True,
    False
)

GHG_EMISSIONS = Satisfaction(
    GHG_EMISSIONS_WEIGHT,
    15,
    False,
    110,
    True,
    False
)

MAINTENANCES = Satisfaction(
    MAINTENANCES_WEIGHT,
    10,
    False,
    60,
    True,
    False
)

NON_POTABLE = Satisfaction(
    NON_POTABLE_WEIGHT,
    0,
    False,
    0.3,
    False,
    True
)

ON_DEMAND_FLOW = Satisfaction(
    ON_DEMAND_FLOW_WEIGHT,
    18,
    True,
    100,
    False,
    True
)

RELIABILITY = Satisfaction(
    RELIABILITY_WEIGHT,
    200,
    True,
    365,
    False,
    True
)