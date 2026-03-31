import random
from satisfaction_curve import Satisfaction
from constants import *

d = GRAVITY * 2

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
