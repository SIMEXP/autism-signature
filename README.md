# Code for the 🧠 high risk autism phenotype paper
[![MIT license](https://img.shields.io/badge/License-MIT-blue.svg)](https://lbesson.mit-license.org/)
[![DOI](https://img.shields.io/badge/DOI-10.1101%2F2020.06.01.127688%20-informational)](https://doi.org/10.1101/2020.06.01.127688 )

This repository implements a **fully reproducible pipeline** for the autism signature project. It uses `invoke` tasks and a Docker container for **consistent, cross-platform execution.**

The entire workflow—data fetching, processing, and figure generation—can be **reproduced in a few commands.**

---

## 🚀 Quick Start

### 1⃣ Install invoke

First, install `invoke`:

```bash
pip install invoke
```

You must also have either Docker or Apptainer installed to use container-based execution.

---

### 2⃣ Fetch Assets

Download all necessary data, results, and container images:

```bash
invoke fetch-all
```

This populates:
* `autism-signature.tar.gz` (a Docker container image from Zenodo)
* `autism-signature.sif` (an Apptainer container image from Zenodo)
* `source_data/` (fMRI + atlas);
* `output_data/Results` (pre-generated results).

> 💡 This command downloads ~7.5 GB of assets from Zenodo and may take minutes to hours depending on your internet speed.

---

### 3⃣ Run Full Pipeline using a container

To run tasks **inside the Docker container** (here using 2 parallel threads):

```bash
invoke docker-run --task run-all --args "--threads=2"
```

This ensures the entire environment (Python, R, dependencies) is fully controlled. The image includes a snapshot of all required software, based on a Jupyter notebook Docker stack image.

To run a smoke test inside the container:

```bash
invoke docker-run --task run-all --args "--threads=2 --smoke-test"
```

> 💡 This will load `autism-signature` into your Docker registry the first time and run it with the `latest` tag.

> 💡💡 A full run generates ~1.5 GB of results; the smoke test only MBs.

> 💡💡💡 A complete recompute takes ~30 minutes per replicate/network (about 37 days total serial time). Use archives or HPC to save time and energy.

> 💡💡💡💡 Each thread requires ~8 GB RAM.

Apptainer is also supported. Use `apptainer-run` in place of `docker-run`.

> 💡 The `apptainer-run` task checks for Apptainer, verifies image presence, and launches with correct bind paths.

---

### 4⃣ Clean Everything

To remove all generated data:

```bash
invoke clean-all
```

---
### 🔪 Running on a Cluster with Apptainer + SLURM

On an HPC system with Apptainer (formerly Singularity):

1. Ensure Apptainer is available:

```bash
module load apptainer
```

2. Submit the job:

```bash
sbatch slurm_run_all.sh
```

This script requests **20 CPUs**, **160 GB RAM**, and runs:

```bash
invoke apptainer-run --task run-all --args "--threads=20"
```
Some variables are hard-coded to run on the infrastructure of Digital Alliance of Canada using the allocation resource of the SIMEXP lab.

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

## Building the environment

### Installing dependencies
To set up everything, ensure functional Python and R environments and run:

```bash
invoke setup-all
```

This:

* sets up Python & R environments (if running locally);
* prepares the folder structure.

**Note:**
This task assumes an Ubuntu-like OS. You still need to install R, Python, etc. See the Dockerfile for complete setup info.

**Note 2:**
You can skip this if using the Docker container and running `docker-run` directly.

### Create a Docker image
To build a Docker image:

```bash
invoke docker-build
```

To generate a compressed archive:

```bash
invoke docker-archive
```

### Create an Apptainer image
After building the Docker image, run:

```bash
invoke apptainer-archive
```

This builds the `.sif` image from the Docker daemon.
