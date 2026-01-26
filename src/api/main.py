from fastapi import FastAPI, BackgroundTasks, HTTPException
from pydantic import BaseModel
from typing import Optional
import uvicorn

from src.services.input_handler import InputHandler
from src.services.framework_detector import FrameworkDetector
# from src.pipelines.rag import RAGService
from src.services.generator import DocGenerator
from src.core.config import settings
# from src.utils.ast_extractor import process_directory
from src.components.extractor.ast_extractor import ASTExtractor
from src.components.CodeMapper import CodeMapper
import yaml
import os
import json

app = FastAPI(title="DocGen RAG Service")

class GenerateRequest(BaseModel):
    source_type: str # 'git' or 'local'
    path: str
    credentials: Optional[str] = None

from typing import Dict, Any
import uuid

# In-memory job store
job_store: Dict[str, Dict[str, Any]] = {}

@app.post("/generate")
async def trigger_generation(request: GenerateRequest, background_tasks: BackgroundTasks):
    """
    Triggers the documentation process in the background.
    Returns a job_id to track the status.
    """
    job_id = str(uuid.uuid4())
    job_store[job_id] = {"status": "processing", "message": "Documentation is being generated."}
    
    background_tasks.add_task(process_documentation, request.source_type, request.path, request.credentials, job_id)
    return {"job_id": job_id, "status": "processing", "message": "Documentation generation started."}

@app.get("/status/{job_id}")
async def get_job_status(job_id: str):
    """
    Returns the current status of the documentation generation job.
    """
    if job_id not in job_store:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return job_store[job_id]

def process_documentation(source_type: str, path: str, credentials: Optional[str], job_id: str):
    print(f"Starting processing for {path} (Job ID: {job_id})")
    input_handler = InputHandler()
    working_dir = None
    
    # Load config
    with open("config.yaml", "r") as f:
        config = yaml.safe_load(f)
    
    try:
        # 1. Input Handling
        if source_type == "git":
            working_dir = input_handler.process_git_repo(path, credentials)
        elif source_type == "local":
            working_dir = input_handler.process_local_folder(path)
        else:
            job_store[job_id] = {"status": "failed", "error": "Invalid source type"}
            return

        if not working_dir:
             job_store[job_id] = {"status": "failed", "error": "Could not determine working directory"}
             return

        # 2. AST Extraction
        print(f"Extracting AST from {working_dir}...")
        extractor = ASTExtractor()
        all_ast_data = []

        # Walk through directory
        for root, dirs, files in os.walk(working_dir):
            # Ignore common exclude dirs
            if 'node_modules' in dirs: dirs.remove('node_modules')
            if '.git' in dirs: dirs.remove('.git')
            if '__pycache__' in dirs: dirs.remove('__pycache__')
            if '.venv' in dirs: dirs.remove('.venv')
            
            for file in files:
                file_path = os.path.join(root, file)
                try:
                    chunks = extractor.extract_by_query(file_path)
                    if chunks:
                        all_ast_data.extend(chunks)
                except Exception as e:
                     print(f"Error extracting from {file}: {e}")

        if not all_ast_data:
            print("No suitable files found for AST extraction.")
            job_store[job_id] = {"status": "completed", "warning": "No AST data found"}
            return

        # 3. Code Mapping
        print(f"Mapping {len(all_ast_data)} AST chunks...")
        mapper = CodeMapper()
        mapped_data = mapper.run(all_ast_data)

        # 4. Save Output
        # output_file = "mapped_ast.json" 
        # Or use a config value if available, e.g. config.get('mapper_output_path', 'mapped_ast.json')
        output_file = config.get('mapper_output_path', 'mapped_ast.json')
        
        with open(output_file, "w") as f:
            json.dump(mapped_data, f, indent=2)
            
        print(f"Mapping complete. Results saved to {output_file}")
        
        job_store[job_id] = {
            "status": "completed", 
            "message": "Documentation generation successful.",
            "results_file": output_file
        }

    except Exception as e:
        print(f"Error during processing: {e}")
        job_store[job_id] = {"status": "failed", "error": str(e)}
    finally:
        input_handler.cleanup()
          

if __name__ == "__main__":
    uvicorn.run("src.api.main:app", host="0.0.0.0", port=8000, reload=True)
