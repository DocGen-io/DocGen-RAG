#!/bin/bash
#SBATCH --job-name=docgen_eval
#SBATCH --partition=gpu
#SBATCH --time=00:30:00
#SBATCH --output=pipeline_batch_job_%j.log
#SBATCH --error=pipeline_error_job_%j.error


# 1. Load Required Modules
module load python/3.9.10
module load singularityce/3.10.2
module load cuda/11.3.0
module load git/2.31.1

module list

# 2. Set Singularity Environment Variables
export SINGULARITYENV_CLUSTER_HOSTNAME="gpu.cluster"
export SINGULARITYENV_RAFT_BOOTSTRAP_EXPECT=1
export SINGULARITYENV_GOSSIP_BIND_ADDR="127.0.0.1"

# 3. Start Weaviate (Singularity)
echo "Starting Weaviate..."
singularity run ~/weaviate.sif > ~/singulartiy_logs.txt 2>&1 &
sleep 15  # Giving Weaviate time to spin up

# 4. Start Ollama
echo "Starting Ollama..."
# Ensure the directory exists for logs
mkdir -p ~/ollama_models
ollama serve > ~/ollama_models/ollama.log 2>&1 &
sleep 10  # Giving Ollama time to load models/drivers

# 5. Navigate to Project Directory
cd ~/DocGen/DocGen-RAG || { echo "Directory not found"; exit 1; }

# 6. Launch Phoenix (Observability)
echo "Launching Phoenix..."
uv run launch_phoenix.py > ~/phoenix.logs 2>&1 &
sleep 15 # Wait for Phoenix dashboard to be ready

# 7. Run Final Evaluation
echo "Run documentation pipeline on $1"
if [ -n "$2" ]; then
   uv run documentation-pipeline git $1 $2
else
   uv run documentation-pipeline git $1 
fi


echo "documentation completed."
