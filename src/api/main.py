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

@app.post("/generate")
async def trigger_generation(request: GenerateRequest, background_tasks: BackgroundTasks):
    """
    Triggers the documentation process in the background.
    """
    background_tasks.add_task(process_documentation, request.source_type, request.path, request.credentials)
    return {"status": "Processing started", "message": "Documentation is being generated in the background."}

def process_documentation(source_type: str, path: str, credentials: Optional[str]):
    print(f"Starting processing for {path}")
    input_handler = InputHandler()
    working_dir = None
    
    try:
        # 1. Input Handling
        if source_type == "git":
            working_dir = input_handler.process_git_repo(path, credentials)
        elif source_type == "local":
            working_dir = input_handler.process_local_folder(path)
        else:
            print("Invalid source type")
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
            ast_data = process_directory(working_dir)
            
            if ast_data:
                print(f"Indexing {len(ast_data)} files into RAG...")
                rag.indexing_pipeline(ast_data)
            else:
                print("No suitable files found for AST extraction.")

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

    except Exception as e:
        print(f"Error during processing: {e}")
    finally:
        input_handler.cleanup()

if __name__ == "__main__":
    uvicorn.run("src.api.main:app", host="0.0.0.0", port=8000, reload=True)
