import ipaddress
import subprocess
import sys


def normalize_mac(mac):
    """Lowercase MAC with separators stripped so formats compare equally."""
    return "".join(ch for ch in mac.lower() if ch.isalnum())


def ping_sweep(network_cidr, timeout_ms=200):
    """Lightweight ping sweep to populate the ARP table."""
    net = ipaddress.ip_network(network_cidr, strict=False)
    cmd_base = ["ping", "-n", "1", "-w", str(timeout_ms)] if sys.platform.startswith("win") else ["ping", "-c", "1", "-W", str(max(1, timeout_ms // 1000))]
    for host in net.hosts():
        cmd = cmd_base + [str(host)]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def find_ip_by_mac(target_mac):
    """Ping a subnet, then read the ARP table to locate the target MAC."""
    network_range = "192.168.1.0/24"  # change to match your LAN
    print(f"Searching {network_range} for Matrix ({target_mac})...")

    ping_sweep(network_range)

    target_norm = normalize_mac(target_mac)
    arp_cmd = ["arp", "-a"] if sys.platform.startswith("win") else ["arp", "-n"]
    try:
        output = subprocess.check_output(arp_cmd, text=True, stderr=subprocess.DEVNULL)
    except Exception as exc:
        print(f"Could not read ARP table: {exc}")
        return None

    for line in output.splitlines():
        parts = line.split()
        if len(parts) < 2:
            continue
        mac_token = next((p for p in parts if "-" in p or ":" in p), None)
        if not mac_token:
            continue
        if normalize_mac(mac_token) == target_norm:
            return parts[0]
    return None


if __name__ == "__main__":
    mac = "00:0F:FF:1B:96:61"  # set your device MAC here
    ip = find_ip_by_mac(mac)

    if ip:
        print(f"SUCCESS! The Matrix is at: {ip}")
    else:
        print("Device not found. Ensure it is on the same subnet and try a different range.")
