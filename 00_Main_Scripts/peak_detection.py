"""Find stress peak times from the global force-displacement CSV.

This is the cleaned-up version of the old ``stressPeakTimes`` scripts.  The
current workflow writes one global CSV per simulation case:

    simulation_outputs/<case_name>/<case_name>.csv

The CSV has one metadata line followed by the real header row, so this module
reads it with ``header=1``.
"""

from __future__ import annotations

from pathlib import Path
from typing import NamedTuple

import pandas as pd


class PeakTimes(NamedTuple):
    """Positive/negative peak times and the matching Abaqus frame numbers."""

    raw_times: list[float | None]
    frame_numbers: list[int | None]


def global_csv_path(case_folder: str | Path) -> Path:
    """Return ``<case_folder>/<case_folder_name>.csv``."""
    folder = Path(case_folder).expanduser().resolve()
    return folder / f"{folder.name}.csv"


def _find_peak_indices(values, *, positive: bool) -> list[int]:
    """Return simple local-max or local-min peak indices.

    I used a small dependency-free peak finder instead of SciPy so this helper
    stays available in the normal project venv and in lightweight test runs.
    """
    series = list(values)
    peak_indices: list[int] = []
    for index in range(1, len(series) - 1):
        previous_value = series[index - 1]
        current_value = series[index]
        next_value = series[index + 1]
        if positive and current_value > previous_value and current_value > next_value:
            peak_indices.append(index)
        if not positive and current_value < previous_value and current_value < next_value:
            peak_indices.append(index)
    return peak_indices


def _drop_leading_zero_peak(times: list[float], stresses: list[float]) -> tuple[list[float], list[float]]:
    if times and (abs(times[0]) == 0.0 or abs(stresses[0]) == 0.0):
        return times[1:], stresses[1:]
    return times, stresses


def last_stress_peak_times(case_folder: str | Path, *, time_to_frame_scale: float = 100.0) -> PeakTimes:
    """Return final positive/negative stress peak times and frame numbers.

    Parameters
    ----------
    case_folder:
        Simulation output folder, for example
        ``simulation_outputs/baseline_parameters``.
    time_to_frame_scale:
        Conversion from step time to Abaqus frame number.  The old workflow used
        ``round(step_time * 100)``; this remains the default.
    """
    csv_path = global_csv_path(case_folder)
    if not csv_path.is_file():
        raise FileNotFoundError(f"Expected global CSV at: {csv_path}")

    data = pd.read_csv(csv_path, header=1)
    required_columns = {"Step Time", "Total RF Y"}
    missing_columns = required_columns.difference(data.columns)
    if missing_columns:
        raise ValueError(f"Global CSV is missing required columns: {sorted(missing_columns)}")

    time = data["Step Time"].astype(float).tolist()
    stress = data["Total RF Y"].astype(float).tolist()

    positive_indices = _find_peak_indices(stress, positive=True)
    negative_indices = _find_peak_indices(stress, positive=False)

    positive_times = [time[index] for index in positive_indices]
    positive_stresses = [stress[index] for index in positive_indices]
    negative_times = [time[index] for index in negative_indices]
    negative_stresses = [stress[index] for index in negative_indices]

    positive_times, positive_stresses = _drop_leading_zero_peak(positive_times, positive_stresses)
    negative_times, negative_stresses = _drop_leading_zero_peak(negative_times, negative_stresses)

    last_positive_time = float(positive_times[-1]) if positive_times else None
    last_negative_time = float(negative_times[-1]) if negative_times else None
    raw_times = [last_positive_time, last_negative_time]
    frame_numbers = [int(round(t * time_to_frame_scale)) if t is not None else None for t in raw_times]
    return PeakTimes(raw_times=raw_times, frame_numbers=frame_numbers)
