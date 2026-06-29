import sys
import os
import sqlite3
import json
from datetime import datetime
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import DB_PATH

def get_connection():
    return sqlite3.connect(DB_PATH)

def init_db():
    """Create all tables if they don't exist"""
    conn = get_connection()
    cursor = conn.cursor()

    # ── Readings table ────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS readings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            vendor TEXT,
            heart_rate REAL,
            spo2 REAL,
            glucose REAL,
            temperature REAL,
            decision TEXT,
            confidence REAL,
            findings TEXT
        )
    """)

    # ── Audit trail table ─────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS audit_trail (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            event_type TEXT,
            component TEXT,
            description TEXT,
            clinical_core INTEGER
        )
    """)

    # ── Model registry table ──────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS model_registry (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            model_version TEXT UNIQUE,
            status TEXT,
            accuracy REAL,
            approved_by TEXT,
            created_at TEXT,
            deployed_at TEXT
        )
    """)

    # ── Confidence log table (for drift detection) ─
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS confidence_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            model_version TEXT,
            confidence REAL,
            drift_suspected INTEGER
        )
    """)

    conn.commit()
    conn.close()
    return True

def save_reading(record, decision, inference_result):
    """Save a processed reading to the database"""
    conn = get_connection()
    cursor = conn.cursor()

    findings_str = json.dumps(inference_result.get("findings", []))

    cursor.execute("""
        INSERT INTO readings
        (timestamp, vendor, heart_rate, spo2, glucose, temperature, decision, confidence, findings)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        datetime.now().isoformat(),
        record.get("original_vendor", "Unknown"),
        record.get("HeartRate"),
        record.get("SpO2"),
        record.get("Glucose"),
        record.get("Temperature"),
        decision,
        inference_result.get("confidence"),
        findings_str
    ))

    conn.commit()
    conn.close()

def log_audit(event_type, component, description, clinical_core=False):
    """Write an entry to the audit trail"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO audit_trail
        (timestamp, event_type, component, description, clinical_core)
        VALUES (?, ?, ?, ?, ?)
    """, (
        datetime.now().isoformat(),
        event_type,
        component,
        description,
        1 if clinical_core else 0
    ))

    conn.commit()
    conn.close()

def log_confidence(model_version, confidence, drift_suspected):
    """Log confidence score for drift detection"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO confidence_log
        (timestamp, model_version, confidence, drift_suspected)
        VALUES (?, ?, ?, ?)
    """, (
        datetime.now().isoformat(),
        model_version,
        confidence,
        1 if drift_suspected else 0
    ))

    conn.commit()
    conn.close()

def seed_model_registry():
    """Add initial models to registry"""
    conn = get_connection()
    cursor = conn.cursor()

    models = [
        ("v1", "DEPLOYED", 0.94, "admin", "2026-06-01", "2026-06-01"),
        ("v2", "PENDING",  0.96, None,    "2026-06-28", None),
        ("v3", "REJECTED", 0.81, "admin", "2026-05-15", None),
    ]

    for m in models:
        cursor.execute("""
            INSERT OR IGNORE INTO model_registry
            (model_version, status, accuracy, approved_by, created_at, deployed_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, m)

    conn.commit()
    conn.close()

def get_recent_readings(limit=5):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM readings ORDER BY id DESC LIMIT ?", (limit,))
    rows = cursor.fetchall()
    conn.close()
    return rows

def get_audit_trail(limit=10):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM audit_trail ORDER BY id DESC LIMIT ?", (limit,))
    rows = cursor.fetchall()
    conn.close()
    return rows

def get_model_registry():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM model_registry ORDER BY id")
    rows = cursor.fetchall()
    conn.close()
    return rows


if __name__ == "__main__":
    print("\n" + "="*55)
    print("  Storage Module — TEST")
    print("="*55)

    print("\n  Initializing database...")
    init_db()
    seed_model_registry()
    print("  Database created: samd.db ✅")

    # ── Save a fake reading ───────────────────────
    fake_record = {
        "original_vendor": "Philips",
        "HeartRate": 160,
        "SpO2": 88,
        "Glucose": 120,
        "Temperature": 37.2
    }
    fake_inference = {
        "confidence": 0.92,
        "findings": ["Arrhythmia suspected", "Hypoxia detected"]
    }
    save_reading(fake_record, "EDGE", fake_inference)
    print("  Reading saved ✅")

    # ── Log audit entries ─────────────────────────
    log_audit("INFERENCE", "edge_execution_engine",
              "Arrhythmia detected — confidence 0.92", clinical_core=True)
    log_audit("MODEL_UPDATE", "model_registry",
              "model_v2 submitted for validation", clinical_core=True)
    log_audit("UI_UPDATE", "dashboard",
              "Dashboard theme updated", clinical_core=False)
    print("  Audit entries logged ✅")

    # ── Log confidence ────────────────────────────
    log_confidence("v1", 0.92, False)
    log_confidence("v1", 0.84, False)
    log_confidence("v1", 0.71, True)
    print("  Confidence logs saved ✅")

    # ── Read back ─────────────────────────────────
    print("\n  Recent readings:")
    for row in get_recent_readings():
        print(f"    {row}")

    print("\n  Audit trail:")
    for row in get_audit_trail():
        print(f"    {row}")

    print("\n  Model registry:")
    for row in get_model_registry():
        print(f"    {row}")