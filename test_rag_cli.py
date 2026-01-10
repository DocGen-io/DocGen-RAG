import os
import sys

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__)))

def load_env(env_path=".env"):
    """
    Manually load .env file since python-dotenv might not be installed.
    """
    if not os.path.exists(env_path):
        return

    print(f"Loading environment from {env_path}...")
    with open(env_path, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, value = line.split("=", 1)
                # Remove quotes if present
                if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
                    value = value[1:-1]
                os.environ[key] = value

if __name__ == "__main__":
    print("Initializing RAG System CLI Test...")
    
    # Load environment variables
    load_env()

    # Check for crucial keys
    if not os.getenv("GOOGLE_API_KEY"):
        print("ERROR: GOOGLE_API_KEY is not set in environment or .env file.")
        print("Please check your .env file.")
        # We allow continuing to see if it gracefully fails or if user uses another provider, 
        # but the request specifically mentioned checking the API key.
    
    try:
        from src.pipelines.rag import RAGService
        
        print("Initializing RAG Service...")
        rag_service = RAGService()
        
        query = "What is the purpose of this project?"
        print(f"\nTest Query: {query}")
        print("Generating answer... (this may take a moment)")
        
        answer = rag_service.search_and_generate(query)
        
        print("\n=== Generated Answer ===")
        print(answer)
        print("========================")
        print("\nSuccess! RAG pipeline is working.")
        
    except Exception as e:
        print(f"\nAn error occurred: {e}")
        import traceback
        traceback.print_exc()
