from dataclasses import dataclass

from topology import get_height, get_pipe_length
from simulator import simulate_design
from optimizer import random_design
from environment import create_daily_rainfall_data, daily_hours_of_sunlight
from utils import print_design, get_pump_constants
from rich import print
from RWHSystem import Design
from satisfaction_curve import *

@dataclass
class PartialDesign:  # Partial design with all non-dependent parameters
    C: float                    # L/day
    
    np_threshold_L: float | None
    np_fraction_C: float | None

    roof_choice: str
    extra_catchment_area_m2: float | None
    extra_catchment_x: float | None
    extra_catchment_y: float | None
    catchment_tank_L: int

    storage_volume_m3: float
    storage_x: float
    storage_y: float
    tower_height_m: int | None
    

    pump: str # "A", "B", or "C"
    filter_location: str  # "to storage" or "to house"
    filters: tuple        # e.g. ("200um", "5um", "1um"). Must include 1um

    uv: str # "36W", "40W", or "50W"
    chem: str # "chlorine" or "ozone"

    power: str  # "diesel" or "solar"
    n_batteries: int            # Must be > 0 in all cases. If diesel, exactly 1. If solar, random.
    
    panel_model: str | None     # "HES_260", "SW_80", or "HES_305P", or None if not solar
    n_panels: int | None

def complete_design(partial: PartialDesign) -> Design:
    z = get_height(partial.storage_x, partial.storage_y) + (partial.tower_height_m or 0)
    storage_pipe_length = get_pipe_length(partial.storage_x, partial.storage_y, (partial.tower_height_m or 0))
    catchment_pipe_length = get_pipe_length(partial.extra_catchment_x or 0, partial.extra_catchment_y or 0, 0) if partial.extra_catchment_area_m2 else None
    pump_flow_consts, pump_efficiency_consts, pump_other_consts = get_pump_constants(partial.pump)
    if partial.power == "diesel":
        n_batteries = 1
    else:
        n_batteries = partial.n_batteries if partial.n_batteries is not None else random.randint(*BATTERY_NUMBER_RANGE)
    return Design(
        C=partial.C,
        np_threshold_L=partial.np_threshold_L,
        np_fraction_C=partial.np_fraction_C,
        roof_choice=partial.roof_choice,
        extra_catchment_area_m2=partial.extra_catchment_area_m2,
        extra_catchment_x=partial.extra_catchment_x,
        extra_catchment_y=partial.extra_catchment_y,
        catchment_tank_L=partial.catchment_tank_L,
        storage_volume_m3=partial.storage_volume_m3,
        storage_x=partial.storage_x,
        storage_y=partial.storage_y,
        tower_height_m=partial.tower_height_m,
        pump=partial.pump,
        filter_location=partial.filter_location,
        filters=partial.filters,
        uv=partial.uv,
        chem=partial.chem,
        power=partial.power,
        n_batteries=partial.n_batteries,
        panel_model=partial.panel_model,
        n_panels=partial.n_panels,
        storage_z=z,
        storage_pipe_length=storage_pipe_length,
        catchment_pipe_length=catchment_pipe_length,
        pump_flow_consts=pump_flow_consts,
        pump_efficiency_consts=pump_efficiency_consts,
        pump_other_consts=pump_other_consts
    )

partial = PartialDesign(
    C=500,
    np_threshold_L=400,
    np_fraction_C=0.25,
    roof_choice="extra",
    extra_catchment_area_m2=175,
    extra_catchment_x=40,
    extra_catchment_y=30,
    catchment_tank_L=10000,
    storage_volume_m3=45,
    storage_x=60,
    storage_y=60,
    tower_height_m=5,
    pump="C",
    filter_location="to house",
    filters=("200um","5um","1um"),
    uv="36W",
    chem="ozone",
    power="solar",
    n_batteries=8,
    panel_model="HES_260",
    n_panels=8
)

# partial = PartialDesign(
#     C=350,
#     np_threshold_L=1000,
#     np_fraction_C=0.2,
#     roof_choice="extra",
#     extra_catchment_area_m2=175,
#     extra_catchment_x=40,
#     extra_catchment_y=30,
#     catchment_tank_L=10000,
#     storage_volume_m3=20,
#     storage_x=20,
#     storage_y=-10,
#     tower_height_m=10,
#     pump="A",
#     filter_location="to house",
#     filters=("1um",),
#     uv="36W",
#     chem="ozone",
#     power="solar",
#     n_batteries=8,
#     panel_model="HES_260",
#     n_panels=8
# )

design = complete_design(partial)


# print("Generating parameters...")
# design1 = random_design()
# design2 = random_design()
rainfall_data = create_daily_rainfall_data()
sunlight_data = daily_hours_of_sunlight()
print("Simulating design...")

results = simulate_design(design, rainfall_data, sunlight_data)
print("Design parameters:")
print_design(design)
print("Simulation results:")
if results is not None:
    print(results)
    satisfactions = {
        "consumption": CONSUMPTION.calculate_satisfaction(results["consumption"]),
        "relative_cost": REL_COST.calculate_satisfaction(results["relative_cost"]),
        "reliability": RELIABILITY.calculate_satisfaction(results["reliability"]),
        "risk_exposure": HEALTH_RISK.calculate_satisfaction(results["risk_exposure"]),
        "relative_ghg": GHG_EMISSIONS.calculate_satisfaction(results["relative_ghg"]),
        "maintenance_operations": MAINTENANCES.calculate_satisfaction(results["maintenance_operations"]),
        "non_potable_avg": NON_POTABLE.calculate_satisfaction(results["non_potable_avg"]),
        "on_demand_flow_rate": ON_DEMAND_FLOW.calculate_satisfaction(results["on_demand_flow_rate"])
        
    }
    if any(s is None for s in satisfactions.values()):
        print("[red][bold]Simulation failed to meet a requirement.")
    
    for metric, satisfaction in satisfactions.items():
        if satisfaction is not None:
            print(f"Satisfaction for {metric}: {satisfaction:.2%}")
        else:
            print(f"Satisfaction for {metric}: [bold][red]Not satisfied (requirement not met)")
    
    weighted_satisfactions = [
        CONSUMPTION.calculate_weighted_satisfaction(results["consumption"]),
        REL_COST.calculate_weighted_satisfaction(results["relative_cost"]),
        RELIABILITY.calculate_weighted_satisfaction(results["reliability"]),
        HEALTH_RISK.calculate_weighted_satisfaction(results["risk_exposure"]),
        GHG_EMISSIONS.calculate_weighted_satisfaction(results["relative_ghg"]),
        MAINTENANCES.calculate_weighted_satisfaction(results["maintenance_operations"]),
        NON_POTABLE.calculate_weighted_satisfaction(results["non_potable_avg"]),
        ON_DEMAND_FLOW.calculate_weighted_satisfaction(results["on_demand_flow_rate"])
    ]
    print("\n[bold]Weighted satisfactions:")
    for i, satisfaction in enumerate(weighted_satisfactions):
        if satisfaction is not None:
            print(f"Weighted satisfaction for {list(satisfactions.keys())[i]}: {satisfaction:.3f}")
        else:
            print(f"Weighted satisfaction for {list(satisfactions.keys())[i]}: [bold][red]Not satisfied (requirement not met)")
    print("\n" + "="*50 + "\n")
    if all(s is not None for s in weighted_satisfactions):
        print("Overall weighted satisfaction score: {:.2%}".format(sum(s for s in weighted_satisfactions if s is not None)))
    else:
        print("[bold][red]Overall weighted satisfaction score cannot be calculated due to unmet requirements.")
else:
    print("Simulation failed due to invalid design parameters.")
# result1 = simulate_design(design1, rainfall_data, sunlight_data)
# result2 = simulate_design(design2, rainfall_data, sunlight_data)
# print("Design parameters (Design 1):")
# print_design(design1)
# print("Simulation result for random design (Design 1):")
# print(result1)
# print("\n" + "="*50 + "\n")
# print("Design parameters (Design 2):")
# print_design(design2)
# print("Simulation result for random design (Design 2):")
# print(result2)