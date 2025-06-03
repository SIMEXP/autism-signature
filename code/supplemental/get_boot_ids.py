import pandas as pd
import numpy as np
from pathlib import Path

# Set paths
root_p = Path("/home/neuromod/ASD_project_clean")
discovery_p = root_p / "Results/Discovery"

# Load phenotype data just to get the number of subjects
pheno = pd.read_csv(root_p / "ABIDE1_Pheno_PSM_matched.tsv", sep="\t")
n_subjects = len(pheno)

boot_ids = np.empty((n_subjects, 100), dtype=int)
# Extract test subject IDs from each bootstrap replicate
for replicate in range(1, 101):
    df = pd.read_csv(discovery_p / f"Results_Instance_{replicate}_Network_1.csv")

    # Store test subject IDs (2nd column)
    boot_ids[:, replicate - 1] = df.iloc[:, 1].values

# Output
df = pd.DataFrame(boot_ids)
df.to_csv(
    discovery_p / "boot_subject_ids.tsv",
    sep="\t",
    header=False,
    index=True,
    index_label=False,
)
print("Done!")
