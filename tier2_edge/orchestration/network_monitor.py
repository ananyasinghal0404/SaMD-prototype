import sys
import os
import subprocess
import socket
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from config import PING_HOST, PING_TIMEOUT

def check_network():
    """
    Checks real network connectivity by pinging 8.8.8.8.
    Also measures approximate latency.
    Returns network status and quality.
    """
    connected, latency_ms = _ping()

    if not connected:
        quality = "OFFLINE"
        suitable_for_cloud = False
    elif latency_ms < 50:
        quality = "EXCELLENT"
        suitable_for_cloud = True
    elif latency_ms < 150:
        quality = "GOOD"
        suitable_for_cloud = True
    elif latency_ms < 300:
        quality = "POOR"
        suitable_for_cloud = False
    else:
        quality = "VERY_POOR"
        suitable_for_cloud = False

    return {
        "connected": connected,
        "latency_ms": latency_ms,
        "quality": quality,
        "suitable_for_cloud": suitable_for_cloud,
        "ping_host": PING_HOST,
        "reason": _reason(connected, quality, latency_ms)
    }

def _ping():
    """
    Pings 8.8.8.8 and returns (connected, latency_ms).
    Works on Mac and Linux.
    """
    try:
        result = subprocess.run(
            ["ping", "-c", "1", "-W", "1000", PING_HOST],
            capture_output=True,
            text=True,
            timeout=PING_TIMEOUT + 1
        )
        if result.returncode == 0:
            # Parse latency from ping output
            output = result.stdout
            for line in output.split("\n"):
                if "time=" in line:
                    time_part = line.split("time=")[1]
                    latency = float(time_part.split(" ")[0])
                    return True, round(latency, 1)
            return True, 99.9
        else:
            return False, None
    except Exception:
        return False, None

def _reason(connected, quality, latency):
    if not connected:
        return "Network OFFLINE — edge inference required"
    return f"Network {quality} — latency {latency}ms"


if __name__ == "__main__":
    print("\n" + "="*55)
    print("  Network Monitor — TEST")
    print("="*55)

    print("\n  Checking network... (pinging 8.8.8.8)")
    result = check_network()

    print(f"\n  Connected        : {result['connected']}")
    print(f"  Latency          : {result['latency_ms']} ms")
    print(f"  Quality          : {result['quality']}")
    print(f"  Cloud suitable   : {result['suitable_for_cloud']}")
    print(f"  Reason           : {result['reason']}")
    print(f"\n  Real network check ✅")
    print(f"\n  TIP: Turn off WiFi and run again")
    print(f"       Connected will become False")
    print(f"       Orchestration will force EDGE routing")