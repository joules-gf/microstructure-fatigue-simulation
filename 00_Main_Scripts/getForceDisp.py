from abaqus import *
from abaqusConstants import *
from odbAccess import openOdb
import csv
import os
import sys

def Get_Force_Disp(odb_file, node_set1, node_set2):
#odb_directory = os.getcwd()

    csv_name = "{}.csv".format(odb_file)

    results = []
    results.append(["ODB file name: {}".format(odb_file)])
    results.append(["Step Time", "U_Y", "Total RF Y"])
    odb = openOdb(path="{}.odb".format(odb_file))
    step = odb.steps['Step-1']
    instance = odb.rootAssembly.instances['I-PART-1']

    bottom_set_region = instance.nodeSets[node_set1]
    upper_set_region = instance.nodeSets[node_set2]

    for frame in step.frames:
        step_time = frame.frameValue
        rf = frame.fieldOutputs['RF'].getSubset(region=bottom_set_region)
        u = frame.fieldOutputs['U'].getSubset(region=upper_set_region)

        rf_y = 0.0
        disp_y = 0.0
        count = 0

        for rf_val, u_val in zip(rf.values, u.values):
            rf_data = -1*rf_val.data
            u_data = u_val.data

            rf_y += rf_data[1]
            disp_y += u_data[1]

            count += 1

        if count > 0:
            avg_disp_y = disp_y / count
        else:
            avg_disp_y = 0.0

        results.append([step_time,avg_disp_y, rf_y])

    odb.close()

    # Write CSV

    # Go up two levels
    target_dir = os.path.dirname(os.getcwd())
    csv_file_output_dir = os.path.join(target_dir, csv_name)

    with open(csv_file_output_dir, 'wb') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerows(results)


if __name__ == "__main__":
    odb_file = os.environ["ODB_FILE"]
    node_set1 = os.environ["BOTTOMNODES"]
    node_set2 = os.environ["UPPERNODES"]

    Get_Force_Disp(odb_file, node_set1, node_set2)
