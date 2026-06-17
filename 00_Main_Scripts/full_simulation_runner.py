import os
from abaqus_input_generation_v02 import generate_input
from run_abaqus_sim import run_simulation
from postprocessing_abaqus_sim_v01 import post_processing

# This has a GUI attached that allows you to the select the default folder to find input files to submit to the simulation.
input_files_folder = r'C:\Users\MAEadmin\Desktop\microstructure fatigue simulation\simulation_inputs\AL7075-T6'

# MODIFY THIS LINE OF CODE:
## Options:
### 1) Empty string. Automatically opens the GUI to select folder in the same directory where this script exists. For example:
# input_files_folder = r''
### 2) a raw string (ie. "r'text'") with the path to your inputs folder. For example:
# input_files_folder = r'C:\Users\MAEadmin\Desktop\microstructure fatigue simulation\simulation_inputs'


def run_full_simulation():
 
    abaqus_output_directory, simulation_name = generate_input(input_files_folder)

    # abaqus_output_directory = r'C:\Users\MAEadmin\Desktop\microstructure fatigue simulation\simulation_outputs\bp_size_case_13\abaqus_files'
    # simulation_name = os.path.basename(os.path.dirname(abaqus_output_directory))
    run_simulation(abaqus_output_directory, simulation_name)


    # If stress_strain_plot_sttngs is None that means default post processing (show_area=True, show_plot=True, save_fig=True)
    # To change this just assign values to it in that order (eg. True, True, False)
    stress_strain_plot_sttngs = None
    post_processing(abaqus_output_directory, simulation_name, stress_strain_plot_sttngs)

def main():

    run_full_simulation()

if __name__ == "__main__":
   main() 