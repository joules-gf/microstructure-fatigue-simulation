"""Cross-platform helpers for running the simulation pipeline.

The project can generate MicroStructPy/Abaqus input files in WSL/Linux, but
Abaqus itself is usually installed on Windows.  This module keeps the bridge
logic isolated so the original research scripts can stay mostly unchanged.
"""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
from pathlib import Path
from typing import Sequence


class AbaqusUnavailableError(RuntimeError):
    """Raised when Abaqus cannot be found from the current environment."""


def is_wsl() -> bool:
    """Return True when running inside Windows Subsystem for Linux."""
    if "microsoft" in platform.release().lower():
        return True
    try:
        return "microsoft" in Path("/proc/version").read_text(errors="ignore").lower()
    except OSError:
        return False


def is_truthy(value: str | None) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def noninteractive_enabled() -> bool:
    """Whether GUI prompts/plots should be skipped for command-line runs."""
    return is_truthy(os.environ.get("MICROSTRUCTURE_NONINTERACTIVE"))


def wsl_to_windows_path(path: str | os.PathLike[str]) -> str:
    """Convert a WSL path to a Windows path using wslpath when available."""
    path_str = str(Path(path).resolve())
    if not is_wsl():
        return path_str
    if shutil.which("wslpath") is None:
        return path_str
    result = subprocess.run(
        ["wslpath", "-w", path_str],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def find_abaqus_command() -> list[str]:
    """Return a command prefix that can launch Abaqus.

    Preference order:
    1. MICROSTRUCTURE_ABAQUS_CMD, if set. This may be a normal executable name
       such as ``abaqus`` or a full command path.
    2. Native ``abaqus`` in the current PATH.
    3. From WSL, Windows ``cmd.exe /C abaqus`` if cmd.exe is exposed.
    """
    configured = os.environ.get("MICROSTRUCTURE_ABAQUS_CMD")
    if configured:
        return configured.split()

    if shutil.which("abaqus"):
        return ["abaqus"]

    if is_wsl() and shutil.which("cmd.exe"):
        return ["cmd.exe", "/C", "abaqus"]

    raise AbaqusUnavailableError(
        "Abaqus was not found. Install/configure Abaqus, add it to PATH, or set "
        "MICROSTRUCTURE_ABAQUS_CMD. In WSL, expose Windows cmd.exe/abaqus or run "
        "the generated .inp file manually on Windows."
    )


def run_command(command: Sequence[str], cwd: str | os.PathLike[str]) -> subprocess.CompletedProcess[str]:
    """Run a subprocess, streaming output, and raise on failure."""
    print("Running:", " ".join(command))
    print("Working directory:", cwd)
    return subprocess.run(command, cwd=str(cwd), check=True, text=True)


def run_abaqus_job(abaqus_simulation_directory: str | os.PathLike[str], simulation_name: str) -> None:
    """Run ``abaqus j=<simulation_name> interactive`` in a portable way."""
    workdir = Path(abaqus_simulation_directory).resolve()
    command = find_abaqus_command() + [f"j={simulation_name}", "interactive"]
    run_command(command, workdir)


def run_abaqus_cae_no_gui(
    abaqus_output_directory: str | os.PathLike[str],
    script_path: str | os.PathLike[str],
) -> None:
    """Run an Abaqus/CAE noGUI postprocessing script portably."""
    workdir = Path(abaqus_output_directory).resolve()
    script = Path(script_path).resolve()

    if is_wsl() and shutil.which("cmd.exe") and not shutil.which("abaqus"):
        script_arg = wsl_to_windows_path(script)
    else:
        script_arg = str(script)

    command = find_abaqus_command() + ["cae", f"noGUI={script_arg}"]
    run_command(command, workdir)
