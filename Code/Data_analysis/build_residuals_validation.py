#!/usr/bin/env python
# coding: utf-8

# # Residuals for validation sample

# ## Build residuals
# The validated data are nuisance regressed against the training data in the transducitve prediction step. In order to get their residual maps, I will repeat the nuisance regression separately for each model and seed region and store them here.

import tqdm
import numpy as np
import pandas as pd
import patsy as pat
import pathlib as pal
from sklearn import linear_model as sln

root_p = pal.Path(
    "/home/nclarke/projects/rrg-pbellec/nclarke/TSM_NO_BACKUP/ASD_project_clean"
)
pheno_valid_p = root_p / "ABIDE2_Pheno_PSM_matched.tsv"
pheno_discovery_p = root_p / "ABIDE1_Pheno_PSM_matched.tsv"

seed_stack_valid_p = root_p / "abide_2_seed_maps_no_cereb.npy"
seed_stack_discovery_p = root_p / "seed_maps_no_cereb.npy"

resid_stack_valid_p = root_p / "abide_2_validation_residuals_regressed_with_abide_1.npy"

pheno_valid = pd.read_csv(pheno_valid_p, sep="\t")
seed_stack_valid = np.load(seed_stack_valid_p)
pheno_discovery = pd.read_csv(pheno_discovery_p, sep="\t")
seed_stack_discovery = np.load(seed_stack_discovery_p)


# ## Residuals
# We are regressing age, head motion, and intercept.

resid_stack_valid = np.zeros(shape=seed_stack_valid.shape)
total_jobs = np.prod((resid_stack_valid.shape[0], resid_stack_valid.shape[2]))
with tqdm.tqdm(total=total_jobs) as pbar:
    for itix, (rid, row) in enumerate(pheno_valid.iterrows()):
        it_pheno = pd.concat(
            [
                pheno_discovery[["AGE_AT_SCAN", "fd_scrubbed"]],
                row[["AGE_AT_SCAN", "fd_scrubbed"]]
                .to_frame()
                .T,  # Convert row to DataFrame
            ]
        )
        it_mat = pat.dmatrix("AGE_AT_SCAN + fd_scrubbed", it_pheno)
        for nid in range(18):
            it_stack = np.concatenate(
                (
                    seed_stack_discovery[..., nid],
                    seed_stack_valid[itix, :, nid][None, :],
                )
            )
            mod = sln.LinearRegression(fit_intercept=False, n_jobs=-1)
            res = mod.fit(it_mat, it_stack)
            resid_stack_valid[itix, :, nid] = (it_stack - res.predict(it_mat))[-1, :]
        pbar.update(18)

np.save(resid_stack_valid_p, resid_stack_valid)
