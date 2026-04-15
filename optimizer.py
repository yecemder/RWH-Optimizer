
from __future__ import annotations

import argparse
import ast
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import asdict
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import random
from typing import Any

from RWHSystem import Design
import topology
from best_state import (
    design_from_jsonable,
    design_to_jsonable,
    load_best_payload,
    load_design_from_file,
    save_best_payload,
)
from constants import *
from environment import create_daily_rainfall_data, daily_hours_of_sunlight
from satisfaction_curve import (
    CONSUMPTION,
    REL_COST,
    HEALTH_RISK,
    GHG_EMISSIONS,
    MAINTENANCES,
    NON_POTABLE,
    ON_DEMAND_FLOW,
    RELIABILITY,
)
from simulator import simulate_design


_PUMP_MAP = {
    "A": ([PUMP_A_a, PUMP_A_b, PUMP_A_c], [PUMP_A_A, PUMP_A_B, PUMP_A_QMAX], [PUMP_A_COST, PUMP_A_MBTF]),
    "B": ([PUMP_B_a, PUMP_B_b, PUMP_B_c], [PUMP_B_A, PUMP_B_B, PUMP_B_QMAX], [PUMP_B_COST, PUMP_B_MBTF]),
    "C": ([PUMP_C_a, PUMP_C_b, PUMP_C_c], [PUMP_C_A, PUMP_C_B, PUMP_C_QMAX], [PUMP_C_COST, PUMP_C_MBTF]),
}


def _random_valid_xy(
    rng: random.Random,
    *,
    min_height: float | None = None,
) -> tuple[int, int]:
    while True:
        x = rng.randint(*XY_PLACEMENT_RANGE)
        y = rng.randint(*XY_PLACEMENT_RANGE)
        if (-20 <= x <= 20) and (-20 <= y <= 20):
            continue
        if min_height is not None and topology.get_height(x, y) < min_height:
            continue
        return x, y


def random_design(rng: random.Random | None = None) -> Design:
    rng = rng or random.Random()

    consumption = rng.randint(*CONSUMPTION_RANGE)
    use_nonpotable = rng.random() < NONPOTABLE_CHANCE
    nonpotable_threshold = rng.randint(*NONPOTABLE_THRESHOLD_RANGE) if use_nonpotable else None
    nonpotable_fraction_C = rng.uniform(*NONPOTABLE_PERDAY_RANGE) if use_nonpotable else None

    roof_choice = rng.choices(CATCHMENT_CHOICES, CATCHMENT_CHANCES, k=1)[0]
    extra_area = rng.randint(*CATCHMENT_EXTRA_AREA_RANGE) if roof_choice == "extra" else None
    extra_x = extra_y = None
    if roof_choice == "extra":
        extra_x, extra_y = _random_valid_xy(rng, min_height=3)

    catchment_tank_capacity = rng.choice(CATCHMENT_TANK_CAPACITY_CHOICES)
    storage_tank_capacity = rng.randint(*STORAGE_TANK_CAPACITY_RANGE)
    storage_tank_x, storage_tank_y = _random_valid_xy(rng)

    storage_tower_height = rng.randint(*STORAGE_TOWER_HEIGHT_RANGE) if rng.random() < STORAGE_TOWER_CHANCE else None
    pump = rng.choice(PUMP_CHOICES)
    filter_location = rng.choice(FILTER_LOCATION_CHOICES)

    # 1um is always required.
    filter_types = tuple(rng.sample(FILTER_CHOICES, rng.randint(0, len(FILTER_CHOICES))) + ["1um"])

    uv_type = rng.choice(UV_CHOICES)
    chem_type = rng.choice(CHEM_CHOICES)
    power_type = rng.choices(POWER_CHOICES, POWER_CHANCES, k=1)[0]
    solar_panel_model = rng.choice(SOLAR_PANEL_MODEL_CHOICES) if power_type == "solar" else None
    solar_panel_number = rng.randint(*SOLAR_PANEL_NUMBER_RANGE) if power_type == "solar" else None
    n_batteries = 1 if power_type == "diesel" else rng.randint(*BATTERY_NUMBER_RANGE)

    storage_z = topology.get_height(storage_tank_x, storage_tank_y) + (storage_tower_height or 0)
    storage_pipe_length = topology.get_pipe_length(storage_tank_x, storage_tank_y, z_offset=(storage_tower_height or 0))
    catchment_pipe_length = (
        topology.get_pipe_length(extra_x, extra_y, z_offset=0.0)
        if extra_x is not None and extra_y is not None
        else None
    )

    pump_flow_consts, pump_efficiency_consts, pump_other_consts = _PUMP_MAP[pump]

    return Design(
        C=consumption,
        np_threshold_L=nonpotable_threshold,
        np_fraction_C=nonpotable_fraction_C,
        roof_choice=roof_choice,
        extra_catchment_area_m2=extra_area,
        extra_catchment_x=extra_x,
        extra_catchment_y=extra_y,
        catchment_tank_L=catchment_tank_capacity,
        storage_volume_m3=storage_tank_capacity,
        storage_x=storage_tank_x,
        storage_y=storage_tank_y,
        tower_height_m=storage_tower_height,
        pump=pump,
        filter_location=filter_location,
        filters=filter_types,
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
        pump_other_consts=pump_other_consts,
    )


def random_designs(n: int, *, seed: int | None = None) -> list[Design]:
    rng = random.Random(seed)
    return [random_design(rng) for _ in range(n)]


def _score_single_result(result: dict[str, float] | None) -> dict[str, Any]:
    if result is None:
        return {
            "feasible": False,
            "score": 0.0,
            "satisfactions": {
                "consumption": 0.0,
                "relative_cost": 0.0,
                "health_risk": 0.0,
                "ghg_emissions": 0.0,
                "maintenances": 0.0,
                "non_potable": 0.0,
                "on_demand_flow": 0.0,
                "reliability": 0.0,
            },
        }

    mapping = {
        "consumption": CONSUMPTION.calculate_weighted_satisfaction(result["consumption"]),
        "relative_cost": REL_COST.calculate_weighted_satisfaction(result["relative_cost"]),
        "health_risk": HEALTH_RISK.calculate_weighted_satisfaction(result["risk_exposure"]),
        "ghg_emissions": GHG_EMISSIONS.calculate_weighted_satisfaction(result["relative_ghg"]),
        "maintenances": MAINTENANCES.calculate_weighted_satisfaction(result["maintenance_operations"]),
        "non_potable": NON_POTABLE.calculate_weighted_satisfaction(result["non_potable_avg"]),
        "on_demand_flow": ON_DEMAND_FLOW.calculate_weighted_satisfaction(result["on_demand_flow_rate"]),
        "reliability": RELIABILITY.calculate_weighted_satisfaction(result["reliability"]),
    }
    feasible = all(value is not None for value in mapping.values())
    satisfactions = {key: (0.0 if value is None else float(value)) for key, value in mapping.items()}
    score = sum(satisfactions.values()) if feasible else 0.0
    return {
        "feasible": feasible,
        "score": score,
        "satisfactions": satisfactions,
    }


def evaluate_design(
    design: Design,
    *,
    weather_seeds: list[int] | tuple[int, ...],
    sample_path: str | Path = "example_rainfall_mm.txt",
) -> dict[str, Any]:
    sunlight = daily_hours_of_sunlight()
    trial_results: list[dict[str, Any]] = []
    criterion_totals = {
        "consumption": 0.0,
        "relative_cost": 0.0,
        "health_risk": 0.0,
        "ghg_emissions": 0.0,
        "maintenances": 0.0,
        "non_potable": 0.0,
        "on_demand_flow": 0.0,
        "reliability": 0.0,
    }
    raw_metric_totals: dict[str, float] = {}
    total_score = 0.0
    feasible_trials = 0

    for weather_seed in weather_seeds:
        rainfall = create_daily_rainfall_data(seed=weather_seed, sample_path=sample_path)
        raw_result = simulate_design(design, rainfall, sunlight)
        scored = _score_single_result(raw_result)
        trial_results.append(
            {
                "weather_seed": weather_seed,
                "raw_result": raw_result,
                "score": scored["score"],
                "feasible": scored["feasible"],
                "satisfactions": scored["satisfactions"],
            }
        )
        if scored["feasible"]:
            feasible_trials += 1
        total_score += scored["score"]

        for key, value in scored["satisfactions"].items():
            criterion_totals[key] += value

        if raw_result is not None:
            for key, value in raw_result.items():
                raw_metric_totals[key] = raw_metric_totals.get(key, 0.0) + float(value)

    trial_count = max(1, len(tuple(weather_seeds)))
    avg_satisfactions = {key: value / trial_count for key, value in criterion_totals.items()}
    avg_raw_metrics = {key: value / trial_count for key, value in raw_metric_totals.items()}

    return {
        "design": design_to_jsonable(design),
        "avg_score": total_score / trial_count,
        "avg_satisfactions": avg_satisfactions,
        "avg_raw_metrics": avg_raw_metrics,
        "feasible_trial_fraction": feasible_trials / trial_count,
        "trial_results": trial_results,
    }


def _worker_best_of_batch(
    batch_size: int,
    *,
    design_seed: int,
    weather_seeds: list[int],
    sample_path: str,
) -> dict[str, Any] | None:
    rng = random.Random(design_seed)
    best: dict[str, Any] | None = None
    for _ in range(batch_size):
        design = random_design(rng)
        evaluation = evaluate_design(design, weather_seeds=weather_seeds, sample_path=sample_path)
        if best is None or evaluation["avg_score"] > best["avg_score"]:
            best = evaluation
    return best


def _build_saved_payload(
    evaluation: dict[str, Any],
    *,
    simulations_run: int,
    weather_trials: int,
    sample_path: str | Path,
) -> dict[str, Any]:
    return {
        "saved_at_utc": datetime.now(timezone.utc).isoformat(),
        "score": evaluation["avg_score"],
        "weather_trials": weather_trials,
        "sample_path": str(sample_path),
        "simulations_run": simulations_run,
        "feasible_trial_fraction": evaluation["feasible_trial_fraction"],
        "avg_satisfactions": evaluation["avg_satisfactions"],
        "avg_raw_metrics": evaluation["avg_raw_metrics"],
        "design": evaluation["design"],
    }


def parallel_random_search(
    total_designs: int,
    *,
    batch_size: int = 256,
    weather_trials: int = 1,
    sample_path: str | Path = "example_rainfall_mm.txt",
    runtime_path: str | Path = "best_runtime.json",
    editable_path: str | Path = "best_editable.json",
    max_workers: int | None = None,
    master_seed: int | None = None,
    resume: bool = True,
) -> dict[str, Any] | None:
    if total_designs <= 0:
        raise ValueError("total_designs must be positive")
    if batch_size <= 0:
        raise ValueError("batch_size must be positive")
    if weather_trials <= 0:
        raise ValueError("weather_trials must be positive")

    rng = random.Random(master_seed)
    sample_path = str(sample_path)

    persisted = load_best_payload(runtime_path) if resume else None
    best_score = float("-inf")
    best_payload: dict[str, Any] | None = None
    if persisted is not None:
        best_score = float(persisted.get("score", float("-inf")))
        best_payload = persisted

    batches = math.ceil(total_designs / batch_size)
    weather_seeds = [rng.randrange(2**63) for _ in range(weather_trials)]
    max_workers = max_workers or os.cpu_count() or 1
    max_workers = max(1, min(max_workers, batches))

    completed_designs = 0
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = []
        remaining = total_designs
        for _ in range(batches):
            current_batch_size = min(batch_size, remaining)
            remaining -= current_batch_size
            futures.append(
                executor.submit(
                    _worker_best_of_batch,
                    current_batch_size,
                    design_seed=rng.randrange(2**63),
                    weather_seeds=weather_seeds,
                    sample_path=sample_path,
                )
            )

        for future in as_completed(futures):
            local_best = future.result()
            if local_best is None:
                continue

            # local_best came from a batch of at most batch_size designs; this is only for progress tracking.
            completed_designs = min(total_designs, completed_designs + batch_size)

            if local_best["avg_score"] > best_score:
                best_score = float(local_best["avg_score"])
                best_payload = _build_saved_payload(
                    local_best,
                    simulations_run=completed_designs,
                    weather_trials=weather_trials,
                    sample_path=sample_path,
                )
                save_best_payload(best_payload, runtime_path=runtime_path, editable_path=editable_path)
                print(
                    f"[improved] score={best_score:.6f} "
                    f"feasible_fraction={local_best['feasible_trial_fraction']:.2%} "
                    f"after ~{completed_designs} designs"
                )

    return best_payload


def find_best_random_design(
    n: int,
    *,
    weather_trials: int = 1,
    sample_path: str | Path = "example_rainfall_mm.txt",
    runtime_path: str | Path = "best_runtime.json",
    editable_path: str | Path = "best_editable.json",
    max_workers: int | None = None,
    master_seed: int | None = None,
) -> dict[str, Any] | None:
    return parallel_random_search(
        n,
        weather_trials=weather_trials,
        sample_path=sample_path,
        runtime_path=runtime_path,
        editable_path=editable_path,
        max_workers=max_workers,
        master_seed=master_seed,
    )


def _parse_override(token: str) -> tuple[str, Any]:
    if "=" not in token:
        raise ValueError(f"Override must look like field=value, got: {token!r}")
    key, raw_value = token.split("=", 1)
    try:
        value = ast.literal_eval(raw_value)
    except Exception:
        lowered = raw_value.lower()
        if lowered == "none":
            value = None
        elif lowered in {"true", "false"}:
            value = lowered == "true"
        else:
            value = raw_value
    return key, value


def apply_overrides(design: Design, overrides: dict[str, Any]) -> Design:
    payload = design_to_jsonable(design, inputs_only=True)
    payload.update(overrides)
    if isinstance(payload.get("filters"), list):
        payload["filters"] = tuple(payload["filters"])
    return design_from_jsonable(payload)


def main() -> None:
    parser = argparse.ArgumentParser(description="Parallel random search for RWH designs.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    search_parser = subparsers.add_parser("search", help="Run parallel random search.")
    search_parser.add_argument("--designs", type=int, required=True, help="Total random designs to evaluate.")
    search_parser.add_argument("--batch-size", type=int, default=512)
    search_parser.add_argument("--weather-trials", type=int, default=3)
    search_parser.add_argument("--sample-path", default="example_rainfall_mm.txt")
    search_parser.add_argument("--runtime-path", default="best_runtime.json")
    search_parser.add_argument("--editable-path", default="best_editable.json")
    search_parser.add_argument("--max-workers", type=int, default=None)
    search_parser.add_argument("--seed", type=int, default=None)

    eval_parser = subparsers.add_parser("eval-best", help="Evaluate the editable design file.")
    eval_parser.add_argument("--design-path", default="best_editable.json")
    eval_parser.add_argument("--weather-trials", type=int, default=3)
    eval_parser.add_argument("--sample-path", default="example_rainfall_mm.txt")
    eval_parser.add_argument("--seed", type=int, default=None)
    eval_parser.add_argument("--set", action="append", default=[], dest="overrides")

    args = parser.parse_args()

    if args.command == "search":
        result = parallel_random_search(
            total_designs=args.designs,
            batch_size=args.batch_size,
            weather_trials=args.weather_trials,
            sample_path=args.sample_path,
            runtime_path=args.runtime_path,
            editable_path=args.editable_path,
            max_workers=args.max_workers,
            master_seed=args.seed,
        )
        if result is None:
            print("No design found.")
        else:
            print(json.dumps(result, indent=2))
        return

    if args.command == "eval-best":
        design = load_design_from_file(args.design_path)
        overrides = dict(_parse_override(token) for token in args.overrides)
        if overrides:
            design = apply_overrides(design, overrides)

        rng = random.Random(args.seed)
        weather_seeds = [rng.randrange(2**63) for _ in range(args.weather_trials)]
        result = evaluate_design(design, weather_seeds=weather_seeds, sample_path=args.sample_path)
        print(json.dumps(result, indent=2))
        return


if __name__ == "__main__":
    main()
