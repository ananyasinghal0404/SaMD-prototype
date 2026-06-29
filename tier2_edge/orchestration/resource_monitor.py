import sys
import os
import psutil
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from config import CPU_LIMIT, RAM_LIMIT

def check_resources():
    """
    Reads actual system CPU and RAM.
    Returns whether edge device can handle local inference.
    """
    cpu = psutil.cpu_percent(interval=0.5)
    ram = psutil.virtual_memory().percent

    battery = None
    try:
        battery_info = psutil.sensors_battery()
        if battery_info:
            battery = round(battery_info.percent, 1)
    except Exception:
        battery = None

    edge_capable = cpu < CPU_LIMIT and ram < RAM_LIMIT

    return {
        "cpu_percent": round(cpu, 1),
        "ram_percent": round(ram, 1),
        "battery_percent": battery,
        "cpu_limit": CPU_LIMIT,
        "ram_limit": RAM_LIMIT,
        "edge_capable": edge_capable,
        "reason": _reason(cpu, ram)
    }

def _reason(cpu, ram):
    reasons = []
    if cpu >= CPU_LIMIT:
        reasons.append(f"CPU {cpu:.1f}% >= limit {CPU_LIMIT}%")
    if ram >= RAM_LIMIT:
        reasons.append(f"RAM {ram:.1f}% >= limit {RAM_LIMIT}%")
    if not reasons:
        return "Resources sufficient for edge inference"
    return " | ".join(reasons)


if __name__ == "__main__":
    print("\n" + "="*55)
    print("  Resource Monitor — TEST")
    print("="*55)

    result = check_resources()
    print(f"\n  CPU usage    : {result['cpu_percent']}%")
    print(f"  RAM usage    : {result['ram_percent']}%")
    print(f"  Battery      : {result['battery_percent']}%")
    print(f"  CPU limit    : {result['cpu_limit']}%")
    print(f"  RAM limit    : {result['ram_limit']}%")
    print(f"  Edge capable : {result['edge_capable']}")
    print(f"  Reason       : {result['reason']}")
    print(f"\n  These are your REAL system values ✅")