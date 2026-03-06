import ipaddress
import socket
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed


SUBNET = "192.168.1.0/24"  # change to your LAN
TARGET_PORTS = [8750, 80, 443, 23]  # primary + common fallbacks
THREADS = 100              # adjust down if CPU is weak
CONNECT_TIMEOUT_S = 0.25


def check_port(host: str, port: int) -> bool:
    """Return True if port is open on host."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(CONNECT_TIMEOUT_S)
        return s.connect_ex((host, port)) == 0


def probe_ip(ip_str: str):
    open_on = []
    for port in TARGET_PORTS:
        if check_port(ip_str, port):
            open_on.append(port)
    return ip_str, open_on


def main():
    net = ipaddress.ip_network(SUBNET, strict=False)
    print(f"Scanning {SUBNET} for Control4. Ports: {TARGET_PORTS} ...")
    hits = {}
    with ThreadPoolExecutor(max_workers=THREADS) as pool:
        futures = {pool.submit(probe_ip, str(host)): str(host) for host in net.hosts()}
        for fut in as_completed(futures):
            ip = futures[fut]
            try:
                ip_addr, open_on = fut.result()
            except Exception as exc:
                print(f"[warn] {ip}: {exc}")
                continue
            if open_on:
                hits[ip_addr] = open_on
                port_list = ",".join(str(p) for p in open_on)
                print(f"FOUND: {ip_addr} (open: {port_list})")
    if not hits:
        print("No devices answered on target ports.")
    else:
        summary = "; ".join(f"{ip}[{','.join(map(str, ports))}]" for ip, ports in hits.items())
        print("Completed. Devices (port open):", summary)

    # Secondary: dump ARP entries and flag Control4 OUI (00:0f:ff)
    try:
        arp_cmd = ["arp", "-a"] if sys.platform.startswith("win") else ["arp", "-n"]
        arp_out = subprocess.check_output(arp_cmd, text=True, stderr=subprocess.DEVNULL)
        print("\nARP table after scan:")
        for line in arp_out.splitlines():
            if not line.strip():
                continue
            if "00-0f-ff" in line.lower() or "00:0f:ff" in line.lower():
                print("  [C4 OUI]", line.strip())
            else:
                print("          ", line.strip())
    except Exception as exc:
        print(f"[warn] Could not read ARP table: {exc}")


if __name__ == "__main__":
    main()
