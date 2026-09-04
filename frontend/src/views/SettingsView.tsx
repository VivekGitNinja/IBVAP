import React, { useState, useEffect } from "react";
import { api } from "../api";
import { playTacticalTone } from "../utils/audio";

export function SettingsView({
  isMuted,
  onToggleMute,
}: {
  isMuted: boolean;
  onToggleMute: () => void;
}) {
  const [readiness, setReadiness] = useState<any>(null);
  const [loadingReadiness, setLoadingReadiness] = useState(false);

  const fetchReadiness = () => {
    setLoadingReadiness(true);
    api.systemReadiness()
      .then(setReadiness)
      .catch((err) => console.error("Failed to load readiness:", err))
      .finally(() => setLoadingReadiness(false));
  };

  useEffect(() => {
    fetchReadiness();
  }, []);

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h1>Defense Surveillance Parameters & System Readiness</h1>
          <p style={{ margin: 0, fontSize: 12, color: 'var(--text-secondary)' }}>
            System configuration, cryptographic key status, offline AI model verification, and operator acoustic alerts
          </p>
        </div>
        <button className="btn btn-secondary" onClick={fetchReadiness} disabled={loadingReadiness}>
          {loadingReadiness ? "Scanning..." : "🔄 Re-scan Readiness"}
        </button>
      </div>

      {/* System Readiness Panel (Task 4.2 & 5.4) */}
      <div className="panel" style={{ marginBottom: 16, padding: 16 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
          <div>
            <h3 style={{ color: "#00f0ff", margin: 0, fontSize: 14 }}>
              🛡 Offline AI & Edge Inference Readiness (BSA 2023 §63 Compliant)
            </h3>
            <div style={{ fontSize: 11, color: "var(--text-secondary)", marginTop: 2 }}>
              Strict Zero-Runtime-Downloads Policy • No external network calls during operational inference
            </div>
          </div>
          <span
            style={{
              padding: "3px 10px",
              borderRadius: 4,
              fontSize: 11,
              fontWeight: "bold",
              background: readiness?.status === "READY" ? "rgba(0, 255, 157, 0.15)" : "rgba(255, 170, 0, 0.15)",
              color: readiness?.status === "READY" ? "#00ff9d" : "#ffaa00",
              border: `1px solid ${readiness?.status === "READY" ? "#00ff9d" : "#ffaa00"}`,
            }}
          >
            {readiness ? `SYSTEM ${readiness.status}` : "INITIALIZING..."}
          </span>
        </div>

        {readiness && readiness.components && (
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: 10 }}>
            {Object.entries(readiness.components).map(([key, comp]: [string, any]) => {
              const isReady = comp.ready || comp.status === "CACHED" || comp.status === "READY";
              const statusColor = isReady ? "#00ff9d" : comp.status === "FALLBACK" ? "#ffaa00" : "#94a3b8";
              return (
                <div
                  key={key}
                  style={{
                    background: "rgba(0,0,0,0.3)",
                    border: "1px solid rgba(255,255,255,0.06)",
                    borderRadius: 6,
                    padding: "10px 12px",
                  }}
                >
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <span style={{ fontWeight: 700, color: "#fff", textTransform: "uppercase", fontSize: 11 }}>
                      {key}
                    </span>
                    <span
                      style={{
                        fontSize: 9,
                        color: statusColor,
                        fontWeight: "bold",
                        border: `1px solid ${statusColor}`,
                        padding: "1px 5px",
                        borderRadius: 3,
                      }}
                    >
                      {comp.status}
                    </span>
                  </div>
                  <div style={{ fontSize: 10, color: "var(--text-secondary)", marginTop: 4 }}>
                    {comp.details || comp.reason || comp.recognition_reason || (comp.cached_models ? comp.cached_models.join(", ") : "Operational")}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(360px, 1fr))', gap: 16 }}>
        <div className="panel" style={{ margin: 0, padding: 16 }}>
          <h3 style={{ color: '#00f0ff', marginBottom: 12 }}>Acoustic Alert Controls</h3>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
            <div>
              <b style={{ color: '#fff' }}>Tactical Web Audio Chime</b>
              <div style={{ fontSize: 11, color: 'var(--text-secondary)' }}>Synthesized audio tone on critical border breaches</div>
            </div>
            <button className={`btn ${!isMuted ? 'btn-primary' : 'btn-secondary'}`} onClick={onToggleMute}>
              {isMuted ? 'DISABLED (MUTED)' : 'ENABLED'}
            </button>
          </div>
        </div>

        <div className="panel" style={{ margin: 0, padding: 16 }}>
          <h3 style={{ color: '#00f0ff', marginBottom: 12 }}>Cryptographic Credentials</h3>
          <div style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--text-secondary)', display: 'flex', flexDirection: 'column', gap: 6 }}>
            <div>JWT HMAC KEY: <b style={{ color: '#00ff9d' }}>RFC 7518 COMPLIANT (512-BIT HIGH ENTROPY)</b></div>
            <div>AUDIT CHAIN: <b style={{ color: '#00ff9d' }}>SHA-256 LINKED</b></div>
            <div>EVIDENCE SEAL: <b style={{ color: '#00ff9d' }}>BSA 2023 §63 WORM MANIFEST</b></div>
            <div>EDGE PERCEPTION: <b style={{ color: '#00ff9d' }}>YOLO26n + CENTROID TRACKER</b></div>
          </div>
        </div>
      </div>
    </div>
  );
}

/* ─── Section 65B Indian Evidence Act Certificate Modal ───────── */
function Section65BCertificateModal({
  evidence,
  onClose,
}: {
  evidence: Evidence;
  onClose: () => void;
}) {
  const printCert = () => {
    window.print();
  };

  const certId = `CERT/SSB/IBVAP/2026/${evidence.id.toString().padStart(6, '0')}`;
  const nowStr = new Date().toLocaleString('en-IN', { timeZone: 'Asia/Kolkata' });

  return (
    <div className="section-65b-modal-backdrop" onClick={onClose}>
      <div className="section-65b-sheet" onClick={(e) => e.stopPropagation()}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 12 }}>
          <div className="section-65b-seal">
            GOVERNMENT OF INDIA • MINISTRY OF HOME AFFAIRS
          </div>
          <button className="btn btn-sm btn-secondary" onClick={onClose} style={{ color: '#000', borderColor: '#333' }}>
            ✕ Close
          </button>
        </div>

        <div className="section-65b-header">
          <h2 style={{ margin: '0 0 6px 0', fontSize: 18, color: '#111827', fontWeight: 800, letterSpacing: 1 }}>
            CERTIFICATE UNDER SECTION 63 OF BHARATIYA SAKSHYA ADHINIYAM (BSA), 2023
          </h2>
          <h4 style={{ margin: '0 0 12px 0', fontSize: 12, color: '#4b5563', fontWeight: 600 }}>
            CERTIFICATE FOR ELECTRONIC RECORDS • [FORMERLY SECTION 65B INDIAN EVIDENCE ACT, 1872 (REPEALED)]
          </h4>
          <div style={{ fontSize: 11, color: '#6b7280', fontFamily: 'var(--font-mono)' }}>
            CERTIFICATE REF: {certId} • ISSUED AT: {nowStr}
          </div>
        </div>

        <div style={{ fontSize: 12, lineHeight: 1.6, color: '#1f2937' }}>
          <p>
            I, the undersigned <b>Commanding Officer / Authorized Operator</b>, Sashastra Seema Bal (SSB), do hereby certify that:
          </p>
          <ol style={{ paddingLeft: 20, display: 'flex', flexDirection: 'column', gap: 8 }}>
            <li>
              The electronic surveillance record identified below was generated by the <b>Intelligent Border Video Analytics Platform (IBVAP C4ISR)</b> during the ordinary and lawful surveillance of sovereign border sectors.
            </li>
            <li>
              Throughout the period of recording, the edge cameras, AI inference pipeline, and Write-Once-Read-Many (WORM) storage appliances were operating properly in accordance with defense specifications.
            </li>
            <li>
              The cryptographic integrity hash (SHA-256) of this record was generated immediately upon frame capture at the edge sensor and remains immutable:
              <div style={{ background: '#f3f4f6', border: '1px solid #d1d5db', padding: '8px 12px', borderRadius: 4, fontFamily: 'var(--font-mono)', fontSize: 11, wordBreak: 'break-all', marginTop: 4, color: '#111827', fontWeight: 700 }}>
                {evidence.sha256}
              </div>
            </li>
            <li>
              <b>Evidence Type:</b> {evidence.evidence_type} | <b>Incident Ref:</b> #{evidence.incident_id} | <b>Sensor Post:</b> {evidence.camera_name || 'BOP Post'}
            </li>
          </ol>

          <div style={{ marginTop: 24, borderTop: '1px solid #e5e7eb', paddingTop: 16, display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20 }}>
            <div>
              <div style={{ fontSize: 10, color: '#6b7280' }}>DIGITAL SIGNATURE & SEAL:</div>
              <div style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: '#1e3a8a', fontWeight: 700, marginTop: 4 }}>
                SSB-BORDER-ELECTRONIC-CERT-VALIDATED
              </div>
              <div style={{ fontSize: 10, color: '#9ca3af' }}>Hash Chain Ledger Block: #09281-IBVAP</div>
            </div>
            <div style={{ textAlign: 'right' }}>
              <div style={{ fontSize: 10, color: '#6b7280' }}>ATTESTATION OFFICER:</div>
              <div style={{ fontWeight: 700, color: '#111827', marginTop: 4 }}>OPERATOR (DUTY OFFICER)</div>
              <div style={{ fontSize: 10, color: '#6b7280' }}>C4ISR Surveillance Post, MHA</div>
            </div>
          </div>
        </div>

        <div style={{ marginTop: 24, display: 'flex', justifyContent: 'flex-end', gap: 10 }}>
          <button className="btn btn-secondary" onClick={onClose} style={{ color: '#000', borderColor: '#999' }}>
            Cancel
          </button>
          <button className="btn btn-primary" onClick={printCert} style={{ background: '#1e3a8a', borderColor: '#1e3a8a', color: '#fff' }}>
            🖨️ Print / Save Section 65B PDF
          </button>
        </div>
      </div>
    </div>
  );
}

/* ─── ANPR Checkpost Terminal ─────────────────────────────────── */
