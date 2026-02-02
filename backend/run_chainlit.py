import os
import sys
import subprocess
import psutil
from pathlib import Path

DEFAULT_PORT = 8000

def check_port_usage(port):
    """Check if port is in use and return process details."""
    for proc in psutil.process_iter(['pid', 'name']):
        try:
            for conn in proc.net_connections(kind='inet'):
                if conn.laddr.port == port:
                    return f"Port {port} is used by {proc.info['name']} (PID: {proc.info['pid']})"
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return None

def build_chainlit_command(port: int, watch: bool = False, debug: bool = False, headless: bool = False):
    """Build the Chainlit command list with optional flags: -w for watch mode, -d for debug mode, -h for headless mode."""
    main_file = Path("backend/main.py")
    
    if not main_file.exists():
        raise FileNotFoundError(f"Source file {main_file} not found.")

    # Start with the base command
    cmd = [sys.executable, "-m", "chainlit", "run", str(main_file), "--port", str(port)]

    # Add flags based on boolean inputs
    if watch:
        cmd.append("-w")
    if debug:
        cmd.append("-d")
    if headless:
        cmd.append("-h")

    return cmd

def main():
    """Main entry point to run Chainlit with specified port and watch mode."""
    port = int(os.environ.get('CHAINLIT_PORT', DEFAULT_PORT))
    if not (1024 <= port <= 65535):
        print(f"Invalid port: {port}. Must be between 1024 and 65535.")
        sys.exit(1)

    usage_msg = check_port_usage(port)
    if usage_msg:
        print(f"❌  {usage_msg}.")
        print(f"    Please configure another port in ./backend/run_chainlit.py")
        sys.exit(1)

    cmd = build_chainlit_command(port)
    watch_mode = "Enabled" if "-w" in cmd else "Disabled"
    debug_mode = "Enabled" if "-d" in cmd else "Disabled"
    open_in_browser = "Disabled" if "-h" in cmd else "Enabled"
    watch_color = "\033[32m" if watch_mode == "Enabled" else "\033[31m"
    debug_color = "\033[32m" if debug_mode == "Enabled" else "\033[31m"
    browser_color = "\033[32m" if open_in_browser == "Enabled" else "\033[31m"
    print(f"✅  Port {port} is free")
    print(f"✅  Starting Chainlit - Watch Mode: [{watch_color}{watch_mode}\033[0m] Debug Mode: [{debug_color}{debug_mode}\033[0m] Open in browser: [{browser_color}{open_in_browser}\033[0m]")

    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌  Chainlit failed with exit code {e.returncode}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\U00002139  Interrupted by user. Exiting...")
        sys.exit(0)

if __name__ == "__main__":
    main()
