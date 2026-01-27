import os
import psutil
import subprocess
import sys

# Spaghetti code, sort it out later
def check_port_usage(port=8000):
    """
    Checks if a port is in use and returns process details.
    Uses psutil to iterate through active internet connections.
    """
    for proc in psutil.process_iter(['pid', 'name']):
        try:
            for conn in proc.net_connections(kind='inet'):
                if conn.laddr.port == port:
                    return f"Port {port} is used by {proc.info['name']} (PID: {proc.info['pid']})"
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            # Ignore processes that close during iteration or lack permissions
            pass
    return None

def build_chainlit_command(port, watch_enabled):
    """
    Constructs the command list for subprocess.
    Uses a set for flags to allow easy adding/removing without duplicates.
    """
    # Base command
    cmd_base = [sys.executable, "-m", "chainlit", "run", "backend/main.py"]
    
    # Parameters
    params = {"--port": str(port)}
    
    # flags.discard("-w") flags.add("-w") to toggle Watch.
    flags = set()
    if watch_enabled:
        flags.add("-w")
    
    final_cmd = cmd_base.copy()
    
    # Add parameters (key - value)
    for key, value in params.items():
        final_cmd.extend([key, value])
    
    final_cmd.extend(list(flags))
    
    return final_cmd

def main():
    port = 8000
    
    # Port availability check 
    usage_msg = check_port_usage(port)
    if usage_msg:
        print(f"\n- Warning: {usage_msg}.")
        print(f"- Please free the port or specify a different one.")
        print(f"- Usage: chainlit run --port <port> backend/main.py")
        sys.exit(1)

    # Determine configuration from environment
    # Logic: Default to True unless 'DISABLE_WATCH' is explicitly 'true'
    is_watch_enabled = os.environ.get('DISABLE_WATCH', 'false').lower() != 'true'
    
    # Construct the command list
    cmd = build_chainlit_command(port, is_watch_enabled)
    
    mode_status = "with watch mode" if "-w" in cmd else "without watch mode"
    print(f"\U00002705  Port {port} is free. Starting Chainlit {mode_status}...")

    try:
        # Launch the process passing the list 'cmd' directly to subprocess.run
        subprocess.run(cmd)
    except KeyboardInterrupt:
        print(f"\n- Interrupted by user. Exiting...")
        sys.exit(0)

if __name__ == "__main__":
    main()
