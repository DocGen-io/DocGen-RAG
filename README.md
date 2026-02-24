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
    SL{"Is Supported Language!"}
    SF{"Is Supported Framework!"}
    HE{"Hash Exists!"}
    
    %% Stop
    SFF{{"Stop for this file!"}}
   %% Stop(["Error: Not a REST API"])


    %% Error
    Error(["Stop & Log Error"])


    %%  Input Sources
    Input1(["Local Codebase Folder"])
    Input2(["GitHub Repo URL"])

    SH["Source Handler"]
    %% 2-3. Processing
    LF["Language Finder"]
    FD["Framework Detector (Using AST Queries)"]
    DF("Dependency Finder")
    FH("File Hasher")
    DS[(" Vectorization Weaviate Storage")]
    AST["AST Extractor"]
    CM["Code Mapper"]
    EGR["Endpoint Documentation Generator"]
    DM["Documentation Merger"]


    Output("Docuemntation as Json Output")

 
    
   


    %% Connections
    Input1 --> SH
    Input2 --> SH
    SH --> LF
    LF --> SL
    SL -- No --> Error
    SL -- Yes --> FD
    FD --> SF
    SF -- No --> Error
    SF -- Yes --> DF
    DF -- List OF Deps --> FH
    FH -- Compare With Store --> DS
    DS --> HE
    HE -- Yes --> SFF
    HE -- NO --> AST
    AST -- To be mapped --> CM
    AST -- To be saved --> DS
    CM -- Map --> DS
    DS -- Get Saved Map --> CM
    DS --> EGR
    EGR --> DM
    DM --> Output


      
  %% Inputs: Deep Navy/Slate
  style Input1 fill:#2c3e50,stroke:#5dade2,stroke-width:2px,color:#fff
  style Input2 fill:#2c3e50,stroke:#5dade2,stroke-width:2px,color:#fff
  style SH     fill:#34495e,stroke:#5dade2,stroke-width:1px,color:#fff

  %% Logic/Analyzers: Sage/Forest
  style LF     fill:#2d5a27,stroke:#a9dfbf,stroke-width:1px,color:#fff
  style FD     fill:#2d5a27,stroke:#a9dfbf,stroke-width:1px,color:#fff
  style DF     fill:#2d5a27,stroke:#a9dfbf,stroke-width:1px,color:#fff
  style AST    fill:#2d5a27,stroke:#a9dfbf,stroke-width:1px,color:#fff
  style CM     fill:#2d5a27,stroke:#a9dfbf,stroke-width:1px,color:#fff

  %% Decisions: Muted Amber/Gold (High visibility for logic gates)
  style SL     fill:#7d6608,stroke:#f1c40f,stroke-width:2px,color:#fff
  style SF     fill:#7d6608,stroke:#f1c40f,stroke-width:2px,color:#fff
  style HE     fill:#7d6608,stroke:#f1c40f,stroke-width:2px,color:#fff

  %% Processing/Storage: Deep Purple/Indigo
  style FH     fill:#4a235a,stroke:#a569bd,stroke-width:1px,color:#fff
  style DS     fill:#1b2631,stroke:#5dade2,stroke-width:2px,color:#fff
  style EGR    fill:#4a235a,stroke:#a569bd,stroke-width:1px,color:#fff
  style DM     fill:#4a235a,stroke:#a569bd,stroke-width:1px,color:#fff

  %% Errors & Stops: Muted Crimson
  style SFF    fill:#641e16,stroke:#ec7063,stroke-width:2px,color:#fff
  style Error  fill:#641e16,stroke:#ec7063,stroke-width:2px,color:#fff

 style Output fill:#0e6251,stroke:#1abc9c,stroke-width:2px,color:#fff
    
    
  



```
