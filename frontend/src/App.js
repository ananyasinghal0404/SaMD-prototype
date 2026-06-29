import { useState, useEffect, useRef } from "react";

const API = "http://localhost:8000";
const WS  = "ws://localhost:8000/ws";

const STEPS = [
  { id: "sensor",           label: "Sensors",                tier: 1 },
  { id: "preprocessing",    label: "Basic Preprocessing",    tier: 1 },
  { id: "threshold",        label: "Threshold Detection",    tier: 1 },
  { id: "interoperability", label: "Interoperability Engine",tier: 2 },
  { id: "stream_optimizer", label: "Stream Optimizer",       tier: 2 },
  { id: "local_buffer",     label: "Local Buffer",           tier: 2 },
  { id: "orchestration",    label: "Orchestration Engine",   tier: 2 },
  { id: "edge_execution",   label: "Edge Execution Engine",  tier: 2 },
  { id: "cloud",            label: "Cloud Layer",            tier: 3 },
  { id: "event_manager",    label: "Event Manager",          tier: 3 },
];

const TIER_COLORS = {
  1: { bg: "#0d3d3d", border: "#1affe4", label: "Tier 1 — Device Layer" },
  2: { bg: "#1a0a3d", border: "#7c3aed", label: "Tier 2 — Intelligent Edge" },
  3: { bg: "#0a1a3d", border: "#3b82f6", label: "Tier 3 — Cloud Layer" },
};

export default function App() {
  const [activeStep, setActiveStep]   = useState(null);
  const [stepData, setStepData]       = useState({});
  const [running, setRunning]         = useState(false);
  const [log, setLog]                 = useState([]);
  const [analytics, setAnalytics]     = useState(null);
  const [models, setModels]           = useState([]);
  const [audit, setAudit]             = useState([]);
  const [decision, setDecision]       = useState(null);
  const wsRef = useRef(null);

  // Load analytics on mount
  useEffect(() => {
    fetchAnalytics();
    fetchModels();
    fetchAudit();
  }, []);

  async function fetchAnalytics() {
    try {
      const r = await fetch(`${API}/analytics`);
      const d = await r.json();
      setAnalytics(d);
    } catch(e) {}
  }

  async function fetchModels() {
    try {
      const r = await fetch(`${API}/models`);
      setModels(await r.json());
    } catch(e) {}
  }

  async function fetchAudit() {
    try {
      const r = await fetch(`${API}/audit`);
      setAudit(await r.json());
    } catch(e) {}
  }

  async function approveModel(version) {
    await fetch(`${API}/models/${version}/approve`, { method: "POST" });
    fetchModels();
    fetchAudit();
  }

  async function deployModel(version) {
    await fetch(`${API}/models/${version}/deploy`, { method: "POST" });
    fetchModels();
    fetchAudit();
  }

  function startSimulation() {
    if (running) return;
    setRunning(true);
    setActiveStep(null);
    setStepData({});
    setDecision(null);

    const ws = new WebSocket(WS);
    wsRef.current = ws;

    ws.onopen = () => {
      ws.send("start");
      addLog("🚀 Simulation started");
    };

    ws.onmessage = (e) => {
      const msg = JSON.parse(e.data);
      const { step, data } = msg;

      setActiveStep(step);
      setStepData(prev => ({ ...prev, [step]: data }));

      if (step === "orchestration" && data.decision) {
        setDecision(data.decision);
      }

      addLog(`→ ${step}: ${JSON.stringify(data).slice(0, 80)}`);

      if (step === "complete" || step === "error") {
        setRunning(false);
        setActiveStep("complete");
        fetchAnalytics();
        fetchModels();
        fetchAudit();
        ws.close();
      }
    };

    ws.onerror = () => {
      addLog("❌ WebSocket error");
      setRunning(false);
    };
  }

  function addLog(msg) {
    const time = new Date().toLocaleTimeString();
    setLog(prev => [`[${time}] ${msg}`, ...prev].slice(0, 30));
  }

  return (
    <div style={styles.app}>
      {/* Header */}
      <div style={styles.header}>
        <h1 style={styles.title}>🏥 SaMD Architecture Prototype</h1>
        <p style={styles.subtitle}>Generic Software as a Medical Device — Live Simulation</p>
        <button
          style={{ ...styles.btn, opacity: running ? 0.5 : 1 }}
          onClick={startSimulation}
          disabled={running}
        >
          {running ? "⏳ Running..." : "▶ Start Simulation"}
        </button>
      </div>

      <div style={styles.body}>
        {/* LEFT: Architecture diagram */}
        <div style={styles.diagram}>
          <h3 style={styles.panelTitle}>Architecture Pipeline</h3>
          {[1, 2, 3].map(tier => (
            <div key={tier} style={{
              ...styles.tierBox,
              borderColor: TIER_COLORS[tier].border,
              background: TIER_COLORS[tier].bg,
            }}>
              <div style={{ ...styles.tierLabel, color: TIER_COLORS[tier].border }}>
                {TIER_COLORS[tier].label}
              </div>
              {STEPS.filter(s => s.tier === tier).map(step => {
                const isActive  = activeStep === step.id;
                const isDone    = stepData[step.id] !== undefined;
                const isCurrent = activeStep === step.id;

                // Hide edge_execution if cloud decision, hide cloud if edge
                if (step.id === "edge_execution" && decision === "CLOUD") return null;
                if (step.id === "cloud" && decision === "EDGE") return null;

                return (
                  <div key={step.id} style={{
                    ...styles.stepBox,
                    borderColor: isActive ? "#fff" : isDone ? TIER_COLORS[tier].border : "#333",
                    background: isActive ? TIER_COLORS[tier].border + "33" : "transparent",
                    boxShadow: isActive ? `0 0 12px ${TIER_COLORS[tier].border}` : "none",
                  }}>
                    <div style={styles.stepHeader}>
                      <span style={styles.stepIcon}>
                        {isActive ? "⚡" : isDone ? "✅" : "○"}
                      </span>
                      <span style={styles.stepName}>{step.label}</span>
                    </div>
                    {isDone && stepData[step.id] && (
                      <div style={styles.stepData}>
                        {step.id === "sensor" && (
                          <span>Vendor: {stepData[step.id].vendor}</span>
                        )}
                        {step.id === "threshold" && (
                          <span>{stepData[step.id].has_critical
                            ? `🚨 ${stepData[step.id].alert_messages[0]}`
                            : "✅ All vitals normal"}</span>
                        )}
                        {step.id === "interoperability" && (
                          <span>HR={stepData[step.id].HeartRate} bpm | SpO2={stepData[step.id].SpO2}%</span>
                        )}
                        {step.id === "orchestration" && (
                          <span>
                            {stepData[step.id].priority} | CPU={stepData[step.id].cpu}% | {stepData[step.id].network}
                            <br/>
                            <strong>→ {stepData[step.id].decision}</strong>
                          </span>
                        )}
                        {step.id === "edge_execution" && (
                          <span>
                            Confidence: {stepData[step.id].confidence}
                            <br/>
                            {stepData[step.id].findings && stepData[step.id].findings.slice(0,2).map((f,i) => (
                              <span key={i} style={{ color: f.includes("normal") ? "#4ade80" : "#f87171" }}>
                                {f.includes("normal") ? "✅" : "🚨"} {f}<br/>
                              </span>
                            ))}
                          </span>
                        )}
                        {step.id === "cloud" && (
                          <span>Processed in cloud ✅</span>
                        )}
                        {step.id === "event_manager" && (
                          <span>🚨 Alert sent | {stepData[step.id].actions} actions</span>
                        )}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          ))}
        </div>

        {/* MIDDLE: Live log + Analytics */}
        <div style={styles.middle}>
          {/* Live log */}
          <div style={styles.panel}>
            <h3 style={styles.panelTitle}>📡 Live Pipeline Log</h3>
            <div style={styles.logBox}>
              {log.map((l, i) => (
                <div key={i} style={styles.logLine}>{l}</div>
              ))}
            </div>
          </div>

          {/* Analytics */}
          {analytics && (
            <div style={styles.panel}>
              <h3 style={styles.panelTitle}>📊 Analytics</h3>
              <div style={styles.statsGrid}>
                <Stat label="Total Readings" value={analytics.summary.total_readings} />
                <Stat label="Edge Decisions" value={`${analytics.summary.edge_percent}%`} />
                <Stat label="Avg HR" value={`${analytics.summary.heart_rate.avg} bpm`} />
                <Stat label="Avg SpO2" value={`${analytics.summary.spo2.avg}%`} />
                <Stat label="Avg Confidence" value={analytics.summary.avg_confidence} />
                <Stat label="Drift Trend" value={analytics.drift_trend.trend} />
              </div>
            </div>
          )}
        </div>

        {/* RIGHT: AI Lifecycle + Audit */}
        <div style={styles.right}>
          {/* Model Registry */}
          <div style={styles.panel}>
            <h3 style={styles.panelTitle}>🤖 AI Lifecycle</h3>
            {models.map(m => (
              <div key={m.version} style={styles.modelRow}>
                <span style={{
                  ...styles.modelVersion,
                  color: m.status === "DEPLOYED" ? "#4ade80"
                       : m.status === "PENDING"  ? "#facc15"
                       : m.status === "APPROVED" ? "#60a5fa"
                       : "#f87171"
                }}>
                  {m.version}
                </span>
                <span style={styles.modelStatus}>{m.status}</span>
                <span style={styles.modelAcc}>acc={m.accuracy}</span>
                <div style={styles.modelBtns}>
                  {m.status === "PENDING" && (
                    <button style={styles.smallBtn} onClick={() => approveModel(m.version)}>
                      Approve
                    </button>
                  )}
                  {m.status === "APPROVED" && (
                    <button style={{ ...styles.smallBtn, background: "#16a34a" }}
                      onClick={() => deployModel(m.version)}>
                      Deploy
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>

          {/* Audit Trail */}
          <div style={styles.panel}>
            <h3 style={styles.panelTitle}>📋 Audit Trail</h3>
            <div style={styles.auditBox}>
              {audit.slice(0, 8).map((a, i) => (
                <div key={i} style={styles.auditRow}>
                  <span style={{
                    color: a.clinical_core ? "#f87171" : "#4ade80",
                    fontSize: 10
                  }}>
                    {a.clinical_core ? "★" : "○"}
                  </span>
                  <span style={styles.auditTime}>
                    {a.timestamp ? a.timestamp.slice(11, 19) : ""}
                  </span>
                  <span style={styles.auditDesc}>
                    {a.description ? a.description.slice(0, 40) : ""}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function Stat({ label, value }) {
  return (
    <div style={styles.stat}>
      <div style={styles.statValue}>{value}</div>
      <div style={styles.statLabel}>{label}</div>
    </div>
  );
}

const styles = {
  app: {
    background: "#0a0a0f",
    minHeight: "100vh",
    color: "#e2e8f0",
    fontFamily: "monospace",
    padding: 16,
  },
  header: {
    textAlign: "center",
    marginBottom: 20,
    paddingBottom: 16,
    borderBottom: "1px solid #1e293b",
  },
  title: { fontSize: 22, margin: 0, color: "#f1f5f9" },
  subtitle: { fontSize: 12, color: "#64748b", margin: "4px 0 12px" },
  btn: {
    background: "#7c3aed",
    color: "#fff",
    border: "none",
    padding: "10px 28px",
    borderRadius: 8,
    fontSize: 14,
    cursor: "pointer",
    fontWeight: "bold",
  },
  body: {
    display: "flex",
    gap: 16,
    alignItems: "flex-start",
  },
  diagram: { flex: 1.2, minWidth: 0 },
  middle:  { flex: 1,   minWidth: 0 },
  right:   { flex: 1,   minWidth: 0 },
  tierBox: {
    border: "1px solid",
    borderRadius: 10,
    padding: 10,
    marginBottom: 12,
  },
  tierLabel: {
    fontSize: 11,
    fontWeight: "bold",
    marginBottom: 8,
    textTransform: "uppercase",
    letterSpacing: 1,
  },
  stepBox: {
    border: "1px solid",
    borderRadius: 6,
    padding: "6px 10px",
    marginBottom: 6,
    transition: "all 0.3s ease",
  },
  stepHeader: { display: "flex", alignItems: "center", gap: 6 },
  stepIcon:   { fontSize: 12 },
  stepName:   { fontSize: 12, fontWeight: "bold" },
  stepData:   { fontSize: 11, color: "#94a3b8", marginTop: 4, paddingLeft: 18 },
  panel: {
    background: "#0f172a",
    border: "1px solid #1e293b",
    borderRadius: 10,
    padding: 12,
    marginBottom: 12,
  },
  panelTitle: { fontSize: 13, margin: "0 0 10px", color: "#cbd5e1" },
  logBox: {
    height: 180,
    overflowY: "auto",
    fontSize: 10,
    color: "#64748b",
  },
  logLine: { padding: "2px 0", borderBottom: "1px solid #0f172a" },
  statsGrid: {
    display: "grid",
    gridTemplateColumns: "1fr 1fr 1fr",
    gap: 8,
  },
  stat: {
    background: "#1e293b",
    borderRadius: 6,
    padding: "8px 10px",
    textAlign: "center",
  },
  statValue: { fontSize: 14, fontWeight: "bold", color: "#7c3aed" },
  statLabel: { fontSize: 10, color: "#64748b", marginTop: 2 },
  modelRow: {
    display: "flex",
    alignItems: "center",
    gap: 8,
    padding: "6px 0",
    borderBottom: "1px solid #1e293b",
    fontSize: 12,
  },
  modelVersion: { fontWeight: "bold", width: 30 },
  modelStatus:  { flex: 1, color: "#94a3b8" },
  modelAcc:     { color: "#64748b", fontSize: 11 },
  modelBtns:    {},
  smallBtn: {
    background: "#7c3aed",
    color: "#fff",
    border: "none",
    padding: "3px 8px",
    borderRadius: 4,
    fontSize: 11,
    cursor: "pointer",
  },
  auditBox: { fontSize: 11 },
  auditRow: {
    display: "flex",
    gap: 6,
    padding: "3px 0",
    borderBottom: "1px solid #1e293b",
    alignItems: "center",
  },
  auditTime: { color: "#64748b", minWidth: 60 },
  auditDesc: { color: "#94a3b8", flex: 1 },
};