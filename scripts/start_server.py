import subprocess
import sys
import os
import time
import requests
import psutil
import socket

PORT = 9922
API_KEY = "yoko_test" # Fixed key for local agent API access

def kill_process_on_port(port):
    """Find and kill the process listening on the specified port."""
    for proc in psutil.process_iter(['pid', 'name', 'connections']):
        try:
            for conn in proc.info.get('connections', []) or []:
                if getattr(conn, 'status', '') == 'LISTEN' and getattr(conn.laddr, 'port', -1) == port:
                    print(f"Killing orphan process {proc.info['name']} (PID: {proc.info['pid']}) on port {port}")
                    # On Windows, taskkill /F /T is more reliable to kill process trees
                    subprocess.run(f"taskkill /F /T /PID {proc.info['pid']}", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass

def cleanup_old_processes():
    """Clean up any existing service.exe or server.py processes."""
    print("Cleaning up old processes...")
    kill_process_on_port(PORT)
    
    # Removed dangerous 'taskkill /IM service.exe' because it kills Trae/IDE background services!
    
    # Give OS a moment to release ports and file handles
    time.sleep(2)

def start_service():
    """Start the RPA backend service."""
    cleanup_old_processes()
    
    print("Starting RPA Backend Server...")
    
    # We assume this script is in `scripts/`, so project root is one level up.
    # Adjust as needed if it's placed differently in the standalone skill repo.
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # Common locations for the executable or script
    service_exe = os.path.join(project_root, "service.exe")
    dist_exe = os.path.join(project_root, "dist", "service.exe")
    main_py = os.path.join(project_root, "server.py")
    alt_main_py = os.path.join(project_root, "main.py")
    
    process = None
    env = os.environ.copy()
    env["WEBOT_BACKEND_MODE"] = "1"
    
    # DETACHED_PROCESS = 0x00000008, prevents child from attaching to console and blocking Agent
    flags = 0x00000008 if sys.platform == "win32" else 0
    
    if os.path.exists(service_exe):
        print(f"Found built executable: {service_exe}")
        process = subprocess.Popen([service_exe, "--no-ui"], cwd=project_root, env=env, creationflags=flags, close_fds=True)
    elif os.path.exists(dist_exe):
        print(f"Found built executable: {dist_exe}")
        process = subprocess.Popen([dist_exe, "--no-ui"], cwd=project_root, env=env, creationflags=flags, close_fds=True)
    elif os.path.exists(main_py):
        print(f"Found source file: {main_py}")
        process = subprocess.Popen([sys.executable, main_py, "--no-ui"], cwd=project_root, env=env, creationflags=flags, close_fds=True)
    elif os.path.exists(alt_main_py):
        print(f"Found source file: {alt_main_py}")
        process = subprocess.Popen([sys.executable, alt_main_py, "--no-ui"], cwd=project_root, env=env, creationflags=flags, close_fds=True)
    else:
        print(f"Error: Could not find service.exe or server.py in {project_root}")
        print("Please ensure you have downloaded the release or cloned the repository correctly.")
        sys.exit(1)
        
    print(f"Server started with PID: {process.pid}")
    return process

def wait_for_health_check():
    """Wait until the service responds to the health check."""
    max_retries = 30
    for i in range(max_retries):
        try:
            # The service might return 401/403 if it requires auth, but that means it's up.
            response = requests.head(f"http://127.0.0.1:{PORT}/docs", timeout=2)
            print("RPA Server is successfully running and ready to accept requests.")
            return True
        except requests.exceptions.ConnectionError:
            pass
            
        print(f"Waiting for server to start... ({i+1}/{max_retries})")
        time.sleep(1)
        
    print("Error: Server process started, but health check failed after 30 seconds.")
    return False

def initialize_rpa():
    """Call the initialization API to check status and bind WeChat."""
    print("Checking RPA status and initializing WeChat binding...")
    headers = {
        "Content-Type": "application/json",
        "X-API-Key": API_KEY
    }
    try:
        response = requests.post(f"http://127.0.0.1:{PORT}/api/init/multi", headers=headers, json={"timestamp": int(time.time() * 1000)}, timeout=10)
        if response.status_code == 200:
            result = response.json()
            if result.get("code") == "ENV_NOT_CONFIGURED":
                print("\n" + "!"*50)
                print("CRITICAL: WeChat environment is NOT configured!")
                print("The Agent MUST immediately call POST /api/system/wechat41/auto_config to fix this automatically.")
                print("(Note: This will kill and restart WeChat).")
                print("After calling auto_config, the Agent MUST call POST /api/init/multi again.")
                print("!"*50 + "\n")
            else:
                print("Initialization successful:", result)
            return True
        elif response.status_code in [401, 403]:
            print("Notice: The software needs to be activated or is missing auth tokens.")
            print("The Agent can activate the software by calling /api/license/activate with an Activation Code.")
            return False
        else:
            print(f"Initialization failed with status {response.status_code}: {response.text}")
            return False
    except Exception as e:
        print(f"Failed to call initialization API: {e}")
        return False

if __name__ == "__main__":
    # Ensure psutil and requests are installed
    try:
        import psutil
        import requests
    except ImportError:
        print("Installing required dependencies (psutil, requests)...")
        subprocess.run([sys.executable, "-m", "pip", "install", "psutil", "requests"], check=True)
        import psutil
        import requests

    process = start_service()
    if wait_for_health_check():
        initialize_rpa()
        print("\n" + "="*50)
        print("RPA Service is now RUNNING in the background.")
        print(f"Agent API Endpoint: http://127.0.0.1:{PORT}")
        print("Frontend UI: http://127.0.0.1:9922/")
        print("="*50 + "\n")
        print("You can now instruct the user to open the Frontend UI in their browser to complete login or configuration.")
        
        # Keep the script running so the agent knows it's active, 
        # or we can exit and leave the service running in the background.
        # Leaving it running in background is better for agents.
        sys.exit(0)
    else:
        if process:
            process.kill()
        sys.exit(1)
