import subprocess
import time
import requests
import sys
import os
import signal

def run_test():
    # Start the server
    print("Starting Uvicorn server...")
    # Determine project root (one level up from tests/)
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    server_process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "src.api.main:app", "--port", "8001"], 
        stdout=sys.stdout,
        stderr=sys.stderr, 
        preexec_fn=os.setsid,
        cwd=project_root # Ensure running from project root
    )
    
    base_url = "http://127.0.0.1:8001"
    
    # Wait for server to start with retry
    print("[Client] Waiting for server to be ready...")
    for _ in range(30):
        try:
            requests.get(f"{base_url}/docs")
            print("Server is ready.")
            break
        except requests.exceptions.ConnectionError:
            time.sleep(1)
    else:
        print("FAILED: Server did not start in 30 seconds.")
        # Kill and exit
        try:
            os.killpg(os.getpgid(server_process.pid), signal.SIGTERM)
        except:
             server_process.kill()
        return

    try:
        # 1. Trigger Generation
        print("\n[Client] Triggering generation...")
        payload = {
            "source_type": "git",
            "path": "https://github.com/AliSaleemHasan/computer_science_sze" 
        }
        resp = requests.post(f"{base_url}/generate", json=payload)
        
        if resp.status_code != 200:
            print(f"FAILED: /generate returned {resp.status_code}")
            print(resp.text)
            return
            
        data = resp.json()
        job_id = data.get("job_id")
        print(f"[Client] Job started. ID: {job_id}")
        
        if not job_id:
            print("FAILED: No job_id received")
            return

        # 2. Poll Status
        print("[Client] Polling status...")
        for _ in range(10): # Poll for 10 seconds max
            status_resp = requests.get(f"{base_url}/status/{job_id}")
            status_data = status_resp.json()
            status = status_data.get("status")
            print(f"Status: {status}")
            
            if status == "completed":
                print("\nSUCCESS: Job completed!")
                print("Result:", status_data)
                break
            elif status == "failed":
                print("\nFAILED: Job reported failure.")
                print("Error:", status_data)
                break
            
            time.sleep(1)
        else:
            print("\nTIMEOUT: Job did not complete in time.")

    except Exception as e:
        print(f"\nEXCEPTION: {e}")
    finally:
        # Kill the server
        print("\nStopping server...")
        try:
            os.killpg(os.getpgid(server_process.pid), signal.SIGTERM)
        except:
             server_process.kill()
        print("Server stopped.")

if __name__ == "__main__":
    run_test()
