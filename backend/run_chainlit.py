import psutil
import subprocess
import sys

def check_port_usage(port=8000):
    """Check if port is in use and return process info."""
    for proc in psutil.process_iter(['pid', 'name']):
        try:
            for conn in proc.net_connections(kind='inet'):
                if conn.laddr.port == port:
                    return f"\n- Port {port} is used by {proc.info['name']} (PID: {proc.info['pid']})"
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return None

if __name__ == "__main__":
    port = 8000  # Default port
    usage = check_port_usage(port)
    if usage:
        print(f"\n- Warning: {usage}. Please free the port or specify a different one.")
        print(f"\n- You can run with a different port using: chainlit run --port <port> backend/main.py")
        sys.exit(1)
    else:
        print(f"\n- Port 8000 is free. Starting Chainlit...")
        # Run chainlit
        cmd = [sys.executable, "-m", "chainlit", "run", "--port", str(port), "backend/main.py"]
        try:
            subprocess.run(cmd)
        except KeyboardInterrupt:
            print(f"\n- Interrupted by user. Exiting...")
            sys.exit(0)