import subprocess
import sys
import os
import time

try:
    import psutil
except ImportError:
    subprocess.run([sys.executable, "-m", "pip", "install", "psutil"], check=True)
    import psutil

PORT = 9922
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PID_FILE = os.path.join(_project_root, ".rpa_service.pid")
LISTENER_PID_FILE = os.path.join(os.path.expanduser("~"), ".yoko", "ws_listener.pid")


def kill_by_pid_file():
    if not os.path.exists(PID_FILE):
        return False
    stopped = False
    try:
        with open(PID_FILE, 'r') as f:
            pid = int(f.read().strip())
        print(f"Found PID file, killing service process (PID: {pid})...")
        result = subprocess.run(f"taskkill /F /T /PID {pid}", shell=True, capture_output=True)
        stopped = result.returncode == 0
    except Exception as e:
        print(f"PID file kill failed: {e}")
    finally:
        try:
            os.remove(PID_FILE)
        except Exception:
            pass
    return stopped


def kill_by_port():
    stopped = False
    for proc in psutil.process_iter(['pid', 'name']):
        try:
            for conn in proc.net_connections():
                if getattr(conn, 'status', '') == 'LISTEN' and getattr(conn.laddr, 'port', -1) == PORT:
                    print(f"Killing process {proc.info['name']} (PID: {proc.info['pid']}) on port {PORT}...")
                    result = subprocess.run(f"taskkill /F /T /PID {proc.info['pid']}", shell=True, capture_output=True)
                    if result.returncode != 0:
                        print(f"  taskkill failed (Access Denied?): {result.stderr.decode(errors='ignore').strip()}")
                    else:
                        stopped = True
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    return stopped


def stop_ws_listener():
    """Stop the WebSocket listener process via its PID file."""
    if not os.path.exists(LISTENER_PID_FILE):
        return
    try:
        with open(LISTENER_PID_FILE) as f:
            pid = int(f.read().strip())
        print(f"Stopping WebSocket listener (PID: {pid})...")
        subprocess.run(f"taskkill /F /T /PID {pid}", shell=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception as e:
        print(f"Listener stop skipped: {e}")
    finally:
        try:
            os.remove(LISTENER_PID_FILE)
        except Exception:
            pass


def stop_service():
    print("Stopping WeChat RPA service...")
    stop_ws_listener()
    stopped_pid = kill_by_pid_file()
    stopped_port = kill_by_port()

    if stopped_pid or stopped_port:
        print("RPA service stopped successfully.")
    else:
        print("No running RPA service found on port 9922.")

    time.sleep(1)


if __name__ == "__main__":
    stop_service()
    print("Done.")
