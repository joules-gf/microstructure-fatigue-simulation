"""Quick environment diagnostic for WSL/Windows simulation runs.

Run from the repository root:

    python 00_Main_Scripts/check_wsl_environment.py

This does not run a simulation. It checks whether the normal Python packages,
MicroStructPy/Gmsh native libraries, and Abaqus bridge are visible.
"""

from __future__ import annotations

import importlib
import shutil
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from wsl_windows_compat import find_abaqus_command, is_wsl, AbaqusUnavailableError


def check_import(module_name: str) -> bool:
    try:
        importlib.import_module(module_name)
    except Exception as exc:  # intentionally broad: native-library import errors matter here
        print(f"❌ {module_name}: {type(exc).__name__}: {exc}")
        return False
    else:
        print(f"✅ {module_name}: available")
        return True


def main() -> int:
    ok = True
    print(f"Python: {sys.executable}")
    print(f"WSL detected: {is_wsl()}")
    print(f"cmd.exe visible: {bool(shutil.which('cmd.exe'))}")
    print(f"native abaqus visible: {bool(shutil.which('abaqus'))}")
    print()

    for module in ["numpy", "pandas", "matplotlib", "scipy", "microstructpy"]:
        ok = check_import(module) and ok

    print()
    try:
        command = find_abaqus_command()
    except AbaqusUnavailableError as exc:
        print(f"⚠️ Abaqus bridge: {exc}")
        # Abaqus can be unavailable for generate-only checks, so do not fail hard.
    else:
        print(f"✅ Abaqus command prefix: {' '.join(command)}")

    if not ok:
        print("\nSuggested WSL system package for the observed Gmsh/MicroStructPy error:")
        print("  sudo apt-get update && sudo apt-get install -y libglu1-mesa")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
