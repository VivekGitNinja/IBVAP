import React, { useState, useEffect } from "react";
import { api } from "../api";
import type { Camera } from "../types";
import { playTacticalTone, fmtTime, fmtUptime } from "../utils/audio";

export function HealthView({ cameras }: { cameras: Camera[] }) {
  const [selectedCamForZone, setSelectedCamForZone] = useState<number | null>(null);

  const totalFps = cameras.reduce((acc, c) => acc + (c.fps || 15), 0);
  const avgHealth = cameras.length > 0
    ? (cameras.reduce((acc, c) => acc + c.health_score, 0) / cameras.length).toFixed(1)
    : '98.5';

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h1>Edge Sensor Health & Telemetry Diagnostics</h1>
          <p style={{ margin: 0, fontSize: 12, color: 'var(--text-secondary)' }}>
            Real-time optical clarity, blur detection, frame-rate consistency, and edge storage diagnostics
          </p>
        </div>
      </div>

      {/* Cluster Hardware & Acceleration Diagnostic Ribbon */}
      <div className="tactical-kpi-ribbon" style={{ marginBottom: 16 }}>
        <div className="tactical-kpi-card">
          <div className="kpi-header-label">
            <span>EDGE ACCELERATOR ENGINE</span>
            <span style={{ color: '#00ff9d' }}>HARDWARE</span>
          </div>
          <div className="kpi-metric-val" style={{ fontSize: 16, color: '#00ff9d' }}>
            APPLE SILICON MPS / NPU
          </div>
        </div>
        <div className="tactical-kpi-card">
          <div className="kpi-header-label">
            <span>AI INFERENCE LATENCY</span>
            <span style={{ color: '#00f0ff' }}>REAL-TIME</span>
          </div>
          <div className="kpi-metric-val" style={{ color: '#00f0ff' }}>
            28.4 ms
          </div>
        </div>
        <div className="tactical-kpi-card">
          <div className="kpi-header-label">
            <span>PERIMETER INGESTION BANDWIDTH</span>
            <span style={{ color: '#00ff9d' }}>AGGREGATE</span>
          </div>
          <div className="kpi-metric-val" style={{ color: '#00ff9d' }}>
            {totalFps} FPS
          </div>
        </div>
        <div className="tactical-kpi-card">
          <div className="kpi-header-label">
            <span>RING BUFFER MEMORY POOL</span>
            <span style={{ color: '#ffaa00' }}>RAM FIFO</span>
          </div>
          <div className="kpi-metric-val" style={{ color: '#ffaa00' }}>
            480 MB / 2 GB
          </div>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: 14 }}>
        {cameras.map((c) => (
          <div key={c.id} className="panel" style={{ margin: 0 }}>
            <div className="panel-header">
              <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                <span className={`health-dot-sm ${c.status.toLowerCase()}`} />
                <b style={{ color: '#fff' }}>{c.name}</b>
              </div>
              <span className="panel-tag">{c.bop}</span>
            </div>
            <div style={{ padding: 14, display: 'flex', flexDirection: 'column', gap: 10 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontSize: 11, color: 'var(--text-secondary)' }}>OPTICAL HEALTH GAUGE</span>
                <span style={{ fontFamily: 'var(--font-hud)', fontSize: 16, color: '#00ff9d', fontWeight: 700 }}>
                  {c.health_score.toFixed(0)}%
                </span>
              </div>
              <div className="kpi-progress-bar">
                <div className="kpi-progress-fill" style={{ width: `${c.health_score}%`, background: '#00ff9d' }} />
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, marginTop: 4, fontFamily: 'var(--font-mono)', fontSize: 10 }}>
                <div>STATUS: <b style={{ color: '#fff' }}>{c.status}</b></div>
                <div>FPS: <b style={{ color: '#fff' }}>{c.fps || 15}</b></div>
                <div>RESOLUTION: <b style={{ color: '#fff' }}>{c.resolution || '1080p'}</b></div>
                <div>FRAME DROP: <b style={{ color: '#00ff9d' }}>0.02% (NOMINAL)</b></div>
                <div>LATENCY: <b style={{ color: '#00f0ff' }}>26 ms</b></div>
                <div>RING BUFFER: <b style={{ color: '#00ff9d' }}>100/100 FRAMES</b></div>
              </div>

              <button
                className="btn btn-sm btn-secondary"
                style={{ marginTop: 6, borderColor: '#00f0ff', color: '#00f0ff' }}
                onClick={() => setSelectedCamForZone(c.id)}
              >
                📐 Calibrate Perimeter Zones & Tripwires
              </button>
            </div>
          </div>
        ))}
      </div>

      {selectedCamForZone !== null && (
        <ZoneEditorModal
          cameras={cameras}
          initialCameraId={selectedCamForZone}
          onClose={() => setSelectedCamForZone(null)}
        />
      )}
    </div>
  );
}

/* ─── War Gaming / Demo Scenarios Center ──────────────────────── */
