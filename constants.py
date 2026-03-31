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