from fastapi import FastAPI, BackgroundTasks, HTTPException
from pydantic import BaseModel
from typing import Optional
import uvicorn

from src.services.input_handler import InputHandler
from src.services.framework_detector import FrameworkDetector
from src.pipelines.rag import RAGService
from src.services.generator import DocGenerator
from src.core.config import settings
from src.utils.ast_extractor import process_directory

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
    ast_data_folder = 'ast'
    
    try:
        # 1. Input Handling
        if source_type == "git":
            working_dir = input_handler.process_git_repo(path, credentials)
        elif source_type == "local":
            working_dir = input_handler.process_local_folder(path)
        else:
            job_store[job_id] = {"status": "failed", "error": "Invalid source type"}
            return

        # 2. Framework Detection
        detector = FrameworkDetector()
        framework = detector.detect(working_dir)
        print(f"Detected Framework: {framework}")

        # 3. RAG Pipeline (Knowledge Injection)
        rag = RAGService()
        # rag.learn_framework(framework) # Fetch external docs
        
        # Execute AST Extraction and Indexing
        if working_dir:
            print(f"Extracting AST from {working_dir}...")
            # We don't necessarily need to save to disk here, so output_dir=None
            try:
                ast_data = process_directory(working_dir,ast_data_folder)
            except Exception as e:
                print(f"Error extracting AST: {e}")
                job_store[job_id] = {"status": "failed", "error": str(e)}
                return
            
            if ast_data:
                print(f"Indexing {len(ast_data)} files into RAG...")
                rag.indexing_pipeline(ast_data)
            else:
                print("No suitable files found for AST extraction.")
                # Could be a warning or failure depending on strictness
                # job_store[job_id] = {"status": "completed", "warning": "No files found"}

        # 4. Analysis & Generation (Mocked extraction for this step primarily)
        # Real implementation would use RAG to query "List all endpoints", "Get details for X"
        
        # Mocking extracted data for demonstration of the flow
        extracted_data = [
            {"path": "/users/{id}", "method": "GET", "description": "Get user by ID", "example_response": {"id": 1, "name": "Alice"}},
            {"path": "/login", "method": "POST", "description": "User login", "example_request": {"username": "u", "password": "p"}}
        ]
        
        # 5. Output Generation
        generator = DocGenerator()
        results = generator.generate_artifacts(extracted_data)
        print(f"Generation complete. Results at: {results}")
        
        job_store[job_id] = {
            "status": "completed", 
            "message": "Documentation generation successful.",
            "results": results
        }

    except Exception as e:
        print(f"Error during processing: {e}")
        job_store[job_id] = {"status": "failed", "error": str(e)}
    finally:
        input_handler.cleanup()

if __name__ == "__main__":
    uvicorn.run("src.api.main:app", host="0.0.0.0", port=8000, reload=True)
