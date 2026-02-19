"""
Application startup with SSH tunnel management
Run this instead of uvicorn directly to enable SSH tunneling
"""

import sys
import os
import time
import atexit
import subprocess

# Suppress warnings from optional modules
os.environ['PYTHONWARNINGS'] = 'ignore'

# Import after environment setup
try:
    from ssh_tunnel import SSHTunnelManager
except ImportError as e:
    print(f"Warning: SSH tunnel module may have issues: {e}")

try:
    from config import settings
except Exception as e:
    print(f"Error loading config: {e}")
    sys.exit(1)

# Global tunnel instance
tunnel = None


def setup_tunnel():
    """Setup SSH tunnel if configured"""
    global tunnel
    
    if not settings.USE_SSH_TUNNEL:
        print("ℹ️  SSH tunnel disabled. Using direct database connection.")
        print("   To enable: set USE_SSH_TUNNEL=true in .env")
        return True
    
    print("🔐 Setting up SSH tunnel...")
    tunnel = SSHTunnelManager(
        ec2_host=settings.SSH_HOST,
        key_path=settings.SSH_KEY_PATH,
        rds_host=settings.RDS_REMOTE_HOST,
        rds_port=settings.RDS_REMOTE_PORT,
        local_port=5432
    )
    
    if tunnel.start():
        # Register cleanup on exit
        atexit.register(cleanup_tunnel)
        return True
    else:
        print("❌ Failed to setup SSH tunnel")
        return False

def cleanup_tunnel():
    """Cleanup SSH tunnel on exit"""
    global tunnel
    if tunnel:
        tunnel.stop()

def main():
    """Start the application"""
    # Setup tunnel if needed
    if not setup_tunnel():
        sys.exit(1)
    
    # Start the server using uvicorn
    print("\n🚀 Starting Finanza Bank application...")
    print("   Running on http://0.0.0.0:8000")
    
    # Use os.system to run uvicorn (simpler than subprocess)
    os.system("python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n⏹️  Shutting down...")
        cleanup_tunnel()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        cleanup_tunnel()
        sys.exit(1)
