#!/bin/bash
#SBATCH --account=def-pbellec
#SBATCH --job-name=ASD_null
#SBATCH --output=/ASD_null_%A_%a.out
#SBATCH --error=/ASD_null_%A_%a.err
#SBATCH --cpus-per-task=1
#SBATCH --mem=16G
#SBATCH --time=2:00:00

# Load the required modules
module load StdEnv/2020
module load gcc/9.3.0
module load flexiblas/3.4.4
module load r/4.0.2
module load python/3.11

# Set the directories
working_dir=""
output_dir=""
mkdir -p "$output_dir"

# Activate environments
source "$working_dir/renv/activate.R"
source "$working_dir/hpc_py11_env/bin/activate"

Rscript Null_Model.R $working_dir $output_dir
