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

sum_weights = ( CONSUMPTION_WEIGHT + RELATIVE_COST_WEIGHT + HEALTH_RISK_WEIGHT + GHG_EMISSIONS_WEIGHT +
                MAINTENANCES_WEIGHT + NON_POTABLE_WEIGHT + ON_DEMAND_FLOW_WEIGHT + RELIABILITY_WEIGHT)

assert abs(sum_weights - 1.0) < 1e-6, f"Weights must sum to 1.0, but they sum to {round(sum_weights, 5)}"

# Invariant constants
# ---------------------------------
GRAVITY = 9.81  # m/s^2
DENSITY = 1000  # kg/m^3
PIPE_DIAMETER = 0.002 # m (2 mm)
PIPE_FRICTION_FACTOR = 0.05 # Dimensionless

REFERENCE_COST = 110_000    # Cost if all water shipped
COST_PER_DAY_SHIP = 90      # Cost of shipping per day that consumption is not met

# Part constants
HALF_ROOF_CATCHMENT_AREA = 50 # m^2
HALF_ROOF_CATCHMENT_COST = 150 # $
FULL_ROOF_CATCHMENT_AREA = 100 # m^2
FULL_ROOF_CATCHMENT_COST = 350 # $

# Tank constants
TANK_1_CAPACITY = 400 # liters
TANK_1_COST = 200 # $

TANK_2_CAPACITY = 1500 # liters
TANK_2_COST = 500 # $

TANK_3_CAPACITY = 2500 # liters
TANK_3_COST = 900 # $

TANK_4_CAPACITY = 5000 # liters
TANK_4_COST = 1500 # $

TANK_5_CAPACITY = 10000 # liters
TANK_5_COST = 2000 # $

MAX_STORAGE_TANK_CAPACITY = 50 * 1000 # liters (50 m^3)
COST_PER_M3_STORAGE_TANK = 300 # $ per m^3 of storage tank capacity

WATER_HEIGHT_PUMPING = 1.5 # m (assumed added height difference when pumping)
WATER_HEIGHT_SUPPLYING = 0 # m (assumed height difference when supplying water to the house)

WATER_LEVEL_SENSOR_COST = 250 # $ per sensor

# Cost of a tower is A(V[m^3]^1.6) + B(h[m]^1.8)
TOWER_COST_A = 25 # $ per m^3 of volume
TOWER_COST_B = 150 # $ per m of height

PIPING_COST_PER_METER = 40 # $ per meter of piping

# K values
LOSS_COEFF_TO_STORAGE = 8
LOSS_COEFF_TO_HOUSE = 12

# Filter constants
CF_EXP = 12431

FILTER_200UM_INITIAL_COST = 100
FILTER_200UM_REPLACEMENT_COST = 50
FILTER_200UM_CF = 0.00417

FILTER_5UM_INITIAL_COST = 110
FILTER_5UM_REPLACEMENT_COST = 60
FILTER_5UM_CF = 0.0833

FILTER_1UM_INITIAL_COST = 125
FILTER_1UM_REPLACEMENT_COST = 75
FILTER_1UM_CF = 0.167

FILTER_FOUL_200UM_NOPREV = 5_000 # 5k liters before fouled without pre-filters
FILTER_FOUL_5UM_NOPREV = 10_000 # 10k liters before fouled without pre-filters
FILTER_FOUL_1UM_NOPREV = 25_000 # 20k liters before fouled without pre-filters

FILTER_FOUL_5UM_200PREV = 20_000 # 20k liters before fouled with 200um pre-filter
FILTER_FOUL_1UM_200PREV = 15_000 # 15k liters before fouled with 200um pre-filter

FILTER_FOUL_1UM_5PREV = 20_000 # 10k liters before fouled with 5um pre-filter

# Chemical treatment constants
# Chlorine
CHLORINE_USED_PER_LITER = 10 # mg/L
CHLORINE_DOSER_COST = 700 # $
CHLORINE_CONTAINER_SIZE = 4400 # grams (4.4 kg)
CHLORINE_CONTAINER_COST = 100 # $
CHLORINE_CONCENTRATION = 0.08
CHLORINE_HEALTH_RISK = 4
CHLORINE_ENVIRO_RISK = 3

# Ozone
OZONE_USED_PER_LITER = 5 # mg/L
OZONE_DOSER_COST = 4000 # $
OZONE_DOSER_ENERGY_CONSUMPTION = 2 # MJ / gram of ozone produced

# UV
UV_BULB_MTBF = 1 # year
# 36W system
UV_36W_COST = 500 # $
UV_36W_REPLACEMENT_COST = 60 # $
UV_36W_ENERGY_CONSUMPTION = 36 # W
# 40W system
UV_40W_COST = 600 # $
UV_40W_REPLACEMENT_COST = 80 # $
UV_40W_ENERGY_CONSUMPTION = 40 # W
# 50W system
UV_50W_COST = 850 # $
UV_50W_REPLACEMENT_COST = 110 # $
UV_50W_ENERGY_CONSUMPTION = 50 # W

# Pumps
# Pump A
PUMP_A_COST = 640 # $
PUMP_A_MBTF = 900 # hours
PUMP_A_a = -0.0172
PUMP_A_b = -0.3605
PUMP_A_c = 150.9
PUMP_A_A = 0.70
PUMP_A_B = 0.39
PUMP_A_QMAX = 83.7 # liters per minute
# Pump B
PUMP_B_COST = 1250 # $
PUMP_B_MBTF = 1650 # hours
PUMP_B_a = -0.0039
PUMP_B_b = -0.096
PUMP_B_c = 237.86
PUMP_B_A = 0.94
PUMP_B_B = 0.85
PUMP_B_QMAX = 245.7 # liters per minute
# Pump C
PUMP_C_COST = 3250 # $
PUMP_C_MBTF = 1800 # hours
PUMP_C_a = -0.0151
PUMP_C_b = -0.5516
PUMP_C_c = 356.8
PUMP_C_A = 0.72
PUMP_C_B = 0.55
PUMP_C_QMAX = 136.5 # liters per minute

PUMP_CONV_G = 15_000 # Conv. factor for velocity to flow rate

# Power system constants
# Solar panels
MAINTENANCES_PER_YEAR_SOLAR = 4
# HES-260
SOLAR_HES_260_AREA = 1.6 # m^2
SOLAR_HES_260_COST = 550 # $
SOLAR_HES_260_EFFICIENCY = 0.17
SOLAR_HES_260_GHG = 496 # kg CO2e per panel
# SW-80
SOLAR_SW_80_AREA = 0.62 # m^2
SOLAR_SW_80_COST = 205 # $
SOLAR_SW_80_EFFICIENCY = 0.15
SOLAR_SW_80_GHG = 192 # kg CO2e per panel
# HES-305P
SOLAR_HES_305P_AREA = 2.0 # m^2
SOLAR_HES_305P_COST = 450 # $
SOLAR_HES_305P_EFFICIENCY = 0.16
SOLAR_HES_305P_GHG = 620 # kg CO2e per panel over

# Diesel generator
GENERATOR_COST = 3250 # $
GENERATOR_WATTAGE = 4000 # W
GENERATOR_EFFICIENCY = 0.35
GENERATOR_OIL_CHANGE_COST = 50 # $
GENERATOR_OIL_CHANGE_INTERVAL = 250 # Hours of operation
GENERATOR_DIESEL_CAPACITY = 100 # Litres of capacity
GENERATOR_FLAT_GHG = 1250 # kg CO2e to build

# Diesel
DIESEL_COST_PER_REFUEL = 325 # $
DIESEL_ENERGY_CONTENT = 40 # MJ per liter
DIESEL_HEALTH_RISK = 2
DIESEL_ENVIRO_RISK = 3
DIESEL_GHG_PER_LITER = 3.25 # kg CO2e per liter of diesel burned

# Battery constants
BATTERY_ENERGY_STORAGE = 2000 * 0.0036 # MJ (2 kWh converted to MJ)
BATTERY_COST = 390 # $
BATTERY_EFFICIENCY = 0.96 # loses 4% of energy going in and 4% coming out
BATTERY_GHG = 240 # kg CO2e per battery

# Inverter constants
INVERTER_COST = 2369 # $
INVERTER_EFFICIENCY = 0.92
INVERTER_GHG = 100 # kg CO2e per inverter

# Reference GHG emissions
GHG_FLAT_EMISSIONS = 2408 # kg CO2e for the pre-existing system AND new system
GHG_TREATMENT_EMISSIONS = 6.5 # kg CO2e / 1000L of water treated for old system