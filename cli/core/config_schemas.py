"""
Config schemas for DocGen CLI.
Contains definitions of required settings and their dynamic prompting configurations.
"""

REQUIRED_SETTINGS_CONFIG = {
    "active_provider": {
        "type": "select",
        "message": "Select active AI provider:",
        "choices": ["gemini", "openai", "ollama"],
        "error_message": "AI provider is required to continue.",
    },
    "rag.active_embedder": {
        "type": "select",
        "message": lambda settings: f"Select RAG active embedder (current provider is {getattr(settings, 'active_provider', 'gemini')}):",
        "choices": ["gemini", "openai", "ollama"],
        "error_message": "Active embedder is required to continue.",
    },
    "rag.embedding_model": {
        "type": "text",
        "message": "Enter RAG embedding model name:",
        "default": lambda settings: (
            "text-embedding-3-small" if getattr(getattr(settings, "rag", None), "active_embedder", "gemini") == "openai"
            else "nomic-embed-text" if getattr(getattr(settings, "rag", None), "active_embedder", "gemini") == "ollama"
            else "gemini-2.5-flash-lite"
        ),
        "error_message": "Embedding model name is required to continue.",
    }
}
