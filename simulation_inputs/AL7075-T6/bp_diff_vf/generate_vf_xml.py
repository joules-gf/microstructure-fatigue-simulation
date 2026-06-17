import os
import csv
import copy
import xml.etree.ElementTree as ET


def indent_xml(elem, level=0):
  """
  Add indentation so the output XML is easier to read.
  """
  indent_str = "\n" + level * "    "

  if len(elem):
    if not elem.text or not elem.text.strip():
      elem.text = indent_str + "    "

    for child in elem:
      indent_xml(child, level + 1)

    if not child.tail or not child.tail.strip():
      child.tail = indent_str
  else:
    if level and (not elem.tail or not elem.tail.strip()):
      elem.tail = indent_str


def fraction_to_filename_piece(value):
  """
  Convert a fraction like 0.25 into '25'
  Convert 0.072 into '7p2' if needed to avoid ambiguity.
  """
  percentage = value * 100

  if abs(percentage - round(percentage)) < 1e-9:
    return str(int(round(percentage)))
  else:
    # Keep one or two decimals only when needed
    formatted = f"{percentage:.2f}".rstrip("0").rstrip(".")
    return formatted.replace(".", "p")


def read_vf_cases_from_csv(csv_file):
  """
  Read VF distributions from a CSV file.

  Expected columns:
  VF 1, VF 2, VF 3, VF 4

  Extra columns like 'Case' or 'Spread (std)' are ignored.
  """
  vf_cases = []

  with open(csv_file, mode="r", newline="", encoding="utf-8") as f:
    reader = csv.DictReader(f)

    required_columns = ["VF 1", "VF 2", "VF 3", "VF 4"]
    missing = [col for col in required_columns if col not in reader.fieldnames]

    if missing:
      raise ValueError(f"Missing required CSV columns: {missing}")

    for row in reader:
      vf = [
        float(row["VF 1"]),
        float(row["VF 2"]),
        float(row["VF 3"]),
        float(row["VF 4"]),
      ]

      vf_sum = sum(vf)
      if abs(vf_sum - 1.0) > 1e-6:
        raise ValueError(
          f"Volume fractions do not sum to 1.0.\n"
          f"Row data: {vf}\n"
          f"Sum = {vf_sum}"
        )

      vf_cases.append(vf)

  return vf_cases


def generate_xml_files_from_csv(csv_file, template_xml_file, output_directory):
  """
  Generate one XML file per VF case in the CSV.
  """

  vf_cases = read_vf_cases_from_csv(csv_file)

  # Parse template once
  template_tree = ET.parse(template_xml_file)
  template_root = template_tree.getroot()

  materials = template_root.findall("material")

  if len(materials) != 4:
    raise ValueError(
      f"Template XML must contain exactly 4 <material> blocks. Found {len(materials)}."
    )

  for case_index, vf in enumerate(vf_cases, start=1):
    # Deep copy the XML root so each file starts from the same template
    new_root = copy.deepcopy(template_root)

    new_materials = new_root.findall("material")

    for i, material in enumerate(new_materials):
      fraction_elem = material.find("fraction")

      if fraction_elem is None:
        raise ValueError(f"Material block {i} does not contain a <fraction> tag.")

      fraction_elem.text = f" {vf[i]:.4f} "

    # Build output filename
    vf_name_parts = [fraction_to_filename_piece(value) for value in vf]
    output_filename = f"bp_vf_{'_'.join(vf_name_parts)}.xml"
    output_path = os.path.join(output_directory, output_filename)

    # Write file
    indent_xml(new_root)
    new_tree = ET.ElementTree(new_root)
    new_tree.write(output_path, encoding="utf-8", xml_declaration=False)

    print(f"Created: {output_path}")


if __name__ == "__main__":
  os.chdir(os.path.abspath(os.path.dirname(__file__)))
  csv_file = r"case_study_overview_vf.csv"
  template_xml_file = r"mesh_equal_vf.xml"
  output_directory = os.path.abspath(os.path.dirname(__file__))

  generate_xml_files_from_csv(
    csv_file=csv_file,
    template_xml_file=template_xml_file,
    output_directory=output_directory
  )