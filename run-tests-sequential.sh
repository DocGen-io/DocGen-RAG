#!/bin/bash
REPOS=(
  "https://github.com/marcusmonteirodesouza/typescript-firestore-terraform-realworld-backend"
  "https://github.com/mikro-orm/nestjs-realworld-example-app"
  "https://github.com/joyheros/realworld"
  "https://github.com/Erikvdv/realworldapiminimal"
)

for repo in "${REPOS[@]}"; do
  echo "Cleaning up outputs for $repo"
  rm -rf output/* analyzer_output/* dependencies.db

  echo "Submitting $repo"
  # Standard sbatch
  OUTPUT=$(sbatch run-pipeline.bash "$repo")
  JOB_ID=$(echo "$OUTPUT" | awk '{print $NF}')
  echo "Submitted job $JOB_ID. Waiting..."
  
  # Wait for it to show up in squeue
  sleep 5
  
  while squeue | grep -q "$JOB_ID"; do
    sleep 10
  done
  
  echo "Job $JOB_ID completed."
  echo "Errors:"
  cat "pipeline_error_job_${JOB_ID}.error" 2>/dev/null
  
  # Save the AST output to check it manually later
  REPO_NAME=$(basename "$repo")
  mkdir -p "saved_ast_outputs/${REPO_NAME}"
  cp -r analyzer_output/* "saved_ast_outputs/${REPO_NAME}/" 2>/dev/null
done
echo "All 4 tests finished!"
