from dataclasses import dataclass, field

@dataclass
class Design:
    C: float                    # L/day
    use_nonpotable: bool
    np_threshold_L: float | None
    np_daily_frac_C: float | None

    roof_choice: str
    extra_catchment_area_m2: float | None
    extra_catchment_x: float | None
    extra_catchment_y: float | None
    catchment_tank_L: int

    storage_volume_m3: float
    storage_x: float
    storage_y: float
    use_tower: bool
    tower_height_m: float | None
    

    pump: str # "A", "B", or "C"
    filter_location: str  # "to storage" or "to house"
    filters: tuple              # e.g. ("200um", "5um", "1um")

    uv: str # "36W", "40W", or "50W"
    chem: str # "chlorine" or "ozone"

    power: str  # "diesel" or "solar"
    n_batteries: int | None             # Must be > 0 in all cases. If diesel, exactly 1. If solar, optimize? or choose random?
    
    panel_model: str | None     # "HES_260", "SW_80", or "HES_305P", or None if not solar
    n_panels: int | None

    # Derived attributes
    storage_z: int  # To be determined by the simulator.
    storage_pipe_length: float
    catchment_pipe_length: float | None
    pump_flow_consts: list[float]
    pump_efficiency_consts: list[float]