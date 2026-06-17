# This script is to convert data gathered from the MTS machine to Stress and Strain to compare with simulation results
import numpy as np
import pandas as pd
import os

def force_disp_to_stress_strain(experimental_results, transformed_filename):

  # Necessary parameters to convert load to stress
  diameter_in = 0.5
  diameter_mm = diameter_in * 25.4
  area_mm2 = (diameter_mm / 2) ** 2 * np.pi

  exp_df = pd.read_csv(experimental_results, header=0)

  # Extract stress and strain data for experiment
  strain_exp = exp_df['mm/mm']
  load_exp = exp_df['N']

  # Convert load to stress
  stress_MPa_exp = load_exp / area_mm2

  # Center the loop
  stress_offset_exp = 0.5 * (np.max(stress_MPa_exp) + np.min(stress_MPa_exp))
  stress_centered_exp = stress_MPa_exp - stress_offset_exp

  resulting_df = pd.DataFrame({
    'strain': strain_exp,
    'stress_MPa': stress_centered_exp})
  resulting_df.to_csv(
    os.path.join(os.path.dirname(__file__), transformed_filename),
    index=False
  )

if __name__ == '__main__':
  # Change the filenames below
  experimental_results = os.path.join(os.path.dirname(__file__), 'aa7075-T651_cyclic_experimental_FvD.csv')
  transformed_filename = 'aa7075-T651_cyclic_experimental_SvS.csv'

  force_disp_to_stress_strain(experimental_results, transformed_filename)