import React, { useState, useEffect } from "react";
import { api } from "../api";
import { playTacticalTone, fmtTime } from "../utils/audio";

function Empty({ text }: { text: string }) {
  return (
    <div style={{ textAlign: "center", padding: "40px 10px", color: "var(--text-ghost)", fontSize: 12 }}>
      {text}
    </div>
  );
}

export function FRSView({ openInc }: { openInc?: (id: number) => void }) {
  const [suspects, setSuspects] = useState<any[]>([]);
  const [matches, setMatches] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [showEnroll, setShowEnroll] = useState(false);
  const [name, setName] = useState("");
  const [notes, setNotes] = useState("");
  const [enrollFile, setEnrollFile] = useState<File | null>(null);
  const [feedback, setFeedback] = useState<string | null>(null);
  const [probeFile, setProbeFile] = useState<File | null>(null);
  const [isVerifyingProbe, setIsVerifyingProbe] = useState(false);
  const [probeResult, setProbeResult] = useState<any>(null);

  const handleVerifyProbe = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!probeFile) return;
    setIsVerifyingProbe(true);
    playTacticalTone("click");
    setProbeResult(null);
    try {
      const res = await api.frsVerifyProbe(probeFile);
      setProbeResult(res);
      if (res.matched) {
        playTacticalTone("alert");
        setFeedback(`🚨 POSITIVE BIOMETRIC MATCH: Subject identified as ${res.subject_name} (${res.similarity_percent} similarity)!`);
      } else {
        playTacticalTone("verify");
        setFeedback(res.face_detected ? "✓ Face detected, but no matching identity in border watchlist gallery." : `⚠️ ${res.message}`);
      }
    } catch (err: any) {
      setFeedback(`Probe Verification Error: ${err.message}`);
    }
    setIsVerifyingProbe(false);
  };

  const loadData = () => {
    setLoading(true);
    Promise.all([
      api.watchlist().catch(() => []),
      api.watchlistMatches().catch(() => []),
    ])
      .then(([wsList, matchEvents]) => {
        setSuspects(wsList);
        setMatches(matchEvents);
      })
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleDelete = async (id: number) => {
    playTacticalTone("click");
    if (!confirm("Are you sure you want to remove this subject from the biometric watchlist?")) return;
    try {
      await api.deleteWatchlist(id);
      playTacticalTone("verify");
      setFeedback("✓ Subject removed from watchlist.");
      loadData();
    } catch (err: any) {
      setFeedback(`Delete error: ${err.message}`);
    }
  };

  const handleEnroll = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;
    if (!enrollFile) {
      alert("Please select a face image file for biometric enrollment.");
      return;
    }
    try {
      await api.enrollWatchlist(name, notes, enrollFile);
      setShowEnroll(false);
      setName("");
      setNotes("");
      setEnrollFile(null);
      playTacticalTone("verify");
      setFeedback(`✓ Suspect ${name} successfully enrolled into biometric watchlist.`);
      loadData();
    } catch (err: any) {
      setFeedback(`Enrollment error: ${err.message}`);
    }
  };

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h1>Facial Recognition System (FRS) & Suspect Intelligence</h1>
          <p style={{ margin: 0, fontSize: 12, color: "var(--text-secondary)" }}>
            Deep learning biometric face matching, national border watchlist management, and operator verification studio
          </p>
        </div>
        <div style={{ display: "flex", gap: 10 }}>
          <button className="btn btn-secondary" onClick={loadData} disabled={loading}>
            {loading ? "Refreshing..." : "🔄 Refresh"}
          </button>
          <button className="btn btn-primary" onClick={() => setShowEnroll(true)}>
            + Enroll Suspect Biometrics
          </button>
        </div>
      </div>

      {feedback && (
        <div className={`test-feedback ${feedback.includes("error") ? "fail" : "success"}`} style={{ marginBottom: 16 }}>
          {feedback}
        </div>
      )}

      {/* FRS KPI Ribbon */}
      <div className="tactical-kpi-ribbon" style={{ marginBottom: 16 }}>
        <div className="tactical-kpi-card">
          <div className="kpi-header-label">
            <span>BIOMETRIC GALLERY</span>
            <span style={{ color: "#00f0ff" }}>ENROLLED</span>
          </div>
          <div className="kpi-metric-val">{suspects.length}</div>
        </div>
        <div className="tactical-kpi-card">
          <div className="kpi-header-label">
            <span>ACTIVE EMBEDDINGS</span>
            <span style={{ color: "#00ff9d" }}>ARCFACE</span>
          </div>
          <div className="kpi-metric-val" style={{ color: "#00ff9d" }}>
            {suspects.filter((s) => s.has_embedding).length}
          </div>
        </div>
        <div className="tactical-kpi-card">
          <div className="kpi-header-label">
            <span>MATCHES RECORDED</span>
            <span style={{ color: "#ffaa00" }}>INCIDENTS</span>
          </div>
          <div className="kpi-metric-val" style={{ color: "#ffaa00" }}>
            {matches.length}
          </div>
        </div>
        <div className="tactical-kpi-card">
          <div className="kpi-header-label">
            <span>LEGAL CITATION</span>
            <span style={{ color: "#00f0ff" }}>STATUTE</span>
          </div>
          <div className="kpi-metric-val" style={{ fontSize: 13, color: "#00f0ff" }}>
            BSA 2023 §63
          </div>
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1.2fr 2fr", gap: 16 }}>
        {/* Left Column: Instant Probe Matching + Live Candidate Face Matches */}
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <div className="panel" style={{ margin: 0, padding: 14 }}>
            <div className="panel-header" style={{ padding: "0 0 10px 0" }}>
              <b style={{ color: "#00f0ff", fontSize: 13 }}>🔍 Instant Probe Match (Field Interception)</b>
              <span className="panel-tag" style={{ borderColor: "#00f0ff", color: "#00f0ff" }}>SFace 128D</span>
            </div>
            <form onSubmit={handleVerifyProbe} style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              <div>
                <label style={{ fontSize: 11, color: "var(--text-secondary)" }}>Upload suspect face photo:</label>
                <input
                  type="file"
                  accept="image/*"
                  onChange={(e) => setProbeFile(e.target.files?.[0] || null)}
                  style={{ width: "100%", marginTop: 4, fontSize: 12, color: "#fff" }}
                />
              </div>
              <button className="btn btn-primary btn-sm" type="submit" disabled={isVerifyingProbe || !probeFile}>
                {isVerifyingProbe ? "Computing Embedding & Matching..." : "⚡ Verify Probe Against Watchlist"}
              </button>
            </form>
            {probeResult && (
              <div style={{ marginTop: 10, padding: 10, borderRadius: 4, background: probeResult.matched ? "rgba(255, 42, 85, 0.1)" : "rgba(0, 255, 157, 0.1)", border: `1px solid ${probeResult.matched ? "#ff2a55" : "#00ff9d"}` }}>
                <div style={{ fontSize: 12, fontWeight: 600, color: probeResult.matched ? "#ff2a55" : "#00ff9d" }}>
                  {probeResult.matched ? `🚨 MATCH: ${probeResult.subject_name}` : (probeResult.face_detected ? "✓ No Watchlist Match" : "⚠️ No Face Detected")}
                </div>
                {probeResult.matched && (
                  <div style={{ fontSize: 10, color: "var(--text-secondary)", marginTop: 4 }}>
                    Similarity: {probeResult.similarity_percent} • Category: {probeResult.threat_level}
                  </div>
                )}
              </div>
            )}
          </div>

          <div className="panel" style={{ margin: 0 }}>
            <div className="panel-header">
              <b style={{ color: "#ff2a55", fontSize: 14 }}>🚨 Live Candidate Face Matches</b>
              <span className="panel-tag" style={{ borderColor: "#ff2a55", color: "#ff2a55" }}>
                INCIDENTS
              </span>
            </div>
            <div style={{ padding: 14, display: "flex", flexDirection: "column", gap: 14 }}>
              {matches.length === 0 ? (
                <Empty text="No candidate facial matches recorded yet. Run video analysis with face detection enabled or verify a probe above." />
              ) : (
              matches.map((m) => {
                const threat = m.threat_score || 85;
                return (
                  <div
                    key={m.id}
                    style={{
                      background: "rgba(255, 42, 85, 0.06)",
                      border: "1px solid rgba(255, 42, 85, 0.4)",
                      borderRadius: 6,
                      padding: 14,
                      display: "flex",
                      flexDirection: "column",
                      gap: 10,
                    }}
                  >
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                      <b style={{ color: "#fff", fontSize: 13 }}>{m.title}</b>
                      <span className="sev-badge sev-critical">{m.severity}</span>
                    </div>

                    <div style={{ fontSize: 11, color: "var(--text-secondary)" }}>
                      {m.description}
                    </div>

                    <div style={{ display: "flex", justifyContent: "space-between", fontSize: 10, color: "var(--text-ghost)" }}>
                      <span>Incident: {m.incident_code}</span>
                      <span>Threat Score: {threat}</span>
                    </div>

                    {openInc && (
                      <button
                        className="btn btn-secondary btn-sm"
                        style={{ alignSelf: "flex-start" }}
                        onClick={() => openInc(m.id)}
                      >
                        Inspect Incident #{m.id}
                      </button>
                    )}
                  </div>
                );
              })
            )}
          </div>
        </div>
      </div>

      {/* Suspect Watchlist Gallery */}
        <div className="panel" style={{ margin: 0 }}>
          <div className="panel-header">
            <b style={{ color: "#fff", fontSize: 14 }}>National Border Lookout & Biometric Watchlist</b>
            <span className="panel-tag">{suspects.length} ENROLLED SUBJECTS</span>
          </div>
          <div style={{ padding: 14 }}>
            {suspects.length === 0 ? (
              <Empty text="No data yet. Click '+ Enroll Suspect Biometrics' to add subjects to the watchlist." />
            ) : (
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(220px, 1fr))", gap: 14 }}>
                {suspects.map((s) => (
                  <div key={s.id} className="frs-suspect-card" style={{ background: "rgba(0,0,0,0.3)", borderRadius: 6, border: "1px solid rgba(255,255,255,0.08)", overflow: "hidden" }}>
                    <div style={{ height: 120, background: "#02060c", position: "relative", display: "flex", alignItems: "center", justifyContent: "center" }}>
                      {s.face_image_path && s.face_image_path !== "none" ? (
                        <img
                          src={`/api/v1/watchlist/${s.id}/image`}
                          alt={s.name}
                          style={{ width: "100%", height: "100%", objectFit: "cover" }}
                          onError={(e) => {
                            (e.target as HTMLElement).style.display = "none";
                          }}
                        />
                      ) : (
                        <span style={{ fontSize: 32 }}>👤</span>
                      )}
                      <span
                        style={{
                          position: "absolute",
                          top: 6,
                          right: 6,
                          background: s.has_embedding ? "#00ff9d" : "#ffaa00",
                          color: "#000",
                          fontWeight: 800,
                          fontSize: 9,
                          padding: "2px 6px",
                          borderRadius: 2,
                        }}
                      >
                        {s.has_embedding ? "EMBEDDED" : "PHOTO ONLY"}
                      </span>
                    </div>
                    <div style={{ padding: 10, display: "flex", flexDirection: "column", gap: 6 }}>
                      <b style={{ color: "#fff", fontSize: 13 }}>{s.name}</b>
                      {s.notes && (
                        <div style={{ fontSize: 11, color: "var(--text-secondary)" }}>
                          {s.notes}
                        </div>
                      )}
                      <div style={{ fontSize: 9, color: "var(--text-ghost)" }}>
                        Enrolled: {new Date(s.created_at).toLocaleDateString()}
                      </div>
                      <div style={{ display: "flex", justifyContent: "flex-end", marginTop: 4 }}>
                        <button
                          className="btn btn-sm btn-danger"
                          style={{ padding: "2px 8px", fontSize: 10 }}
                          onClick={() => handleDelete(s.id)}
                        >
                          🗑 Remove
                        </button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Enroll Suspect Modal */}
      {showEnroll && (
        <div className="section-65b-modal-backdrop" onClick={() => setShowEnroll(false)}>
          <div className="panel" style={{ maxWidth: 480, width: "100%", margin: 0, padding: 24 }} onClick={(e) => e.stopPropagation()}>
            <h3 style={{ color: "#00f0ff", marginBottom: 14 }}>Enroll Subject into Biometric Watchlist</h3>
            <form onSubmit={handleEnroll} style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              <div>
                <label style={{ fontSize: 11, color: "var(--text-secondary)" }}>Full Name / Identification Code:</label>
                <input
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="e.g. Tariq Mehmood"
                  style={{ width: "100%", background: "#040b14", border: "1px solid #333", color: "#fff", padding: 8, borderRadius: 4, marginTop: 4 }}
                  required
                />
              </div>
              <div>
                <label style={{ fontSize: 11, color: "var(--text-secondary)" }}>Tactical Notes / Risk Profile:</label>
                <input
                  type="text"
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  placeholder="e.g. Suspected cross-border infiltration / contraband trafficking"
                  style={{ width: "100%", background: "#040b14", border: "1px solid #333", color: "#fff", padding: 8, borderRadius: 4, marginTop: 4 }}
                />
              </div>
              <div>
                <label style={{ fontSize: 11, color: "var(--text-secondary)" }}>Face Photo (JPG / PNG):</label>
                <input
                  type="file"
                  accept="image/*"
                  onChange={(e) => setEnrollFile(e.target.files?.[0] || null)}
                  style={{ width: "100%", background: "#040b14", border: "1px solid #333", color: "#fff", padding: 8, borderRadius: 4, marginTop: 4 }}
                  required
                />
              </div>
              <div style={{ display: "flex", justifyContent: "flex-end", gap: 8, marginTop: 8 }}>
                <button className="btn btn-secondary" type="button" onClick={() => setShowEnroll(false)}>
                  Cancel
                </button>
                <button className="btn btn-primary" type="submit">
                  + Enroll Biometric Target
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
