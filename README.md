# Code for the 🧠 high risk autism phenotype paper
[![MIT license](https://img.shields.io/badge/License-MIT-blue.svg)](https://lbesson.mit-license.org/)
[![DOI](https://img.shields.io/badge/DOI-10.1101%2F2020.06.01.127688%20-informational)](https://doi.org/10.1101/2020.06.01.127688 )

This repository implements a **fully reproducible pipeline** for the autism signature project. It uses `invoke` tasks and a Docker container for **consistent, cross-platform execution.**

The entire workflow—data fetching, processing, and figure generation—can be **reproduced in a few commands.**

---

## 🚀 Quick Start

### 1️⃣ Install invoke

First, install `invoke`:

```bash
pip install invoke
```

You will also need to have either Docker or Apptainer installed in order to use either containarization methods.
---

### 2️⃣ Fetch Assets

Download all necessary data, results, and container images:

```bash
invoke fetch-all
```

This populates:
* `autism-signature.tar.gz`(a docker container image)
* `source_data/` (fMRI + atlas);
* `output_data/Results` (pre-generated results).

> 💡 This commands downloads 7 GB of assets from the platform zenodo, and may take minutes to hours to run, depending on the speed of your internet connection.
---

### 3️⃣ Run Full Pipeline using a container

To run tasks **inside the Docker container** (here using 2 parallel threads):

```bash
invoke docker-run --task run-all --args "--threads=2"
```

This ensures the entire environment (Python, R, deps) is fully controlled. The container image includes a snapshot of all the required dependencies, starting with a jupyter notebook docker stack image. To run a smoke test inside the container:
```bash
invoke docker-run --task run-all --args "--threads=2 --smoke-test"
```
> 💡 This command will add the autism-signature image to your docker registry and will run the image with the `latest` tag, the first time it is run

> 💡💡 Starting from a clean run, a full run generates 1.5 GB of results inside `output_data` and can take several hours using 20 threads. Each thread requires about 8GB of RAM. The smoke test only runs for a few minutes.

It is also possible to use Apptainer instead, using `apptainer-run` in place of `docker-run`.

> 💡 The `apptainer-run` task automatically checks if Apptainer is installed, ensures the image is loaded, and launches the task with the correct bind paths.


---

### 4️⃣ Clean Everything

To remove all generated data:

```bash
invoke clean-all
```

---
### 🔪 Running on a Cluster with Apptainer + SLURM

If you're on an HPC system with Apptainer (formerly Singularity), you can run the full pipeline with a single SLURM job.

1. Make sure Apptainer is available on your system:

```bash
module load apptainer
```

2. Then, submit the job:

```bash
sbatch slurm_run_all.sh
```

This script will request **20 CPUs**, **160GB of RAM**, and run the full analysis with:

```bash
invoke apptainer-run --task run-all --args "--threads=20"
```
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
To set up everything, you will first need a functional Python and R environment and run:

```bash
invoke setup-all
```

This:

* sets up Python & R environments (if running locally);
* prepares the folder structure.

**Note:**
This task assumes an Ubuntu-like operating system. You will still need to have a number of dependencies installed, such as R and Python. Check the Docker build file (`Dockerfile`) for more info on installing all required dependencies.

**Note 2:**
You can skip this step if you choose to build the environment in a docker container, provided you have docker installed and complete the following steps.

### Create a docker image
To build a docker image:

```bash
invoke docker-build
```
This:
* builds (or sets up) the Docker container;
* see the file `Dockerfile` for details of the set up;
* note that `invoke setup-all` is used to deploy all dependencies.

To generate a binary archive:
```bash
invoke docker-archive
```

### Create an apptainer image
To build an apptainer sif image, you need to first build a docker image (see above) and run:

```bash
invoke apptainer-build
```
