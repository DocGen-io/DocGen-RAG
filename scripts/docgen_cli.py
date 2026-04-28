#!/usr/bin/env python3
import os
import sys
import subprocess
import yaml

def print_onboarding():
    print("=====================================================")
    print(" Welcome to DocGen-RAG Interactive CLI")
    print("This tool generates rich API documentation automatically.")
    print("=====================================================\n")

def get_repo_dir():
    script_path = os.path.realpath(__file__)
    return os.path.dirname(os.path.dirname(script_path))

def configure_provider(config, repo_dir, init=False):
    print("\n--- Configuration Wizard ---")
    if init:
        print("Let's configure your AI Provider.")
    print("Options:")
    print("  1) default (Gemini with Vertex - Google Cloud)")
    print("  2) ollama (Local models)")
    
    choice = input("Select provider (1 for Gemini, 2 for Ollama) [1]: ").strip()
    provider = "ollama" if choice == "2" else "gemini"
    
    # Update config dict
    if "rag" not in config: config["rag"] = {}
    config["rag"]["active_embedder"] = provider

    if "code_analyzer" not in config: config["code_analyzer"] = {}
    config["code_analyzer"]["active_generator"] = provider

    if "doc_creator" not in config: config["doc_creator"] = {}
    config["doc_creator"]["active_generator"] = provider

    if "query_generator" not in config: config["query_generator"] = {}
    config["query_generator"]["active_generator"] = provider
    
    # Ensure verbose is set
    if "ast_extractor" not in config: config["ast_extractor"] = {}
    config["ast_extractor"]["verbose"] = True
    config["ast_extractor"]["save_ast"] = True

    config_path = os.path.join(repo_dir, "config.yaml")
    try:
        with open(config_path, "w") as f:
            yaml.dump(config, f, default_flow_style=False)
        print(f"Configuration updated! Active provider: {provider}")
    except Exception as e:
        print(f"Warning: Failed to write config.yaml: {e}")
    return config

def load_or_init_config(repo_dir):
    config_path = os.path.join(repo_dir, "config.yaml")
    config = {}
    if os.path.exists(config_path):
        with open(config_path, "r") as f:
            config = yaml.safe_load(f) or {}

    # If active_embedder is missing, we consider it unconfigured
    if "rag" not in config or "active_embedder" not in config["rag"]:
        config = configure_provider(config, repo_dir, init=True)
    else:
        # Just ensure verbose is true always on load
        if "ast_extractor" not in config: config["ast_extractor"] = {}
        config["ast_extractor"]["verbose"] = True
        config["ast_extractor"]["save_ast"] = True
        with open(config_path, "w") as f:
            yaml.dump(config, f, default_flow_style=False)

    return config

def start_external_services(repo_dir):
    try:
        if os.path.exists(os.path.join(repo_dir, "docker-compose.yaml")):
            print("Starting necessary background services (Weaviate) via Docker...")
            subprocess.run(["docker", "compose", "up", "-d"], cwd=repo_dir, check=True)
            print("Services are up and running!\n")
    except Exception as e:
        print(f"Could not start docker compose: {e}. Ensure Docker is running.")

def stop_external_services(repo_dir):
    try:
        if os.path.exists(os.path.join(repo_dir, "docker-compose.yaml")):
            print("\nShutting down Docker containers gracefully...")
            subprocess.run(["docker", "compose", "down"], cwd=repo_dir, check=False)
            print("Containers stopped.")
    except Exception as e:
        print(f"Warning: Could not stop docker containers gracefully: {e}")

def main():
    print_onboarding()
    repo_dir = get_repo_dir()
    
    # 1. Update/Setup config
    config = load_or_init_config(repo_dir)
    
    # 2. Start Services
    start_external_services(repo_dir)
    
    # 3. Interactive Loop
    try:
        while True:
            try:
                url = input("\nEnter a Git URL (or type 'config' to setup provider, 'exit' to quit): ").strip()
                if not url:
                    continue
                    
                if url.lower() in ("exit", "quit", "q"):
                    print("Exiting DocGen-RAG CLI. Goodbye!")
                    break
                    
                if url.lower() == "config":
                    config = configure_provider(config, repo_dir, init=False)
                    continue
                    
                print(f"\n Generating documentation for: {url}")
                
                # Using uv run
                run_cmd = ["uv", "run", "documentation-pipeline", "git", url]
                subprocess.run(run_cmd, cwd=repo_dir)
                
                print(f"\n Finished processing {url}. The output has been saved.")
                
            except KeyboardInterrupt:
                # Catch interrupt during a specific documentation run to just cancel that run
                print("\nOperation cancelled by user. Returning to prompt...")
                continue
            except Exception as e:
                print(f"\n Error: An error occurred: {e}")
                
    finally:
        # Guarantee docker shuts down when the script exits (normally or via Ctrl+C)
        stop_external_services(repo_dir)

if __name__ == "__main__":
    main()
