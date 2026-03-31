import random
from satisfaction_curve import Satisfaction
from constants import *
from enum import Enum
from dataclasses import dataclass

@dataclass
class Design:
    C: float                    # L/day
    use_nonpotable: bool
    np_threshold_L: float
    np_fraction_of_C: float

    roof_choice: str            # "none", "half", "whole"
    extra_catchment_area_m2: float
    extra_catchment_x: float
    extra_catchment_y: float
    catchment_tank_L: int

    storage_volume_m3: float
    storage_x: float
    storage_y: float
    use_tower: bool
    tower_height_m: float

    pump: str                   # "A", "B", "C"
    filter_location: str        # "upstream" or "downstream"
    filters: tuple              # e.g. ("200um", "5um", "1um")

    uv: str                     # "36W", "40W", "50W"
    chem: str                   # "chlorine", "ozone"

    power: str                  # "solar" or "diesel"
    n_batteries: int
    panel_model: str | None
    n_panels: int | None
    use_inverter: bool
    generator: bool

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

def evaluate_solution(solution: Design):
    pass