import phoenix as px
import time

if __name__ == "__main__":
    # Launch Phoenix
    import os
    os.environ["PHOENIX_HOST"] = "0.0.0.0"
    os.environ["PHOENIX_PORT"] = "6006"
    session = px.launch_app()
    print(f"Phoenix UI is running at: {session.url}")
    print("Press Ctrl+C to exit.")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Stopping Phoenix...")
