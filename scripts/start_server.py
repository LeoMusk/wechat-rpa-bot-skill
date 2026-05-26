import subprocess
import sys
import os
import time
import requests
import psutil
import socket

PORT = 9922
API_KEY = "yoko_test" # Fixed key for local agent API access

# PID file path at project root to track the running service process
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PID_FILE = os.path.join(_project_root, ".rpa_service.pid")

def kill_process_on_port(port):
    """Find and kill the process listening on the specified port."""
    for proc in psutil.process_iter(['pid', 'name']):
        try:
            for conn in proc.net_connections():
                if getattr(conn, 'status', '') == 'LISTEN' and getattr(conn.laddr, 'port', -1) == port:
                    print(f"Killing orphan process {proc.info['name']} (PID: {proc.info['pid']}) on port {port}")
                    subprocess.run(f"taskkill /F /T /PID {proc.info['pid']}", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass

def kill_by_pid_file():
    """Kill the previously recorded service process via PID file."""
    if not os.path.exists(PID_FILE):
        return
    try:
        with open(PID_FILE, 'r') as f:
            pid = int(f.read().strip())
        print(f"Found PID file, killing previous service process (PID: {pid})...")
        subprocess.run(f"taskkill /F /T /PID {pid}", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception as e:
        print(f"PID file cleanup skipped: {e}")
    finally:
        try:
            os.remove(PID_FILE)
        except Exception:
            pass

def save_pid_file(pid):
    """Save the service process PID for later cleanup."""
    try:
        with open(PID_FILE, 'w') as f:
            f.write(str(pid))
    except Exception as e:
        print(f"Warning: could not write PID file: {e}")

def cleanup_old_processes():
    """Clean up any existing service processes before starting a new one."""
    print("Cleaning up old processes...")
    # Step 1: try PID file (most precise, avoids killing unrelated service.exe)
    kill_by_pid_file()
    # Step 2: scan port 9922 for any surviving process
    kill_process_on_port(PORT)
    # Give OS a moment to release ports and file handles
    time.sleep(2)

def _find_service_exe(project_root):
    """
    定位 service.exe 的位置。v1.7.9+ 用 PyInstaller onedir 模式，
    service.exe 必须和 _internal/ 同级才能跑起来。

    检查顺序(从最常见到不常见):
      1. <root>/service.exe + <root>/_internal/                  ← release zip 直接解压到根
      2. <root>/service/service.exe + <root>/service/_internal/  ← zip 解压保留子目录
      3. <root>/dist/service/service.exe + .../_internal/        ← 本地 build_backend.py 直接产物
      4. <root>/dist/service.exe                                  ← legacy 兼容(单文件 onefile)
      5. <root>/service.exe (无 _internal)                        ← legacy 兼容(单文件 onefile)

    返回:(exe_path, 是否 onedir 且 _internal 齐全) — 找不到则 (None, False)
    """
    candidates = [
        (os.path.join(project_root, "service.exe"),
         os.path.join(project_root, "_internal")),
        (os.path.join(project_root, "service", "service.exe"),
         os.path.join(project_root, "service", "_internal")),
        (os.path.join(project_root, "dist", "service", "service.exe"),
         os.path.join(project_root, "dist", "service", "_internal")),
        # 以下两个是 legacy onefile,_internal 不存在但 exe 可独立跑
        (os.path.join(project_root, "dist", "service.exe"), None),
        (os.path.join(project_root, "service.exe"), None),  # 已在 1 覆盖,但保留以防 _internal 缺失
    ]
    seen = set()
    for exe, internal in candidates:
        if exe in seen:
            continue
        seen.add(exe)
        if not os.path.exists(exe):
            continue
        if internal is None:
            # legacy onefile 路径,直接返回
            return exe, False
        if os.path.isdir(internal):
            # onedir 完整产物
            return exe, True
        # exe 存在但 _internal 缺失 — 用户可能下错了/没解压完整
        print(f"⚠️  Found {exe} but adjacent _internal/ is missing — "
              f"the new packaging is onedir; both must coexist. Skipping this candidate.")
    return None, False


def start_service():
    """Start the RPA backend service."""
    cleanup_old_processes()

    print("Starting RPA Backend Server...")

    # We assume this script is in `scripts/`, so project root is one level up.
    # Adjust as needed if it's placed differently in the standalone skill repo.
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    # Locate the executable (v1.7.9+ onedir 模式 优先;legacy onefile 兼容)
    service_exe, is_onedir = _find_service_exe(project_root)
    main_py = os.path.join(project_root, "server.py")
    alt_main_py = os.path.join(project_root, "main.py")

    process = None
    env = os.environ.copy()
    env["WEBOT_BACKEND_MODE"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    env["VITE_CHANNEL_ID"] = "agent_generic"
    env["YOKO_CHANNEL_ID"] = "agent_generic"
    # CRITICAL: Force the underlying webot backend to run in completely headless mode
    # bypassing any internal GUI creation logic
    env["HEADLESS_MODE"] = "1"
    env["DISABLE_WEBVIEW"] = "1"
    
    # CRITICAL: Prevent the backend from automatically opening the default browser
    # We want the agent to control when and how the UI is opened.
    env["NO_BROWSER"] = "1"
    env["AUTO_OPEN_BROWSER"] = "0"
    
    # DETACHED_PROCESS = 0x00000008, prevents child from attaching to console and blocking Agent
    flags = 0x00000008 if sys.platform == "win32" else 0
    
    startupinfo = None
    if sys.platform == "win32":
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = subprocess.SW_HIDE
    
    if service_exe is not None:
        # exe 的 cwd 必须是它自己所在目录，否则 onedir 模式找不到 _internal/
        exe_cwd = os.path.dirname(service_exe)
        mode_label = "onedir" if is_onedir else "onefile"
        print(f"Found built executable ({mode_label}): {service_exe}")
        process = subprocess.Popen(
            [service_exe, "--no-ui", "--channel-id", "agent_generic"],
            cwd=exe_cwd, env=env,
            creationflags=flags, startupinfo=startupinfo, close_fds=True,
        )
    elif os.path.exists(main_py):
        print(f"Found source file: {main_py}")
        process = subprocess.Popen([sys.executable, main_py, "--no-ui", "--channel-id", "agent_generic"], cwd=project_root, env=env, creationflags=flags, startupinfo=startupinfo, close_fds=True)
    elif os.path.exists(alt_main_py):
        print(f"Found source file: {alt_main_py}")
        process = subprocess.Popen([sys.executable, alt_main_py, "--no-ui", "--channel-id", "agent_generic"], cwd=project_root, env=env, creationflags=flags, startupinfo=startupinfo, close_fds=True)
    else:
        print(f"Error: Could not find service.exe or server.py in {project_root}")
        print("v1.7.9+ 用 PyInstaller onedir 模式打包, 期望以下任一布局:")
        print(f"  1. {os.path.join(project_root, 'service.exe')} + {os.path.join(project_root, '_internal/')}")
        print(f"  2. {os.path.join(project_root, 'service', 'service.exe')} + {os.path.join(project_root, 'service', '_internal/')}")
        print("请确认下载的 zip 包已正确解压(service.exe 和 _internal/ 必须同级)。")
        sys.exit(1)
        
    print(f"Server started with PID: {process.pid}")
    save_pid_file(process.pid)
    return process

def wait_for_health_check():
    """Wait until the service responds to the health check."""
    max_retries = 30
    # Disable proxy for localhost requests to avoid system proxy (like 33210) interception
    proxies = {"http": None, "https": None}
    
    for i in range(max_retries):
        try:
            # The service might return 401/403 if it requires auth, but that means it's up.
            response = requests.head(f"http://127.0.0.1:{PORT}/docs", timeout=2, proxies=proxies)
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
    proxies = {"http": None, "https": None}
    
    try:
        response = requests.post(f"http://127.0.0.1:{PORT}/api/init/multi", headers=headers, json={"timestamp": int(time.time() * 1000)}, timeout=10, proxies=proxies)
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

LISTENER_PID_FILE = os.path.join(os.path.expanduser("~"), ".yoko", "ws_listener.pid")


def start_ws_listener():
    """Start the WebSocket agent listener as a detached background process."""
    listener_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ws_listener.py")
    if not os.path.exists(listener_script):
        print("Warning: ws_listener.py not found, skipping WebSocket listener startup.")
        return None

    # Kill any stale listener first
    if os.path.exists(LISTENER_PID_FILE):
        try:
            with open(LISTENER_PID_FILE) as f:
                old_pid = int(f.read().strip())
            subprocess.run(f"taskkill /F /T /PID {old_pid}", shell=True,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass

    flags = 0x00000008 if sys.platform == "win32" else 0  # DETACHED_PROCESS
    startupinfo = None
    if sys.platform == "win32":
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = subprocess.SW_HIDE

    proc = subprocess.Popen(
        [sys.executable, listener_script],
        creationflags=flags,
        startupinfo=startupinfo,
        close_fds=True,
    )
    print(f"WebSocket listener started (PID: {proc.pid})")
    return proc


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
        start_ws_listener()
        print("\n" + "="*50)
        print("RPA Service is now RUNNING in the background.")
        print(f"Agent API Endpoint:    http://127.0.0.1:{PORT}")
        print(f"WebSocket Event API:   http://127.0.0.1:9923")
        print("Frontend UI:           http://127.0.0.1:9922/")
        print("="*50)
        print()
        print(">>> NEXT STEP: HEARTBEAT SETUP REQUIRED <<<")
        print("The WebSocket event listener is running but no agent has")
        print("registered for heartbeat monitoring yet.")
        print()
        print("Immediately call:")
        print("  POST http://127.0.0.1:9923/setup/heartbeat")
        print('  Body: {"intervalSeconds": 60}')
        print()
        print("The response contains the exact heartbeat prompt to paste")
        print("into your agent platform (OpenClaw / QClaw Heartbeat settings).")
        print("="*50 + "\n")
        sys.exit(0)
    else:
        if process:
            process.kill()
        sys.exit(1)
