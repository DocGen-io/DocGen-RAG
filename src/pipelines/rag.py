import os
from typing import List, Dict, Optional
import phoenix as px
from openinference.instrumentation.haystack import HaystackInstrumentor

from haystack import Pipeline
from haystack.components.preprocessors import DocumentSplitter, DocumentCleaner
from haystack.components.embedders import SentenceTransformersDocumentEmbedder, SentenceTransformersTextEmbedder
from haystack.components.writers import DocumentWriter
from haystack.components.retrievers.in_memory import InMemoryEmbeddingRetriever
from haystack.components.rankers import TransformersSimilarityRanker
from haystack.components.builders import PromptBuilder
from haystack.document_stores.in_memory import InMemoryDocumentStore
from haystack.dataclasses import Document
from haystack_integrations.document_stores.weaviate import WeaviateDocumentStore
from haystack_integrations.components.retrievers.weaviate import WeaviateEmbeddingRetriever

from src.core.config import settings
from src.pipelines.llm_factory import LLMFactory

class RAGService:
    _instrumented = False

    def __init__(self):
        # Phoenix Tracing Setup
        if settings.PHOENIX_ENABLED and not RAGService._instrumented:
            try:
                px.launch_app()
                HaystackInstrumentor().instrument()
                RAGService._instrumented = True
                print("Phoenix tracing enabled and instrumented.")
            except Exception as e:
                print(f"Failed to launch Phoenix: {e}")

        # Initialize Document Store
        # Weaviate configuration
        headers = {}
        if settings.GOOGLE_API_KEY:
             headers["X-Goog-Studio-Api-Key"] = settings.GOOGLE_API_KEY
        
        self.document_store = WeaviateDocumentStore(
            url=settings.WEAVIATE_URL, 
            additional_headers=headers
        )
        
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
        splitter = DocumentSplitter(split_by="word", split_length=settings.get("rag.chunk_size", 500), split_overlap=50)
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

    def search_and_generate(self, query: str) -> str:
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
        
        # Generator from Factory
        generator = LLMFactory.get_generator(settings.LLM_TYPE)

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
        pass
