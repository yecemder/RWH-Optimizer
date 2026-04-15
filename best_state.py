
from __future__ import annotations

from dataclasses import asdict
import json
from pathlib import Path
from typing import Any

from RWHSystem import Design
import topology
from constants import (
    PUMP_A_a, PUMP_A_b, PUMP_A_c, PUMP_A_A, PUMP_A_B, PUMP_A_QMAX, PUMP_A_COST, PUMP_A_MBTF,
    PUMP_B_a, PUMP_B_b, PUMP_B_c, PUMP_B_A, PUMP_B_B, PUMP_B_QMAX, PUMP_B_COST, PUMP_B_MBTF,
    PUMP_C_a, PUMP_C_b, PUMP_C_c, PUMP_C_A, PUMP_C_B, PUMP_C_QMAX, PUMP_C_COST, PUMP_C_MBTF,
)


DESIGN_KEYS = tuple(Design.__annotations__.keys())
INPUT_KEYS = (
    "C",
    "np_threshold_L",
    "np_fraction_C",
    "roof_choice",
    "extra_catchment_area_m2",
    "extra_catchment_x",
    "extra_catchment_y",
    "catchment_tank_L",
    "storage_volume_m3",
    "storage_x",
    "storage_y",
    "tower_height_m",
    "pump",
    "filter_location",
    "filters",
    "uv",
    "chem",
    "power",
    "n_batteries",
    "panel_model",
    "n_panels",
)
_DERIVED_KEYS = tuple(key for key in DESIGN_KEYS if key not in INPUT_KEYS)

_PUMP_MAP = {
    "A": ([PUMP_A_a, PUMP_A_b, PUMP_A_c], [PUMP_A_A, PUMP_A_B, PUMP_A_QMAX], [PUMP_A_COST, PUMP_A_MBTF]),
    "B": ([PUMP_B_a, PUMP_B_b, PUMP_B_c], [PUMP_B_A, PUMP_B_B, PUMP_B_QMAX], [PUMP_B_COST, PUMP_B_MBTF]),
    "C": ([PUMP_C_a, PUMP_C_b, PUMP_C_c], [PUMP_C_A, PUMP_C_B, PUMP_C_QMAX], [PUMP_C_COST, PUMP_C_MBTF]),
}


def design_to_jsonable(design: Design, *, inputs_only: bool = False) -> dict[str, Any]:
    payload = asdict(design)
    if isinstance(payload.get("filters"), tuple):
        payload["filters"] = list(payload["filters"])
    if inputs_only:
        payload = {key: payload[key] for key in INPUT_KEYS}
    return payload


def _derive_fields(payload: dict[str, Any]) -> dict[str, Any]:
    storage_x = payload["storage_x"]
    storage_y = payload["storage_y"]
    tower_height_m = payload["tower_height_m"] or 0
    storage_z = topology.get_height(storage_x, storage_y) + tower_height_m
    storage_pipe_length = topology.get_pipe_length(storage_x, storage_y, z_offset=tower_height_m)

    extra_x = payload.get("extra_catchment_x")
    extra_y = payload.get("extra_catchment_y")
    catchment_pipe_length = (
        topology.get_pipe_length(extra_x, extra_y, z_offset=0.0)
        if extra_x is not None and extra_y is not None
        else None
    )

    pump = payload["pump"]
    pump_flow_consts, pump_efficiency_consts, pump_other_consts = _PUMP_MAP[pump]

    return {
        "storage_z": storage_z,
        "storage_pipe_length": storage_pipe_length,
        "catchment_pipe_length": catchment_pipe_length,
        "pump_flow_consts": pump_flow_consts,
        "pump_efficiency_consts": pump_efficiency_consts,
        "pump_other_consts": pump_other_consts,
    }


def design_from_jsonable(data: dict[str, Any]) -> Design:
    payload = dict(data)
    if "filters" in payload and isinstance(payload["filters"], list):
        payload["filters"] = tuple(payload["filters"])

    missing_inputs = [key for key in INPUT_KEYS if key not in payload]
    if missing_inputs:
        raise ValueError(f"Missing design input fields: {missing_inputs}")

    inputs = {key: payload[key] for key in INPUT_KEYS}
    derived = _derive_fields(inputs)
    return Design(**inputs, **derived)


def save_best_payload(
    payload: dict[str, Any],
    runtime_path: str | Path = "best_runtime.json",
    editable_path: str | Path = "best_editable.json",
) -> None:
    runtime_path = Path(runtime_path)
    editable_path = Path(editable_path)

    runtime_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    editable_design = payload.get("design")
    if editable_design is not None:
        editable_path.write_text(
            json.dumps({key: editable_design[key] for key in INPUT_KEYS}, indent=2, sort_keys=True),
            encoding="utf-8",
        )


def load_best_payload(path: str | Path = "best_runtime.json") -> dict[str, Any] | None:
    target = Path(path)
    if not target.exists():
        return None
    return json.loads(target.read_text(encoding="utf-8"))


def load_design_from_file(path: str | Path = "best_editable.json") -> Design:
    target = Path(path)
    data = json.loads(target.read_text(encoding="utf-8"))
    return design_from_jsonable(data)
