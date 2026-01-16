import os
from src.utils.logging import configure_logging

configure_logging()
from typing import List, Dict, Optional
import phoenix as px
from openinference.instrumentation.haystack import HaystackInstrumentor

from haystack import Pipeline
from haystack.components.embedders import SentenceTransformersDocumentEmbedder, SentenceTransformersTextEmbedder

from src.components.ASTOutputChunker import ASTOutputChunker

from haystack.components.writers import DocumentWriter
from haystack.components.retrievers.in_memory import InMemoryEmbeddingRetriever
from haystack.components.rankers import SentenceTransformersSimilarityRanker
from haystack.components.builders import PromptBuilder
from haystack.utils import ComponentDevice
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

    def indexing_pipeline(self, ast_data: List[dict]):
        """
        Creates and runs the indexing pipeline.
        """
        pipeline = Pipeline()
        
        # Components
        splitter = ASTOutputChunker()
        embedder = SentenceTransformersDocumentEmbedder(model=self.embedding_model)
        writer = DocumentWriter(document_store=self.document_store)
        
        # Connections
        pipeline.add_component("splitter", splitter)
        pipeline.add_component("embedder", embedder)
        pipeline.add_component("writer", writer)
        
        pipeline.connect("splitter", "embedder")
        pipeline.connect("embedder", "writer")
        
        # Run
        pipeline.run({"splitter": {"ast_data_list": ast_data}})

    def search_and_generate(self, query: str) -> str:
        """
        Retrieval and Generation Pipeline.
        """
        pipeline = Pipeline()
        
        # Components
        text_embedder = SentenceTransformersTextEmbedder(model=self.embedding_model)
        retriever = WeaviateEmbeddingRetriever(document_store=self.document_store, top_k=settings.get("rag.top_k_retriever", 10))
        reranker = SentenceTransformersSimilarityRanker(
            model="cross-encoder/ms-marco-MiniLM-L-6-v2",
            top_k=5,
            device=ComponentDevice.from_str("cuda") 
        )
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
        prompt_builder = PromptBuilder(template=prompt_template,required_variables=['documents','query'])
        
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
