# DocGen-RAG

DocGen-RAG is an AI-powered tool designed to automatically generate comprehensive API documentation from source code using Retrieval-Augmented Generation (RAG). It leverages Haystack 2.0 and Weaviate to analyze codebases and produce structured documentation including Swagger specs collections, and usage examples.

## Features

- **Automated Documentation**: Generates REST API documentation from code.
- **RAG Pipeline**: Uses knowledge injection from framework documentation and codebase indexing.
- **Multi-Source Support**: Processes both local directories and Git repositories.
- **Output Formats**: Generates Swagger/OpenAPI JSON Collections, and usage examples.
- **Project Management**: Managed with `uv` for fast, reliable dependency management.

## Prerequisites

- **Python**: 3.8+
- **Weaviate**: A running Weaviate instance (local or cloud).
- **OpenAI API Key**: (Optional) For generation capabilities if using OpenAI models.

## Installation

1.  **Clone the repository**:
    ```bash
    git clone https://github.com/your-repo/DocGen-RAG.git
    cd DocGen-RAG
    ```

2.  **Create and activate a virtual environment**:
    ```bash
    python -m venv rag_venv
    source rag_venv/bin/activate  # On Windows: rag_venv\Scripts\activate
    ```

3.  **Install dependencies**:
    ```bash
    pip install . --use-feature=in-tree-build
    ```

## Configuration

Configuration is managed via `settings.yml` and environment variables.

### `settings.yml`
Adjust RAG pipeline settings such as retrieval thresholds and model choices:
```yaml
rag:
  embedding_model: "sentence-transformers/all-MiniLM-L6-v2"
  top_k_retriever: 10
  top_k_reranker: 5
  chunk_size: 50
```

### Environment Variables
Set the following environment variables (e.g., in a `.env` file or export them):

- `WEAVIATE_URL`: URL to your Weaviate instance.
- `WEAVIATE_API_KEY`: (If authentication is enabled).
- `OPENAI_API_KEY`: Required for the generator component if using OpenAI.

## Usage

1.  **Start the Server**:
    ```bash
    uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload
    ```

2.  **Trigger Generation**:
    Send a `POST` request to `/generate`:

    **Endpoint**: `http://localhost:8000/generate`

    **Body (Local)**:
    ```json
    {
        "source_type": "local",
        "path": "/absolute/path/to/project"
    }
    ```

    **Body (Git)**:
    ```json
    {
        "source_type": "git",
        "path": "https://github.com/username/repo.git",
        "credentials": "optional_token"
    }
    ```

3.  **Check Output**:
    Documentation artifacts will be generated in `output/<timestamp>/`.

## Project Structure

- `src/api`: FastAPI application entry point.
- `src/core`: Configuration and security settings.
- `src/pipelines`: Haystack RAG pipelines for indexing and generation.
- `src/services`: Core logic for input handling, framework detection, and document generation.
- `settings.yml`: Configuration file.

## Current RAG System Chart
```mermaid
graph TD

    %% Compare
    HE{"Hash Exists!"}
    
    %% Stop
    SFF{{"Stop for this file!"}}

    %% Input Sources
    Input1(["Local Codebase Folder"])
    Input2(["GitHub Repo URL"])

    SH["Source Handler"]
    
    %% Processing
    FH("File Hasher")
    SQLL[("Simple SQL DATABASE")]
    DS[("Vectorization Weaviate Storage")]
    EGM["Endpoint Graph Manager"]
    FA["File Analyzer"]
    EGR["Endpoint Documentation Generator"]
    DM["Documentation Merger"]

    Output("Documentation as Json Output")

    %% ==========================================
    %% 1. PRIMARY DOWNWARD FLOW 
    %% (Defining this first forces a clean vertical hierarchy)
    %% ==========================================
    Input1 --> SH
    Input2 --> SH
    SH --> FH
    FH -- Compare with Key/Value Store --> SQLL
    SQLL --> HE
    HE -- NO --> FA
    FA -- Update Graph and Indicate changes for each endpoint --> EGM
    EGM --> EGR
    EGR --> DM
    DM --> Output

    %% ==========================================
    %% 2. SIDE BRANCHES
    %% ==========================================
    HE -- Yes --> SFF
    FA -- Save Code chunks --> DS
    DS --> EGR

    %% ==========================================
    %% 3. LOOPBACKS (Extended Links)
    %% (Using ---> prevents the layout from tangling)
    %% ==========================================
    EGR -- Save documentation info (vectorized) ---> DS
    EGM -- Save Graphs ---> SQLL

    %% ==========================================
    %% STYLES
    %% ==========================================
    %% Inputs: Deep Navy/Slate
    style Input1 fill:#2c3e50,stroke:#5dade2,stroke-width:2px,color:#fff
    style Input2 fill:#2c3e50,stroke:#5dade2,stroke-width:2px,color:#fff
    style SH     fill:#34495e,stroke:#5dade2,stroke-width:1px,color:#fff

    %% Logic/Analyzers: Sage/Forest
    style FA     fill:#2d5a27,stroke:#a9dfbf,stroke-width:1px,color:#fff

    %% Decisions: Muted Amber/Gold
    style HE     fill:#7d6608,stroke:#f1c40f,stroke-width:2px,color:#fff

    %% Processing/Management: Deep Purple/Indigo
    style FH     fill:#4a235a,stroke:#a569bd,stroke-width:1px,color:#fff
    style EGM    fill:#4a235a,stroke:#a569bd,stroke-width:1px,color:#fff
    style EGR    fill:#4a235a,stroke:#a569bd,stroke-width:1px,color:#fff
    style DM     fill:#4a235a,stroke:#a569bd,stroke-width:1px,color:#fff

    %% Storage: Dark Navy
    style SQLL   fill:#1b2631,stroke:#5dade2,stroke-width:2px,color:#fff
    style DS     fill:#1b2631,stroke:#5dade2,stroke-width:2px,color:#fff

    %% Errors & Stops: Muted Crimson
    style SFF    fill:#641e16,stroke:#ec7063,stroke-width:2px,color:#fff

    %% Outputs: Deep Teal
    style Output fill:#0e6251,stroke:#1abc9c,stroke-width:2px,color:#fff
```
