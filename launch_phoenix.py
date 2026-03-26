import phoenix as px
import time
import os
import signal
import sys
from src.utils.config_loader import load_config

def handle_shutdown(signum, frame):
    print(f"\nReceived signal {signum}. Shutting down Phoenix gracefully...")
    try:
        px.close_app()
    except Exception as e:
        print(f"Error during shutdown: {e}")
    sys.exit(0)

if __name__ == "__main__":
    # Register signal handlers for graceful shutdown (e.g. from scancel or Ctrl+C)
    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)

    # Load configuration for phoenix data directory
    try:
        config = load_config("config.yaml")
        phoenix_data_dir = config.get("phoenix_data_dir", "~/.phoenix_data")
    except Exception as e:
        print(f"Warning: Could not load config.yaml: {e}")
        phoenix_data_dir = "~/.phoenix_data"

    # Resolve the path properly
    phoenix_dir = os.path.abspath(os.path.expanduser(phoenix_data_dir))
    os.makedirs(phoenix_dir, exist_ok=True)
    os.environ["PHOENIX_WORKING_DIR"] = phoenix_dir
    os.environ["PHOENIX_HOST"] = "0.0.0.0"
    os.environ["PHOENIX_PORT"] = "6006"
    
    print(f"Starting Phoenix with persistent storage at: {phoenix_dir}")
    session = px.launch_app(use_temp_dir=False)
    
    print(f"Phoenix UI is running at: {session.url}")
    print("Press Ctrl+C or send SIGTERM to exit.")
    
    # Keep the main thread alive to catch signals
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        handle_shutdown(signal.SIGINT, None)
