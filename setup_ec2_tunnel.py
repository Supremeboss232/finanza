#!/usr/bin/env python3
"""
SSH Tunnel Manager for EC2 Bastion Host
Manages SSH tunnel to reach RDS database through EC2
"""

import subprocess
import time
import os
import sys
import signal
from pathlib import Path

# Configuration
EC2_HOST = "ec2-51-20-190-13.eu-north-1.compute.amazonaws.com"
EC2_IP = "51.20.190.13"
EC2_USER = "ec2-user"
EC2_KEY_PATH = "BankingBackendKey.pem"
RDS_HOST = "finbank-db.cxo2eume87bz.eu-north-1.rds.amazonaws.com"
RDS_PORT = 5432
LOCAL_PORT = 5432

def check_pem_file():
    """Check if .pem file exists and has correct permissions."""
    pem_path = Path(EC2_KEY_PATH)
    
    if not pem_path.exists():
        print(f"❌ Error: {EC2_KEY_PATH} not found!")
        print(f"   Current directory: {os.getcwd()}")
        print(f"   Please ensure the .pem file is in the same directory as this script.")
        sys.exit(1)
    
    print(f"✅ Found {EC2_KEY_PATH}")
    return str(pem_path.absolute())

def create_ssh_tunnel(pem_path):
    """Create SSH tunnel to EC2 -> RDS."""
    cmd = [
        "ssh",
        "-i", pem_path,
        "-L", f"{LOCAL_PORT}:{RDS_HOST}:{RDS_PORT}",
        f"{EC2_USER}@{EC2_HOST}",
        "-N"  # Don't execute remote command
    ]
    
    print("\n" + "="*70)
    print("SSH TUNNEL SETUP")
    print("="*70)
    print(f"\n📡 Creating SSH tunnel...")
    print(f"   EC2 Host: {EC2_HOST}")
    print(f"   EC2 IP: {EC2_IP}")
    print(f"   RDS Host: {RDS_HOST}")
    print(f"   Local Port: {LOCAL_PORT}")
    print(f"   Command: {' '.join(cmd)}\n")
    
    try:
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        time.sleep(2)  # Give tunnel time to establish
        
        # Check if process is still running
        if process.poll() is not None:
            stdout, stderr = process.communicate()
            print(f"❌ Tunnel failed:")
            print(stderr.decode())
            return None
        
        print("✅ SSH tunnel established!")
        print(f"\n🔗 You can now connect to RDS at: localhost:{LOCAL_PORT}")
        print(f"\n📝 Connection string: postgresql://postgres_admin:Supposedbe5@localhost:{LOCAL_PORT}/finbank")
        print("\n⏸️  Press Ctrl+C to close the tunnel...\n")
        
        return process
        
    except FileNotFoundError:
        print("❌ SSH not found! Please install OpenSSH for Windows or use WSL.")
        print("   Download: https://www.microsoft.com/en-us/p/openssh/9mzd3tgd5oci")
        return None
    except Exception as e:
        print(f"❌ Error creating tunnel: {e}")
        return None

def main():
    """Main function."""
    print("\n" + "="*70)
    print("FINANZA BANK - EC2 BASTION TUNNEL")
    print("="*70)
    
    # Check .pem file
    pem_path = check_pem_file()
    
    # Create tunnel
    process = create_ssh_tunnel(pem_path)
    
    if not process:
        sys.exit(1)
    
    # Keep tunnel alive
    def signal_handler(sig, frame):
        print("\n\n🛑 Closing tunnel...")
        process.terminate()
        process.wait()
        print("✅ Tunnel closed.")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    
    try:
        process.wait()
    except KeyboardInterrupt:
        print("\n\n🛑 Closing tunnel...")
        process.terminate()
        print("✅ Tunnel closed.")

if __name__ == "__main__":
    main()
