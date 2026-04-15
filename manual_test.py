
from __future__ import annotations

import argparse
import ast
import json
import random
from typing import Any

from best_state import load_design_from_file
from optimizer import apply_overrides, evaluate_design


def _parse_override(token: str) -> tuple[str, Any]:
    if "=" not in token:
        raise ValueError(f"Override must look like field=value, got {token!r}")
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


def main() -> None:
    parser = argparse.ArgumentParser(description="Quickly re-simulate a saved design with optional overrides.")
    parser.add_argument("--design", default="best_editable.json", help="Path to an editable design JSON file.")
    parser.add_argument("--sample-path", default="example_rainfall_mm.txt")
    parser.add_argument("--weather-trials", type=int, default=3)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--set", action="append", default=[], dest="overrides", help="Override like C=420 or filters=['200um','1um']")
    args = parser.parse_args()

    design = load_design_from_file(args.design)
    if args.overrides:
        design = apply_overrides(design, dict(_parse_override(token) for token in args.overrides))

    rng = random.Random(args.seed)
    weather_seeds = [rng.randrange(2**63) for _ in range(args.weather_trials)]
    evaluation = evaluate_design(design, weather_seeds=weather_seeds, sample_path=args.sample_path)
    print(json.dumps(evaluation, indent=2))


if __name__ == "__main__":
    main()
