# Session Log

## Objective

Locate a Control4 unit on the local network without router admin access.

## Current repo state

- Local Git repo initialized in this folder
- Remote configured as `https://github.com/21stSentry/Control4`
- Latest local commit:
  - `cde78f67604733f0d5a485f510dac4aa2bcdb0b6`
  - `Add Control4 network discovery scripts`

## Scripts and purpose

- `network_scan.py`
  - Pings every host in a /24 and checks TCP port 8750
- `find_matrix.py`
  - Sweeps a subnet, then inspects the ARP table for a known MAC
  - Current target MAC in file: `00:0F:FF:1B:96:61`
- `matrix_probe.py`
  - Probes ports `[8750, 80, 443, 23]` across a subnet
  - Dumps ARP entries after the scan
  - Flags Control4 OUI `00:0f:ff` if seen
- `ssdp_probe.py`
  - Broadcasts SSDP discovery and prints responses

## Last observed network facts

- Local PC IP: `192.168.1.105`
- Subnet mask: `255.255.255.0`
- Default gateway: `192.168.1.1`

## Last scan results

From `matrix_probe.py` on `192.168.1.0/24`:

- `192.168.1.1` open on `80,443`
- `192.168.1.151` open on `80`

ARP lookup for `192.168.1.151`:

- MAC: `6a-ff-7a-d8-bd-4e`
- This does not match the expected Control4 OUI `00-0f-ff`

ARP table snapshot did not contain any `00-0f-ff` entries.

## Interpretation

- `192.168.1.1` is almost certainly the router
- `192.168.1.151` is not the expected Control4 unit, at least by MAC prefix
- The target device may be:
  - on another subnet
  - using a different NIC / bridge MAC than expected
  - isolated by switch/router behavior
  - easier to detect through a direct Ethernet connection

## Recommended next steps on Mac

1. Clone the repo and run the current tools on the normal LAN first:
   - `python3 matrix_probe.py`
   - `python3 ssdp_probe.py`
2. Try adjacent common private subnets:
   - `python3 -c "import matrix_probe as m; m.SUBNET='192.168.0.0/24'; m.main()"`
   - `python3 -c "import matrix_probe as m; m.SUBNET='10.0.0.0/24'; m.main()"`
3. Direct-connect the Mac to the device or place both on an unmanaged switch
4. Disable Wi-Fi and set Ethernet manually:
   - IP `192.168.1.10`
   - Mask `255.255.255.0`
   - Router blank
5. Re-run:
   - `python3 matrix_probe.py`
   - `python3 ssdp_probe.py`
   - `arp -an`
6. If a candidate IP appears, test:
   - `http://<ip>/`
   - `https://<ip>/`

## Notes

- The current scripts avoid `scapy` and `Npcap` so they work with stock Python.
- No external dependencies are needed at this point.
- If the direct-connect test still shows nothing, the next improvement should be adding:
  - a wider port list
  - optional HTTP title/banner grabbing
  - optional reverse DNS lookup
