# Control4 Discovery

Small Python utilities for locating a Control4 device on a LAN when router admin access is unavailable.

## Files

- `network_scan.py`: simple ping sweep plus TCP check on port 8750
- `find_matrix.py`: ping sweep plus ARP table lookup for a known MAC address
- `matrix_probe.py`: threaded TCP probe across a subnet, then dumps the ARP table
- `ssdp_probe.py`: sends SSDP `M-SEARCH` requests and prints replies
- `matrix_app.py`: local web app for matrix discovery/status/routing profile management
- `app_static/`: frontend used by `matrix_app.py`
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

Run the cross-platform local app:

```bash
python3 matrix_app.py
```

Open `http://127.0.0.1:8765` on the same machine.

Physical I/O test (all 16x16 paths):

- Open the app and go to `Physical I/O Test`
- Click `Start 16x16 Test`
- For each prompted route (`Source X -> Zone Y`), verify audio physically and click `Pass + Next` / `Fail + Next` / `Skip + Next`
- At completion, the app prints a full JSON result log in the panel

## Cross-platform usage (PC + iPhone/Android)

- Windows/Mac/Linux: run `python3 matrix_app.py`, then open `http://127.0.0.1:8765`
- Phone on same LAN: open `http://<pc-lan-ip>:8765`
- If your matrix is on a second NIC/direct cable, set `Local Bind IP` in the app (example: `192.168.1.10`)

## Official Control4 tooling notes

- Full matrix setup is documented as a **Composer Pro** workflow (`Configure Audio Matrix Switch in Composer Pro` in Control4 docs).
- Composer Pro is dealer-focused; customer access is typically via dealer credentials/training.
- Control4 also has **Composer Express** mobile app docs (homeowner configuration tasks), but matrix-deep setup is still primarily Composer Pro territory.

## macOS network notes

- The scripts default to `192.168.1.0/24`. Update `SUBNET` or `network_range` if your LAN differs.
- If direct-connecting to the device, disable Wi-Fi and set Ethernet to a static IP such as:
  - IP: `192.168.1.10`
  - Mask: `255.255.255.0`
  - Router: blank
- On macOS, the ARP command used is `arp -n`.

## Resume point

Read `SESSION_LOG.md` first. It contains the last observed IPs, ARP results, and the next debugging sequence to run.
