# Start from the blessed Jupyter base
FROM jupyter/r-notebook:python-3.10

# Switch to root to install system-level dependencies
USER root

# Install R system dependencies (for RcppGSL, Matrix, etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgsl0-dev \
    liblapack-dev \
    libblas-dev \
    libssl-dev \
    libpng-dev \
    make \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install invoke and get repo tasks
USER $NB_UID
RUN pip install invoke
COPY tasks.py ./tasks.py

# R install
USER root
COPY renv.lock ./renv.lock
RUN invoke setup-env-r
RUN echo '.libPaths("/usr/local/lib/R/site-library")' >> /opt/conda/lib/R/etc/Rprofile.site
RUN echo '.libPaths("/usr/local/lib/R/site-library")' >> /opt/conda/lib/R/etc/Rprofile.site && \
    echo 'reticulate::use_python("/opt/conda/bin/python", required = TRUE)' >> /opt/conda/lib/R/etc/Rprofile.site

# Python install
USER $NB_UID
RUN pip install numpy
#COPY requirements.txt ./requirements.txt
#RUN invoke setup-env-python

WORKDIR /home/jovyan/work
