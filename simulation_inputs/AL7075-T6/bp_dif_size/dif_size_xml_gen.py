import os
import re
import csv


def generate_xml_cases_from_csv(
  csv_file,
  template_xml,
  filename_prefix='bm_size'
):
  """
  Create one XML file per CSV row by copying the template XML exactly
  and only replacing the first four <loc>...</loc> values.

  Assumptions:
    - The CSV has columns:
        Case, Size 1, Size 2, Size 3, Size 4
    - The template XML contains 4 phases, each with one <loc> value.
    - The first 4 <loc> tags in the XML correspond to Phase-0 to Phase-3.
  """

  # Read template XML as raw text so formatting stays unchanged
  with open(template_xml, 'r', encoding='utf-8') as f:
    template_text = f.read()

  # Regex for <loc> value </loc>, preserving surrounding spacing/format
  loc_pattern = re.compile(r'(<loc>\s*)([^<]*?)(\s*</loc>)')

  # Find all loc tags in the template
  matches = list(loc_pattern.finditer(template_text))

  if len(matches) < 4:
    raise ValueError(
      f"Template XML contains only {len(matches)} <loc> tags. Expected at least 4."
    )

  created_files = []

  with open(csv_file, 'r', encoding='utf-8-sig', newline='') as f:
    reader = csv.DictReader(f)

    required_columns = ['Case', 'Size 1', 'Size 2', 'Size 3', 'Size 4']
    missing_columns = [col for col in required_columns if col not in reader.fieldnames]
    if missing_columns:
      raise ValueError(f"Missing required CSV columns: {missing_columns}")

    for row in reader:
      case_name = row['Case'].strip()

      size_values = [
        str(row['Size 1']).strip(),
        str(row['Size 2']).strip(),
        str(row['Size 3']).strip(),
        str(row['Size 4']).strip(),
      ]

      # Replace only the first 4 <loc> values
      new_text_parts = []
      last_end = 0

      for i, match in enumerate(matches):
        start, end = match.span()

        # Copy unchanged text before this <loc>
        new_text_parts.append(template_text[last_end:start])

        if i < 4:
          # Replace loc value for first 4 occurrences only
          replacement = f"{match.group(1)}{size_values[i]}{match.group(3)}"
          new_text_parts.append(replacement)
        else:
          # Leave any additional <loc> tags unchanged
          new_text_parts.append(template_text[start:end])

        last_end = end

      # Copy remaining text
      new_text_parts.append(template_text[last_end:])
      new_xml_text = ''.join(new_text_parts)

      # Safe filename
      case_slug = case_name.lower().replace(' ', '_')
      output_name = f"{filename_prefix}_{case_slug}.xml"

      with open(output_name, 'w', encoding='utf-8', newline='') as out:
        out.write(new_xml_text)

      created_files.append(output_name)

  return created_files


if __name__ == '__main__':
  os.chdir(os.path.dirname(os.path.abspath(__file__)))
  csv_file = 'case_study_overview_diameter_size.csv'
  template_xml = 'bm_example.xml'

  created_files = generate_xml_cases_from_csv(
    csv_file=csv_file,
    template_xml=template_xml,
    filename_prefix='bp_size'
  )

  print('Files created:')
  for file_path in created_files:
    print(file_path)