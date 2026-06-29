import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from config import PRIORITY
from tier2_edge.orchestration.clinical_priority import assess_priority
from tier2_edge.orchestration.resource_monitor import check_resources
from tier2_edge.orchestration.network_monitor import check_network

def decide(record):
    """
    THE CORE OF GAP 1.
    Combines clinical priority, resources, and network
    to decide: run on EDGE or send to CLOUD.

    Rules (in order of priority):
    1. CRITICAL + network offline    → EDGE  (no choice)
    2. CRITICAL + network online     → EDGE  (speed matters)
    3. ROUTINE  + network offline    → EDGE  (no choice)
    4. ROUTINE  + edge not capable   → CLOUD (offload)
    5. ROUTINE  + network excellent  → CLOUD (better accuracy)
    6. Default                       → EDGE  (safe default)
    """
    # ── Step 1: Assess all three factors ─────────
    priority_result  = assess_priority(record)
    resource_result  = check_resources()
    network_result   = check_network()

    priority     = priority_result["priority"]
    is_critical  = priority_result["is_critical"]
    edge_capable = resource_result["edge_capable"]
    cloud_ok     = network_result["suitable_for_cloud"]
    connected    = network_result["connected"]

    # ── Step 2: Apply decision rules ─────────────
    if is_critical:
        decision = "EDGE"
        reason = "Critical condition — local inference for minimum latency"

    elif not connected:
        decision = "EDGE"
        reason = "Network offline — forced edge execution"

    elif not edge_capable:
        decision = "CLOUD"
        reason = f"Edge resources overloaded — offloading to cloud"

    elif priority == "ROUTINE" and cloud_ok:
        decision = "CLOUD"
        reason = "Routine workload + excellent network — cloud for better accuracy"

    else:
        decision = "EDGE"
        reason = "Default — edge execution preferred"

    return {
        "decision": decision,
        "reason": reason,
        "priority": priority,
        "is_critical": is_critical,
        "edge_capable": edge_capable,
        "network_connected": connected,
        "network_quality": network_result["quality"],
        "cpu_percent": resource_result["cpu_percent"],
        "ram_percent": resource_result["ram_percent"],
        "latency_ms": network_result["latency_ms"],
    }


if __name__ == "__main__":
    from tier1_device.sensor_simulator import generate_reading
    from tier1_device.preprocessing import preprocess
    from tier1_device.threshold_detector import check_thresholds
    from tier2_edge.interoperability_engine import adapt

    print("\n" + "="*55)
    print("  Placement Decision Engine — TEST")
    print("="*55)

    # ── Test 1: Normal reading ────────────────────
    print("\n--- TEST 1: Normal reading ---")
    raw = generate_reading()
    standard = adapt(check_thresholds(preprocess(raw)))
    result = decide(standard)

    print(f"\n  ┌─────────────────────────────────────┐")
    print(f"  │  ORCHESTRATION DECISION              │")
    print(f"  ├─────────────────────────────────────┤")
    print(f"  │  Priority   : {result['priority']:<22}│")
    print(f"  │  CPU        : {result['cpu_percent']}%{'':<20}│")
    print(f"  │  RAM        : {result['ram_percent']}%{'':<20}│")
    print(f"  │  Network    : {result['network_quality']:<22}│")
    print(f"  │  Latency    : {str(result['latency_ms']) + ' ms':<22}│")
    print(f"  ├─────────────────────────────────────┤")
    print(f"  │  DECISION → {result['decision']:<24}│")
    print(f"  │  {result['reason'][:37]:<37}│")
    print(f"  └─────────────────────────────────────┘")

    # ── Test 2: Critical reading ──────────────────
    print("\n--- TEST 2: Critical reading (HR=185, SpO2=82) ---")
    raw = generate_reading("Philips")
    raw["HR"] = 185
    raw["spo2"] = 82
    standard = adapt(check_thresholds(preprocess(raw)))
    result = decide(standard)

    print(f"\n  ┌─────────────────────────────────────┐")
    print(f"  │  ORCHESTRATION DECISION              │")
    print(f"  ├─────────────────────────────────────┤")
    print(f"  │  Priority   : {result['priority']:<22}│")
    print(f"  │  CPU        : {result['cpu_percent']}%{'':<20}│")
    print(f"  │  Network    : {result['network_quality']:<22}│")
    print(f"  ├─────────────────────────────────────┤")
    print(f"  │  DECISION → {result['decision']:<24}│")
    print(f"  │  {result['reason'][:37]:<37}│")
    print(f"  └─────────────────────────────────────┘")

    print("\n  Decision Engine combining all 3 factors ✅")
    print("  Turn off WiFi → network offline → forces EDGE")
    print("  Spike CPU     → edge overloaded → forces CLOUD")
    print("  Critical HR   → always EDGE regardless of network")