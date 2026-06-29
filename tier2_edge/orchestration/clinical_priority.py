import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from config import THRESHOLDS, PRIORITY

def assess_priority(record):
    """
    Evaluates clinical urgency of a standardized record.
    Returns CRITICAL, HIGH, or ROUTINE with reasons.
    """
    reasons = []
    highest_priority = PRIORITY["ROUTINE"]

    hr = record.get("HeartRate")
    spo2 = record.get("SpO2")
    glucose = record.get("Glucose")
    temp = record.get("Temperature")

    # ── Heart Rate ────────────────────────────────
    if hr is not None and isinstance(hr, (int, float)):
        if hr > THRESHOLDS["HeartRate"]["max"] or hr < THRESHOLDS["HeartRate"]["min"]:
            reasons.append(f"HeartRate {hr} bpm out of range")
            highest_priority = min(highest_priority, PRIORITY["CRITICAL"])

    # ── SpO2 ──────────────────────────────────────
    if spo2 is not None and isinstance(spo2, (int, float)):
        if spo2 < THRESHOLDS["SpO2"]["min"]:
            reasons.append(f"SpO2 {spo2}% critically low")
            highest_priority = min(highest_priority, PRIORITY["CRITICAL"])

    # ── Glucose ───────────────────────────────────
    if glucose is not None and isinstance(glucose, (int, float)):
        if glucose < THRESHOLDS["Glucose"]["min"]:
            reasons.append(f"Glucose {glucose} mg/dL critically low")
            highest_priority = min(highest_priority, PRIORITY["CRITICAL"])
        elif glucose > THRESHOLDS["Glucose"]["max"]:
            reasons.append(f"Glucose {glucose} mg/dL high")
            highest_priority = min(highest_priority, PRIORITY["HIGH"])

    # ── Temperature ───────────────────────────────
    if temp is not None and isinstance(temp, (int, float)):
        if temp > THRESHOLDS["Temperature"]["max"] or temp < THRESHOLDS["Temperature"]["min"]:
            reasons.append(f"Temperature {temp}°C out of range")
            highest_priority = min(highest_priority, PRIORITY["HIGH"])

    # ── Map number back to label ──────────────────
    priority_label = "ROUTINE"
    for label, val in PRIORITY.items():
        if val == highest_priority:
            priority_label = label
            break

    return {
        "priority": priority_label,
        "priority_value": highest_priority,
        "reasons": reasons,
        "is_critical": highest_priority == PRIORITY["CRITICAL"]
    }


if __name__ == "__main__":
    from tier1_device.sensor_simulator import generate_reading
    from tier1_device.preprocessing import preprocess
    from tier1_device.threshold_detector import check_thresholds
    from tier2_edge.interoperability_engine import adapt

    print("\n" + "="*55)
    print("  Clinical Priority Manager — TEST")
    print("="*55)

    print("\n--- Normal reading ---")
    raw = generate_reading("GE")
    standard = adapt(check_thresholds(preprocess(raw)))
    result = assess_priority(standard)
    print(f"  Priority : {result['priority']}")
    print(f"  Critical : {result['is_critical']}")
    print(f"  Reasons  : {result['reasons'] or 'None — all vitals normal'}")

    print("\n--- Critical reading (HR=180, SpO2=84) ---")
    raw = generate_reading("Philips")
    raw["HR"] = 180
    raw["spo2"] = 84
    standard = adapt(check_thresholds(preprocess(raw)))
    result = assess_priority(standard)
    print(f"  Priority : {result['priority']}")
    print(f"  Critical : {result['is_critical']}")
    for r in result["reasons"]:
        print(f"  ⚠️  {r}")

    print("\n--- High priority reading (Glucose=200, Temp=39) ---")
    raw = generate_reading("Siemens")
    raw["glucose_level"] = 200
    raw["temp_c"] = 39.0
    standard = adapt(check_thresholds(preprocess(raw)))
    result = assess_priority(standard)
    print(f"  Priority : {result['priority']}")
    print(f"  Critical : {result['is_critical']}")
    for r in result["reasons"]:
        print(f"  ⚠️  {r}")