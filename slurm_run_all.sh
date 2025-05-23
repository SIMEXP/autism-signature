#!/bin/bash
#SBATCH --account=def-pbellec
#SBATCH --job-name=ASD_full_run
#SBATCH --output=ASD_%j.out
#SBATCH --error=ASD_%j.err
#SBATCH --cpus-per-task=20
#SBATCH --mem=160G
#SBATCH --time=24:00:00

# Load required modules
module load StdEnv/2020
module load apptainer
module load python/3.11

# Echo a dramatic prelude
echo "🌑 Beginning full pipeline execution via Apptainer..."

# Run the invoke task inside Apptainer with specified threads
invoke apptainer-run --task run-all --args "--threads=20"
