import os
import shutil
from invoke import task, Context

## SET UP ENVIRONMENT
@task
def setup_env_python(c, reqs="requirements.txt"):
    """
    Set up Python environment by installing from a requirements file.
    """
    if not os.path.exists(reqs):
        raise FileNotFoundError(f"⚠️ Requirements file not found: {reqs}")

    print(f"🐍 Installing Python requirements from {reqs}...")
    c.run(f"pip install -r {reqs}")

### CLEAN
def clean_folder(dir_name, label=None):
    """
    Remove an entire directory recursively. Use with caution!!!
    """
    label = label or dir_name
    if os.path.exists(dir_name):
        shutil.rmtree(dir_name)
        print(f"💥 Removed {label} at {dir_name}")
    else:
        print(f"🫧 Nothing to clean: {label}")

### Container tasks
def _set_image(c, image=None):
    """
    Resolve the Docker image name from parameter or invoke.yaml.
    """
    image = image or c.config.get("container_image")
    if not image:
        raise ValueError("No Docker image specified. Please set container_image in invoke.yaml or pass it explicitly.")
    return image

@task
def container_build(c, image=None):
    """
    Build the Docker image from the Dockerfile in the project root.
    """
    image = _set_image(c, image)
    print(f"🐳 Building Docker image: {image}")
    c.run(f"docker build -t {image} .")

@task
def container_archive(c, image=None):
    """
    Save the Docker image to a compressed archive for Zenodo or transport.
    """
    image = _set_image(c, image)
    output = f"{image}.tar.gz"
    print(f"📦 Archiving Docker image '{image}' to {output}...")
    c.run(f"docker save {image} | gzip > {output}")
    print("🪦 Archive complete.")

@task
def container_setup(c, url=None, image=None):
    """
    Download and load the prebuilt Docker image from Zenodo.
    """
    image = _set_image(c, image)
    if not url:
        url = c.config.get("container_archive")
        if not url:
            raise ValueError("No archive URL provided. Set container_archive in invoke.yaml or pass --url.")

    output = f"{image}.tar.gz"
    if not os.path.exists(output):
        print(f"📥 Downloading container from {url}...")
        c.run(f"wget -O {output} '{url}'")
    else:
        print(f"📦 Container archive already exists: {output}")

    print("🐳 Loading Docker image...")
    c.run(f"gunzip -c {output} | docker load")

    print("✨ Container setup complete.")

@task
def container_run(c, task, args=""):
    """
    Run an invoke task inside the Docker container.

    Args:
        task (str): the invoke task to run
        args (str): any additional CLI args to pass to the task
    """
    image = c.config.get("container_image", "autism_signature")
    cmd = f"invoke {task} {args}"
    docker_cmd = f'docker run --rm -v $PWD:/home/jovyan/work -w /home/jovyan/work {image} {cmd}'
    Context().run(docker_cmd)

## Fetch data from zenodo
@task
def fetch_from_zenodo(c, name=None):
    """
    Generic fetch/unzip task using config.fetch_zenodo values.

    Expects invoke.yaml to have:
      fetch_zenodo:
        <name>:
          url: https://...
          dest: path/to/final/dir
          zip: path/to/temp.zip
    """
    import os

    if not name:
        raise ValueError("Missing dataset name. Use --name=atlas or similar.")

    conf = c.config.get("fetch_zenodo", {}).get(name)
    if not conf:
        raise ValueError(f"No fetch_zenodo config found for '{name}'. Define it under 'fetch_zenodo' in invoke.yaml.")

    url = conf.get("url")
    dest_dir = conf.get("dest")
    zip_path = conf.get("zip")

    if not url or not dest_dir or not zip_path:
        raise ValueError(f"Missing url, dest, or zip in config for '{name}'.")

    if os.path.exists(dest_dir):
        print(f"🧠 '{name}' already extracted at {dest_dir}")
        return

    os.makedirs(os.path.dirname(zip_path), exist_ok=True)
    print(f"📥 Downloading '{name}' from {url}...")
    c.run(f"wget -O {zip_path} '{url}'")

    print(f"🗃️ Unzipping '{name}' to {dest_dir}...")
    c.run(f"unzip {zip_path} -d {os.path.dirname(dest_dir)}")
    c.run(f"rm {zip_path}")

    print(f"✅ Done fetching '{name}'")

### Analyses
@task
def run_figures(c):
    """
    Run figure notebooks, skipping any that already have output folders.
    Notebooks directory and output location pulled from invoke.yaml.
    """
    import pathlib

    notebooks_path = pathlib.Path(c.config.get("notebooks_dir", "code/figures"))
    figures_base = pathlib.Path(c.config.get("figures_dir", "output_data/Figures"))

    if not notebooks_path.exists():
        print(f"⚠️ Notebooks directory not found: {notebooks_path}")
        return

    notebooks = sorted(notebooks_path.glob("*.ipynb"))

    if not notebooks:
        print(f"⚠️ No notebooks found in {notebooks_path}/")
        return

    for nb in notebooks:
        fig_name = nb.stem
        fig_output_dir = figures_base / fig_name

        if fig_output_dir.exists():
            print(f"✅ Skipping {nb.name} (output exists at {fig_output_dir})")
            continue

        print(f"📈 Running {nb.name}...")
        c.run(f"jupyter nbconvert --to notebook --execute --inplace {nb}")

    print("🎉 All figure notebooks processed.")
