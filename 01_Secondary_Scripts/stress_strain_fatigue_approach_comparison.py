import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# Import data files
os.chdir(os.path.dirname(__file__))
AA7075_T651_SN_strainN_data = pd.read_csv('fatigue_AA7075-T651_Zhao_2007.csv', header=0)

df = AA7075_T651_SN_strainN_data.copy()
df.columns = df.columns.str.strip()

# Get the two specimen types
specimen_types = df["specimen"].unique()
specimen_1 = specimen_types[0]
specimen_2 = specimen_types[1]

# Split data by specimen type
group_1 = df[df["specimen"] == specimen_1]
group_2 = df[df["specimen"] == specimen_2]

# Select runout data: specimens that did not fail
runout_data = df[df["failed"] == False]

fig, ax = plt.subplots()

# Specimen 1: open red circles
ax.scatter(
    group_1["Nf_cycles"],
    group_1["stress_amplitude_MPa"],
    marker="o",
    facecolors="none",
    edgecolors="red",
    label=specimen_1
)

# Specimen 2: open thin diamonds
ax.scatter(
    group_2["Nf_cycles"],
    group_2["stress_amplitude_MPa"],
    marker="d",
    facecolors="green",
    label=specimen_2
)

# Right arrows for specimens that did not fail
# Multiplication shifts arrow slightly right on a log-scale x-axis
ax.scatter(
    runout_data["Nf_cycles"] * 1,
    runout_data["stress_amplitude_MPa"],
    marker=r"$\rightarrow$",
    color="black",
    s=100,
    label="Runout"
)

ax.set_xlabel("Cycles to failure, N")
ax.set_ylabel("Stress amplitude [MPa]")
ax.set_xscale("log")
ax.grid(True)
ax.legend()

plt.show()