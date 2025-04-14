from invoke import task, Context
import os
import shutil
import glob
import sys
import random
from tasks_utils import (
    clean_folder,
    container_build,
    container_archive,
    container_setup,
    container_run,
    fetch_from_zenodo,
)

@task
def setup_env_r(c):
    """
    Restore R environment using renv, installing packages system-wide (for Docker builds).
    """
    print("📦 Restoring R environment system-wide...")

    lockfile_path = "renv.lock"
    lib_path = "/usr/local/lib/R/site-library"

    if not os.path.exists(lockfile_path):
        print(f"❌ Lockfile not found at {lockfile_path}.")
        return

    # install renv explicitly to known path
    c.run(
        f'Rscript -e "install.packages(\'renv\', lib = \'{lib_path}\', repos = \'https://cloud.r-project.org\')"'
    )

    # restore with matching lib path in .libPaths()
    c.run(
        f'Rscript -e ".libPaths(\'{lib_path}\'); '
        f'renv::restore(lockfile = \'{lockfile_path}\', library = \'{lib_path}\')"'
    )

### FETCH SOURCE DATA
@task
def fetch_atlas(c):
    fetch_from_zenodo(c, name="atlas")

@task
def fetch_fmri(c):
    fetch_from_zenodo(c, name="fmri")

@task(pre=[fetch_atlas, fetch_fmri])
def setup_source_data(c):
    """
    Fetch all source data (atlases + fMRI) and unzip it under source_data/.
    """
    print("✨ All source data ready.")

### FETCH OUTPUT_DATA
@task
def fetch_results(c):
    fetch_from_zenodo(c, name="results")

### RUN ANALYSES
@task
def run_discovery(c, output_dir="./output_data/Discovery", network=None, replication=None, debug=False):
    """
    Run the discovery conformal score analysis for selected networks and replications.
        network: (integer) index of network to process using 0-indexing (default None: loop over all)
        replication: (integer) index of bootstrap replication to generate using 0-indexing (default: None, generate 100)
    """
    working_dir = os.path.join(".", "source_data", "Data")
    debug_flag = "TRUE" if debug else "FALSE"

    if not os.path.exists(working_dir):
        print(f"❌ Source data missing in {working_dir}. Run 'invoke setup-source-data' first.")
        return

    os.makedirs(output_dir, exist_ok=True)

    # Use specified network and replication index, or by default run everything
    list_replication = [int(replication)] if replication is not None else range(100)
    list_network = [int(network)] if network is not None else range(18)

    for n in list_network:
        for r in list_replication:
            net_id = n + 1  # cursed 1-indexing
            rep_id = r + 1
            container_output_dir = f"/home/jovyan/work/{os.path.relpath(output_dir)}"
            result_file = os.path.join(output_dir, f"Results_Instance_{rep_id}_Network_{net_id}.csv")

            if os.path.exists(result_file):
                print(f"🟡 Skipping existing: {result_file}")
                continue

            print(f"🔮 Running replicate {rep_id}, network {net_id}")
            cmd = (
                f"Rscript code/data_analysis/discovery_conformal_score.R "
                f"{rep_id} {rep_id} {net_id} {working_dir} {container_output_dir} {debug_flag}"
            )
            c.run(cmd)

@task
def run_figures(c):
    """
    Run figure notebooks in code/figures/, skipping any that have already been executed.
    Assumes each notebook has an output folder under output_data/figures/{notebook_stem}.
    """
    import pathlib

    notebooks_dir = pathlib.Path("code/figures")
    output_base = pathlib.Path("output_data/Figures")

    notebooks = sorted(notebooks_dir.glob("*.ipynb"))

    if not notebooks:
        print("⚠️ No notebooks found in code/figures/")
        return

    for nb in notebooks:
        fig_name = nb.stem
        fig_output_dir = output_base / fig_name

        if fig_output_dir.exists():
            print(f"✅ Skipping {nb.name} (output exists)")
            continue

        print(f"📈 Running {nb.name}...")
        c.run(f"jupyter nbconvert --to notebook --execute --inplace {nb}")

    print("🎉 Figure notebooks processed.")

### CLEANING
@task
def clean_discovery(c):
    """
    Remove the entire output_data/Discovery folder and its contents.
    """
    clean_folder("output_data/Discovery")

@task
def clean_figures(c):
    """
    Remove the entire output_data/Figures folder and its contents.
    """
    clean_folder("output_data/Figures")



# @task(pre=[check_env, check_seeds, clean_results, run_analysis, build_figures])
# def all(c):
#     """
#     Run the full pipeline.
#     """
#     print("🎉 All steps completed successfully.")
