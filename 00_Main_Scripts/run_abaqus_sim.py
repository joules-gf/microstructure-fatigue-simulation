import os

# Run Abaqus Simulation 
def run_simulation(abaqus_simulation_directory, simulation_name):
    os.chdir(abaqus_simulation_directory)
    os.system(f"abaqus j={simulation_name} interactive")