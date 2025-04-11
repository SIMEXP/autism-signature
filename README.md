# Code for the high risk autism phenotype paper
[![MIT license](https://img.shields.io/badge/License-MIT-blue.svg)](https://lbesson.mit-license.org/)

Much of the code in this repo originated from [ASD High Risk Endophenotype Code Supplement](https://github.com/surchs/ASD_high_risk_endophenotype_code_supplement) and was written by Sebastian Urchs and Hien Nguyen.

### Data availability
All data to reproduce the analysis can be downloaded from [![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.15192559.svg)](https://doi.org/10.5281/zenodo.15192559)

- The study uses data from ABIDE 1 and 2 datasets. Participants were matched using propensity score matching as part of another project, matching scripts can be found here [ASD Subtype Code Supplement](https://github.com/surchs/ASD_subtype_code_supplement/tree/master/scripts/pheno).
- Resting state functional connectivity data was preprocessed using NIAK, described in the paper. This study uses the seed maps.
- Using the following scripts the full analysis can be reproduced. Alternatively, to skip the data analysis part and recreate the figures, download only the results and atlas data from Zenodo.

### Data analysis
These steps were run on the Alliance Canada Beluga server.

On an HPC server, first set up the R environment. After cloning the repository:
1. Open R in the project directory
2. ```R install.packages("renv") renv::restore() ```

For scripts 1-5 do:
```
python -m venv hpc_py11_env
source hpc_py11_env/bin/activate
pip install -r environments/requirements_py11.txt
```

Update the paths and slurm preamble, then run:
1. `Discovery_Conformal_Score.R` using `submit_discovery.sh`
2. `Discovery_Read_Conformal_Scores.R`
3. `Validation_Conformal_Score_Boot.R` using `submit_validation.sh`
4. `Validation_Read_Conformal_Scores.R`
5. `Null_Model.R` using `submit_null.sh`

For script 6, do:
```
python -m venv hpc_py10_env
source hpc_py10_env/bin/activate
pip install -r environments/requirements_py10.txt
```
Run:
6. `build_residuals_validation.py` using `submit_residuals.py`

### Supplemental analyses and figures
Make sure you have downloaded the atlas files from Zenodo. If you skipped the data analysis part, just download the results and data files. Set up the local Python environment:

```
python -m venv env
source env/bin/activate
pip install -r environments/requirements_local.txt
```
Run:
1. `medication_usage.ipynb`
2. `convert_ados.ipynb`
3. `correlate_severity.ipynb`

#### Figures
1. `get_boot_ids.py` - run this first.
2. `figure_1_network.ipynb`
3. `figure_1supplementary_null.ipynb`
4. `figure_2_profile.ipynb`
5. `figure_2supplementary_performance.ipynb`
6. `figure_3_nuisance.ipynb`
7. `figure_4_dice.ipynb`
8. `figure_4_ppv.ipynb`
9. `figure_7_conformal_space.ipynb`
