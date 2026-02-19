"""
SSH Tunnel Manager for RDS Connection
Allows local development to connect to private RDS cluster through EC2 bastion
"""

import subprocess
import time
import os
import sys
import signal
from typing import Optional

class SSHTunnelManager:
    """Manages SSH tunnel to RDS through bastion host"""
    
    def __init__(
        self,
        ec2_host: str = "51.20.190.13",
        key_path: str = "BankingBackendKey.pem",
        rds_host: str = "finanza-bank.cluster-cxo2eume87bz.eu-north-1.rds.amazonaws.com",
        rds_port: int = 5432,
        local_port: int = 5432
    ):
        self.ec2_host = ec2_host
        self.key_path = key_path
        self.rds_host = rds_host
        self.rds_port = rds_port
        self.local_port = local_port
        self.process: Optional[subprocess.Popen] = None
    
    def start(self):
        """Start SSH tunnel"""
        # Construct SSH command
        ssh_cmd = [
            "ssh",
            "-i", self.key_path,
            "-L", f"{self.local_port}:{self.rds_host}:{self.rds_port}",
            f"ec2-user@{self.ec2_host}",
            "-N"  # Don't execute remote command
        ]
        
        print(f"Starting SSH tunnel...")
        print(f"Command: {' '.join(ssh_cmd)}")
        
        try:
            # Start tunnel process
            self.process = subprocess.Popen(
                ssh_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Give tunnel time to establish
            time.sleep(2)
            
            # Check if process is still running
            if self.process.poll() is not None:
                stdout, stderr = self.process.communicate()
                raise Exception(f"SSH tunnel failed: {stderr}")
            
            print(f"✅ SSH tunnel established on localhost:{self.local_port}")
            print(f"   Connecting to {self.rds_host}:{self.rds_port} via {self.ec2_host}")
            return True
            
        except Exception as e:
            print(f"❌ Failed to start SSH tunnel: {e}")
            return False
    
    def stop(self):
        """Stop SSH tunnel"""
        if self.process:
            print("Stopping SSH tunnel...")
            try:
                self.process.terminate()
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
            print("✅ SSH tunnel stopped")
    
    def is_running(self) -> bool:
        """Check if tunnel is still running"""
        if self.process is None:
            return False
        return self.process.poll() is None


def create_tunnel(
    ec2_host: str = "51.20.190.13",
    key_path: str = "BankingBackendKey.pem",
    local_port: int = 5432
) -> SSHTunnelManager:
    """Create and start SSH tunnel"""
    tunnel = SSHTunnelManager(
        ec2_host=ec2_host,
        key_path=key_path,
        local_port=local_port
    )
    if tunnel.start():
        return tunnel
    else:
        raise Exception("Failed to establish SSH tunnel")


if __name__ == "__main__":
    # Example usage
    tunnel = None
    try:
        tunnel = create_tunnel()
        print("\nTunnel is running. Press Ctrl+C to stop.")
        
        # Keep tunnel alive
        while True:
            time.sleep(1)
            if not tunnel.is_running():
                print("Tunnel disconnected!")
                break
                
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        if tunnel:
            tunnel.stop()
