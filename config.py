# config.py
# Central configuration for the entire SaMD prototype
# Change values here and they apply everywhere

# ── Vendor simulation ──────────────────────────────
VENDORS = ["Philips", "GE", "Siemens"]

# ── Clinical thresholds ────────────────────────────
THRESHOLDS = {
    "HeartRate": {"min": 40,  "max": 150},
    "SpO2":      {"min": 90,  "max": 100},
    "Glucose":   {"min": 70,  "max": 180},
    "Temperature":{"min": 35, "max": 38.5},
}

# ── Orchestration thresholds ───────────────────────
CPU_LIMIT    = 75   # above this → consider cloud
RAM_LIMIT    = 80   # above this → consider cloud
PING_HOST    = "8.8.8.8"
PING_TIMEOUT = 1    # seconds

# ── Stream optimizer ───────────────────────────────
BATCH_WINDOW_SECONDS = 5
BATCH_SIZE           = 10

# ── Database ───────────────────────────────────────
DB_PATH = "samd.db"

# ── AI model simulation ────────────────────────────
MODEL_VERSION = "v1"
DRIFT_THRESHOLD = 0.75  # below this confidence → drift alert

# ── Clinical priority levels ───────────────────────
PRIORITY = {
    "CRITICAL": 1,
    "HIGH":     2,
    "ROUTINE":  3,
}