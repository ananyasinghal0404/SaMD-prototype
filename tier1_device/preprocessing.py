# preprocessing.py
# Cleans raw sensor data before it enters the pipeline
# Removes noise, clamps outliers, smooths ECG signal
# Works on ANY vendor format — operates on raw values only

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def remove_ecg_noise(ecg_signal):
    """
    Simple moving average to smooth ECG noise.
    Window of 3 — lightweight enough for edge devices.
    """
    if len(ecg_signal) < 3:
        return ecg_signal

    smoothed = []
    for i in range(len(ecg_signal)):
        if i == 0:
            smoothed.append(ecg_signal[i])
        elif i == 1:
            smoothed.append(round((ecg_signal[i-1] + ecg_signal[i]) / 2, 3))
        else:
            avg = round((ecg_signal[i-2] + ecg_signal[i-1] + ecg_signal[i]) / 3, 3)
            smoothed.append(avg)
    return smoothed

def clamp_value(value, min_val, max_val):
    """
    Clamps a value within a physiologically plausible range.
    Removes sensor glitches like HR=300 or SpO2=200.
    """
    return max(min_val, min(max_val, value))

def preprocess(raw_reading):
    """
    Takes a raw vendor reading and returns a cleaned version.
    Does NOT standardize field names — that's the Interoperability Engine's job.
    Only cleans values.
    """
    cleaned = raw_reading.copy()
    vendor = raw_reading.get("vendor")

    # ── Clean ECG signal ──────────────────────────
    if "ecg" in cleaned:
        cleaned["ecg"] = remove_ecg_noise(cleaned["ecg"])

    # ── Clamp Philips values ──────────────────────
    if vendor == "Philips":
        if "HR" in cleaned:
            cleaned["HR"] = clamp_value(cleaned["HR"], 20, 250)
        if "spo2" in cleaned:
            cleaned["spo2"] = clamp_value(cleaned["spo2"], 50, 100)
        if "gluc" in cleaned:
            cleaned["gluc"] = clamp_value(cleaned["gluc"], 20, 600)
        if "temp" in cleaned:
            cleaned["temp"] = clamp_value(cleaned["temp"], 90, 110)

    # ── Clamp GE values ───────────────────────────
    elif vendor == "GE":
        if "heartRate" in cleaned:
            cleaned["heartRate"] = clamp_value(cleaned["heartRate"], 20, 250)
        if "oxygen" in cleaned:
            cleaned["oxygen"] = clamp_value(cleaned["oxygen"], 50, 100)
        if "bloodSugar" in cleaned:
            cleaned["bloodSugar"] = clamp_value(cleaned["bloodSugar"], 20, 600)
        if "temperature" in cleaned:
            cleaned["temperature"] = clamp_value(cleaned["temperature"], 30, 45)

    # ── Clamp Siemens values ──────────────────────
    elif vendor == "Siemens":
        if "pulse" in cleaned:
            cleaned["pulse"] = clamp_value(cleaned["pulse"], 20, 250)
        if "o2_sat" in cleaned:
            cleaned["o2_sat"] = clamp_value(cleaned["o2_sat"], 50, 100)
        if "glucose_level" in cleaned:
            cleaned["glucose_level"] = clamp_value(cleaned["glucose_level"], 20, 600)
        if "temp_c" in cleaned:
            cleaned["temp_c"] = clamp_value(cleaned["temp_c"], 30, 45)

    cleaned["preprocessed"] = True
    return cleaned


# ── Run directly to test ──────────────────────────
if __name__ == "__main__":
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from tier1_device.sensor_simulator import generate_reading

    print("\n" + "="*50)
    print("  Preprocessing Module — TEST")
    print("="*50)

    for vendor in ["Philips", "GE", "Siemens"]:
        raw = generate_reading(vendor)
        cleaned = preprocess(raw)

        print(f"\nVendor : {vendor}")
        print(f"RAW ECG    : {raw['ecg']}")
        print(f"CLEAN ECG  : {cleaned['ecg']}")
        print(f"Preprocessed: {cleaned['preprocessed']}")