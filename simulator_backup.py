from constants import *
from RWHSystem import Design
from math import log

def simulate_design(solution: Design, rainfall_data: list[float], sunlight_data: list[float]) -> dict[str, float] | None:
    # Rainfall data in mm/day. Sunlight data in hours/day.
    # Running counters for output. 
    
    if len(rainfall_data) != DAYS_OF_OPERATION or len(sunlight_data) != DAYS_OF_OPERATION:
        raise ValueError(f"Rainfall and sunlight data must be lists of length {DAYS_OF_OPERATION}. Got {len(rainfall_data)} and {len(sunlight_data)} respectively.")
    
    cost = calculate_static_costs(solution)  # Total cost.
    days_without_water = 0 # Number of days where the system fails to meet the daily water demand.
    diesel_used_total = 0.0  # For later GHG calculations.
    nonpotable_used_total = 0.0 # Total liters of non-potable water used over the simulation period.
    
    maintenance_operations = (YEARS_OF_OPERATION - 1) # UV bulbs need to be replaced once per year.
    
    # Non-dependent data can be calculated first.
    if solution.roof_choice == "half":
        catchment_area = HALF_ROOF_CATCHMENT_AREA
    elif solution.roof_choice == "full":
        catchment_area = FULL_ROOF_CATCHMENT_AREA
    elif solution.extra_catchment_area_m2 is not None: # "extra"
        catchment_area = FULL_ROOF_CATCHMENT_AREA + solution.extra_catchment_area_m2
    else:  # Shouldn't ever happen, but just in case...
        catchment_area = FULL_ROOF_CATCHMENT_AREA
    
    q_in = [rainfall_data[i] * catchment_area for i in range(len(rainfall_data))]  # Gross inflow from rainfall in L/day
    
    # Calculate system constants.
    to_storage_consts = calculate_consts_to_storage(solution)  # Check constants on the way to storage.
    if to_storage_consts is None:
        return None  # System won't work if these values are invalid.
    
    flow_rate_up, pressure_up = to_storage_consts  # L/min and kPa respectively.
    flow_rate_down = calculate_flow_rate_to_house(solution)  # Flow rate down to the house from the tower in L/min.
    if flow_rate_down is None:
        return None  # System won't work if the storage height < 0.
    pump_efficiency = pump_efficiency_from_flow_rate(flow_rate_up, solution)  # Efficiency of the pump at the given flow rate.
    
    volume_in_storage_m3 = 0.0  # Current volume in storage tank in m^3.
    volume_in_catchment_m3 = 0.0  # Current volume in catchment tank in m^3.
    
    # For risk frequency calculations
    chlorine_maintenances = 0  # Number of times chlorine needs to be refilled (total)
    diesel_maintenances = 0  # Number of times diesel needs to be refilled (total)
    
    uv_power = int(solution.uv[:-1])
    
    diesel_level = GENERATOR_DIESEL_CAPACITY
    chlorine_level = CHLORINE_CONTAINER_SIZE
    
    generator_runtime = 0.0
    hours_spent_pumping = 0.0
    
    is_solar = solution.power == "solar"
    if is_solar:
        match solution.panel_model:
            case "HES_260":
                panel_effiency = SOLAR_HES_260_EFFICIENCY
                panel_area = SOLAR_HES_260_AREA
            case "SW_80":
                panel_effiency = SOLAR_SW_80_EFFICIENCY
                panel_area = SOLAR_SW_80_AREA
            case "HES_305P":
                panel_effiency = SOLAR_HES_305P_EFFICIENCY
                panel_area = SOLAR_HES_305P_AREA
            case _:
                raise ValueError(f"Solar panel model {solution.panel_model} not recognized for efficiency calculation.")
        panel_const = SOLAR_INTENSITY * panel_area * (solution.n_panels or 0) * panel_effiency # W
        sunlight_energy_daily = [panel_const * sunlight_data[i] * 3600 / 1e6 for i in range(len(sunlight_data))]  # Convert W to MJ for daily energy from solar panels.
    
    max_battery_energy = solution.n_batteries * BATTERY_ENERGY_STORAGE  # Max energy that can be stored in batteries in MJ.
    energy_in_batteries = 0.0
    
    filter_usage = [0.0 for _ in solution.filters]  # Track usage of each filter for maintenance calculations.
    # Determine filter MBTF from filters used.
    filter_mbtf = [0.0 for _ in solution.filters]
    for i, f in enumerate(solution.filters):
        if f == "200um":
            filter_mbtf[i] = FILTER_FOUL_200UM_NOPREV
        elif f == "5um":
            if "200um" in solution.filters:
                filter_mbtf[i] = FILTER_FOUL_5UM_200PREV
            else:
                filter_mbtf[i] = FILTER_FOUL_5UM_NOPREV
        elif f == "1um":
            if "5um" in solution.filters:
                filter_mbtf[i] = FILTER_FOUL_1UM_5PREV
            elif "200um" in solution.filters:
                filter_mbtf[i] = FILTER_FOUL_1UM_200PREV
            else:
                filter_mbtf[i] = FILTER_FOUL_1UM_NOPREV
    
    chlorine_per_liter = CHLORINE_MG_USED_PER_LITER / (1000 * CHLORINE_CONCENTRATION)  # grams of chlorine per liter, including concentration
    
    water_consumed_total = 0.0  # Total water consumed over the simulation period in liters.
    
    # ----------------------------------------------------
    for day in range(DAYS_OF_OPERATION):
        day_is_lost = False  # Whether the day is lost due to lack of water.
        # Store energy into batteries from solar panels.
        # Immediately use energy for 24-hour UV lamp if not within first few days of non-consumption. 
        if is_solar:
            energy_in_batteries = min(energy_in_batteries + sunlight_energy_daily[day] * BATTERY_EFFICIENCY, max_battery_energy)
            if not(day < DAYS_WITH_NO_CONSUMPTION) and (energy_in_batteries >= uv_power * 24 * 3600 / 1e6): # Convert W to MJ
                energy_in_batteries -= uv_power * 24 * 3600 / 1e6
            elif day < DAYS_WITH_NO_CONSUMPTION:
                # During the first few days of non-consumption, do not use energy for UV lamp.
                pass
            else:
                # Not enough energy to power UV lamp for the day, so water quality is not maintained, and system fails for the day.
                day_is_lost = True
        
        volume_in_catchment_m3 = min(volume_in_catchment_m3 + q_in[day] / 1000, solution.catchment_tank_L / 1000)  # Convert L to m^3 for volume calculations.
        water_to_pump_m3 = volume_in_catchment_m3  # Pump tries to move all available catchment water; storage overflow is handled downstream.
        elec_energy_to_pump_MJ = water_to_pump_m3 * pressure_up / (pump_efficiency * 1e3)  # Energy needed to pump the water up to the tower in MJ. (pressure in kPa)
        
        elec_energy_ozone = 0.0
        # If using ozone, calculate energy used to generate sufficient ozone for maximum water being pumped.
        if solution.chem == "ozone":
            elec_energy_ozone = water_to_pump_m3 * OZONE_DOSER_ENERGY_CONSUMPTION * OZONE_MG_PER_LITER  # Energy needed for ozone disinfection in MJ.
        elec_energy_to_pump_MJ += elec_energy_ozone
        
        if is_solar:
            energy_from_batteries_to_pump = elec_energy_to_pump_MJ / BATTERY_EFFICIENCY  # Losses from coming out of battery
            energy_from_batteries_to_pump /= INVERTER_EFFICIENCY  # Losses from inverter when using solar
            if energy_in_batteries >= energy_from_batteries_to_pump:
                volume_pumped_m3 = water_to_pump_m3  # Assume we can pump the entire catchment tank if we have enough energy.
                energy_in_batteries -= energy_from_batteries_to_pump
            else:
                # Pump/treat as much as possible with all remaining battery energy.
                # For ozone systems, this ensures only fully disinfected water is moved to storage.
                volume_pumped_m3 = 0.0
                if energy_from_batteries_to_pump > 0:
                    fraction_transferable = energy_in_batteries / energy_from_batteries_to_pump
                    volume_pumped_m3 = water_to_pump_m3 * max(0.0, min(1.0, fraction_transferable))
                energy_in_batteries = 0
        else:   # Diesel can meet any needs, but if there's not enough diesel left,
                # then refuel.
            diesel_energy_needed_MJ = elec_energy_to_pump_MJ / GENERATOR_EFFICIENCY
            diesel_needed_L = diesel_energy_needed_MJ / DIESEL_ENERGY_CONTENT
            generator_runtime_today = elec_energy_to_pump_MJ * 1e6 / (GENERATOR_WATTAGE * 3600)
            if generator_runtime_today + generator_runtime >= GENERATOR_OIL_CHANGE_INTERVAL:
                maintenance_operations += 1
                cost += GENERATOR_OIL_CHANGE_COST
                generator_runtime = generator_runtime_today
            else:
                generator_runtime += generator_runtime_today
            # If we have enough diesel in the generator, use it.
            if diesel_needed_L <= diesel_level:
                diesel_level -= diesel_needed_L
                diesel_used_total += diesel_needed_L
            else:
                # Otherwise, refuel and then use diesel.
                if (diesel_needed_L - diesel_level) > GENERATOR_DIESEL_CAPACITY:
                    return None  # System won't work if we can't store enough diesel to meet pumping needs.
                diesel_maintenances += 1
                maintenance_operations += 1
                cost += DIESEL_COST_PER_REFUEL
                diesel_level = GENERATOR_DIESEL_CAPACITY - diesel_needed_L
                diesel_used_total += diesel_needed_L
            volume_pumped_m3 = water_to_pump_m3  # Assume we can pump the entire catchment tank; we should always have enough energy.
        
        # Pump volume to storage, allowing overflow of storage.
        volume_in_storage_m3 = min(volume_in_storage_m3 + volume_pumped_m3, solution.storage_volume_m3) # Can only add up to storage capacity; excess is overflow and lost.
        volume_in_catchment_m3 -= volume_pumped_m3
        
        hours_to_pump = volume_pumped_m3 * 1000 / (flow_rate_up * 60)  # L pumped divided by L/min converted to min, then to hours.
        if hours_spent_pumping + hours_to_pump >= solution.pump_other_consts[1]:  # MBTF in hours
            # Replace pump if MBTF reached.
            maintenance_operations += 1
            cost += solution.pump_other_consts[0]  # Pump cost
            hours_spent_pumping = hours_to_pump
        else:
            hours_spent_pumping += hours_to_pump
        
        if solution.chem == "chlorine":
            chlorine_needed = volume_pumped_m3 * 1000 * chlorine_per_liter  # Total grams of chlorine needed for the pumped volume.
            if chlorine_needed <= chlorine_level:
                chlorine_level -= chlorine_needed
            else:
                # Not enough chlorine to treat the pumped water, so refill the chlorine doser
                # and add to maintenances and trackers.
                chlorine_maintenances += 1
                maintenance_operations += 1
                cost += CHLORINE_CONTAINER_COST
                chlorine_level = CHLORINE_CONTAINER_SIZE - chlorine_needed
        
        if day < DAYS_WITH_NO_CONSUMPTION:
            consumption = 0
        else:
            consumption = min(solution.C, volume_in_storage_m3 * 1000)  # Convert m^3 back to L for consumption comparison.
        
        if consumption < solution.C:
            day_is_lost = True
        volume_in_storage_m3 = max(0.0, volume_in_storage_m3 - consumption / 1000)  # Convert L to m^3 for volume calculations.
        water_consumed_total += consumption
        # Non potable water calculations.
        if solution.np_threshold_L is not None and volume_in_storage_m3 * 1000 > solution.np_threshold_L:
            # Treat non-potable water use as reserve-floor
            available_for_np_L = max(0, volume_in_storage_m3 * 1000 - solution.np_threshold_L)  # L
            nonpotable_use_L = min(solution.C * (solution.np_fraction_C or 0.0), available_for_np_L)
            volume_in_storage_m3 -= nonpotable_use_L / 1000  # Convert L to m^3 for volume calculations.
            nonpotable_used_total += nonpotable_use_L
            water_consumed_total += nonpotable_use_L  # Non-potable water still counts towards total water consumed.
        
        # Filter calculations
        filter_replacement_maintenance = False  # Filters can be replaced a single operation on a single day, even if multiple filters need replacement.
        if solution.filter_location == "to storage":
            filter_use_today = volume_pumped_m3 * 1000  # Convert m^3 to L for filter usage tracking.
            for i, f in enumerate(solution.filters):
                if filter_use_today + filter_usage[i] >= filter_mbtf[i]:
                    filter_replacement_maintenance = True
                    # Reset usage after replacement.
                    filter_usage[i] = filter_use_today
                    # Add replacement cost to costs.
                    if f == "200um":
                        cost += FILTER_200UM_REPLACEMENT_COST
                    elif f == "5um":
                        cost += FILTER_5UM_REPLACEMENT_COST
                    elif f == "1um":
                        cost += FILTER_1UM_REPLACEMENT_COST
                else:
                    filter_usage[i] += filter_use_today
        elif solution.filter_location == "to house":
            filter_use_today = consumption  # L. Non-potable skips any filters on the way back.
            for i, f in enumerate(solution.filters):
                if filter_use_today + filter_usage[i] >= filter_mbtf[i]:
                    filter_replacement_maintenance = True
                    # Reset usage after replacement.
                    filter_usage[i] = filter_use_today
                    # Add replacement cost to costs.
                    if f == "200um":
                        cost += FILTER_200UM_REPLACEMENT_COST
                    elif f == "5um":
                        cost += FILTER_5UM_REPLACEMENT_COST
                    elif f == "1um":
                        cost += FILTER_1UM_REPLACEMENT_COST
                else:
                    filter_usage[i] += filter_use_today
        
        if filter_replacement_maintenance:
            maintenance_operations += 1
        
        if day_is_lost:
            days_without_water += 1
            cost += COST_PER_DAY_SHIP # Add cost of water delivery for the day if demand not met.
    
    # Conduct analysis of results and return.
    # consumption
    relative_cost = cost / REFERENCE_COST
    reliability = (DAYS_OF_OPERATION - days_without_water) / YEARS_OF_OPERATION  # Average number of days per year water is properly supplied
    risk_exposure = calculate_risk_exposure(diesel_maintenances, chlorine_maintenances)
    relative_ghg = calculate_relative_ghg_emissions(solution, diesel_used_total, water_consumed_total)
    maintenance_operations /= YEARS_OF_OPERATION  # Average number of maintenance operations per year.
    non_potable_avg = nonpotable_used_total / (DAYS_OF_OPERATION * solution.C) if solution.C != 0 else 0.0
    on_demand_flow_rate = flow_rate_down  # L/min, which is the flow rate available to the house when water is being supplied.

    return {
        "consumption": solution.C,
        "relative_cost": relative_cost,
        "reliability": reliability,
        "risk_exposure": risk_exposure,
        "relative_ghg": relative_ghg,
        "maintenance_operations": maintenance_operations,
        "non_potable_avg": non_potable_avg,
        "on_demand_flow_rate": on_demand_flow_rate
    }


def calculate_consts_to_storage(solution: Design) -> tuple[float, float] | None:
    # Flow rate up to the tower from the catchment tank in L/min.
    filter_consts = 0
    if solution.filter_location == "to storage":
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
        * (PIPE_FRICTION_FACTOR * solution.storage_pipe_length / PIPE_DIAMETER + LOSS_COEFF_TO_STORAGE)
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
    
    discriminant = X**2 - 4*W*Y
    if (discriminant < 0): # If the discriminant is negative, the pump can't push hard enough.
        return None
    
    Q1 = (-X + discriminant**0.5) / (2*W)
    Q2 = (-X - discriminant**0.5) / (2*W)
    
    Q = max(Q1, Q2)  # Only the positive root makes physical sense, but just in case, take the max.
    # Calculate pressure from aQ^2 + bQ + c
    P = solution.pump_flow_consts[0] * Q**2 + solution.pump_flow_consts[1] * Q + solution.pump_flow_consts[2]
    if P <= 0 or Q <= 0:
        # If pressure or flow rate is negative, that means the pump can't push hard enough to overcome the system's resistance, so return None to indicate failure.
        return None
    return Q, P

def calculate_flow_rate_to_house(solution: Design):
    # Flow rate down to the house from the tower in L/min.
    filter_consts = 0
    if solution.filter_location == "to house":
        if "200um" in solution.filters:
            filter_consts += FILTER_200UM_CF
        if "5um" in solution.filters:
            filter_consts += FILTER_5UM_CF
        if "1um" in solution.filters:
            filter_consts += FILTER_1UM_CF
    cf_total = filter_consts * CF_EXP
    
    if (solution.storage_z + WATER_HEIGHT_SUPPLYING + (solution.tower_height_m or 0)) <= 0:
        # If the storage tank is at or below the height of the house,
        # the configuration is invalid; no flow will occur to the house. In this case,
        # return None to indicate failure.
        return None
    
    W = (
        DENSITY
        * (PIPE_FRICTION_FACTOR * solution.storage_pipe_length / PIPE_DIAMETER + LOSS_COEFF_TO_HOUSE)
        / (2 * PUMP_CONV_G**2 * PIPE_DIAMETER**4 * pi**2)
    )
    
    X = (
        cf_total
        / (PUMP_CONV_G * pi * PIPE_DIAMETER**2)
    )
    Y = (
        -DENSITY * GRAVITY * (solution.storage_z + WATER_HEIGHT_SUPPLYING)
    )
    
    discriminant = X**2 - 4*W*Y
    if (discriminant < 0): # If the discriminant is negative, the pump can't push hard enough to overcome the system's resistance, so return None to indicate failure.
        return None
    # By the properties of quadratics, only the plus-root will be positive.
    Q = max((-X + discriminant**0.5) / (2*W), (-X - discriminant**0.5) / (2*W))
    
    # Flow rate is limited by the UV pump used as well.
    if solution.uv == "36W":
        Q = min(Q, UV_36W_MAX_FLOW_RATE)
    elif solution.uv == "40W":
        Q = min(Q, UV_40W_MAX_FLOW_RATE)
    elif solution.uv == "50W":
        Q = min(Q, UV_50W_MAX_FLOW_RATE)
    return Q

def pump_efficiency_from_flow_rate(flow_rate, solution) -> float:
    return (
        1.2 * solution.pump_efficiency_consts[0] # 1.2A
        * (
            exp(flow_rate / solution.pump_efficiency_consts[2]) - 1 # exp(Q/Qmax) - 1
            - 1.72 * (flow_rate / solution.pump_efficiency_consts[2])**4 # - 1.72(Q/Qmax)^4 
        )** solution.pump_efficiency_consts[1] # ^B
    )

def calculate_static_costs(solution: Design):
    # Calculate static costs that will always be incurred. 
    # Includes initial costs of replacable items, such as
    # filters, diesel, chlorine, and pumps.
    cost = 0
    # Roof catchment cost
    match solution.roof_choice:
        case "half":
            cost += HALF_ROOF_CATCHMENT_COST
        case "full":
            cost += FULL_ROOF_CATCHMENT_COST
        case "extra":
            cost += FULL_ROOF_CATCHMENT_COST + EXTRA_CATCHMENT_FLAT_COST + (solution.extra_catchment_area_m2 or 0) * EXTRA_CATCHMENT_COST_PER_M2
    
    # Catchment tank costs
    TANK_COSTS = {
        TANK_1_CAPACITY: TANK_1_COST,
        TANK_2_CAPACITY: TANK_2_COST,
        TANK_3_CAPACITY: TANK_3_COST,
        TANK_4_CAPACITY: TANK_4_COST,
        TANK_5_CAPACITY: TANK_5_COST,
    }
    tank_cost = TANK_COSTS.get(solution.catchment_tank_L)
    # Tank cost should never be None. If it is, that means there's a bug in the code that generates designs, since it should only be able to choose from valid tank capacities.
    if tank_cost is None:
        raise ValueError(f"Invalid catchment tank capacity: {solution.catchment_tank_L}")

    cost += tank_cost
    # Storage tank cost
    cost += solution.storage_volume_m3 * COST_PER_M3_STORAGE_TANK
    
    if solution.np_threshold_L is not None:
        cost += WATER_LEVEL_SENSOR_COST
    
    if solution.tower_height_m is not None and solution.tower_height_m > 0:
        cost += TOWER_COST_A * (solution.storage_volume_m3**1.6) + TOWER_COST_B * (solution.tower_height_m**1.8)
    
    # Piping cost. Three pipes exist:
    # 1. From catchment to storage.
    # 2. From storage to house.
    # 3. From catchment to house (if applicable).
    cost += PIPING_COST_PER_METER * solution.storage_pipe_length
    if solution.catchment_pipe_length is not None:
        cost += PIPING_COST_PER_METER * solution.catchment_pipe_length
    
    # Initial filter costs.
    for f in solution.filters:
        if f == "200um":
            cost += FILTER_200UM_INITIAL_COST
        elif f == "5um":
            cost += FILTER_5UM_INITIAL_COST
        elif f == "1um":
            cost += FILTER_1UM_INITIAL_COST
    
    # Disinfection system costs.
    if solution.chem == "chlorine":
        cost += CHLORINE_DOSER_COST + CHLORINE_CONTAINER_COST
    elif solution.chem == "ozone":
        cost += OZONE_DOSER_COST
    
    # We know the UV system costs for the whole sim immediately.
    if solution.uv == "36W":
        cost += UV_36W_COST * YEARS_OF_OPERATION # Replaced once per year
    elif solution.uv == "40W":
        cost += UV_40W_COST * YEARS_OF_OPERATION
    elif solution.uv == "50W":
        cost += UV_50W_COST * YEARS_OF_OPERATION
    
    # Initial pump costs
    match solution.pump:
        case "A":
            cost += PUMP_A_COST
        case "B":
            cost += PUMP_B_COST
        case "C":
            cost += PUMP_C_COST
    
    # Solar panel costs
    if solution.power == "solar":
        if solution.panel_model == "HES_260":
            cost += SOLAR_HES_260_COST * (solution.n_panels or 0)
        elif solution.panel_model == "SW_80":
            cost += SOLAR_SW_80_COST * (solution.n_panels or 0)
        elif solution.panel_model == "HES_305P":
            cost += SOLAR_HES_305P_COST * (solution.n_panels or 0)
    
    # Battery costs.
    cost += BATTERY_COST * solution.n_batteries
    if solution.power == "solar":
        cost += INVERTER_COST  # Solar always needs an inverter
    elif solution.power == "diesel":
        cost += GENERATOR_COST + DIESEL_COST_PER_REFUEL  # Initial purchase of diesel
    return cost

def calculate_relative_ghg_emissions(solution: Design, diesel_used_L: float, water_consumed_L: float):
    # Calculate non-RWH system kg C02e emissions for the same water consumption as the RWH system, for comparison.
    nonRWH_CO2 = 2408 + water_consumed_L * 6.5 / 1000 # 2408 kg CO2e from storage and distribution to house, and 6.5 kg CO2e per 1000L from treatment at water plant.
    
    # Calculate total GHG emissions
    # Diesel
    diesel_emissions_kg = diesel_used_L * DIESEL_GHG_PER_LITER
    # System
    solar_panel_emissions_kg = 0
    if solution.power == "solar":
        if solution.panel_model == "HES_260":
            solar_panel_emissions_kg = SOLAR_HES_260_GHG * (solution.n_panels or 0)
        elif solution.panel_model == "SW_80":
            solar_panel_emissions_kg = SOLAR_SW_80_GHG * (solution.n_panels or 0)
        elif solution.panel_model == "HES_305P":
            solar_panel_emissions_kg = SOLAR_HES_305P_GHG * (solution.n_panels or 0)
    
    battery_emissions_kg = solution.n_batteries * BATTERY_GHG
    inverter_emissions_kg = INVERTER_GHG if solution.power == "solar" else 0
    generator_flat_emissions_kg = GENERATOR_FLAT_GHG if solution.power == "diesel" else 0
    
    total_emissions_kg = (
        diesel_emissions_kg
        + solar_panel_emissions_kg
        + battery_emissions_kg
        + inverter_emissions_kg
        + generator_flat_emissions_kg
    )
    
    relative_emissions = total_emissions_kg / nonRWH_CO2
    return relative_emissions

def likelihood_rating_from_days(event_days_yearly: float) -> float:
    period_between_events = 365 / event_days_yearly
    return 4 - 0.5*log(period_between_events)

def calculate_risk_exposure(total_diesel_refills: int, total_chlorine_refills: int):
    # Likelihood rating is calculated from a yearly average.
    if total_diesel_refills == 0:
        diesel_risk = 0.0
    else:
        diesel_likelihood = likelihood_rating_from_days(total_diesel_refills / YEARS_OF_OPERATION)
        diesel_health = DIESEL_HEALTH_RISK * diesel_likelihood
        diesel_environment = DIESEL_ENVIRO_RISK * diesel_likelihood
        diesel_risk = diesel_health + diesel_environment
    
    if total_chlorine_refills == 0:
        chlorine_risk = 0.0
    else:
        chlorine_likelihood = likelihood_rating_from_days(total_chlorine_refills / YEARS_OF_OPERATION)
        chlorine_health = CHLORINE_HEALTH_RISK * chlorine_likelihood
        chlorine_environment = CHLORINE_ENVIRO_RISK * chlorine_likelihood
        chlorine_risk = chlorine_health + chlorine_environment
    
    return diesel_risk + chlorine_risk