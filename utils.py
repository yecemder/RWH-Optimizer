from RWHSystem import Design
from math import log
from constants import *

from time import perf_counter_ns as timer

def print_design(design: Design):
    print(f"Consumption: {design.C} L/day")
    print(f"Use non-potable water: {design.np_threshold_L is not None}")
    if design.np_threshold_L is not None:
        print(f"  Non-potable threshold: {design.np_threshold_L} L/day")
        print(f"  Non-potable daily fraction: {design.np_fraction_C:.2%}")
    else:
        print(f"Does not use non-potable water")
    print(f"Roof choice: {design.roof_choice}")
    if design.roof_choice == "extra":
        print(f"  Extra catchment area: {design.extra_catchment_area_m2} m^2")
        print(f"  Extra catchment location: ({design.extra_catchment_x}, {design.extra_catchment_y})")
    print(f"Catchment tank capacity: {design.catchment_tank_L} L")
    print(f"Storage volume: {design.storage_volume_m3} m^3")
    print(f"Storage location: ({design.storage_x}, {design.storage_y})")
    if design.tower_height_m is not None:
        print(f"  Uses storage tower: {design.tower_height_m} m")
    else:
        print(f"No storage tower")
    print(f"Pump choice: {design.pump}")
    print(f"Filter location: {design.filter_location}")
    print(f"Filters: {', '.join(design.filters)}")
    print(f"UV choice: {design.uv}")
    print(f"Chemical choice: {design.chem}")
    print(f"Power choice: {design.power}")
    if design.power == "solar":
        print(f"  Solar panel model: {design.panel_model}")
        print(f"  Number of solar panels: {design.n_panels}")
    
    print(f"Derived attributes:")
    print(f"  Storage z: {design.storage_z} m")
    print(f"  Storage pipe length: {design.storage_pipe_length:.2f} m")
    if design.catchment_pipe_length is not None:
        print(f"  Catchment pipe length: {design.catchment_pipe_length:.2f} m")

def sgn(x):
    return (x > 0) - (x < 0)

def time_function(func, *args, **kwargs):
    iters = kwargs.pop("iters", 100)
    total_time_ns = 0
    for _ in range(iters):
        start = timer()
        result = func(*args, **kwargs)
        end = timer()
        total_time_ns += (end - start)
    avg_time_ns = total_time_ns / iters
    elapsed_ms = avg_time_ns / 1_000
    print(f"Function {func.__name__} took {elapsed_ms:.3f} us")
    return result

def get_pump_constants(pump_choice):
    if pump_choice == "A":
        return [PUMP_A_a, PUMP_A_b, PUMP_A_c], [PUMP_A_A, PUMP_A_B, PUMP_A_QMAX], [PUMP_A_COST, PUMP_A_MBTF]
    elif pump_choice == "B":
        return [PUMP_B_a, PUMP_B_b, PUMP_B_c], [PUMP_B_A, PUMP_B_B, PUMP_B_QMAX], [PUMP_B_COST, PUMP_B_MBTF]
    elif pump_choice == "C":
        return [PUMP_C_a, PUMP_C_b, PUMP_C_c], [PUMP_C_A, PUMP_C_B, PUMP_C_QMAX], [PUMP_C_COST, PUMP_C_MBTF]
    else:
        raise ValueError(f"Invalid pump choice: {pump_choice}")