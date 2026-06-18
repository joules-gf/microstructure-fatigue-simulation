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

This file intentionally avoids modern Python-only syntax because Abaqus/CAE can
run an older Python interpreter.  Keep the script readable and conservative.
"""

from __future__ import print_function

import json
import math
import os


DEFAULT_INSTANCE_NAME = "DOMAIN-1"
DEFAULT_REPORT_VARIABLES = (
    ("E", "E22"),
    ("S", "S22"),
)


class ROIRegion(object):
    """A half-circular border ROI."""

    def __init__(self, name, side, center, radius):
        self.name = name
        self.side = side
        self.center = center
        self.radius = radius

    def contains_centroid(self, centroid):
        """Return True when an element centroid belongs to this ROI."""
        x_value = float(centroid[0])
        y_value = float(centroid[1])
        center_x, center_y = self.center
        distance = math.sqrt((x_value - center_x) ** 2 + (y_value - center_y) ** 2)
        inside_circle = distance <= self.radius
        if self.side == "right":
            inside_domain_half = x_value <= center_x
        else:
            inside_domain_half = x_value >= center_x
        return inside_circle and inside_domain_half


def build_edge_roi_specs(width, height, radius=0.1, count_per_side=9, vertical_spacing=None, x_min=0.0, y_min=0.0):
    """Build right-border then left-border ROI definitions.

    ``width`` and ``height`` describe the domain size.  ``x_min`` and ``y_min``
    describe where that domain starts in the ODB coordinates.  This matters
    because Abaqus meshes are not guaranteed to start at (0, 0).
    """
    if vertical_spacing is None:
        vertical_spacing = radius

    x_max = x_min + width
    y_max = y_min + height

    specs = []
    for index in range(count_per_side):
        y_value = y_max - radius - (index * vertical_spacing)
        specs.append(ROIRegion("roi_right_%02d" % (index + 1), "right", (x_max, y_value), radius))
    for index in range(count_per_side):
        y_value = y_max - radius - (index * vertical_spacing)
        specs.append(ROIRegion("roi_left_%02d" % (index + 1), "left", (x_min, y_value), radius))
    return specs


def element_centroid(element, node_coordinates_by_label=None):
    """Return the centroid of an Abaqus element from its connected node coords."""
    if node_coordinates_by_label is None and hasattr(element, "getNodes"):
        coordinates = [node.coordinates for node in element.getNodes()]
    else:
        coordinates = [node_coordinates_by_label[label] for label in element.connectivity]
    count = float(len(coordinates))
    centroid = []
    for axis in range(3):
        
        total = 0.0
        for coord in coordinates:
            total += coord[axis]
        centroid.append(total / count)
    return tuple(centroid)


def group_element_labels_by_roi(elements, roi_specs, node_coordinates_by_label=None):
    """Map each ROI name to the labels of elements whose centroids fall inside it."""
    labels_by_roi = dict((roi.name, []) for roi in roi_specs)
    for element in elements:
        centroid = element_centroid(element, node_coordinates_by_label)
        for roi in roi_specs:
            if roi.contains_centroid(centroid):
                labels_by_roi[roi.name].append(element.label)
    return labels_by_roi


def infer_domain_bounds_from_instance(instance):
    """Infer domain bounds from instance node coordinates."""
    x_values = [float(node.coordinates[0]) for node in instance.nodes]
    y_values = [float(node.coordinates[1]) for node in instance.nodes]
    return min(x_values), max(x_values), min(y_values), max(y_values)


def infer_domain_size_from_instance(instance):
    """Infer domain width/height from instance node coordinates."""
    x_min, x_max, y_min, y_max = infer_domain_bounds_from_instance(instance)
    return x_max - x_min, y_max - y_min


def choose_instance(odb, preferred_name=DEFAULT_INSTANCE_NAME):
    """Return the preferred instance, or the only available instance as fallback."""
    instances = odb.rootAssembly.instances
    if preferred_name in instances.keys():
        return preferred_name, instances[preferred_name]
    names = list(instances.keys())
    if len(names) == 1:
        return names[0], instances[names[0]]
    raise KeyError("Could not find instance %s. Available instances: %s" % (preferred_name, names))


def available_roi_set_name(assembly, roi_name):
    """Return an element-set name that can be safely created in this ODB.

    Abaqus ODB element sets cannot be deleted once added.  That matters while
    testing this script because an ODB can already contain stale ROI sets from an
    older geometry rule.  For a fresh ODB we keep the readable name, e.g.
    ``roi_left_05``.  If that name already exists, we create a clearly marked
    replacement set, e.g. ``roi_left_05_current``.
    """
    existing = assembly.elementSets.keys()
    candidates = [roi_name, roi_name + "_current"]
    for index in range(2, 100):
        candidates.append(roi_name + "_current_%02d" % index)

    for candidate in candidates:
        if candidate not in existing and candidate.upper() not in existing:
            if candidate != roi_name:
                print("Existing ROI set %s cannot be deleted; creating %s instead." % (roi_name, candidate))
            return candidate
    raise RuntimeError("Could not find an available element-set name for %s" % roi_name)


def create_roi_sets(odb, roi_specs, instance_name=DEFAULT_INSTANCE_NAME):
    """Create ODB element sets for the requested ROIs and return their labels."""
    assembly = odb.rootAssembly
    instance_name, instance = choose_instance(odb, instance_name)
    node_coordinates_by_label = dict((node.label, node.coordinates) for node in instance.nodes)
    labels_by_roi = group_element_labels_by_roi(instance.elements, roi_specs, node_coordinates_by_label)
    set_name_by_roi = {}

    for roi_name, labels in labels_by_roi.items():
        if not labels:
            print("Warning: ROI %s has no elements. Check domain size/radius/spacing." % roi_name)
            continue
        actual_set_name = available_roi_set_name(assembly, roi_name)
        assembly.ElementSetFromElementLabels(
            name=actual_set_name,
            elementLabels=((instance_name, tuple(labels)),),
        )
        set_name_by_roi[roi_name] = actual_set_name
    odb.save()
    return set_name_by_roi


def resolve_element_set_name(assembly, requested_name):
    """Find the ODB repository key for an element set name."""
    if requested_name in assembly.elementSets.keys():
        return requested_name
    upper_name = requested_name.upper()
    if upper_name in assembly.elementSets.keys():
        return upper_name
    return None

def export_roi_field_reports(odb, roi_specs, frames, output_folder=".", set_name_by_roi=None):
    """Export E22/S22 field reports for each ROI at the selected frames."""
    import visualization
    from abaqus import session
    from abaqusConstants import COMMA_SEPARATED_VALUES, COMPONENT, INTEGRATION_POINT, OFF, SPECIFY
    import displayGroupOdbToolset as dgo

    if set_name_by_roi is None:
        set_name_by_roi = {}

    if not os.path.isdir(output_folder):
        os.makedirs(output_folder)

    viewport_name = "Viewport: 1"
    if viewport_name not in session.viewports.keys():
        viewport = session.Viewport(name=viewport_name)
    else:
        viewport = session.viewports[viewport_name]
    viewport.setValues(displayedObject=odb)

    if hasattr(session, "fieldReportOptions"):
        session.fieldReportOptions.setValues(reportFormat=COMMA_SEPARATED_VALUES)

    variables = tuple(
        (field_name, INTEGRATION_POINT, ((COMPONENT, component_name),))
        for field_name, component_name in DEFAULT_REPORT_VARIABLES
    )

    for frame_number in frames:
        for roi in roi_specs:
            requested_set_name = set_name_by_roi.get(roi.name, roi.name)
            element_set_name = resolve_element_set_name(odb.rootAssembly, requested_set_name)
            if element_set_name is None:
                print("Skipping %s because no element set was created." % roi.name)
                continue
            leaf = dgo.LeafFromElementSets(elementSets=(element_set_name,))
            display_group = session.DisplayGroup(name="dg_" + roi.name, leaf=leaf)
            viewport.odbDisplay.setValues(visibleDisplayGroups=(display_group,))
            report_name = os.path.join(output_folder, "%s_frame%d.csv" % (roi.name, int(frame_number)))
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

def load_config(config_path="roi_report_config.json"):
    """Load optional JSON config from the Abaqus working directory."""
    if not os.path.isfile(config_path):
        return {}
    with open(config_path, "r") as config_file:
        return json.load(config_file)


def find_odb_file(config):
    if config.get("odb_path"):
        return os.path.abspath(config["odb_path"])
    odb_files = sorted(name for name in os.listdir(os.getcwd()) if name.lower().endswith(".odb"))
    if not odb_files:
        raise IOError("No ODB file found in the Abaqus working directory.")
    return os.path.abspath(odb_files[0])


def main():
    """Abaqus noGUI entry point."""
    from abaqus import session

    config = load_config()
    odb_path = find_odb_file(config)
    odb = session.openOdb(name=odb_path, readOnly=False)

    instance_name = config.get("instance_name", DEFAULT_INSTANCE_NAME)
    instance_name, instance = choose_instance(odb, instance_name)
    if config.get("domain_size"):
        width, height = config["domain_size"]
        x_min = float(config.get("x_min", 0.0))
        y_min = float(config.get("y_min", 0.0))
    else:
        x_min, x_max, y_min, y_max = infer_domain_bounds_from_instance(instance)
        width = x_max - x_min
        height = y_max - y_min

    print("ROI domain bounds: x_min=%s, width=%s, y_min=%s, height=%s" % (x_min, width, y_min, height))
    roi_specs = build_edge_roi_specs(
        width=float(width),
        height=float(height),
        radius=float(config.get("radius", 0.1)),
        count_per_side=int(config.get("count_per_side", 9)),
        vertical_spacing=float(config["vertical_spacing"]) if "vertical_spacing" in config else None,
        x_min=float(x_min),
        y_min=float(y_min),
    )
    frames = [int(frame) for frame in config.get("frames", [])]
    if not frames:
        raise ValueError("roi_report_config.json must provide a non-empty 'frames' list.")

    output_folder = config.get("output_folder", "../roi_reports")
    set_name_by_roi = create_roi_sets(odb, roi_specs, instance_name=instance_name)
    export_roi_field_reports(odb, roi_specs, frames, output_folder=output_folder, set_name_by_roi=set_name_by_roi)
    odb.close()


if __name__ == "__main__":
    main()
