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

## 🛣️ Using the docker Container

To run tasks **inside the Docker container** (here using 4 threads):

```bash
invoke docker-run --task run-all --args "--threads=4"
```

You will need docker installed for this to work though. This ensures the entire environment (Python, R, deps) is fully controlled. If you use that route, you are not required to complete `invoke setup-all`. The container image includes a snapshot of all the required dependencies, starting with a jupyter notebook docker stack image. To run a smoke test inside the container:
```bash
invoke docker-run --task run-all --args "--threads=4 --smoke-test"
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

## ✅ Minimal Example

```bash
invoke setup-all
invoke fetch-all
invoke container-run --task run-all --args "--smoke-test --threads=4"
```
