import React from "react";
import type { DemoScenario } from "../types";
import { playTacticalTone } from "../utils/audio";

export function DemoView({
  scenarios,
  runDemo,
  runAll,
  busy,
  demoMsg,
}: {
  scenarios: DemoScenario[];
  runDemo: (s: string) => void;
  runAll: () => void;
  busy: boolean;
  demoMsg: string;
}) {
  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h1>Tactical Simulation & War Gaming Engine</h1>
          <p style={{ margin: 0, fontSize: 12, color: 'var(--text-secondary)' }}>
            Deterministic military scenario generator demonstrating multi-signal AI reasoning and border defense SOPs
          </p>
        </div>
        <button className="btn btn-primary" onClick={runAll} disabled={busy}>
          {busy ? 'Simulating...' : '⚡ Simulate Multi-Sector Incursion'}
        </button>
      </div>

      {demoMsg && <div className="test-feedback success" style={{ marginBottom: 16 }}>{demoMsg}</div>}

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: 14 }}>
        {scenarios.map((sc) => (
          <div key={sc.id} className="panel" style={{ margin: 0, display: 'flex', flexDirection: 'column' }}>
            <div className="panel-header">
              <b style={{ color: '#fff', fontSize: 14 }}>{sc.name}</b>
              <span className={`sev-badge sev-${sc.expected_severity?.toLowerCase() || 'high'}`}>
                {sc.expected_severity || 'HIGH'}
              </span>
            </div>
            <div style={{ padding: 14, flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
              <p style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 12 }}>
                {sc.description}
              </p>
              <div style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: '#00f0ff', marginBottom: 14 }}>
                TARGET THREAT SCORE: ~{sc.expected_score || 85}/100
              </div>
              <button className="btn btn-primary" onClick={() => runDemo(sc.id)} disabled={busy} style={{ width: '100%' }}>
                {busy ? 'Executing...' : `▶ Execute ${sc.name}`}
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ─── Settings & Defense Parameters ───────────────────────────── */
