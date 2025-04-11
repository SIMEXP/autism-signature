from invoke import task, Context
import os
import subprocess
import sys
import random

## Helper functions
def run_container(command, volumes=None, image="autism-signature"):
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


## SET UP
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

    lockfile_path = "Requirements/renv.lock"
    if not os.path.exists(lockfile_path):
        print(f"❌ Lockfile not found at {lockfile_path}.")
        return

    c.run(
        'Rscript -e "install.packages(\'renv\', repos=\'https://cloud.r-project.org\')"'
    )
    c.run(
        f'Rscript -e "renv::restore(lockfile = \'{lockfile_path}\', '
        f'library = \'/usr/local/lib/R/site-library\')"'
    )

@task
def setup_env_data(c):
    """
    Download source data and prepare sourcedata folder.
    """
    print("📥 Downloading source data from Zenodo...")
    c.run("mkdir -p sourcedata")

    # Replace 'filename.zip' with the actual archive name if known
    c.run("wget -O sourcedata/data.zip https://zenodo.org/record/15192559/files/autism-signature-sourcedata.zip?download=1")
    c.run("unzip -o sourcedata/data.zip -d sourcedata")
    c.run("rm sourcedata/data.zip")

    # Add placeholder for documentation
    with open("sourcedata/CONTENT.md", "w") as f:
        f.write("# Source Data\\n\\nData downloaded from Zenodo: https://doi.org/10.5281/zenodo.15192559\\n")

    print("✨ Source data setup complete.")

### BUILD THINGS
@task
def build_docker(c):
    """
    Build the Docker image from the Dockerfile in the project root.
    """
    print("🐳 Building Docker image: autism-signature")
    c.run("docker build -t autism_signature .")

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
