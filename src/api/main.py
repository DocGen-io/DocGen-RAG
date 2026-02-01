"""
DocGen API - FastAPI service for documentation generation.

Endpoints:
    POST /generate - Start documentation generation
    GET /status/{job_id} - Check generation status
"""
from fastapi import FastAPI, BackgroundTasks, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any
import uvicorn
import uuid
import logging

from src.pipelines.documentation_pipeline import DocumentationPipeline

logger = logging.getLogger(__name__)

app = FastAPI(title="DocGen RAG Service")

# In-memory job store
job_store: Dict[str, Dict[str, Any]] = {}


class GenerateRequest(BaseModel):
    source_type: str  # 'git' or 'local'
    path: str
    credentials: Optional[str] = None


@app.post("/generate")
async def trigger_generation(request: GenerateRequest, background_tasks: BackgroundTasks):
    """
    Triggers the documentation process in the background.
    Returns a job_id to track the status.
    """
    job_id = str(uuid.uuid4())
    job_store[job_id] = {"status": "processing", "message": "Documentation is being generated."}
    
    background_tasks.add_task(
        process_documentation,
        request.source_type,
        request.path,
        request.credentials,
        job_id
    )
    
    return {"job_id": job_id, "status": "processing", "message": "Documentation generation started."}


@app.get("/status/{job_id}")
async def get_job_status(job_id: str):
    """Returns the current status of the documentation generation job."""
    if job_id not in job_store:
        raise HTTPException(status_code=404, detail="Job not found")
    return job_store[job_id]


def process_documentation(source_type: str, path: str, credentials: Optional[str], job_id: str):
    """Background task that runs the full documentation pipeline."""
    logger.info(f"Starting pipeline for {path} (Job ID: {job_id})")
    
    try:
        pipeline = DocumentationPipeline()
        result = pipeline.run(
            source_type=source_type,
            path=path,
            credentials=credentials
        )
        
        job_store[job_id] = result
        
    except Exception as e:
        logger.error(f"Pipeline failed: {e}")
        job_store[job_id] = {"status": "failed", "error": str(e)}


if __name__ == "__main__":
    uvicorn.run("src.api.main:app", host="0.0.0.0", port=8000, reload=True)
