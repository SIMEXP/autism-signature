#!/bin/bash
#SBATCH --account=def-pbellec
#SBATCH --job-name=ASD_analysis_rep
#SBATCH --output=/ASD_%A_%a.out
#SBATCH --error=/ASD_%A_%a.err
#SBATCH --cpus-per-task=1
#SBATCH --mem=16G
#SBATCH --time=24:00:00
#SBATCH --array=1-100

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

for network in {1..18}; do
    output_file="$output_dir/Results_Instance_${SLURM_ARRAY_TASK_ID}_Network_${network}.csv"

    if [ ! -f "$output_file" ]; then
        echo "=== Processing Replicate $SLURM_ARRAY_TASK_ID Network $network ==="
        Rscript Discovery_Conformal_Score_HPC.R $SLURM_ARRAY_TASK_ID $SLURM_ARRAY_TASK_ID $network $working_dir $output_dir
    else
        echo "=== Output file $output_file already exists, skipping ==="
    fi
done
