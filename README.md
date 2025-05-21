# Code for the 🧠 high risk autism phenotype paper
[![MIT license](https://img.shields.io/badge/License-MIT-blue.svg)](https://lbesson.mit-license.org/)
[![DOI](https://img.shields.io/badge/DOI-10.1101%2F2020.06.01.127688%20-informational)](https://doi.org/10.1101/2020.06.01.127688 )

This repository implements a **fully reproducible pipeline** for the autism signature project. It uses `invoke` tasks and a Docker container for **consistent, cross-platform execution.**

The entire workflow—data fetching, processing, and figure generation—can be **reproduced in a few commands.**

---

## 🚀 Quick Start

### 1️⃣ Environment Setup

First, install `invoke`:

```bash
pip install invoke
```

To set up everything:

```bash
invoke setup-all
```

This:

* builds (or sets up) the Docker container;
* sets up Python & R environments (if running locally);
* prepares the folder structure.

**Note:**
This task assumes an Ubuntu-like operating system. You will still need to have a number of dependencies installed, such as R and Python. Check the Docker build file (`Dockerfile`) for more info on installing all required dependencies.

**Note 2:**
You can skip this step if you choose to run the analysis in a docker container, provided you have docker installed and complete the following steps using invoke.
 
---

### 2️⃣ Fetch Data & Results

Download all necessary data & results:

```bash
invoke fetch-all
```

This populates:

* `source_data/` (fMRI + atlas);
* `output_data/Results` (pre-generated results).

---

### 3️⃣ Run Full Pipeline

```bash
invoke run-all
```

This runs:

* **Discovery** (conformal score analysis);
* **Score aggregation**;
* **Figure generation**.

**Smoke test:** To quickly test the setup with a single replication:

```bash
invoke run-all --smoke-test
```

---

### 4️⃣ Clean Everything

To remove all generated data:

```bash
invoke clean-all
```

---

## 🛣️ Using the Container

To run tasks **inside the Docker container**:

```bash
invoke container-run --task run-all
```

This ensures the entire environment (Python, R, deps) is fully controlled. If you use that route, you are not required to complete `invoke setup-all`. The container image includes a snapshot of all the required dependencies, starting with a jupyter notebook docker stack image.

---

## 📁 Folder Structure

| Folder                        | Description                                              |
| ----------------------------- | -------------------------------------------------------- |
| `source_data/`                | Raw data: Atlases & fMRI data.                           |
| `output_data/`                | All generated outputs: Discovery results, figures, etc.  |
| `code/figures/`               | Jupyter notebooks used to generate all figures.          |
| `output_data/Figures/`        | Output folders for each figure notebook.                 |
| `tasks.py` / `tasks_utils.py` | The heart of the pipeline: all `invoke` tasks live here. |

---

## 📝 Key Tasks Overview

| Task                   | What it Does                                                        |
| ---------------------- | ------------------------------------------------------------------- |
| `setup-all`            | Sets up container + environment + folder structure.                 |
| `fetch-all`            | Downloads all data & results from Zenodo.                           |
| `run-all`              | Runs full pipeline (discovery + scores + figures).                  |
| `run-all --smoke-test` | Runs a quick smoke test (1 replication).                            |
| `clean-all`            | Removes all generated outputs.                                      |
| `container-run`        | Runs any task inside the Docker container (e.g., `--task run-all`). |

---

## ✅ Minimal Example

```bash
invoke setup-all
invoke fetch-all
invoke container-run --task run-all -- --smoke-test
```

# Old README

## Steps to reproduce the analysis
### Data
The study uses data from ABIDE 1 and 2 datasets. Participants were matched using propensity score matching, which was completed as part of a separate project - the scripts are here (LINK).
Resting state functional connectivity data was preprocessed using NIAK, described in the paper. This study uses the seed maps.
Using the following scripts the full analysis can be reproduced. Alternatively, to skip the data analysis part and recreate the figures, download all results data from (LINK).

### Data analysis
These steps were run on the Alliance Canada Beluga server. Download the data from (LINK) and update the paths and slurm preamble.

On an HPC server, first set up the R environment. After cloning the repository:
1. Open R in the project directory
2. ```R install.packages("renv") renv::restore() ```

For scripts 1-5 do:
```
python -m venv hpc_py11_env
source hpc_py11_env/bin/activate
pip install -r environments/requirements_py11.txt
```

Run:
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
If you skipped the data analysis part, download the results and data files from (LINK). Set up the local Python environment:

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
