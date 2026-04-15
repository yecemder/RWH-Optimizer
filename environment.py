
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
import math
import random
from typing import Sequence

from constants import YEARS_OF_OPERATION


@dataclass(frozen=True)
class RainfallModel:
    wet_if_wet: tuple[float, ...]
    wet_if_dry: tuple[float, ...]
    gamma_shape: tuple[float, ...]
    gamma_scale: tuple[float, ...]
    empirical_windows: tuple[tuple[float, ...], ...]
    direct_resample_prob: float
    max_event_mm: float
    wet_threshold_mm: float = 0.1


def _default_sample_path() -> Path:
    return Path(__file__).with_name("example_rainfall_mm.txt")


def load_sample_rainfall_year(path: str | Path | None = None) -> list[float]:
    """Load a single reference year of daily rainfall in mm/day."""
    sample_path = Path(path) if path is not None else _default_sample_path()
    values = [
        float(line.strip())
        for line in sample_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if len(values) != 365:
        raise ValueError(f"Expected 365 rainfall entries, got {len(values)} from {sample_path}")
    return values


def _circular_distance(a: int, b: int, period: int = 365) -> int:
    diff = abs(a - b)
    return min(diff, period - diff)


def _gaussian_weight(distance: int, bandwidth: float) -> float:
    return math.exp(-0.5 * (distance / bandwidth) ** 2)


def _weighted_mean(values: Sequence[float], weights: Sequence[float]) -> float:
    weight_sum = sum(weights)
    if weight_sum <= 0:
        return 0.0
    return sum(v * w for v, w in zip(values, weights)) / weight_sum


def _fit_gamma_from_samples(values: Sequence[float], weights: Sequence[float]) -> tuple[float, float]:
    """Method-of-moments gamma fit with conservative fallbacks."""
    if not values:
        return 1.0, 1.0

    mean = _weighted_mean(values, weights)
    if mean <= 0:
        return 1.0, 1.0

    weight_sum = sum(weights)
    if weight_sum <= 0:
        return 1.0, mean

    var = sum(w * (v - mean) ** 2 for v, w in zip(values, weights)) / weight_sum
    var = max(var, 0.25)  # keep distribution from collapsing
    shape = max(0.35, min(25.0, mean * mean / var))
    scale = max(0.05, min(250.0, var / mean))
    return shape, scale


def fit_rainfall_model(sample_year_mm: Sequence[float], *, bandwidth_days: float = 18.0) -> RainfallModel:
    """
    Fit a simple seasonal wet/dry Markov model plus wet-day gamma amounts.

    This is intentionally lightweight and robust to having only one reference year.
    """
    if len(sample_year_mm) != 365:
        raise ValueError(f"Expected 365 daily rainfall values, got {len(sample_year_mm)}")

    rain = [max(0.0, float(x)) for x in sample_year_mm]
    wet = [value > 0.1 for value in rain]
    wet_amounts_global = [value for value in rain if value > 0.1]
    if not wet_amounts_global:
        raise ValueError("Sample rainfall year contains no wet days.")

    wet_if_wet: list[float] = []
    wet_if_dry: list[float] = []
    gamma_shape: list[float] = []
    gamma_scale: list[float] = []
    empirical_windows: list[tuple[float, ...]] = []

    overall_wet_rate = sum(wet) / 365.0
    global_shape, global_scale = _fit_gamma_from_samples(wet_amounts_global, [1.0] * len(wet_amounts_global))
    sample_max = max(rain)

    for day in range(365):
        wet_from_wet_vals: list[float] = []
        wet_from_wet_wts: list[float] = []
        wet_from_dry_vals: list[float] = []
        wet_from_dry_wts: list[float] = []
        local_wet_vals: list[float] = []
        local_wet_wts: list[float] = []

        for j in range(365):
            distance = _circular_distance(day, j)
            weight = _gaussian_weight(distance, bandwidth_days)
            if wet[j]:
                local_wet_vals.append(rain[j])
                local_wet_wts.append(weight)

            prev_wet = wet[j - 1] if j > 0 else wet[-1]
            if prev_wet:
                wet_from_wet_vals.append(1.0 if wet[j] else 0.0)
                wet_from_wet_wts.append(weight)
            else:
                wet_from_dry_vals.append(1.0 if wet[j] else 0.0)
                wet_from_dry_wts.append(weight)

        p_ww = _weighted_mean(wet_from_wet_vals, wet_from_wet_wts) if wet_from_wet_vals else overall_wet_rate
        p_wd = _weighted_mean(wet_from_dry_vals, wet_from_dry_wts) if wet_from_dry_vals else overall_wet_rate

        # Keep some persistence and avoid pathological 0/1 probabilities from one-year data.
        wet_if_wet.append(min(0.98, max(0.02, p_ww)))
        wet_if_dry.append(min(0.98, max(0.02, p_wd)))

        if len(local_wet_vals) >= 3:
            shape, scale = _fit_gamma_from_samples(local_wet_vals, local_wet_wts)
            gamma_shape.append(shape)
            gamma_scale.append(scale)
        else:
            gamma_shape.append(global_shape)
            gamma_scale.append(global_scale)

        local_empirical = [v for v in local_wet_vals if v > 0.1]
        if not local_empirical:
            local_empirical = wet_amounts_global
        empirical_windows.append(tuple(local_empirical))

    return RainfallModel(
        wet_if_wet=tuple(wet_if_wet),
        wet_if_dry=tuple(wet_if_dry),
        gamma_shape=tuple(gamma_shape),
        gamma_scale=tuple(gamma_scale),
        empirical_windows=tuple(empirical_windows),
        direct_resample_prob=0.18,
        max_event_mm=max(80.0, sample_max * 1.4),
        wet_threshold_mm=0.1,
    )


@lru_cache(maxsize=4)
def load_rainfall_model(sample_path: str | Path | None = None) -> RainfallModel:
    values = load_sample_rainfall_year(sample_path)
    return fit_rainfall_model(values)


def _generate_one_year(model: RainfallModel, rng: random.Random) -> list[float]:
    wet_today = rng.random() < 0.5 * (model.wet_if_wet[0] + model.wet_if_dry[0])
    out: list[float] = []

    for day in range(365):
        p_wet = model.wet_if_wet[day] if wet_today else model.wet_if_dry[day]
        wet_today = rng.random() < p_wet

        if not wet_today:
            out.append(0.0)
            continue

        if rng.random() < model.direct_resample_prob and model.empirical_windows[day]:
            amount = rng.choice(model.empirical_windows[day])
            amount *= rng.uniform(0.9, 1.15)
        else:
            amount = rng.gammavariate(model.gamma_shape[day], model.gamma_scale[day])

        amount = min(model.max_event_mm, max(0.1, amount))
        out.append(round(amount, 1))

    return out


def create_daily_rainfall_data(
    years: int = YEARS_OF_OPERATION,
    *,
    seed: int | None = None,
    sample_path: str | Path | None = None,
) -> list[float]:
    """
    Generate daily rainfall in mm/day.

    The generator uses the attached one-year rainfall file as an empirical baseline,
    preserving:
      - lots of zero-rain days
      - wet/dry spell clustering
      - seasonal wet-day intensity
      - occasional heavy storms
    """
    rng = random.Random(seed)
    model = load_rainfall_model(sample_path)
    rainfall: list[float] = []
    for _ in range(years):
        rainfall.extend(_generate_one_year(model, rng))
    return rainfall


def daily_hours_of_sunlight(years: int = YEARS_OF_OPERATION) -> list[float]:
    return (
        [8.50]  * 31 +  # January
        [10.0]  * 28 +  # February
        [11.8]  * 31 +  # March
        [13.6]  * 30 +  # April
        [15.3]  * 31 +  # May
        [16.0]  * 30 +  # June
        [15.75] * 31 +  # July
        [14.2]  * 31 +  # August
        [12.5]  * 30 +  # September
        [10.75] * 31 +  # October
        [9.0]   * 30 +  # November
        [8.25]  * 31    # December
    ) * years

if __name__ == "__main__":
    for r in range(3):
        data = create_daily_rainfall_data(seed=r)
        print(f"Sample rainfall data (first 60 days): {data[:60]}")