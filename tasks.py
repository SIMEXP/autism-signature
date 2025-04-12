from invoke import task, Context
import os
import shutil
import glob
import sys
import random

## SET UP ENVIRONMENT
@task
def setup_env_python(c):
    """
    Install Python requirements based on Python version.

    Args:
        target (String) which requirements to use ("3.10", "3.11" or "figures", which is a 3.10 variant)
    """
    print("🐍 Installing Python requirements...")
    c.run(f"pip install -r requirements.txt")

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
    """
    Download and unzip the ATLAS archive into source_data/.
    """
    url = "https://zenodo.org/records/15192559/files/ATLAS.zip?download=1"
    dest_dir = "source_data/ATLAS"
    zip_path = "source_data/ATLAS.zip"

    if os.path.exists(dest_dir):
        print(f"🧠 ATLAS already extracted at {dest_dir}")
        return

    os.makedirs("source_data", exist_ok=True)
    print("📥 Downloading ATLAS...")
    c.run(f"wget -O {zip_path} '{url}'")
    print("🗃️ Unzipping ATLAS...")
    c.run(f"unzip {zip_path} -d source_data/")
    c.run(f"rm {zip_path}")

@task
def fetch_fmri(c):
    """
    Download and unzip the fMRI Data archive into source_data/.
    """
    url = "https://zenodo.org/records/15192559/files/Data.zip?download=1"
    dest_dir = "source_data/Data"
    zip_path = "source_data/Data.zip"

    if os.path.exists(dest_dir):
        print(f"🧬 fMRI data already extracted at {dest_dir}")
        return

    os.makedirs("source_data", exist_ok=True)
    print("📥 Downloading fMRI data...")
    c.run(f"wget -O {zip_path} '{url}'")
    print("🗃️ Unzipping fMRI data...")
    c.run(f"unzip {zip_path} -d source_data/")
    c.run(f"rm {zip_path}")

@task(pre=[fetch_atlas, fetch_fmri])
def setup_source_data(c):
    """
    Fetch all source data (atlases + fMRI) and unzip it under source_data/.
    """
    print("✨ All source data ready.")

### FETCH OUTPUT_DATA
@task
def fetch_results(c):
    """
    Download and extract the Results.zip archive from Zenodo into output_data/.
    """
    url = "https://zenodo.org/records/15192559/files/Results.zip?download=1"
    zip_path = "output_data/Results.zip"
    dest_dir = "output_data"

    if os.path.exists(os.path.join(dest_dir, "Results")):
        print("🧠 Results already appear to be extracted. Run 'invoke clean-results' to clean previous download before fetching.")
        return

    os.makedirs(dest_dir, exist_ok=True)

    print("📥 Downloading Results.zip...")
    c.run(f"wget -O {zip_path} '{url}'")

    print("🗃️ Unzipping archive into output_data/...")
    c.run(f"unzip -o {zip_path} -d {dest_dir}")
    c.run(f"rm {zip_path}")

    print("✅ Results fetched and unzipped.")

### CONTAINER OPERATIONS
@task
def container_build(c):
    """
    Build the Docker image from the Dockerfile in the project root.
    """
    print("🐳 Building Docker image: autism_signature")
    c.run("docker build -t autism_signature .")

@task
def container_archive(c, image="autism_signature", output="autism_signature.tar.gz"):
    """
    Save the Docker image to a compressed archive for Zenodo or transport.
    """
    print(f"📦 Archiving Docker image '{image}' to {output}...")
    c.run(f"docker save {image} | gzip > {output}")
    print("🪦 Archive complete.")

@task
def container_setup(c, url="https://zenodo.org/record/15192559/files/autism-signature.tar.gz", output="autism-signature.tar.gz"):
    """
    Download and load the prebuilt Docker image from Zenodo.
    """
    if not os.path.exists(output):
        print(f"📥 Downloading container from {url}...")
        c.run(f"wget -O {output} '{url}'")
    else:
        print(f"📦 Container archive already exists: {output}")

    print("🐳 Loading Docker image...")
    c.run(f"gunzip -c {output} | docker load")

    print("✨ Container setup complete.")

def container_run(command, volumes=None, image="autism_signature"):
    """
    Run a command inside the Docker container.

    Parameters:
        command (str): The shell command to run inside the container.
        volumes (dict): A dict mapping host paths to container paths.
        image (str): Docker image to use.
    """
    volumes = volumes or {os.getcwd(): "/home/jovyan/work"}
    volume_args = " ".join([f"-v {host}:{container}" for host, container in volumes.items()])
    container_cmd = f"docker run --rm {volume_args} -w /home/jovyan/work {image} bash -c \"{command}\""
    Context().run(container_cmd)

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
            container_run(cmd)

### CLEANING
@task
def clean_discovery(c):
    """
    Remove the entire output_data/Discovery folder and its contents.
    """
    discovery_dir = "output_data/Discovery"

    if os.path.exists(discovery_dir):
        shutil.rmtree(discovery_dir)
        print(f"💥 Removed {discovery_dir} and all its contents.")
    else:
        print("🫧 No Discovery folder to remove.")

@task
def clean_results(c):
    """
    Clean up old results.
    """
    print("🧹 Cleaning Results directory...")
    c.run("rm -rf Results/*", warn=True)

@task
def run_analysis(c):
    """
    Run all R and Python analysis scripts.
    """
    print("🚀 Running analysis scripts...")
    c.run("Rscript Code/Data_analysis/Discovery_Conformal_Score.R")
    c.run("Rscript Code/Data_analysis/Validation_Conformal_Score.R")
    c.run("python3 Code/Data_analysis/build_residuals_validation.py")

@task
def build_figures(c):
    """
    Execute all Jupyter notebooks to regenerate figures.
    """
    print("📊 Rebuilding figures from notebooks...")
    c.run("jupyter nbconvert --execute --inplace Code/Figures/*.ipynb")

# @task(pre=[check_env, check_seeds, clean_results, run_analysis, build_figures])
# def all(c):
#     """
#     Run the full pipeline.
#     """
#     print("🎉 All steps completed successfully.")
