import socket
import time


MCAST_GRP = "239.255.255.250"
MCAST_PORT = 1900
TIMEOUT = 5  # seconds to listen for replies
REPEATS = 3  # how many M-SEARCH requests to send

MSEARCH = "\r\n".join(
    [
        "M-SEARCH * HTTP/1.1",
        f"HOST: {MCAST_GRP}:{MCAST_PORT}",
        'MAN: "ssdp:discover"',
        "MX: 2",
        "ST: ssdp:all",
        "",  # blank line ends headers
        "",
    ]
).encode()


def send_msearch(sock):
    sock.sendto(MSEARCH, (MCAST_GRP, MCAST_PORT))


def main():
    print(f"Sending SSDP M-SEARCH ({REPEATS}x), listening {TIMEOUT}s for replies...")
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.settimeout(TIMEOUT)
    ttl_bin = (2).to_bytes(1, byteorder="little")
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, ttl_bin)

    for _ in range(REPEATS):
        send_msearch(sock)
        time.sleep(0.5)

    start = time.time()
    seen = set()
    try:
        while time.time() - start < TIMEOUT:
            try:
                data, addr = sock.recvfrom(2048)
            except socket.timeout:
                break
            key = (addr[0], data[:40])
            if key in seen:
                continue
            seen.add(key)
            text = data.decode(errors="ignore")
            if "control4" in text.lower():
                flag = " [POSSIBLE CONTROL4]"
            else:
                flag = ""
            print(f"{addr[0]}:{addr[1]}{flag}\n{text.strip()}\n")
    finally:
        sock.close()
    if not seen:
        print("No SSDP responses received.")


if __name__ == "__main__":
    main()
