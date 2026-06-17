"""Export Abaqus field reports for border regions of interest (ROIs).

This is the cleaned-up replacement for the old replay-generated
``createCrackData`` scripts.  The old scripts manually selected element sets in
Abaqus and called them cracks.  In this workflow we call them ROIs.

Julio's manual selection pattern, translated into code:

1. Start on the right border near the top of the domain.
2. Move 0.1 domain units down.
3. Select the elements in the half-circle inside the domain by moving 0.1 units
   left from the border point.
4. Repeat down the right side for nine ROIs total.
5. Repeat from the left border, except the half-circle points right.

The script can be imported by normal Python for tests.  Abaqus imports happen
inside Abaqus-only functions so the repository remains importable without Abaqus.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Iterable, NamedTuple, Sequence


DEFAULT_INSTANCE_NAME = "DOMAIN-1"
DEFAULT_REPORT_VARIABLES = (
    ("E", "E22"),
    ("S", "S22"),
)


class ROIRegion(NamedTuple):
    """A half-circular border ROI."""

    name: str
    side: str
    center: tuple[float, float]
    radius: float

    def contains_centroid(self, centroid: Sequence[float]) -> bool:
        """Return True when an element centroid belongs to this ROI."""
        x_value = float(centroid[0])
        y_value = float(centroid[1])
        center_x, center_y = self.center
        distance = math.hypot(x_value - center_x, y_value - center_y)
        inside_circle = distance <= self.radius
        inside_domain_half = x_value <= center_x if self.side == "right" else x_value >= center_x
        return inside_circle and inside_domain_half


def build_edge_roi_specs(
    *,
    width: float,
    height: float,
    radius: float = 0.1,
    count_per_side: int = 9,
    vertical_spacing: float | None = None,
) -> list[ROIRegion]:
    """Build right-border then left-border ROI definitions.

    ``vertical_spacing`` defaults to ``radius`` because the old manual workflow
    moved 0.1 units down between highlighted areas while using a 0.1-unit
    circular selection reach into the domain.
    """
    if vertical_spacing is None:
        vertical_spacing = radius

    specs: list[ROIRegion] = []
    for index in range(count_per_side):
        y_value = height - radius - (index * vertical_spacing)
        specs.append(ROIRegion(f"roi_right_{index + 1:02d}", "right", (width, y_value), radius))
    for index in range(count_per_side):
        y_value = height - radius - (index * vertical_spacing)
        specs.append(ROIRegion(f"roi_left_{index + 1:02d}", "left", (0.0, y_value), radius))
    return specs


def element_centroid(element) -> tuple[float, float, float]:
    """Return the centroid of an Abaqus element from its connected node coords."""
    coordinates = [node.coordinates for node in element.getNodes()]
    count = float(len(coordinates))
    return tuple(sum(coord[axis] for coord in coordinates) / count for axis in range(3))


def group_element_labels_by_roi(elements: Iterable, roi_specs: Sequence[ROIRegion]) -> dict[str, list[int]]:
    """Map each ROI name to the labels of elements whose centroids fall inside it."""
    labels_by_roi = {roi.name: [] for roi in roi_specs}
    for element in elements:
        centroid = element_centroid(element)
        for roi in roi_specs:
            if roi.contains_centroid(centroid):
                labels_by_roi[roi.name].append(element.label)
    return labels_by_roi


def infer_domain_size_from_instance(instance) -> tuple[float, float]:
    """Infer domain width/height from instance node coordinates."""
    x_values = [float(node.coordinates[0]) for node in instance.nodes]
    y_values = [float(node.coordinates[1]) for node in instance.nodes]
    return max(x_values) - min(x_values), max(y_values) - min(y_values)


def create_roi_sets(odb, roi_specs: Sequence[ROIRegion], *, instance_name: str = DEFAULT_INSTANCE_NAME) -> dict[str, list[int]]:
    """Create ODB element sets for the requested ROIs and return their labels."""
    assembly = odb.rootAssembly
    instance = assembly.instances[instance_name]
    labels_by_roi = group_element_labels_by_roi(instance.elements, roi_specs)

    for roi_name, labels in labels_by_roi.items():
        if not labels:
            print(f"Warning: ROI {roi_name} has no elements. Check domain size/radius/spacing.")
            continue
        picked_elements = tuple(instance.elements.sequenceFromLabels(labels))
        assembly.ElementSet(name=roi_name, elements=picked_elements)
    odb.save()
    return labels_by_roi


def export_roi_field_reports(odb, roi_specs: Sequence[ROIRegion], frames: Sequence[int], *, output_folder: str | Path = ".") -> None:
    """Export E22/S22 field reports for each ROI at the selected frames."""
    from abaqus import session
    from abaqusConstants import COMMA_SEPARATED_VALUES, COMPONENT, INTEGRATION_POINT, OFF, SPECIFY
    import displayGroupOdbToolset as dgo

    output_path = Path(output_folder)
    output_path.mkdir(parents=True, exist_ok=True)

    viewport_name = "Viewport: 1"
    if viewport_name not in session.viewports.keys():
        viewport = session.Viewport(name=viewport_name)
    else:
        viewport = session.viewports[viewport_name]
    viewport.setValues(displayedObject=odb)
    session.fieldReportOptions.setValues(reportFormat=COMMA_SEPARATED_VALUES)

    variables = tuple(
        (field_name, INTEGRATION_POINT, ((COMPONENT, component_name),))
        for field_name, component_name in DEFAULT_REPORT_VARIABLES
    )

    for frame_number in frames:
        for roi in roi_specs:
            element_set_name = roi.name.upper()
            leaf = dgo.LeafFromElementSets(elementSets=(element_set_name,))
            display_group = session.DisplayGroup(name=roi.name, leaf=leaf)
            viewport.odbDisplay.setValues(visibleDisplayGroups=(display_group,))
            report_name = output_path / f"{roi.name}_frame{frame_number}.csv"
            session.writeFieldReport(
                fileName=str(report_name),
                append=OFF,
                sortItem="Element Label",
                odb=odb,
                step=0,
                frame=int(frame_number),
                outputPosition=INTEGRATION_POINT,
                variable=variables,
                stepFrame=SPECIFY,
            )


def load_config(config_path: str | Path = "roi_report_config.json") -> dict:
    """Load optional JSON config from the Abaqus working directory."""
    path = Path(config_path)
    if not path.is_file():
        return {}
    return json.loads(path.read_text())


def main() -> None:
    """Abaqus noGUI entry point.

    Expected to run from ``simulation_outputs/<case>/abaqus_files``.  A small
    ``roi_report_config.json`` can override defaults, but the script also works
    with a single ODB in the working directory.
    """
    from abaqus import session

    config = load_config()
    odb_files = sorted(Path.cwd().glob("*.odb"))
    if not odb_files:
        raise FileNotFoundError("No ODB file found in the Abaqus working directory.")
    odb_path = Path(config.get("odb_path", odb_files[0])).resolve()

    odb = session.openOdb(name=str(odb_path), readOnly=False)
    instance_name = config.get("instance_name", DEFAULT_INSTANCE_NAME)
    instance = odb.rootAssembly.instances[instance_name]
    width, height = config.get("domain_size") or infer_domain_size_from_instance(instance)

    roi_specs = build_edge_roi_specs(
        width=float(width),
        height=float(height),
        radius=float(config.get("radius", 0.1)),
        count_per_side=int(config.get("count_per_side", 9)),
        vertical_spacing=float(config["vertical_spacing"]) if "vertical_spacing" in config else None,
    )
    frames = [int(frame) for frame in config.get("frames", [])]
    if not frames:
        raise ValueError("roi_report_config.json must provide a non-empty 'frames' list.")

    create_roi_sets(odb, roi_specs, instance_name=instance_name)
    export_roi_field_reports(odb, roi_specs, frames, output_folder=config.get("output_folder", "../roi_reports"))
    odb.close()


if __name__ == "__main__":
    main()
