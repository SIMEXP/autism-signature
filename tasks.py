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
    run_figures
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

### FETCH DATA
@task
def fetch_atlas(c):
    fetch_from_zenodo(c, name="atlas")

@task
def fetch_fmri(c):
    fetch_from_zenodo(c, name="fmri")

@task
def fetch_old_results(c):
    fetch_from_zenodo(c, name="results")

@task
def fetch_container(c):
    fetch_container(c, name="container")

@task(pre=[fetch_atlas, fetch_fmri, fetch_old_results])
def fetch_all(c):
    """
    Fetch all data assets.
    """
    print("✨ All data assets ready.")

### RUN ANALYSES
@task
def run_discovery(c, output_dir=None, network=None, replication=None, debug=False):
    """
    Run the discovery conformal score analysis for selected networks and replications.

    Args:
        network (int): index of network to process using 0-indexing (default: all)
        replication (int): index of bootstrap replication using 0-indexing (default: all 100)
        debug (bool): set TRUE to enable debugging behavior in R script
    """
    import os

    # Config-driven paths
    output_dir = output_dir or c.config.get("output_discovery", "output_data/Discovery")
    working_dir = c.config.get("source_fmri_dir", "source_data/Data")
    debug_flag = "TRUE" if debug else "FALSE"

    if not os.path.exists(working_dir):
        print(f"❌ Source fMRI data missing at {working_dir}. Run 'invoke setup-source-data' first.")
        return

    os.makedirs(output_dir, exist_ok=True)

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
def run_scores(c, debug=False):
    """
    Run Discovery_Read_Conformal_Scores.R to aggregate discovery results.
    Skips if 'table_split.csv' already exists.
    """
    import os

    source_dir = c.config.get("source_fmri_dir", "source_data/Data")
    discovery_dir = c.config.get("output_discovery", "output_data/Discovery")
    output_file = os.path.join(discovery_dir, "table_split.csv")
    debug_flag = "TRUE" if debug else "FALSE"

    if os.path.exists(output_file):
        print(f"✅ Split table already exists at {output_file}. Skipping.")
        return

    print(f"🔎 Running conformal score aggregation (debug mode: {debug_flag})...")
    cmd = f"Rscript code/data_analysis/Discovery_Read_Conformal_Scores.R {source_dir} {discovery_dir} {debug_flag}"
    c.run(cmd)
    print("🎯 Split score table created.")

@task
def run_validation(c, output_dir=None, debug=False):
    """
    Run Validation_Conformal_Score.R to validate discovery results.
    """
    import os

    source_dir = c.config.get("source_fmri_dir", "source_data/Data")
    output_dir = output_dir or c.config.get("output_validation", "output_data/Validation")
    debug_flag = "TRUE" if debug else "FALSE"
    os.makedirs(output_dir, exist_ok=True)

    real_results = glob.glob(os.path.join(output_dir, "Results_Real_Network_*.csv"))
    if real_results:
        print(f"🧠 Found {len(real_results)} existing 'real' results. Skipping.")
        return

    print(f"🔎 Running conformal score validation (debug mode: {debug_flag})...")
    cmd = f"Rscript code/data_analysis/Validation_Conformal_Score.R {source_dir} {output_dir} {debug_flag}"
    c.run(cmd)
    print("🎯 Validation of conformal scores complete.")

@task
def run_validation_read(c, debug=False):
    """
    Run Validation_Read_Conformal_Scores.R to parse validation results.
    Skips if 'validation_net_split_1_model_1_combined_p_values' already exists.
    """
    import os

    source_dir = c.config.get("source_fmri_dir", "source_data/Data")
    discovery_dir = c.config.get("output_discovery", "output_data/Discovery")
    validation_dir = c.config.get("output_validation", "output_data/Validation")
    output_file = os.path.join(validation_dir, "validation_net_split_1_model_1_combined_p_values")
    debug_flag = "TRUE" if debug else "FALSE"

    if os.path.exists(output_file):
        print(f"✅ Split table already exists at {output_file}. Skipping.")
        return

    print(f"🔎 Running validation score aggregation (debug mode: {debug_flag})...")
    cmd = f"Rscript code/data_analysis/Validation_Read_Conformal_Scores.R {source_dir} {discovery_dir} {validation_dir} {debug_flag}"
    c.run(cmd)
    print("🎯 Split score table created.")

@task run_supplemental(c):
    run_figures(c, c.config.get("supplemental_notebooks_dir"), c.config.get("supplemental_figures_dir"))
@task
def run_all(c, smoke_test=False):
    """
    Run all analyses
    Use --parallel to enable parallel execution with xargs.
    Use --smoke-test to run a short smoke test (1 replication with 20 subjects)
    """
    if smoke_test
        print("🧨 Smoke test initiated: 1 replication across all 18 networks...")
        flag_smoke_test=" --debug"
    else:
        print("🧨 Full replication run initiated (this is going to take a while!):")
        flag_smoke_test=""
    for net in range(18):
        if smoke_test:
            c.run(f"invoke run-discovery --replication=1 --network={net} --debug")
        else:
            c.run(f"invoke run-discovery")
    c.run(f"invoke run-scores{flag_smoke_test}")
    c.run(f"invoke run-validation{flag_smoke_test}")
    c.run(f"invoke run-validation-read{flag_smoke_test}")
    c.run(f"invoke run-null{flag_smoke_test}")
    if smoke_test:
        print("🖤 Smoke test complete.")
    else:
        print("🖤🖤🖤 Full replication complete.")

### CLEANING
@task
def clean_discovery(c):
    """
    Remove the entire output_data/Discovery folder and its contents.
    """
    clean_folder(c.config.get("output_discovery", "output_data/Discovery"))

@task
def clean_validation(c):
    """
    Remove the entire output_data/Validation folder and its contents.
    """
    clean_folder(c.config.get("output_validation", "output_data/Validation"))

@task
def clean_figures(c):
    """
    Remove the entire output_data/Figures folder and its contents.
    """
    clean_folder(c.config.get("figures_dir", "output_data/Figures"))

@task
def clean_supplemental(c):
    """
    Remove the entire output_data/Supplemental folder and its contents.
    """
    clean_folder(c.config.get("supplemental_dir", "output_data/Supplemental"))
