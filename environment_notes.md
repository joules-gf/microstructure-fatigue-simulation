# Environment notes

These notes are meant to make the project easier to share through GitHub while keeping the current research code mostly unchanged.

## Intended environments

### 1. Windows + VS Code

This is the primary target for running the full workflow because Abaqus is usually installed on Windows lab/workstation machines.

Recommended workflow:

1. Clone or download the repository.
2. Open the project folder in VS Code.
3. Create a Python virtual environment for the regular Python scripts.
4. Install `requirements.txt`.
5. Confirm Abaqus is callable from a terminal.
6. Run the pipeline scripts from the project root or from `00_Main_Scripts/`, depending on the current script behavior.

Example PowerShell setup:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Check Abaqus:

```powershell
abaqus information=system
```

If that command fails, Abaqus is either not installed, not licensed, or not on the system PATH.

### 2. WSL / Linux

WSL is useful for validating the parts of the workflow that do not require Abaqus:

- Python syntax checks
- XML parsing and file organization
- plotting utilities, if dependencies are installed
- project-relative path changes
- general code review and automation

WSL usually cannot run the full Abaqus workflow unless Abaqus is installed/configured in that environment, which is uncommon.

Example WSL setup:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Python dependencies

Install regular Python dependencies with:

```bash
pip install -r requirements.txt
```

Current regular dependencies:

- `numpy`
- `pandas`
- `matplotlib`
- `microstructpy`

## Abaqus dependencies

The following modules are not normal pip packages:

- `abaqus`
- `abaqusConstants`
- `odbAccess`

They are provided by the Abaqus Python environment. Scripts that import these modules must be run through Abaqus, for example:

```bash
abaqus cae noGUI=00_Main_Scripts/getForceDisp.py
```

Do not add Abaqus Python modules to `requirements.txt`.

## Current portability limitation

Some scripts still contain hardcoded Windows paths from the original development machine, for example paths under:

```text
C:\Users\MAEadmin\Desktop\...
```

For GitHub sharing, this is acceptable as a first checkpoint, but the next cleanup step should replace these with project-relative paths using `pathlib.Path`.

Recommended target pattern:

```python
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
input_files_folder = PROJECT_ROOT / "simulation_inputs" / "AL7075-T6"
```

This style works on both Windows and WSL/Linux.

## Current full-pipeline entry point

The current intended full-pipeline script is:

```bash
python 00_Main_Scripts/full_simulation_runner.py
```

That script calls:

1. `abaqus_input_generation_v02.generate_input(...)`
2. `run_abaqus_sim.run_simulation(...)`
3. `postprocessing_abaqus_sim_v01.post_processing(...)`

## Recommended near-term improvements

These are intentionally small and compatible with keeping the code mostly as-is:

1. Replace hardcoded absolute paths with project-relative paths.
2. Add optional command-line arguments for input folders/files.
3. Separate the workflow into generate-only, run-Abaqus, and postprocess-only modes.
4. Replace `os.system(...)` calls with `subprocess.run(...)` for better error reporting.
5. Save simulation metadata with each output folder.

## GitHub sharing notes

Before uploading generated or sensitive content, check that `.gitignore` excludes:

- Python caches: `__pycache__/`, `*.pyc`
- virtual environments: `.venv/`, `venv/`
- Abaqus generated files: `.odb`, `.dat`, `.msg`, `.sta`, `.lck`, etc.
- generated output folders: `simulation_outputs/`, `generated_outputs/`

The repository should keep source code, input XML files, reference CSV data, and documentation.
