"""Cross-platform helpers for running the simulation pipeline.

The project can generate MicroStructPy/Abaqus input files in WSL/Linux, but
Abaqus itself is usually installed on Windows.  This module keeps the bridge
logic isolated so the original research scripts can stay mostly unchanged.
"""

from __future__ import annotations

import os
import platform
import shutil
import shlex
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
        return shlex.split(configured)

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


def _is_cmd_abaqus_bridge(command: Sequence[str]) -> bool:
    """Return True when Abaqus will be launched through Windows cmd.exe."""
    lowered = [part.lower() for part in command]
    return len(lowered) >= 3 and lowered[0].endswith("cmd.exe") and lowered[1] == "/c" and lowered[2] == "abaqus"


def _windows_safe_cwd() -> str | None:
    r"""Return a WSL path that resolves to a normal Windows drive path.

    Windows cmd.exe cannot start with a WSL UNC path as its current directory
    (for example ``\\wsl.localhost\Ubuntu\...``).  Starting cmd.exe from a
    real Windows path avoids the "UNC paths are not supported" fallback.
    """
    for candidate in (Path("/mnt/c/Windows/Temp"), Path("/mnt/c/Users/Public")):
        if candidate.exists():
            return str(candidate)
    return None


def _cmd_quote(value: str) -> str:
    """Quote a Windows cmd.exe argument."""
    return '"' + value.replace('"', '\\"') + '"'


def run_cmd_abaqus_in_wsl_directory(
    abaqus_args: Sequence[str],
    cwd: str | os.PathLike[str],
) -> subprocess.CompletedProcess[str]:
    r"""Run Windows Abaqus from WSL while using a WSL output directory.

    ``cmd.exe`` cannot use a ``\\wsl.localhost\...`` UNC path as its initial
    working directory.  ``pushd`` can temporarily map that UNC path to a Windows
    drive letter, so Abaqus sees a normal working directory and can find the
    generated ``.inp`` file by job name.
    """
    win_cwd = wsl_to_windows_path(cwd)
    command_text = "pushd " + _cmd_quote(win_cwd) + " && abaqus " + " ".join(abaqus_args) + " && popd"
    command = ["cmd.exe", "/C", command_text]
    safe_cwd = _windows_safe_cwd()
    print("Running:", " ".join(command))
    print("Working directory:", cwd)
    if safe_cwd:
        print("cmd.exe launch directory:", safe_cwd)
    return subprocess.run(command, cwd=safe_cwd, check=True, text=True)


def run_abaqus_job(abaqus_simulation_directory: str | os.PathLike[str], simulation_name: str) -> None:
    """Run ``abaqus j=<simulation_name> interactive`` in a portable way."""
    workdir = Path(abaqus_simulation_directory).resolve()
    command = find_abaqus_command() + [f"j={simulation_name}", "interactive"]
    if is_wsl() and _is_cmd_abaqus_bridge(command):
        run_cmd_abaqus_in_wsl_directory([f"j={simulation_name}", "interactive"], workdir)
        return
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
    if is_wsl() and _is_cmd_abaqus_bridge(command):
        run_cmd_abaqus_in_wsl_directory(["cae", f"noGUI={script_arg}"], workdir)
        return
    run_command(command, workdir)
