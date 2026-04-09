from RWHSystem import Design
from math import log

from time import perf_counter_ns as timer

def print_design(design: Design):
    print(f"Consumption: {design.C} L/day")
    if design.np_threshold_L is not None:
        print(f"Use non-potable water: {design.np_threshold_L is not None}")
        print(f"  Non-potable threshold: {design.np_threshold_L} L/day")
        # print(f"  Non-potable daily fraction: {design.np_daily_frac_C:.2%}")
    print(f"Roof choice: {design.roof_choice}")
    if design.roof_choice == "extra":
        print(f"  Extra catchment area: {design.extra_catchment_area_m2} m^2")
        print(f"  Extra catchment location: ({design.extra_catchment_x}, {design.extra_catchment_y})")
    print(f"Catchment tank capacity: {design.catchment_tank_L} L")
    print(f"Storage volume: {design.storage_volume_m3} m^3")
    print(f"Storage location: ({design.storage_x}, {design.storage_y})")
    if design.tower_height_m is not None:
        print(f"  Uses storage tower: {design.tower_height_m} m")
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

def likelihood_rating_from_days(event_days_yearly: float) -> float:
    period_between_events = 365 / event_days_yearly
    return 4 - 0.5*log(period_between_events)

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
