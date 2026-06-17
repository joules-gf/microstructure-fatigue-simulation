import os
from itertools import combinations
import numpy as np
import matplotlib.pyplot as plt

# ---------------------------------
# Plot style settings
# Modify these values as needed
# ---------------------------------
plt.rcParams.update({
  # Figure size
  'figure.figsize': (10, 7),

  # Title size
  'axes.titlesize': 18,

  # Axis label sizes
  'axes.labelsize': 16,

  # Tick label sizes
  'xtick.labelsize': 16,
  'ytick.labelsize': 16,
  
  # Line and grid defaults
  'lines.linewidth': 3,
  'axes.grid': True,

  # Legend size
  'legend.fontsize': 14,
  'legend.title_fontsize': 16,

  # Saved figure quality
  'savefig.bbox': 'tight',
})

def ramberg_osgood_model(stress, material_properties):
  E_MPa, H_prime_MPa, n_prime = get_material_properties(material_properties)
  strain = (stress / E_MPa) + (stress / H_prime_MPa) ** (1 / n_prime)
  return strain

def first_derivative_rom(stress, material_properties):
  E_MPa, H_prime_MPa, n_prime = get_material_properties(material_properties)
  d_strain_stress = (
    1 / E_MPa
    + (1 / n_prime) * (stress ** ((1 / n_prime) - 1)) / H_prime_MPa ** (1 / n_prime)
  )
  return d_strain_stress

def second_derivative_rom(stress, material_properties):
  E_MPa, H_prime_MPa, n_prime = get_material_properties(material_properties)
  d2_strain_stress2 = (
    (1 / n_prime)
    * ((1 / n_prime) - 1)
    * (stress ** ((1 / n_prime) - 2))
    / H_prime_MPa ** (1 / n_prime)
  )
  return d2_strain_stress2

def curvature_of_rom(stress, material_properties):
  d_strain_stress = first_derivative_rom(stress, material_properties)
  d2_strain_stress2 = second_derivative_rom(stress, material_properties)

  curvature = abs(d2_strain_stress2) / (1 + d_strain_stress ** 2) ** (3 / 2)
  return curvature

def plot_all_rom_curves(materials, output_folder):
  plt.figure(figsize=(10, 7))

  for material_name, material_properties in materials.items():
    stress_max_MPa = get_stress_max(material_properties)
    stress_array = np.linspace(0, stress_max_MPa, stress_max_MPa + 1)
    strain_array = ramberg_osgood_model(stress_array, material_properties)
    plt.plot(strain_array, stress_array, label=material_name)

  plt.xlabel('Strain, ε')
  plt.ylabel('Stress, σ (MPa)')
  plt.title('Ramberg-Osgood Stress-Strain Curves')
  plt.grid(True)
  plt.legend()
  plt.tight_layout()

  save_path = os.path.join(output_folder, '01_all_rom_stress_strain_curves.png')
  plt.savefig(save_path, dpi=300, bbox_inches='tight')
  plt.close()

  print(f'Saved: {save_path}')

def plot_individual_material_curves(material_name, material_properties, output_folder):
 
  stress_max_MPa = get_stress_max(material_properties)
  stress_array = np.linspace(0, stress_max_MPa, stress_max_MPa + 1)
  
  second_derivative_array = second_derivative_rom(stress_array, material_properties)
  curvature_array = curvature_of_rom(stress_array, material_properties)

  plt.figure()

  plt.plot(
    second_derivative_array,
    stress_array,
    lw=6,
    label='Second Derivative'
  )

  plt.plot(
    curvature_array,
    stress_array,
    linestyle='--',
    label='Curvature'
  )

  plt.xlabel(r'Value $(1/\mathrm{MPa}^2)$')
  plt.ylabel(r'Stress, $\sigma$ (MPa)')
  plt.title(f'{material_name}: Curvature and Second Derivative vs Stress')
  plt.legend()
  plt.grid(True)
  plt.tight_layout()

  clean_name = material_name.replace('/', '_').replace(' ', '_')
  save_path = os.path.join(
    output_folder,
    f'02_{clean_name}_curvature_and_second_derivative_vs_stress_flipped.png'
  )

  plt.savefig(save_path)
  plt.close()

  print(f'Saved: {save_path}')

def plot_all_second_derivatives(materials, output_folder):
  plt.figure()

  for material_name, material_properties in materials.items():

    stress_max_MPa = get_stress_max(material_properties)
    stress_array = np.linspace(0, stress_max_MPa, stress_max_MPa + 1)
    
    second_derivative_array = second_derivative_rom(stress_array, material_properties)

    plt.plot(
      second_derivative_array,
      stress_array,
      label=f'{material_name}'
    )

  plt.xlabel(r'Second Derivative, $d^2\varepsilon/d\sigma^2$ $(1/\mathrm{MPa}^2)$')
  plt.ylabel(r'Stress, $\sigma$ (MPa)')
  plt.title('All Materials: Second Derivative vs Stress')
  plt.legend()
  plt.grid(True)
  plt.tight_layout()

  save_path = os.path.join(output_folder, '03_all_materials_second_derivative_vs_stress.png')
  plt.savefig(save_path)
  plt.close()

  print(f'Saved: {save_path}')

def get_material_properties(material_data):
  return material_data[:3]


def get_stress_max(material_data):
  return material_data[3]



def get_plastic_range_indices(stress_array, strain_array, material_properties, plastic_threshold):
  """
  Finds the start and end indices of the plastic range.

  Plastic strain is defined as:

      plastic_strain = total_strain - elastic_strain
                     = strain - stress / E

  The plastic range starts when plastic_strain reaches the chosen threshold.
  The end of the plastic range is the final stress point.
  """

  E_MPa, H_prime_MPa, n_prime = get_material_properties(material_properties)

  plastic_strain_array = strain_array - stress_array / E_MPa

  plastic_indices = np.where(plastic_strain_array >= plastic_threshold)[0]

  if len(plastic_indices) == 0:
    raise ValueError(
      f'No plastic range found. Try lowering plastic_threshold = {plastic_threshold}'
    )

  plastic_start_index = plastic_indices[0]
  plastic_end_index = len(stress_array) - 1

  return plastic_start_index, plastic_end_index, plastic_strain_array


def piecewise_linear_prediction(x_array, y_array, breakpoint_indices):
  """
  Creates a piecewise-linear approximation through selected breakpoint indices.

  x_array: strain
  y_array: stress

  breakpoint_indices should include:
    - plastic start index
    - interior breakpoint indices
    - plastic end index
  """

  x_breakpoints = x_array[breakpoint_indices]
  y_breakpoints = y_array[breakpoint_indices]

  y_prediction = np.interp(x_array, x_breakpoints, y_breakpoints)

  return y_prediction


def piecewise_linear_error(x_array, y_array, breakpoint_indices):
  """
  Computes sum of squared error between the actual curve and the
  piecewise-linear approximation.
  """

  y_prediction = piecewise_linear_prediction(
    x_array,
    y_array,
    breakpoint_indices
  )

  error_array = y_array - y_prediction

  sse = np.sum(error_array ** 2)

  return sse


def find_best_piecewise_linear_breakpoints(
    strain_array,
    stress_array,
    material_properties,
    plastic_threshold,
    n_segments,
    min_points_between=5
  ):
  """
  Finds the best breakpoint locations for a piecewise-linear approximation
  of the plastic range.

  n_segments = 2 means:
    start point + 1 interior point + end point

  n_segments = 3 means:
    start point + 2 interior points + end point

  The selected points lie on the original Ramberg-Osgood curve.
  """

  if n_segments < 1:
    raise ValueError('n_segments must be at least 1.')

  plastic_start_index, plastic_end_index, plastic_strain_array = get_plastic_range_indices(
    stress_array,
    strain_array,
    material_properties,
    plastic_threshold
  )

  n_interior_points = n_segments - 1

  candidate_indices = np.arange(
    plastic_start_index + min_points_between,
    plastic_end_index - min_points_between + 1
  )

  best_error = np.inf
  best_breakpoint_indices = None

  for interior_indices in combinations(candidate_indices, n_interior_points):

    breakpoint_indices = np.array(
      [plastic_start_index, *interior_indices, plastic_end_index]
    )

    # Enforce minimum spacing between points
    spacing = np.diff(breakpoint_indices)

    if np.any(spacing < min_points_between):
      continue

    plastic_slice = slice(plastic_start_index, plastic_end_index + 1)

    current_error = piecewise_linear_error(
      strain_array[plastic_slice],
      stress_array[plastic_slice],
      breakpoint_indices - plastic_start_index
    )

    if current_error < best_error:
      best_error = current_error
      best_breakpoint_indices = breakpoint_indices

  return {
    'plastic_start_index': plastic_start_index,
    'plastic_end_index': plastic_end_index,
    'plastic_strain_array': plastic_strain_array,
    'breakpoint_indices': best_breakpoint_indices,
    'sse': best_error,
  }

def plot_piecewise_linear_fit(
    material_name,
    material_properties,
    output_folder,
    plastic_threshold,
    n_segments
  ):

  stress_max_MPa = get_stress_max(material_properties)
  stress_array = np.linspace(0, stress_max_MPa, stress_max_MPa + 1)
  strain_array = ramberg_osgood_model(stress_array, material_properties)

  result = find_best_piecewise_linear_breakpoints(
    strain_array=strain_array,
    stress_array=stress_array,
    material_properties=material_properties,
    plastic_threshold=plastic_threshold,
    n_segments=n_segments,
    min_points_between=5
  )

  breakpoint_indices = result['breakpoint_indices']
  plastic_start_index = result['plastic_start_index']
  plastic_end_index = result['plastic_end_index']

  x_breakpoints = strain_array[breakpoint_indices]
  y_breakpoints = stress_array[breakpoint_indices]

  plastic_slice = slice(plastic_start_index, plastic_end_index + 1)

  stress_prediction = piecewise_linear_prediction(
  strain_array[plastic_slice],
  stress_array[plastic_slice],
  breakpoint_indices - plastic_start_index
  )

  # ---------------------------------
  # Area under curve calculation
  # ---------------------------------
  # Elastic range is assumed identical for ROM and linear approximation.
  # Therefore:
  # total ROM area    = elastic area + ROM plastic area
  # total linear area = elastic area + linear plastic area

  elastic_slice = slice(0, plastic_start_index + 1)

  elastic_area = np.trapezoid(
    stress_array[elastic_slice],
    strain_array[elastic_slice]
  )

  rom_plastic_area = np.trapezoid(
    stress_array[plastic_slice],
    strain_array[plastic_slice]
  )

  linear_plastic_area = np.trapezoid(
    stress_prediction,
    strain_array[plastic_slice]
  )

  rom_total_area = elastic_area + rom_plastic_area
  linear_total_area = elastic_area + linear_plastic_area

  plt.figure()

  plt.plot(
    strain_array,
    stress_array,
    label=f'Ramberg-Osgood curve | Area = {rom_total_area:.4f}'
  )

  plt.plot(
    strain_array[plastic_slice],
    stress_prediction,
    linestyle='--',
    marker='o',
    label=f'{n_segments}-segment linear fit | Area = {linear_total_area:.4f}'
  )

  plt.scatter(
    x_breakpoints,
    y_breakpoints,
    s=60,
    zorder=5,
    label='Selected breakpoints'
  )

  # ---------------------------------
  # Add stress-value labels at breakpoints
  # ---------------------------------
  for i, (x_point, y_point) in enumerate(zip(x_breakpoints, y_breakpoints)):

    plt.annotate(
      f'{y_point:.1f}',
      xy=(x_point, y_point),
      xytext=(8, 8),
      textcoords='offset points',
      fontsize=12,
      bbox=dict(
        boxstyle='round,pad=0.25',
        fc='white',
        alpha=0.8
      ),
      arrowprops=dict(
        arrowstyle='->',
        lw=1
      )
    )

  plt.xlabel(r'Strain, $\varepsilon$')
  plt.ylabel(r'Stress, $\sigma$ (MPa)')
  plt.title(f'{material_name}: {n_segments}-Segment Plastic Range Approximation')
  plt.legend()
  plt.tight_layout()

  clean_name = material_name.replace('/', '_').replace(' ', '_')

  save_path = os.path.join(
    output_folder,
    f'04_{clean_name}_{n_segments}_segment_piecewise_fit.png'
  )

  plt.savefig(save_path)
  plt.close()

  print(f'Saved: {save_path}')

  print(f'\n{material_name} — {n_segments} segment fit')
  print(f'Plastic threshold: {plastic_threshold}')
  print(f'SSE: {result["sse"]:.6e}')
  print(f'ROM total area: {rom_total_area:.4f}')
  print(f'Linear approximation total area: {linear_total_area:.4f}')
  print(f'Area difference: {rom_total_area - linear_total_area:.4f}')
  print('Selected points:')

  for i, index in enumerate(breakpoint_indices):
    print(
      f'  Point {i + 1}: '
      f'index = {index}, '
      f'strain = {strain_array[index]:.8f}, '
      f'stress = {stress_array[index]:.3f} MPa, '
      f'plastic strain = {result["plastic_strain_array"][index]:.8f}'
    )

  return result

if __name__ == "__main__":

  # ---------------------------------
  # Material database
  # ---------------------------------
  materials = {
    'AA7075-T6': [71e3, 977, 0.106, 521],
    'AA2024-T351': [731e2, 662, 0.070, 449],
    'AA7075-T651': [70e3, 852, 0.074, 543],
  }

  # ---------------------------------
  # User settings
  # ---------------------------------
  output_folder = os.path.join(os.path.dirname(__file__),'rom_outputs')
  os.makedirs(output_folder, exist_ok=True)

  # ---------------------------------
  # Output 1:
  # all stress-strain ROM curves
  # ---------------------------------
  plot_all_rom_curves(materials, output_folder)

  # ---------------------------------
  # Output 2:
  # one figure per material:
  # curvature and second derivative on x-axis
  # stress on y-axis
  # ---------------------------------
  for material_name, material_properties in materials.items():
    plot_individual_material_curves(
      material_name,
      material_properties,
      output_folder
    )

  # ---------------------------------
  # Output 3:
  # all curvature and second derivative curves
  # in one figure
  # ---------------------------------
  plot_all_second_derivatives(materials, output_folder)

  # ---------------------------------
  # Output 4:
  # Piecewise-linear approximation
  # of the plastic range
  # ---------------------------------

  plastic_threshold = 0.00006

  for material_name, material_properties in materials.items():

    # Try 2 line segments
    plot_piecewise_linear_fit(
    material_name=material_name,
    material_properties=material_properties,
    output_folder=output_folder,
    plastic_threshold=plastic_threshold,
    n_segments=2
    )

    # Try 3 line segments
    plot_piecewise_linear_fit(
    material_name=material_name,
    material_properties=material_properties,
    output_folder=output_folder,
    plastic_threshold=plastic_threshold,
    n_segments=3
    )
  print('\nDone. All figures were saved.')