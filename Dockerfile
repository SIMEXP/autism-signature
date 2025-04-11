# Start from the blessed Jupyter base
FROM jupyter/base-notebook:python-3.10

# Switch to root to install system-level dependencies
USER root

# Install R system dependencies (for RcppGSL, Matrix, etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgsl0-dev \
    liblapack-dev \
    libblas-dev \
    libssl-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Create a local user library for R packages
ENV R_LIBS_USER=/home/jovyan/.local/R_libs
RUN mkdir -p $R_LIBS_USER

# Switch back to jovyan user for safety
USER $NB_UID

# Copy only the Requirements folder (assume it's mounted or copied in build context)
COPY requirements_extra/ ./requirements_extra/

# Install invoke and other Python dependencies
COPY requirements.txt /tmp/
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# Install dependencies
COPY tasks.py ./tasks.py
RUN invoke setup-env-python
RUN invoke setup-env-r

# Optional: copy full codebase later, or mount it in docker-compose or with volume
# COPY . /home/jovyan/work/

WORKDIR /home/jovyan/work
