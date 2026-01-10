import os
import shutil
from typing import List, Dict, Any, Optional
from haystack import Pipeline
from haystack.components.preprocessors import DocumentSplitter, DocumentCleaner
from haystack.components.embedders import SentenceTransformersDocumentEmbedder, SentenceTransformersTextEmbedder
from haystack.components.writers import DocumentWriter
from haystack.components.retrievers.in_memory import InMemoryEmbeddingRetriever
from haystack.components.rankers import TransformersSimilarityRanker
from haystack_integrations.components.generators.google_ai import GoogleAIGeminiGenerator
from haystack.components.builders import PromptBuilder
from haystack.document_stores.in_memory import InMemoryDocumentStore
from haystack.dataclasses import Document
from haystack_integrations.document_stores.weaviate import WeaviateDocumentStore
from haystack_integrations.components.retrievers.weaviate import WeaviateEmbeddingRetriever

from src.core.config import settings

class RAGService:
    def __init__(self):
        # Initialize Document Store
        # For production/this task, we use Weaviate. 
        # Using embedded URL or user provided URL.
        # headers = {}

        # # Add OpenAI if exists
        # if settings.GOOGLE_API_KEY:
        # headers["X-OpenAI-Api-Key"] = settings.GOOGLE_API_KEY

        # # Add Google Gemini/AI Studio if exists
        # if settings.GOOGLE_API_KEY:
        # headers["X-Goog-Studio-Api-Key"] = settings.GOOGLE_API_KEY

        # self.document_store = WeaviateDocumentStore(
        # url=settings.WEAVIATE_URL,
        # additional_headers=headers
        # )
        self.document_store = WeaviateDocumentStore(url=settings.WEAVIATE_URL, additional_headers={"X-Goog-Studio-Api-Key": settings.GOOGLE_API_KEY} if settings.GOOGLE_API_KEY else {})
        
        # Models
        self.embedding_model = settings.EMBEDDING_MODEL
        self.reranker_model = settings.RERANKER_MODEL

    def indexing_pipeline(self, documents: List[Document]):
        """
        Creates and runs the indexing pipeline.
        """
        pipeline = Pipeline()
        
        # Components
        cleaner = DocumentCleaner()
        splitter = DocumentSplitter(split_by="word", split_length=settings.get("rag.chunk_size", 50), split_overlap=10)
        embedder = SentenceTransformersDocumentEmbedder(model=self.embedding_model)
        writer = DocumentWriter(document_store=self.document_store)
        
        # Connections
        pipeline.add_component("cleaner", cleaner)
        pipeline.add_component("splitter", splitter)
        pipeline.add_component("embedder", embedder)
        pipeline.add_component("writer", writer)
        
        pipeline.connect("cleaner", "splitter")
        pipeline.connect("splitter", "embedder")
        pipeline.connect("embedder", "writer")
        
        # Run
        pipeline.run({"cleaner": {"documents": documents}})

    def search_and_generate(self, query: str, context_filters: Optional[Dict] = None) -> str:
        """
        Retrieval and Generation Pipeline.
        """
        pipeline = Pipeline()
        
        # Components
        text_embedder = SentenceTransformersTextEmbedder(model=self.embedding_model)
        retriever = WeaviateEmbeddingRetriever(document_store=self.document_store, top_k=settings.get("rag.top_k_retriever", 10))
        reranker = TransformersSimilarityRanker(model=self.reranker_model, top_k=settings.get("rag.top_k_reranker", 5))
        
        prompt_template = """
        You are an expert API documentation generator.
        Using the following context code snippets, strictly answer the query.
        
        Context:
        {% for doc in documents %}
            {{ doc.content }}
        {% endfor %}
        
        Query: {{ query }}
        
        Answer:
        """
        prompt_builder = PromptBuilder(template=prompt_template)
        
        # If OpenAI Key is present, use OpenAI, otherwise simple placeholder or user must provide
        if not settings.GOOGLE_API_KEY:
             # Fallback or error warning
             print("WARNING: No OpenAI API Key found. Generation might fail if using GoogleAIGeminiGenerator.")
        
        from haystack.utils import Secret
        generator = GoogleAIGeminiGenerator(api_key=Secret.from_token(os.getenv("GOOGLE_API_KEY")))

        # Connections
        pipeline.add_component("text_embedder", text_embedder)
        pipeline.add_component("retriever", retriever)
        pipeline.add_component("reranker", reranker)
        pipeline.add_component("prompt_builder", prompt_builder)
        pipeline.add_component("generator", generator)
        
        pipeline.connect("text_embedder.embedding", "retriever.query_embedding")
        pipeline.connect("retriever", "reranker")
        pipeline.connect("reranker", "prompt_builder.documents")
        pipeline.connect("prompt_builder", "generator")
        
        # Run
        result = pipeline.run({
            "text_embedder": {"text": query},
            "reranker": {"query": query},
            "prompt_builder": {"query": query}
        })

        return result["generator"]["replies"][0]

    def reset_knowledge_base(self):
        """
        Clears the document store (if policy allows).
        """
        # Logic to delete old documents
        pass

    def learn_framework(self, framework_name: str):
        """
        Searches for framework documentation and indexes it.
        """
        # Placeholder for the learning step
        # 1. Search web for framework docs
        # 2. Scrape/Fetch
        # 3. Index into Weaviate (maybe with metadata type='framework_knowledge')
        pass
