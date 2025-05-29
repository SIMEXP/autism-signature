import os
import shutil
from invoke import task, Context
import tempfile
import gzip
from pathlib import Path

## SET UP
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

### CONTAINER
def _set_image(c, image=None):
    """
    Resolve the Docker image name from parameter or invoke.yaml.
    """
    image = image or c.config.get("docker_image")
    if not image:
        raise ValueError("No Docker image specified. Please set docker_image in invoke.yaml or pass it explicitly.")
    return image

@task
def docker_build(c, image=None):
    """
    Build the Docker image from the Dockerfile in the project root.
    """
    image = _set_image(c, image)
    print(f"🐳 Building Docker image: {image}")
    c.run(f"docker build -t {image} .")

@task
def docker_archive(c, image=None):
    """
    Save the Docker image to a compressed archive for Zenodo or transport.
    """
    image = _set_image(c, image)
    output = f"{image}.tar.gz"
    print(f"📦 Archiving Docker image '{image}' to {output}...")
    c.run(f"docker save {image} | gzip > {output}")
    print("🪦 Archive complete.")

@task
def docker_setup(c, url=None, image=None):
    """
    Download and load the prebuilt Docker image from Zenodo.
    """
    image = _set_image(c, image)
    if not url:
        url = c.config.get("docker_archive")
        if not url:
            raise ValueError("No archive URL provided. Set docker_archive in invoke.yaml or pass --url.")

    output = f"{image}.tar.gz"
    if not os.path.exists(output):
        print(f"📥 Downloading container from {url}...")
        c.run(f"wget -O {output} '{url}'")
    else:
        print(f"📦 Container archive already exists: {output}")

    print("🐳 Loading Docker image...")
    c.run(f"gunzip -c {output} | docker load")

    print("✨ Container setup complete.")

def _ensure_docker_image_loaded(c, image, image_tar):
    """
    Ensure the specified Docker image is available. If not, try to load it from a .tar or .tar.gz.
    """
    if not shutil.which("docker"):
        raise RuntimeError("❌ Docker is not installed or not in PATH. Please install Docker.")

    result = c.run(f"docker images -q {image}", hide=True, warn=True)
    if result.stdout.strip():
        # Ensure it's tagged as :latest for Apptainer
        c.run(f"docker tag {image} {image}:latest", warn=True)
        return

    print(f"📦 Docker image '{image}' not found. Attempting to load from {image_tar}...")

    image_tar = Path(image_tar)
    if not image_tar.exists():
        raise FileNotFoundError(f"❌ Docker image file not found: {image_tar}")

    if image_tar.suffixes[-2:] == ['.tar', '.gz']:
        print(f"🗜️ Extracting {image_tar}...")
        with tempfile.NamedTemporaryFile(suffix=".tar", delete=False) as temp_tar:
            with gzip.open(image_tar, "rb") as f_in:
                shutil.copyfileobj(f_in, temp_tar)
            temp_tar_path = temp_tar.name
        c.run(f"docker load -i {temp_tar_path}")
        os.remove(temp_tar_path)
    elif image_tar.suffix == ".tar":
        c.run(f"docker load -i {image_tar}")
    else:
        raise ValueError("❌ Unsupported container format. Use .tar or .tar.gz")
    # Tag the loaded image
    c.run(f"docker tag {image} {image}:latest", warn=True)

@task
def docker_run(c, task, args=""):
    """
    Run an invoke task inside the Docker container.

    Args:
        task (str): the invoke task to run
        args (str): any additional CLI args to pass to the task
    """
    image = c.config.get("docker_image")
    image_tar = f"{image}.tar.gz"

    _ensure_docker_image_loaded(c, image, image_tar)

    hostdir = os.getcwd()
    workdir = "/home/jovyan/work"
    cmd = f"invoke {task} {args}"
    docker_cmd = f'docker run --rm -v {hostdir}:{workdir} -w {workdir} {image} {cmd}'

    print(f"🐳 Running inside container: {cmd}")
    c.run(docker_cmd)

## Apptainer
@task
def apptainer_archive(c, image=None):
    """
    Archive the Apptainer (Singularity) image from a Docker image using Docker daemon.
    Builds the .sif file if not present.
    """
    image = _set_image(c, image)
    sif_path = Path(f"{image}.sif")

    if not shutil.which("apptainer"):
        raise RuntimeError("❌ Apptainer is not installed or not in PATH. Please install it.")

    if sif_path.exists():
        print(f"✅ Apptainer image already exists at {sif_path}. Skipping build.")
        return

    if not shutil.which("docker"):
        raise RuntimeError("❌ Docker is required to build from Docker image. Please install it.")

    _ensure_docker_image_loaded(c, image, f"{image}.tar.gz")
    print(f"🧪 Building Apptainer image {sif_path} from Docker image {image}:latest...")
    c.run(f"apptainer build {sif_path} docker-daemon:{image}:latest")
    print("✅ Apptainer image build complete.")

@task
def apptainer_run(c, task, args=""):
    """
    Run an invoke task inside the Apptainer container.

    Args:
        task (str): the invoke task to run
        args (str): any additional CLI args to pass to the task
    """
    docker_image = c.config.get("docker_image")
    sif_path = Path(f"{docker_image}.sif")

    if not sif_path.exists():
        raise FileNotFoundError(f"❌ Apptainer image not found: {sif_path}")

    hostdir = os.getcwd()
    workdir = "/home/jovyan/work"
    cmd = f"invoke {task} {args}"
    apptainer_cmd = f"apptainer exec --cleanenv --bind {hostdir}:{workdir} {sif_path} {cmd}"

    print(f"🧪 Running inside Apptainer: {cmd}")
    c.run(apptainer_cmd)

## Fetch data from zenodo
@task
def fetch_from_zenodo(c, name=None):
    """
    Generic fetch/uncompress task using config.fetch_zenodo values.

    Expects invoke.yaml to have:
      fetch_zenodo:
        <name>:
          url: https://...
          dest: path/to/final/dir [optional: triggers extraction if set]
          archive: path/to/downloaded/file (e.g. tmp/file.tar.gz or tmp/file.zip)
    """
    import os

    if not name:
        raise ValueError("Missing dataset name. Use --name=atlas or similar.")

    conf = c.config.get("fetch_zenodo", {}).get(name)
    if not conf:
        raise ValueError(f"No fetch_zenodo config found for '{name}'.")

    url = conf.get("url")
    dest_dir = conf.get("dest")  # optional
    archive_path = conf.get("archive")
    if dest_dir:
        path_done = Path(dest_dir, f"{name}.downloaded")

    if not url or not archive_path:
        raise ValueError(f"Missing url or archive path in config for '{name}'.")

    if dest_dir and path_done.exists():
        print(f"🧠 '{name}' already extracted at {dest_dir}")
        return

    if (not dest_dir) and os.path.exists(archive_path):
        print(f"🧠 '{name}' already extracted at {archive_path}")
        return

    os.makedirs(os.path.dirname(archive_path), exist_ok=True)
    print(f"📥 Downloading '{name}' from {url}...")
    c.run(f"wget -O {archive_path} '{url}'")

    if dest_dir:
        os.makedirs(dest_dir, exist_ok=True)
        print(f"🗃️ Extracting '{name}' to {dest_dir}...")

        if archive_path.endswith(".zip"):
            c.run(f"unzip {archive_path} -d {dest_dir}")
        elif archive_path.endswith(".tar.gz") or archive_path.endswith(".tgz"):
            c.run(f"tar -xzf {archive_path} -C {dest_dir}")
        else:
            raise ValueError(f"Cannot extract archive format: {archive_path}")

        c.run(f"rm {archive_path}")
        path_done.touch() # create a lock file to flag successful download
        print(f"✅ Done extracting '{name}'")
    else:
        print(f"📦 Downloaded raw archive for '{name}' to {archive_path} (no extraction)")

### Analyses
@task
def run_figures(c, notebooks_path=None, figures_base=None):
    """
    Run figure notebooks, skipping any that already have output folders.
    Notebooks directory and output location pulled from invoke.yaml.
    """
    import pathlib

    notebooks_path = notebooks_path or lib.Path(c.config.get("notebooks_dir", "code/figures"))
    figures_base = figures_base or pathlib.Path(c.config.get("figures_dir", "output_data/Figures"))

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
