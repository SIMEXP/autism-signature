#!/bin/bash
#SBATCH --account=def-pbellec
#SBATCH --job-name=build_residuals
#SBATCH --cpus-per-task=1
#SBATCH --mem=10G
#SBATCH --time=12:00:00

source hpc_py10_env/bin/activate

python build_residuals_validation.py
