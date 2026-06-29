# threshold_detector.py
# Checks cleaned sensor data against clinical thresholds
# Fires emergency alerts LOCALLY — no cloud needed
# Works on vendor-specific field names (before interoperability engine)

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import THRESHOLDS, PRIORITY

def get_heart_rate(reading):
    """Extract heart rate regardless of vendor field name"""
    vendor = reading.get("vendor")
    if vendor == "Philips":
        return reading.get("HR")
    elif vendor == "GE":
        return reading.get("heartRate")
    elif vendor == "Siemens":
        return reading.get("pulse")
    return None

def get_spo2(reading):
    """Extract SpO2 regardless of vendor field name"""
    vendor = reading.get("vendor")
    if vendor == "Philips":
        return reading.get("spo2")
    elif vendor == "GE":
        return reading.get("oxygen")
    elif vendor == "Siemens":
        return reading.get("o2_sat")
    return None

def get_glucose(reading):
    """Extract glucose regardless of vendor field name"""
    vendor = reading.get("vendor")
    if vendor == "Philips":
        return reading.get("gluc")
    elif vendor == "GE":
        return reading.get("bloodSugar")
    elif vendor == "Siemens":
        return reading.get("glucose_level")
    return None

def get_temperature_celsius(reading):
    """Extract temperature and convert to Celsius if needed"""
    vendor = reading.get("vendor")
    if vendor == "Philips":
        temp_f = reading.get("temp")
        if temp_f:
            return round((temp_f - 32) * 5/9, 1)  # convert F to C
    elif vendor == "GE":
        return reading.get("temperature")
    elif vendor == "Siemens":
        return reading.get("temp_c")
    return None

def check_thresholds(reading):
    """
    Checks all vital signs against clinical thresholds.
    Returns a result dict with alerts if any thresholds are breached.
    No cloud needed — runs entirely on device/edge.
    """
    alerts = []
    values_checked = {}

    # ── Heart Rate ────────────────────────────────
    hr = get_heart_rate(reading)
    if hr is not None:
        values_checked["HeartRate"] = hr
        if hr > THRESHOLDS["HeartRate"]["max"]:
            alerts.append({
                "parameter": "HeartRate",
                "value": hr,
                "limit": THRESHOLDS["HeartRate"]["max"],
                "type": "HIGH",
                "priority": PRIORITY["CRITICAL"],
                "message": f"Heart rate {hr} bpm exceeds max {THRESHOLDS['HeartRate']['max']} bpm"
            })
        elif hr < THRESHOLDS["HeartRate"]["min"]:
            alerts.append({
                "parameter": "HeartRate",
                "value": hr,
                "limit": THRESHOLDS["HeartRate"]["min"],
                "type": "LOW",
                "priority": PRIORITY["CRITICAL"],
                "message": f"Heart rate {hr} bpm below min {THRESHOLDS['HeartRate']['min']} bpm"
            })

    # ── SpO2 ──────────────────────────────────────
    spo2 = get_spo2(reading)
    if spo2 is not None:
        values_checked["SpO2"] = spo2
        if spo2 < THRESHOLDS["SpO2"]["min"]:
            alerts.append({
                "parameter": "SpO2",
                "value": spo2,
                "limit": THRESHOLDS["SpO2"]["min"],
                "type": "LOW",
                "priority": PRIORITY["CRITICAL"],
                "message": f"SpO2 {spo2}% below min {THRESHOLDS['SpO2']['min']}%"
            })

    # ── Glucose ───────────────────────────────────
    glucose = get_glucose(reading)
    if glucose is not None:
        values_checked["Glucose"] = glucose
        if glucose > THRESHOLDS["Glucose"]["max"]:
            alerts.append({
                "parameter": "Glucose",
                "value": glucose,
                "limit": THRESHOLDS["Glucose"]["max"],
                "type": "HIGH",
                "priority": PRIORITY["HIGH"],
                "message": f"Glucose {glucose} mg/dL exceeds max {THRESHOLDS['Glucose']['max']} mg/dL"
            })
        elif glucose < THRESHOLDS["Glucose"]["min"]:
            alerts.append({
                "parameter": "Glucose",
                "value": glucose,
                "limit": THRESHOLDS["Glucose"]["min"],
                "type": "LOW",
                "priority": PRIORITY["CRITICAL"],
                "message": f"Glucose {glucose} mg/dL below min {THRESHOLDS['Glucose']['min']} mg/dL"
            })

    # ── Temperature ───────────────────────────────
    temp = get_temperature_celsius(reading)
    if temp is not None:
        values_checked["Temperature"] = temp
        if temp > THRESHOLDS["Temperature"]["max"]:
            alerts.append({
                "parameter": "Temperature",
                "value": temp,
                "limit": THRESHOLDS["Temperature"]["max"],
                "type": "HIGH",
                "priority": PRIORITY["HIGH"],
                "message": f"Temperature {temp}°C exceeds max {THRESHOLDS['Temperature']['max']}°C"
            })
        elif temp < THRESHOLDS["Temperature"]["min"]:
            alerts.append({
                "parameter": "Temperature",
                "value": temp,
                "limit": THRESHOLDS["Temperature"]["min"],
                "type": "LOW",
                "priority": PRIORITY["HIGH"],
                "message": f"Temperature {temp}°C below min {THRESHOLDS['Temperature']['min']}°C"
            })

    # ── Build result ──────────────────────────────
    result = reading.copy()
    result["values_checked"] = values_checked
    result["alerts"] = alerts
    result["alert_count"] = len(alerts)
    result["has_critical_alert"] = any(
        a["priority"] == PRIORITY["CRITICAL"] for a in alerts
    )
    result["threshold_checked"] = True

    return result


# ── Run directly to test ──────────────────────────
if __name__ == "__main__":
    from tier1_device.sensor_simulator import generate_reading
    from tier1_device.preprocessing import preprocess

    print("\n" + "="*50)
    print("  Threshold Detector — TEST")
    print("="*50)

    # Test with all 3 vendors
    for vendor in ["Philips", "GE", "Siemens"]:
        raw = generate_reading(vendor)
        cleaned = preprocess(raw)
        result = check_thresholds(cleaned)

        print(f"\nVendor  : {vendor}")
        print(f"Values  : {result['values_checked']}")
        print(f"Alerts  : {result['alert_count']}")

        if result["alerts"]:
            for alert in result["alerts"]:
                print(f"  ⚠️  {alert['message']}")
        else:
            print(f"  ✅  All vitals within normal range")

        print(f"Critical: {result['has_critical_alert']}")

    # ── Force a critical reading to test alerts ───
    print("\n" + "="*50)
    print("  FORCING CRITICAL READING (HR=180)")
    print("="*50)

    critical_reading = generate_reading("Philips")
    critical_reading["HR"] = 180  # force critical heart rate
    critical_reading["spo2"] = 85  # force low SpO2
    cleaned = preprocess(critical_reading)
    result = check_thresholds(cleaned)

    print(f"\nValues  : {result['values_checked']}")
    print(f"Alerts  : {result['alert_count']}")
    for alert in result["alerts"]:
        print(f"  🚨 {alert['message']}")
    print(f"Critical: {result['has_critical_alert']}")