from wsl_windows_compat import run_abaqus_job


# Run Abaqus Simulation
# On normal Windows/Linux this calls `abaqus` directly.  In WSL, if native
# Abaqus is unavailable but Windows cmd.exe is exposed, the helper tries to
# bridge to Windows with `cmd.exe /C abaqus`.
def run_simulation(abaqus_simulation_directory, simulation_name):
    run_abaqus_job(abaqus_simulation_directory, simulation_name)
