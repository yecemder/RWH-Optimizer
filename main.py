import random
from satisfaction_curve import Satisfaction

# Invariant constants
GRAVITY = 9.81  # m/s^2
DENSITY = 1000  # kg/m^3
PIPE_DIAMETER = 0.002 # m (2 mm)
PIPE_FRICTION_FACTOR = 0.05 # Dimensionless

REFERENCE_COST = 110_000    # Cost if all water shipped
COST_PER_DAY_SHIP = 90      # Cost of shipping per day that consumption is not met


# Parameters

# Satisfaction weights for each criterion (these can be adjusted based on importance)
# H weight: 16-25%
# M weight: 10-15%
# L weight: 5-9%
# Weights should sum to 1.0
CONSUMPTION_WEIGHT =    0.20    # H
RELATIVE_COST_WEIGHT =  0.20    # H
HEALTH_RISK_WEIGHT =    0.15    # M
GHG_EMISSIONS_WEIGHT =  0.15    # M
MAINTENANCES_WEIGHT =   0.10    # M
NON_POTABLE_WEIGHT =    0.07    # L
ON_DEMAND_FLOW_WEIGHT = 0.08    # L
RELIABILITY_WEIGHT =    0.05    # M




weights_sum = (CONSUMPTION_WEIGHT + RELATIVE_COST_WEIGHT + HEALTH_RISK_WEIGHT + GHG_EMISSIONS_WEIGHT +
                MAINTENANCES_WEIGHT + NON_POTABLE_WEIGHT + ON_DEMAND_FLOW_WEIGHT + RELIABILITY_WEIGHT)
assert abs(weights_sum - 1.0) < 1e-6, f"Weights must sum to 1.0, but they sum to {round(weights_sum, 5)}"


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
