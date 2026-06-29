import sys
import os
import sqlite3
import json
import random
from datetime import datetime
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import DB_PATH, DRIFT_THRESHOLD, MODEL_VERSION

def get_connection():
    return sqlite3.connect(DB_PATH)

# ══════════════════════════════════════════════════
# MODEL REGISTRY
# ══════════════════════════════════════════════════

def get_active_model():
    """Returns the currently deployed model"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM model_registry WHERE status='DEPLOYED'")
    row = cursor.fetchone()
    conn.close()
    return row

def get_all_models():
    """Returns all models in registry"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM model_registry ORDER BY id")
    rows = cursor.fetchall()
    conn.close()
    return rows

def submit_model(version, accuracy):
    """Submit a new model for validation"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO model_registry
            (model_version, status, accuracy, created_at)
            VALUES (?, 'PENDING', ?, ?)
        """, (version, accuracy, datetime.now().isoformat()))
        conn.commit()
        result = f"Model {version} submitted — status: PENDING"
    except sqlite3.IntegrityError:
        result = f"Model {version} already exists"
    conn.close()
    return result

# ══════════════════════════════════════════════════
# VALIDATION MANAGER
# ══════════════════════════════════════════════════

def approve_model(version, approved_by="admin"):
    """Approve a pending model for deployment"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT status FROM model_registry WHERE model_version=?", (version,))
    row = cursor.fetchone()

    if not row:
        conn.close()
        return f"Model {version} not found"

    if row[0] != "PENDING":
        conn.close()
        return f"Model {version} is {row[0]} — only PENDING models can be approved"

    cursor.execute("""
        UPDATE model_registry
        SET status='APPROVED', approved_by=?, deployed_at=?
        WHERE model_version=?
    """, (approved_by, datetime.now().isoformat(), version))
    conn.commit()
    conn.close()

    _log_governance(version, "APPROVED", approved_by)
    return f"Model {version} APPROVED by {approved_by}"

def reject_model(version, rejected_by="admin"):
    """Reject a pending model"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE model_registry SET status='REJECTED'
        WHERE model_version=?
    """, (version,))
    conn.commit()
    conn.close()
    _log_governance(version, "REJECTED", rejected_by)
    return f"Model {version} REJECTED"

# ══════════════════════════════════════════════════
# VERSION MANAGER + ROLLBACK MANAGER
# ══════════════════════════════════════════════════

def deploy_model(version):
    """
    Deploy an approved model.
    Marks previous deployed model as ROLLED_BACK.
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT status FROM model_registry WHERE model_version=?", (version,))
    row = cursor.fetchone()

    if not row:
        conn.close()
        return f"Model {version} not found"

    if row[0] != "APPROVED":
        conn.close()
        return f"Model {version} is {row[0]} — only APPROVED models can be deployed"

    # Rollback current deployed model
    cursor.execute("""
        UPDATE model_registry SET status='ROLLED_BACK'
        WHERE status='DEPLOYED'
    """)

    # Deploy new model
    cursor.execute("""
        UPDATE model_registry
        SET status='DEPLOYED', deployed_at=?
        WHERE model_version=?
    """, (datetime.now().isoformat(), version))

    conn.commit()
    conn.close()

    _log_governance(version, "DEPLOYED", "system")
    return f"Model {version} DEPLOYED — previous model rolled back"

def rollback(target_version):
    """Emergency rollback to a specific version"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE model_registry SET status='ROLLED_BACK'
        WHERE status='DEPLOYED'
    """)
    cursor.execute("""
        UPDATE model_registry SET status='DEPLOYED', deployed_at=?
        WHERE model_version=?
    """, (datetime.now().isoformat(), target_version))

    conn.commit()
    conn.close()

    _log_governance(target_version, "ROLLBACK", "drift_detector")
    return f"Emergency rollback → {target_version} now DEPLOYED"

# ══════════════════════════════════════════════════
# DRIFT DETECTION MONITOR
# ══════════════════════════════════════════════════

def check_drift():
    """
    Analyzes confidence logs to detect model drift.
    If drift detected → triggers rollback automatically.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT confidence FROM confidence_log
        ORDER BY id DESC LIMIT 10
    """)
    rows = cursor.fetchall()
    conn.close()

    if len(rows) < 3:
        return {
            "status": "INSUFFICIENT_DATA",
            "message": "Need at least 3 confidence logs",
            "action": "NONE"
        }

    confidences = [r[0] for r in rows]
    avg = round(sum(confidences) / len(confidences), 3)
    recent_avg = round(sum(confidences[:3]) / 3, 3)

    drift_detected = recent_avg < DRIFT_THRESHOLD

    if drift_detected:
        active = get_active_model()
        active_version = active[1] if active else "v1"

        # Find previous stable version
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT model_version FROM model_registry
            WHERE status='ROLLED_BACK'
            ORDER BY id DESC LIMIT 1
        """)
        prev = cursor.fetchone()
        conn.close()

        rollback_target = prev[0] if prev else "v1"
        rollback_msg = rollback(rollback_target)

        return {
            "status": "DRIFT_DETECTED",
            "avg_confidence": avg,
            "recent_avg": recent_avg,
            "threshold": DRIFT_THRESHOLD,
            "action": f"AUTO_ROLLBACK → {rollback_target}",
            "message": rollback_msg
        }

    return {
        "status": "STABLE",
        "avg_confidence": avg,
        "recent_avg": recent_avg,
        "threshold": DRIFT_THRESHOLD,
        "action": "NONE",
        "message": "Model performance stable"
    }

# ══════════════════════════════════════════════════
# FEDERATED LEARNING COORDINATOR
# ══════════════════════════════════════════════════

def federated_avg(hospital_weights):
    """
    Simulates FedAvg — averages model weights from
    multiple hospitals without sharing raw patient data.
    Each hospital trains locally, shares only weights.
    """
    if not hospital_weights:
        return None

    num_hospitals = len(hospital_weights)
    avg_weights = {}

    all_keys = hospital_weights[0].keys()
    for key in all_keys:
        values = [h[key] for h in hospital_weights]
        avg_weights[key] = round(sum(values) / num_hospitals, 4)

    return avg_weights

def simulate_federated_round():
    """
    Simulates one round of federated learning
    across 3 hospitals.
    """
    hospitals = {
        "Hospital_A_Indore": {
            "w1": round(random.uniform(0.80, 0.95), 4),
            "w2": round(random.uniform(0.70, 0.90), 4),
            "bias": round(random.uniform(0.01, 0.05), 4)
        },
        "Hospital_B_Bhopal": {
            "w1": round(random.uniform(0.80, 0.95), 4),
            "w2": round(random.uniform(0.70, 0.90), 4),
            "bias": round(random.uniform(0.01, 0.05), 4)
        },
        "Hospital_C_Mumbai": {
            "w1": round(random.uniform(0.80, 0.95), 4),
            "w2": round(random.uniform(0.70, 0.90), 4),
            "bias": round(random.uniform(0.01, 0.05), 4)
        }
    }

    aggregated = federated_avg(list(hospitals.values()))

    return {
        "hospitals": hospitals,
        "aggregated_weights": aggregated,
        "round": "federated_round_1",
        "privacy": "Raw patient data never left hospitals — only weights shared"
    }

# ══════════════════════════════════════════════════
# GOVERNANCE MANAGER
# ══════════════════════════════════════════════════

def _log_governance(model_version, action, actor):
    from tier3_cloud.storage import log_audit
    log_audit(
        event_type=action,
        component="model_registry",
        description=f"Model {model_version} — {action} by {actor}",
        clinical_core=True
    )

def get_governance_log():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT timestamp, event_type, description
        FROM audit_trail
        WHERE component='model_registry'
        ORDER BY id DESC LIMIT 10
    """)
    rows = cursor.fetchall()
    conn.close()
    return rows


# ══════════════════════════════════════════════════
# TEST
# ══════════════════════════════════════════════════

if __name__ == "__main__":
    from tier3_cloud.storage import init_db, seed_model_registry, log_confidence

    init_db()
    seed_model_registry()

    print("\n" + "="*55)
    print("  AI Lifecycle Management Framework — TEST")
    print("="*55)

    # ── Model Registry ────────────────────────────
    print("\n--- Model Registry ---")
    for m in get_all_models():
        print(f"  {m[1]:<6} | {m[2]:<12} | accuracy={m[3]} | approved_by={m[4]}")

    # ── Validation + Deployment ───────────────────
    print("\n--- Validation Manager ---")
    print(f"  {approve_model('v2')}")

    print("\n--- Version Manager + Rollback ---")
    print(f"  {deploy_model('v2')}")

    print("\n--- Updated Registry ---")
    for m in get_all_models():
        print(f"  {m[1]:<6} | {m[2]:<12} | accuracy={m[3]}")

    # ── Drift Detection ───────────────────────────
    print("\n--- Drift Detection Monitor ---")
    # Seed some low confidence logs to trigger drift
    for conf in [0.91, 0.88, 0.85, 0.71, 0.68, 0.65]:
        log_confidence("v2", conf, conf < DRIFT_THRESHOLD)

    result = check_drift()
    print(f"  Status    : {result['status']}")
    print(f"  Recent avg: {result['recent_avg']}")
    print(f"  Threshold : {result['threshold']}")
    print(f"  Action    : {result['action']}")
    print(f"  Message   : {result['message']}")

    # ── Federated Learning ────────────────────────
    print("\n--- Federated Learning Coordinator ---")
    fed = simulate_federated_round()
    print(f"  Hospitals participating: {len(fed['hospitals'])}")
    for name, weights in fed["hospitals"].items():
        print(f"    {name}: {weights}")
    print(f"  Aggregated (FedAvg): {fed['aggregated_weights']}")
    print(f"  Privacy: {fed['privacy']}")

    # ── Governance Log ────────────────────────────
    print("\n--- Governance Manager (Audit Trail) ---")
    for entry in get_governance_log():
        print(f"  {entry[0][:19]} | {entry[1]:<12} | {entry[2]}")