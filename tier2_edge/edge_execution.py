import sys
import os
import random
from datetime import datetime
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import MODEL_VERSION, DRIFT_THRESHOLD

def run_local_inference(record):
    """
    Simulates local AI model running on edge device.
    In a real system this would load a TensorFlow Lite / ONNX model.
    Here we simulate realistic inference with rule-based logic
    plus a confidence score — which feeds into drift detection later.
    """
    hr   = record.get("HeartRate")
    spo2 = record.get("SpO2")
    glucose = record.get("Glucose")
    temp = record.get("Temperature")

    findings = []
    confidence_scores = []

    # ── Arrhythmia detection ──────────────────────
    if hr is not None and isinstance(hr, (int, float)):
        if hr > 150 or hr < 40:
            findings.append("Arrhythmia suspected")
            confidence_scores.append(0.94)
        elif hr > 130:
            findings.append("Tachycardia — monitor closely")
            confidence_scores.append(0.87)
        elif hr < 55:
            findings.append("Bradycardia — monitor closely")
            confidence_scores.append(0.85)
        else:
            findings.append("Heart rate normal")
            confidence_scores.append(round(random.uniform(0.88, 0.97), 2))

    # ── Hypoxia detection ─────────────────────────
    if spo2 is not None and isinstance(spo2, (int, float)):
        if spo2 < 90:
            findings.append("Hypoxia detected — critical")
            confidence_scores.append(0.96)
        elif spo2 < 94:
            findings.append("Low SpO2 — supplemental oxygen advised")
            confidence_scores.append(0.89)
        else:
            findings.append("SpO2 normal")
            confidence_scores.append(round(random.uniform(0.88, 0.97), 2))

    # ── Glucose assessment ────────────────────────
    if glucose is not None and isinstance(glucose, (int, float)):
        if glucose < 70:
            findings.append("Hypoglycemia — immediate attention")
            confidence_scores.append(0.93)
        elif glucose > 180:
            findings.append("Hyperglycemia — elevated")
            confidence_scores.append(0.88)
        else:
            findings.append("Glucose normal")
            confidence_scores.append(round(random.uniform(0.85, 0.95), 2))

    # ── Temperature assessment ────────────────────
    if temp is not None and isinstance(temp, (int, float)):
        if temp > 38.5:
            findings.append("Fever detected")
            confidence_scores.append(0.91)
        elif temp < 35:
            findings.append("Hypothermia suspected")
            confidence_scores.append(0.90)
        else:
            findings.append("Temperature normal")
            confidence_scores.append(round(random.uniform(0.87, 0.96), 2))

    # ── Overall confidence ────────────────────────
    avg_confidence = round(sum(confidence_scores) / len(confidence_scores), 3) \
        if confidence_scores else 0.0

    # ── Drift flag ────────────────────────────────
    drift_suspected = avg_confidence < DRIFT_THRESHOLD

    result = {
        "execution_location": "EDGE",
        "model_version": MODEL_VERSION,
        "findings": findings,
        "confidence": avg_confidence,
        "drift_suspected": drift_suspected,
        "inference_timestamp": datetime.now().isoformat(),
        "latency_note": "Local inference — sub-100ms",
        "input_vitals": {
            "HeartRate": hr,
            "SpO2": spo2,
            "Glucose": glucose,
            "Temperature": temp
        }
    }

    return result


if __name__ == "__main__":
    from tier1_device.sensor_simulator import generate_reading
    from tier1_device.preprocessing import preprocess
    from tier1_device.threshold_detector import check_thresholds
    from tier2_edge.interoperability_engine import adapt

    print("\n" + "="*55)
    print("  Edge Execution Engine — TEST")
    print("="*55)

    # ── Test 1: Normal patient ────────────────────
    print("\n--- TEST 1: Normal patient ---")
    raw = generate_reading("GE")
    standard = adapt(check_thresholds(preprocess(raw)))
    result = run_local_inference(standard)

    print(f"\n  Model version : {result['model_version']}")
    print(f"  Confidence    : {result['confidence']}")
    print(f"  Drift flag    : {result['drift_suspected']}")
    print(f"  Findings:")
    for f in result["findings"]:
        print(f"    — {f}")

    # ── Test 2: Critical patient ──────────────────
    print("\n--- TEST 2: Critical patient (HR=185, SpO2=82) ---")
    raw = generate_reading("Philips")
    raw["HR"] = 185
    raw["spo2"] = 82
    standard = adapt(check_thresholds(preprocess(raw)))
    result = run_local_inference(standard)

    print(f"\n  Model version : {result['model_version']}")
    print(f"  Confidence    : {result['confidence']}")
    print(f"  Findings:")
    for f in result["findings"]:
        print(f"    🚨 {f}")
    print(f"\n  Execution: {result['execution_location']}")
    print(f"  Latency  : {result['latency_note']}")

    # ── Test 3: Simulate drift ────────────────────
    print("\n--- TEST 3: Simulate drift (low confidence) ---")
    raw = generate_reading("Siemens")
    standard = adapt(check_thresholds(preprocess(raw)))
    result = run_local_inference(standard)
    result["confidence"] = 0.71  # force low confidence
    result["drift_suspected"] = result["confidence"] < DRIFT_THRESHOLD

    print(f"\n  Confidence    : {result['confidence']} ← artificially lowered")
    print(f"  Drift flag    : {result['drift_suspected']}")
    print(f"  Action needed : Send confidence log to Drift Detection Monitor")