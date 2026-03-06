# Control4 Discovery

Small Python utilities for locating a Control4 device on a LAN when router admin access is unavailable.

## Files

- `network_scan.py`: simple ping sweep plus TCP check on port 8750
- `find_matrix.py`: ping sweep plus ARP table lookup for a known MAC address
- `matrix_probe.py`: threaded TCP probe across a subnet, then dumps the ARP table
- `ssdp_probe.py`: sends SSDP `M-SEARCH` requests and prints replies
- `SESSION_LOG.md`: handoff notes and latest findings

## macOS setup

1. Confirm Python 3 is available:
   `python3 --version`
2. Clone the repo:
   `git clone https://github.com/21stSentry/Control4.git`
3. Enter the project:
   `cd Control4`

No third-party Python packages are required for the current scripts.

## Typical usage

Run the threaded probe on the local /24:

```bash
python3 matrix_probe.py
```

Run the known-MAC lookup:

```bash
python3 find_matrix.py
```

Run SSDP discovery:

```bash
python3 ssdp_probe.py
```

## macOS network notes

- The scripts default to `192.168.1.0/24`. Update `SUBNET` or `network_range` if your LAN differs.
- If direct-connecting to the device, disable Wi-Fi and set Ethernet to a static IP such as:
  - IP: `192.168.1.10`
  - Mask: `255.255.255.0`
  - Router: blank
- On macOS, the ARP command used is `arp -n`.

## Resume point

Read `SESSION_LOG.md` first. It contains the last observed IPs, ARP results, and the next debugging sequence to run.
