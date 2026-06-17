import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# Data to use for plot
yield_stresses_MPa = np.array([350, 470, 710, 710])
E_MPa = 71e3

# x values (strain)
strain_percentage = np.linspace(0, 1)

# Determine matrix output shape
n = len(strain_percentage)
m = len(yield_stresses_MPa)
shape = (n, m)

# Assign output variable
stresses_MPa = np.zeros(shape)

# Extracting data from the different yield values
for i in range(m):
  for j in range(n):

    current_stress = E_MPa * strain_percentage[j] / 100

    if current_stress < yield_stresses_MPa[i]:
      stresses_MPa[j, i] = current_stress
    else:
      stresses_MPa[j, i] = yield_stresses_MPa[i]

for i in range(stresses_MPa.shape[1]):
  plt.plot(strain_percentage, stresses_MPa[:, i], c='k')

plt.xlabel('Strain (%)')
plt.ylabel('Stress (MPa)')
plt.grid()
# plt.show()

def extract_total_energy(
  yield_stress_list=yield_stresses_MPa,
  strain_list=strain_percentage / 100,
  volume_fraction_list=np.array([0.1, 0.1, 0.4, 0.4])
):
  n = len(yield_stress_list)
  strain_energy_densities = np.zeros((n,))
  strain_energies= np.zeros((n,))

  for i in range(n):

    yield_strain = yield_stress_list[i] / E_MPa

    # strain energy density (sed)
    sed_pt1 = 0.5 * yield_strain * yield_stress_list[i]
    strain_diff = strain_list[-1] - yield_strain
    sed_pt2 = strain_diff * yield_stress_list[i]

    strain_energy_densities[i] = sed_pt1 + sed_pt2

    strain_energies[i] = strain_energy_densities[i] * volume_fraction_list[i]

  total_strain_energy = np.sum(strain_energies)

  return strain_energy_densities, strain_energies, total_strain_energy

def find_missing_phase_yield_stress(
  remaining_vf=0.3,
  total_energy_needed=1.065,
  young_modulus=E_MPa
):
  # Final quadratic equation to solve for the missing yield stress
  a = 1/(2*young_modulus) - 1/young_modulus
  b = 1/100
  c = -total_energy_needed / remaining_vf

  discriminant = b**2 - 4*a*c

  # Handle floating-point roundoff near zero
  if np.isclose(discriminant, 0.0, atol=1e-12):
    discriminant = 0.0

  if discriminant < 0:
    raise ValueError(f"No real solution. Discriminant = {discriminant}")

  sy1 = (-b + np.sqrt(discriminant)) / (2*a)
  sy2 = (-b - np.sqrt(discriminant)) / (2*a)

  return sy1, sy2

def main():

  baseline_seds, baseline_ses, baseline_tse = extract_total_energy()
  print(f'\n**Baseline**')
  print(f'Strain energy densities: \n{baseline_seds}')
  print(f'Strain energies: \n{baseline_ses}')
  print(f'Total Strain Energy: \n{baseline_tse:.3f}\n')

  print(f'\n**Case #1**')
  # Case #1: Increase the volume fraction of phase 3
  case1_vf = np.array([0.1, 0.1, 0.6])
  case1_ys = np.array([350, 470, 710])
  case1_seds, case1_ses, case1_tse = extract_total_energy(
    yield_stress_list=case1_ys,
    volume_fraction_list=case1_vf)
  print(f'Strain energy densities: \n{case1_seds}')
  print(f'Strain energies: \n{case1_ses}')
  print(f'Total Strain Energy: \n{case1_tse:.3f}\n')

  case1_missing_energy = baseline_tse - case1_tse
  print(f'The total strain energy missing is: {case1_missing_energy:.3f}\n')
  case1_sy1, case1_sy2 = find_missing_phase_yield_stress(
    remaining_vf=1 - np.sum(case1_vf),
    total_energy_needed=case1_missing_energy)
  print(f'Possible missing yield stresses for phase 3: {case1_sy1:.3f} MPa, {case1_sy2:.3f} MPa\n')
  
  print(f'\n**Case #2**')
  # Case #2: Increase the yield stress of phase 1
  case2_vf = np.array([0.1, 0.1, 0.4])
  case2_ys = np.array([350, 500, 710])
  case2_seds, case2_ses, case2_tse = extract_total_energy(
    yield_stress_list=case2_ys,
    volume_fraction_list=case2_vf)
  print(f'Strain energy densities: \n{case2_seds}')
  print(f'Strain energies: \n{case2_ses}')
  print(f'Total Strain Energy: \n{case2_tse:.3f}\n')

  case2_missing_energy = baseline_tse - case2_tse
  print(f'The total strain energy missing is: {case2_missing_energy:.3f}\n')
  case2_sy1, case2_sy2 = find_missing_phase_yield_stress(
    remaining_vf = 1 - np.sum(case2_vf),
    total_energy_needed=case2_missing_energy)
  print(f'Possible missing yield stresses for phase 3: {case2_sy1:.3f} MPa, {case2_sy2:.3f} MPa\n')
  
  print(f'\n**Case #3**')
  # Case #3: Increase the yield stress of phase 1
  case3_vf = np.array([0.1, 0.4])
  case3_ys = np.array([350, 710])
  case3_seds, case3_ses, case3_tse = extract_total_energy(
    yield_stress_list=case3_ys,
    volume_fraction_list=case3_vf)
  print(f'Strain energy densities: \n{case3_seds}')
  print(f'Strain energies: \n{case3_ses}')
  print(f'Total Strain Energy: \n{case3_tse:.3f}\n')

  case3_missing_energy = baseline_tse - case3_tse
  print(f'The total strain energy missing is: {case3_missing_energy:.3f}\n')
  case3_sy1, case3_sy2 = find_missing_phase_yield_stress(
    remaining_vf = 1 - np.sum(case3_vf),
    total_energy_needed=case3_missing_energy)
  print(f'Possible missing yield stresses for phase 1: {case3_sy1:.3f} MPa, {case3_sy2:.3f} MPa\n')

if __name__ == "__main__":
  main()

# def yield_gauss_seidel_determination():
#     # Dictionary of known phase values. If a phase key is not in this dictionary it will be determined
#     known_phase_values ={
#             'Phase 0':350,
#             'Phase 1':470}
#     # There will be a phase to find
#     find_phase_value = 'Phase 4'
#     # The remaining phase will be randomly determined from a set of values
#     # To do so we will generate a random number within the two bounds
#     def get_rng(seed=None):
#         """ This function is to either fix the seed (by providing an input) or totally randomize it (no input)"""
#         return np.random.default_rng(seed)

#     rng = get_rng(42)     # Use a reproducible seed to debug

#     known_phase_values['Phase 2'] = rng.integers(350, 710 + 1)
#     print(f'Phase 2 value: {known_phase_values["Phase 2"]}')

#     # Determine the total energy density for the known phases
#     current_energy_density = extract_total_energy_density(
#         stress_list=list(known_phase_values.values()))
#     print(f'Current energy density: {np.sum(current_energy_density)}')
#     print(f'Vs global energy density needed: {global_sed_result}')


# yield_gauss_seidel_determination()