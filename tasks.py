from invoke import task, Context
import os
import shutil
import glob
import sys
from pathlib import Path
import random
from tasks_utils import (
    clean_folder,
    docker_build,
    docker_archive,
    docker_setup,
    docker_run,
    apptainer_archive, 
    apptainer_run,
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

@task
def setup_all(c):
    """
    Setup all the requirements.
    """
    setup_env_r(c)
    setup_env_python(c)
    print(f"✨ Setup complete!")

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
def fetch_docker(c):
    fetch_from_zenodo(c, name="docker")

@task(pre=[fetch_atlas, fetch_fmri, fetch_old_results, fetch_docker])
def fetch_all(c):
    """
    Fetch all data assets.
    """
    print("✨ All data assets ready.")

### RUN ANALYSES
@task
def run_discovery(c, network, replication, debug=False):
    """
    Run the discovery conformal score analysis for selected networks and replications.

    Args:
        network (int): index of network to process using 0-indexing
        replication (int): index of bootstrap replication using 0-indexing
        debug (bool): set TRUE to enable debugging behavior in R script
    """
    # Config-driven paths
    output_dir = os.path.relpath(c.config.get("output_discovery", "output_data/Discovery"))
    working_dir = c.config.get("source_fmri_dir", "source_data/Data")
    debug_flag = "TRUE" if debug else "FALSE"

    if not os.path.exists(working_dir):
        print(f"❌ Source fMRI data missing at {working_dir}. Run 'invoke setup-source-data' first.")
        return

    os.makedirs(output_dir, exist_ok=True)

    rep = int(replication) + 1 # cursed 1 indexing
    net = int(network) + 1 # cursed 1 indexing

    result_file = os.path.join(output_dir, f"Results_Instance_{rep}_Network_{net}.csv")

    if os.path.exists(result_file):
        print(f"🟡 Skipping existing: {result_file}")
        return

    print(f"🔮 Running replicate {rep}, network {net}")
    cmd = (
        f"Rscript code/data_analysis/discovery_conformal_score.R "
        f"{rep} {rep} {net} {working_dir} ./{output_dir} {debug_flag}"
    )
    c.run(cmd)

@task
def run_discovery_all(c, threads=1, debug=False):
    """
    Run all discovery conformal score analyses (100 replications × 18 networks).
    Runs in parallel using threads if threads > 1.

    Args:
        threads (int): number of threads to use (default: 1, i.e. serial execution)
        debug (bool): enable debugging behavior in R script
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed

    debug_flag = "--debug" if debug else ""
    if debug:
        jobs = [(0, net) for net in range(18)]
    else:
        jobs = [(rep, net) for rep in range(100) for net in range(18)]

    def run_single(rep_net):
        rep, net = rep_net
        c.run(f"invoke run-discovery --replication={rep} --network={net} {debug_flag}")

    print(f"🧵 Launching discovery with {str(threads)} thread{'s' if threads != 1 else ''}...")

    if threads == 1:
        for job in jobs:
            run_single(job)
    else:
        with ThreadPoolExecutor(max_workers=threads) as executor:
            futures = [executor.submit(run_single, job) for job in jobs]
            for future in as_completed(futures):
                # fail loudly
                future.result()

    print("🖤 Full discovery run complete.")

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

@task
def run_null(c, output_dir=None, debug=False):
    """
    Run Validation_Conformal_Score.R to validate discovery results.
    """
    import os

    source_dir = c.config.get("source_fmri_dir", "source_data/Data")
    output_dir = output_dir or c.config.get("output_null", "output_data/Null")
    debug_flag = "TRUE" if debug else "FALSE"
    os.makedirs(output_dir, exist_ok=True)

    real_results = glob.glob(os.path.join(output_dir, "Results_Instance_*.csv"))
    if real_results:
        print(f"🧠 Found {len(real_results)} existing 'real' results. Skipping.")
        return

    print(f"🔎 Running null permutation experiments (debug mode: {debug_flag})...")
    cmd = f"Rscript code/data_analysis/Null_Model.R {source_dir} {output_dir} {debug_flag}"
    c.run(cmd)
    print("🎯 Null experiments complete.")

@task
def run_supplemental(c):
    notebooks_dir = Path(c.config.get("supplemental_notebooks_dir"))
    figures_dir = Path(c.config.get("supplemental_figures_dir"))
    run_figures(c, notebooks_dir, figures_dir)

@task
def run_all(c, smoke_test=False, threads=1):
    """
    Run all analyses
    Use --smoke-test to run a short smoke test (1 replication with 20 subjects)
    Use --threads to specify the number of parallel threads (default 1)
    """
    if smoke_test:
        print("🧨 Smoke test initiated: 1 replication across all 18 networks...")
        flag_smoke_test=" --debug"
    else:
        print("🧨 Full replication run initiated (this is going to take a while!):")
        flag_smoke_test=""
    c.run(f"invoke run-discovery-all --threads={threads}{flag_smoke_test}")
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
def clean_null(c):
    """
    Remove the entire output_data/Null folder and its contents.
    """
    clean_folder(c.config.get("output_null", "output_data/Null"))

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

@task(pre=[clean_discovery, clean_validation, clean_null, clean_figures, clean_supplemental])
def clean_all(c):
    """
    Clean all outputs
    """
    print("✨ All output data assets have been cleaned.")
