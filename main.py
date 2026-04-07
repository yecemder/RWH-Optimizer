from satisfaction_curve import *
from topology import get_height

import random
from constants import *
from enum import Enum
from dataclasses import dataclass, field
from math import exp

@dataclass
class Design:
    C: float                    # L/day
    use_nonpotable: bool
    np_threshold_L: float

    roof_choice: str
    extra_catchment_area_m2: float
    extra_catchment_x: float
    extra_catchment_y: float
    catchment_tank_L: int

    storage_volume_m3: float
    storage_x: float
    storage_y: float
    use_tower: bool
    tower_height_m: float
    

    pump: str
    filter_location: str
    filters: tuple              # e.g. ("200um", "5um", "1um")

    uv: str
    chem: str

    power: str
    n_batteries: int            # Must be > 0 in all cases
    panel_model: str | None     # "HES_260", "SW_80", or "HES_305P", or None if not solar
    n_panels: int | None

    storage_z: float = 0
    pipe_length: float = 0
    pump_flow_consts: list[float] = field(default_factory=lambda: [0, 0, 0])
    pump_efficiency_consts: list[float] = field(default_factory=lambda: [0, 0, 0])



def get_rainfall_data():
    # Random data for now. 5 years of daily rainfall data (in mm)
    rainfall_data = []
    for day in range(365*5):
        # Simulate seasonal rainfall patterns with some randomness
        if 60 <= day % 365 <= 150:  # Rainy season
            rainfall = random.uniform(5, 20)  # mm/day
        else:  # Dry season
            rainfall = random.uniform(0, 10)  # mm/day
        rainfall_data.append(rainfall)
    return rainfall_data

def build_results_dict(solution: Design):
    return {
        "consumption": solution.C,
        "relative_cost": None,
        "health_risk": None,
        "ghg_emissions": None,
        "maintenances": None,
        "non_potable": None,
        "on_demand_flow": None,
        "reliability": None
    }

def run_simulation(solution: Design):
    
    results = build_results_dict(solution)
    
    running_trackers = {
        "cost": 0,
        "health_risk": 0,
        "ghg_emissions": 0,
        "maintenances": 0,
        "non_potable": 0
    }
    # Collect data that doesn't depend on previous states first
    data = get_rainfall_data()
    solution.storage_z = get_tank_z(solution)
    solution.pipe_length = (solution.storage_x**2 + solution.storage_y**2 + solution.storage_z**2)**0.5
    solution.pump_flow_consts, solution.pump_efficiency_consts = pump_consts_from_choice(solution.pump)
    catchment_collected, losses = water_collected(data, solution)
    days_overflowed = sum(1 for lost in losses if lost > 0)
    flow_rate_up = calculate_flow_rate_up(solution)
    pump_efficiency = pump_efficiency_from_flow_rate(flow_rate_up, solution)
    
    is_maintenance_day = [0] * len(catchment_collected)
    
    solar_energy_daily = daily_solar_energy(solution, catchment_collected)
    
    # Data that relies on previous states or other data will be calculated day by day in this loop
    
    
    
    return dict()

def get_tank_z(solution: Design):
    return get_height(solution.storage_x, solution.storage_y)

def pump_consts_from_choice(pump_choice):
    # Pump constants from pump choice.
    if pump_choice == "A":
        return [PUMP_A_a, PUMP_A_b, PUMP_A_c], [PUMP_A_A, PUMP_A_B, PUMP_A_QMAX]
    elif pump_choice == "B":
        return [PUMP_B_a, PUMP_B_b, PUMP_B_c], [PUMP_B_A, PUMP_B_B, PUMP_B_QMAX]
    elif pump_choice == "C":
        return [PUMP_C_a, PUMP_C_b, PUMP_C_c], [PUMP_C_A, PUMP_C_B, PUMP_C_QMAX]
    else:
        raise ValueError(f"Invalid pump choice. Must be 'A', 'B', or 'C', but got {pump_choice}")

def water_collected(rainfall_data, solution: Design):
    # Calculate daily water collected from roof catchment in L.
    if solution.roof_choice == "none":
        return [0] * len(rainfall_data), [0] * len(rainfall_data)
    elif solution.roof_choice == "half":
        roof_collected = [HALF_ROOF_CATCHMENT_AREA * rainfall for rainfall in rainfall_data]
    elif solution.roof_choice == "whole":
        roof_collected = [FULL_ROOF_CATCHMENT_AREA * rainfall for rainfall in rainfall_data]
    
    if solution.extra_catchment_area_m2 > 0:
        extra_catchment_collected = [solution.extra_catchment_area_m2 * rainfall for rainfall in rainfall_data]
        total_collected = [roof + extra for roof, extra in zip(roof_collected, extra_catchment_collected)]
    else:
        total_collected = roof_collected
    
    # Can only collect up to the catchment tank capacity
    final_collected = [min(collected, solution.catchment_tank_L) for collected in total_collected]
    losses = [max(0, collected - solution.catchment_tank_L) for collected in total_collected]

    return final_collected, losses

def calculate_flow_rate_up(solution: Design):
    # Flow rate up to the tower from the catchment tank in L/s.
    filter_consts = 0
    if solution.filter_location == "upstream":
        for f in solution.filters:
            if f == "200um":
                filter_consts += FILTER_200UM_CF
            elif f == "5um":
                filter_consts += FILTER_5UM_CF
            elif f == "1um":
                filter_consts += FILTER_1UM_CF
    
    cf_total = filter_consts * CF_EXP
    
    W = ( 
        DENSITY 
        * (PIPE_FRICTION_FACTOR * solution.pipe_length / PIPE_DIAMETER + LOSS_COEFF_TO_STORAGE)
        / (2000 * PUMP_CONV_G**2 * PIPE_DIAMETER**4 * pi**2)
        - solution.pump_flow_consts[0]
    )
    X = (
        cf_total
        / (1000 * PUMP_CONV_G * pi * PIPE_DIAMETER**2)
        - solution.pump_flow_consts[1]
    )
    Y = (
        DENSITY * GRAVITY * (solution.storage_z + WATER_HEIGHT_PUMPING)
        / (1000)
        - solution.pump_flow_consts[2]
    )
    Q1 = (-X + (X**2 - 4*W*Y)**0.5) / (2*W)
    Q2 = (-X - (X**2 - 4*W*Y)**0.5) / (2*W)
    if (isinstance(Q1, complex)): # Only need to check one since if one is complex, the other will be too
        raise ValueError("Storage is too high for pump.")
    
    Q = max(Q1, Q2)
    return Q

def daily_uv_energy(solution, daily_water_L):
    uv_choice = solution.uv
    if uv_choice in ("36W", "40W", "50W"):
        # UV energy is just the wattage of the UV system; the system is permanently switched on.
        return [int(uv_choice[:-1]) * 86400 / 1e6] * len(daily_water_L) # Convert W to MJ/day
    else:
        raise ValueError(f"Invalid UV choice. Must be '36W', '40W', or '50W', but got {uv_choice}")

def pump_efficiency_from_flow_rate(flow_rate, solution):
    return (
        1.2 * solution.pump_efficiency_consts[0] # 1.2A
        * (
            exp(flow_rate / solution.pump_efficiency_consts[2]) - 1 # exp(Q/Qmax) - 1
            - 1.72 * (flow_rate / solution.pump_efficiency_consts[2])**4 # - 1.72(Q/Qmax)^4 
        )** solution.pump_efficiency_consts[1] # ^B
    )

def daily_hours_of_sunlight():
    # Gives back daily hours of sunlight for 5 years.
    return (
        [8.50]  * 31 + # January
        [10.0]  * 28 + # February
        [11.8]  * 31 + # March
        [13.6]  * 30 + # April
        [15.3]  * 31 + # May
        [16.0]  * 30 + # June
        [15.75] * 31 + # July
        [14.2]  * 31 + # August
        [12.5]  * 30 + # September
        [10.75] * 31 + # October
        [9.0]   * 30 + # November
        [8.25]  * 31 # December
    ) * YEARS_OF_OPERATION

def daily_solar_energy(solution, daily_water_L):
    if (
        solution.power == "solar"
        and solution.panel_model is not None
        and solution.n_panels is not None
        and solution.panel_model in ("HES_260", "SW_80", "HES_305P")
    ):
        # Solar energy is just the wattage of the solar panels, since they're on for 24 hours per day
        system_consts = [0.0, 0.0] # area per panel, efficiency
        match solution.panel_model:
            case "HES_260":
                system_consts = [SOLAR_HES_260_AREA, SOLAR_HES_260_EFFICIENCY]
            case "SW_80":
                system_consts = [SOLAR_SW_80_AREA, SOLAR_SW_80_EFFICIENCY]
            case "HES_305P":
                system_consts = [SOLAR_HES_305P_AREA, SOLAR_HES_305P_EFFICIENCY]
            case _:
                raise ValueError("What?")
        daily_energy_per_panel = [
            SOLAR_INTENSITY * system_consts[0] * system_consts[1] * hours for hours in daily_hours_of_sunlight()
        ]
        return [energy * solution.n_panels for energy in daily_energy_per_panel]
    elif solution.power == "solar":
        raise ValueError(f"""Invalid power source. Expected solar with valid panel model and number of panels, but got power={solution.power}, panel_model={solution.panel_model}, n_panels={solution.n_panels}""")
    
    return [0] * len(daily_water_L)

def calculate_diesel_data(daily_energy_MJ, solution):
    if solution.power == "diesel":
        
        diesel_needs =  [
                            sum(
                                (pump_energy,
                                ozone_energy,
                                uv_energy / (BATTERY_EFFICIENCY ** 2)
                                )
                            ) for (pump_energy, ozone_energy, uv_energy) in daily_energy_MJ
                        ]
        
        # Calculate refuel events from generator cap and diesel needs
        maintenance_events = [0.0] * len(diesel_needs)
        hrs_operated = [0.0] * len(diesel_needs)
        current_capacity = GENERATOR_DIESEL_CAPACITY
        oil_changes = 0  # Oil changes happen every 250 hours of operation
        for i, diesel_need in enumerate(diesel_needs):
            if diesel_need > current_capacity:
                maintenance_events[i] = 1
                current_capacity = GENERATOR_DIESEL_CAPACITY - diesel_need
            else:
                current_capacity -= diesel_need
            
            # Convert diesel need to hours of operation
            hours_operated_on_day = diesel_need / (GENERATOR_WATTAGE * GENERATOR_EFFICIENCY / DIESEL_ENERGY_CONTENT)
            if i > 0 and hrs_operated[i-1] + hours_operated_on_day > GENERATOR_OIL_CHANGE_INTERVAL:
                maintenance_events[i] = 1
                hrs_operated[i] = hours_operated_on_day  # reset hours after oil change
            else:
                hrs_operated[i] = hrs_operated[i-1] + hours_operated_on_day
        
        return sum(diesel_needs), maintenance_events
    else:
        return 0, [0] * len(daily_energy_MJ)
