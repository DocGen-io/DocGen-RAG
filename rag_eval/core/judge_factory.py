"""
Factory to create Langchain LLM and Embedding judges for Ragas evaluations.
Uses Langchain classes natively to remove all custom Ragas or Haystack wrappers.
"""
from src.utils.config_loader import load_config, get_config_value
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_community.chat_models import ChatOllama
from langchain_community.embeddings import OllamaEmbeddings

class JudgeFactory:
    """Creates Langchain LLM + Embedding judges for Ragas evaluation."""

    @staticmethod
    def get_vertex_ai_judge(
        model: str = "gemini-2.5-flash-lite",
        embedding_model: str = "text-embedding-004",
    ):
        """Vertex AI judge using standard Langchain providers."""
        config = load_config("config.yaml")

        try:
            gemini_config = get_config_value(["generators", "gemini"], config)
            project = gemini_config.get("project_id")
            location = gemini_config.get("location")
          
        except Exception:
            raise Exception("Failed to load Vertex AI configuration")

        print(f"Initializing Langchain Vertex AI Judge: {model} / {embedding_model}")


        llm = ChatGoogleGenerativeAI(
            model=model, project=project, location=location, temperature=0.0
        )
        embeddings = GoogleGenerativeAIEmbeddings(
            model=embedding_model, project=project, location=location
        )

        return llm, embeddings

    @staticmethod
    def get_ollama_judge(
        model: str = "llama3",
        embedding_model: str = "nomic-embed-text",
    ):
        """Ollama local judge using standard Langchain providers."""
        config = load_config("config.yaml")
        try:
            ollama_config = get_config_value(["generators", "ollama"], config)
            base_url = ollama_config.get("url", "http://127.0.0.1:11434")
        except Exception:
            base_url = "http://127.0.0.1:11434"

        print(f"Initializing Langchain Ollama Judge: {model} / {embedding_model}")

     

        llm = ChatOllama(model=model, temperature=0.0, base_url=base_url)
        embeddings = OllamaEmbeddings(model=embedding_model, base_url=base_url)

        return llm, embeddings
