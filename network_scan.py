import os
import platform
import socket

def scan_network(subnet):
    print(f"Scanning {subnet}.0/24 for Control4 Matrix...")
    for i in range(1, 255):
        ip = f"{subnet}.{i}"
        # Ping the IP once
        param = "-n" if platform.system().lower() == "windows" else "-c"
        response = os.system(f"ping {param} 1 {ip} > {'nul' if platform.system().lower() == 'windows' else '/dev/null'} 2>&1")
        
        if response == 0:
            # If it pings, check if Port 8750 is open (Control4 Matrix Port)
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(0.1)
                if s.connect_ex((ip, 8750)) == 0:
                    print(f"!!! FOUND UNIT AT: {ip} !!!")

# Usage: Change '192.168.1' to match your router's subnet
scan_network("192.168.1")