import random
from RWHSystem import Design
import topology
from constants import *

from utils import print_design, time_function

def random_design() -> Design:
    consumption = random.randint(*CONSUMPTION_RANGE)
    
    use_nonpotable = random.random() < NONPOTABLE_CHANCE
    nonpotable_threshold = random.randint(*NONPOTABLE_THRESHOLD_RANGE) if use_nonpotable else None
    nonpotable_fraction_C = random.uniform(*NONPOTABLE_PERDAY_RANGE) if use_nonpotable else None
    
    catchment = random.choices(CATCHMENT_CHOICES, CATCHMENT_CHANCES)[0]
    catchment_extra_area = random.randint(*CATCHMENT_EXTRA_AREA_RANGE) if catchment == "extra" else None
    catchment_extra_x = random.randint(*XY_PLACEMENT_RANGE) if catchment == "extra" else None
    catchment_extra_y = random.randint(*XY_PLACEMENT_RANGE) if catchment == "extra" else None
    
    # Don't allow the extra catchment to be inside -20 <= x,y <= 20
    # Catchment Z also cannot be below 3 m
    if catchment_extra_x is not None and catchment_extra_y is not None:
        while ( (-20 <= catchment_extra_x <= 20) and (-20 <= catchment_extra_y <= 20) 
                or topology.get_height(catchment_extra_x, catchment_extra_y) < 3):
            catchment_extra_x = random.randint(*XY_PLACEMENT_RANGE)
            catchment_extra_y = random.randint(*XY_PLACEMENT_RANGE)
    
    catchment_tank_capacity = random.choice(CATCHMENT_TANK_CAPACITY_CHOICES)
    storage_tank_capacity = random.randint(*STORAGE_TANK_CAPACITY_RANGE)
    
    storage_tank_x = random.randint(*XY_PLACEMENT_RANGE)
    storage_tank_y = random.randint(*XY_PLACEMENT_RANGE)
    
    # Don't allow the tank to be inside -20 <= x,y <= 20
    while (-20 <= storage_tank_x <= 20) and (-20 <= storage_tank_y <= 20):
        storage_tank_x = random.randint(*XY_PLACEMENT_RANGE)
        storage_tank_y = random.randint(*XY_PLACEMENT_RANGE)

    storage_tower_height = random.randint(*STORAGE_TOWER_HEIGHT_RANGE) if random.random() < STORAGE_TOWER_CHANCE else None
    
    pump = random.choice(PUMP_CHOICES)
    filter_location = random.choice(FILTER_LOCATION_CHOICES)
    # Any combo of the 200um and 5um filters may be included, but the 1um filter is always included.
    filter_types = random.sample(FILTER_CHOICES, random.randint(0, len(FILTER_CHOICES))) + ["1um"]
    uv_type = random.choice(UV_CHOICES)
    chem_type = random.choice(CHEM_CHOICES)
    power_type = random.choices(POWER_CHOICES, POWER_CHANCES)[0]
    solar_panel_model = random.choice(SOLAR_PANEL_MODEL_CHOICES) if power_type == "solar" else None
    solar_panel_number = random.randint(*SOLAR_PANEL_NUMBER_RANGE) if power_type == "solar" else None
    n_batteries = 1 if power_type == "diesel" else random.randint(*BATTERY_NUMBER_RANGE)
        
    # Calculate derived attributes.
    storage_z = topology.get_height(storage_tank_x, storage_tank_y) + (storage_tower_height if storage_tower_height is not None else 0)
    storage_pipe_length = topology.get_pipe_length(storage_tank_x, storage_tank_y, z_offset=(storage_tower_height or 0))
    catchment_pipe_length = topology.get_pipe_length(catchment_extra_x, catchment_extra_y, z_offset=0.0) if catchment_extra_x is not None and catchment_extra_y is not None else None

    match pump:
        case "A":
            pump_flow_consts = [PUMP_A_a, PUMP_A_b, PUMP_A_c]
            pump_efficiency_consts = [PUMP_A_A, PUMP_A_B, PUMP_A_QMAX]
            pump_other_consts = [PUMP_A_COST, PUMP_A_MBTF]
        case "B":
            pump_flow_consts = [PUMP_B_a, PUMP_B_b, PUMP_B_c]
            pump_efficiency_consts = [PUMP_B_A, PUMP_B_B, PUMP_B_QMAX]
            pump_other_consts = [PUMP_B_COST, PUMP_B_MBTF]
        case "C":
            pump_flow_consts = [PUMP_C_a, PUMP_C_b, PUMP_C_c]
            pump_efficiency_consts = [PUMP_C_A, PUMP_C_B, PUMP_C_QMAX]
            pump_other_consts = [PUMP_C_COST, PUMP_C_MBTF]
    
    return Design(
        C=consumption,
        np_threshold_L=nonpotable_threshold,
        np_fraction_C=nonpotable_fraction_C,
        roof_choice=catchment,
        extra_catchment_area_m2=catchment_extra_area,
        extra_catchment_x=catchment_extra_x,
        extra_catchment_y=catchment_extra_y,
        catchment_tank_L=catchment_tank_capacity,
        storage_volume_m3=storage_tank_capacity,
        storage_x=storage_tank_x,
        storage_y=storage_tank_y,
        tower_height_m=storage_tower_height,
        pump=pump,
        filter_location=filter_location,
        filters=tuple(filter_types),
        uv=uv_type,
        chem=chem_type,
        power=power_type,
        n_batteries=n_batteries,
        panel_model=solar_panel_model,
        n_panels=solar_panel_number,
        storage_z=storage_z,
        storage_pipe_length=storage_pipe_length,
        catchment_pipe_length=catchment_pipe_length,
        pump_flow_consts=pump_flow_consts,
        pump_efficiency_consts=pump_efficiency_consts,
        pump_other_consts=pump_other_consts        
    )

def random_designs(n: int) -> list[Design]:
    return [random_design() for _ in range(n)]

def find_best_random_design(n: int):
    pass

if __name__ == "__main__":
    print("Generating random design...")
    design = random_design()
    time_function(random_design, iters=100)
    print_design(design)