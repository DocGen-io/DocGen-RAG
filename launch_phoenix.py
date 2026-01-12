import phoenix as px
import time

if __name__ == "__main__":
    # Launch Phoenix
    session = px.launch_app(host="0.0.0.0", port=6006)
    print(f"Phoenix UI is running at: {session.url}")
    print("Press Ctrl+C to exit.")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Stopping Phoenix...")
