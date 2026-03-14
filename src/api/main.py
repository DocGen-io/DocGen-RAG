"""
DocGen API - FastAPI service for documentation generation.

Endpoints:
    POST /generate          - Start documentation generation (async job)
    GET  /status/{job_id}   - Check generation status
    POST /query             - Semantic + keyword search over stored endpoint docs
    POST /cluster           - Group endpoints by semantic similarity (on-demand)
    POST /example           - Generate fetch code examples for an endpoint (on-demand)
"""
from fastapi import FastAPI, BackgroundTasks, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import uvicorn
import uuid
import logging

from src.pipelines.documentation_pipeline import DocumentationPipeline
from src.pipelines.query_pipeline import QueryPipeline
from src.pipelines.postprocessing_pipeline import PostprocessingPipeline

logger = logging.getLogger(__name__)

app = FastAPI(title="DocGen RAG Service")

# In-memory job store
job_store: Dict[str, Dict[str, Any]] = {}


# --------------------------------------------------------------------------- #
# Request models
# --------------------------------------------------------------------------- #

class GenerateRequest(BaseModel):
    source_type: str  # 'git' or 'local'
    path: str
    credentials: Optional[str] = None


class QueryRequest(BaseModel):
    query: str


class ClusterRequest(BaseModel):
    n_clusters: Optional[int] = None


class ExampleRequest(BaseModel):
    swagger_data: Dict[str, Any]


# --------------------------------------------------------------------------- #
# Generation (async job)
# --------------------------------------------------------------------------- #

@app.post("/generate")
async def trigger_generation(request: GenerateRequest, background_tasks: BackgroundTasks):
    """Trigger documentation generation in the background. Returns a job_id."""
    job_id = str(uuid.uuid4())
    job_store[job_id] = {"status": "processing", "message": "Documentation is being generated."}

    background_tasks.add_task(
        _run_documentation,
        request.source_type,
        request.path,
        request.credentials,
        job_id,
    )
    return {"job_id": job_id, "status": "processing", "message": "Documentation generation started."}


@app.get("/status/{job_id}")
async def get_job_status(job_id: str):
    """Return the current status of a documentation generation job."""
    if job_id not in job_store:
        raise HTTPException(status_code=404, detail="Job not found")
    return job_store[job_id]


def _run_documentation(source_type: str, path: str, credentials: Optional[str], job_id: str):
    """Background task: runs the full documentation pipeline."""
    logger.info(f"Starting pipeline for {path} (Job ID: {job_id})")
    try:
        result = DocumentationPipeline().run(
            source_type=source_type, path=path, credentials=credentials
        )
        job_store[job_id] = result
    except Exception as e:
        logger.error(f"Pipeline failed: {e}")
        job_store[job_id] = {"status": "failed", "error": str(e)}


# --------------------------------------------------------------------------- #
# Query  (synchronous — typically fast)
# --------------------------------------------------------------------------- #

@app.post("/query")
async def query_endpoints(request: QueryRequest) -> List[Dict[str, Any]]:
    """
    Semantic + keyword search over stored endpoint documentation.

    Returns a ranked list of matching API endpoints.
    """
    pipeline = QueryPipeline()
    return pipeline.run(query=request.query)


# --------------------------------------------------------------------------- #
# Postprocessing (on-demand)
# --------------------------------------------------------------------------- #

@app.post("/cluster")
async def cluster_endpoints(request: ClusterRequest) -> Dict[str, Any]:
    """Group all stored endpoint docs by semantic similarity (K-means)."""
    pipeline = PostprocessingPipeline()
    clusters = pipeline.cluster(n_clusters=request.n_clusters)
    return {"clusters": {str(k): v for k, v in clusters.items()}}


@app.post("/example")
async def fetch_example(request: ExampleRequest) -> Dict[str, str]:
    """Generate fetch code examples (JS, Python, cURL) for a single endpoint."""
    pipeline = PostprocessingPipeline()
    return pipeline.fetch_example(swagger_data=request.swagger_data)


# --------------------------------------------------------------------------- #

if __name__ == "__main__":
    uvicorn.run("src.api.main:app", host="0.0.0.0", port=8000, reload=True)
