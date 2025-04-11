#!/bin/bash
#SBATCH --account=def-pbellec
#SBATCH --job-name=ASD_validation
#SBATCH --output=/ASD_validation_%j.out
#SBATCH --error=/ASD_validation_%j.err
#SBATCH --cpus-per-task=1
#SBATCH --mem=20G
#SBATCH --time=24:00:00

# Load the required modules
module load StdEnv/2020
module load gcc/9.3.0
module load flexiblas/3.4.4
module load r/4.0.2
module load python/3.11

# Set the directories
working_dir=""

# Activate environments
source "$working_dir/renv/activate.R"
source "$working_dir/hpc_py11_env/bin/activate"

# Run the script
Rscript Validation_Conformal_Score_HPC.R
