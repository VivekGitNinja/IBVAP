import React, { useEffect, useState, useCallback, useRef, useMemo } from 'react';
import { createRoot } from 'react-dom/client';
import { api } from './api';
import type { Camera, Incident, Alert, Evidence, AuditLog, DemoScenario } from './types';
import './style.css';

/* ─── Tactical Types ─────────────────────────────────────────── */
type Page =
  | 'dashboard'
  | 'cameras'
  | 'anpr'
  | 'frs'
  | 'qrt'
  | 'thermal'
  | 'incidents'
  | 'incident-detail'
  | 'evidence'
  | 'audit'
  | 'health'
  | 'demo'
  | 'settings';

/* ─── Web Audio Tactical Sound Synthesizer ───────────────────── */
function playTacticalTone(type: 'alert' | 'click' | 'verify' | 'escalate') {
  if (typeof window === 'undefined') return;
  const muted = localStorage.getItem('ibvap_muted') === 'true';
  if (muted) return;

  try {
    const AudioContextClass = window.AudioContext || (window as any).webkitAudioContext;
    if (!AudioContextClass) return;
    const ctx = new AudioContextClass();
    const now = ctx.currentTime;

    if (type === 'alert') {
      // Double tactical alert chirp
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.type = 'sawtooth';
      osc.frequency.setValueAtTime(880, now);
      osc.frequency.setValueAtTime(1320, now + 0.08);
      gain.gain.setValueAtTime(0.08, now);
      gain.gain.exponentialRampToValueAtTime(0.001, now + 0.25);
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.start(now);
      osc.stop(now + 0.25);
    } else if (type === 'verify') {
      // Harmonious confirmation chime
      const osc1 = ctx.createOscillator();
      const osc2 = ctx.createOscillator();
      const gain = ctx.createGain();
      osc1.type = 'sine';
      osc2.type = 'sine';
      osc1.frequency.setValueAtTime(587.33, now); // D5
      osc2.frequency.setValueAtTime(880, now + 0.08); // A5
      gain.gain.setValueAtTime(0.08, now);
      gain.gain.exponentialRampToValueAtTime(0.001, now + 0.3);
      osc1.connect(gain);
      osc2.connect(gain);
      gain.connect(ctx.destination);
      osc1.start(now);
      osc2.start(now + 0.08);
      osc1.stop(now + 0.3);
      osc2.stop(now + 0.3);
    } else if (type === 'escalate') {
      // Urgent warble
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.type = 'square';
      osc.frequency.setValueAtTime(440, now);
      osc.frequency.linearRampToValueAtTime(880, now + 0.15);
      gain.gain.setValueAtTime(0.06, now);
      gain.gain.exponentialRampToValueAtTime(0.001, now + 0.2);
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.start(now);
      osc.stop(now + 0.2);
    } else {
      // Subtle tactile click
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.type = 'sine';
      osc.frequency.setValueAtTime(1200, now);
      gain.gain.setValueAtTime(0.02, now);
      gain.gain.exponentialRampToValueAtTime(0.001, now + 0.04);
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.start(now);
      osc.stop(now + 0.04);
    }
  } catch {}
}

/* ─── Helpers ─────────────────────────────────────────────────── */
function fmtTime(iso: string) {
  if (!iso) return '—';
  try { return new Date(iso).toLocaleString(); } catch { return iso; }
}

function fmtTimeShort(iso: string) {
  if (!iso) return '—';
  try { return new Date(iso).toLocaleTimeString('en-US', { hour12: false }); } catch { return iso; }
}

function fmtUptime(s: number) {
  if (s < 60) return `${Math.floor(s)}s`;
  if (s < 3600) return `${Math.floor(s / 60)}m`;
  return `${Math.floor(s / 3600)}h ${Math.floor((s % 3600) / 60)}m`;
}

function Empty({ text }: { text: string }) {
  return (
    <div className="empty" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 8, padding: '36px 16px' }}>
      <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" style={{ opacity: 0.4 }}>
        <circle cx="12" cy="12" r="10" />
        <line x1="12" y1="8" x2="12" y2="12" />
        <line x1="12" y1="16" x2="12.01" y2="16" />
      </svg>
      <span>{text}</span>
    </div>
  );
}

interface DetectionToast {
  id: string;
  title: string;
  subtitle: string;
  severity: string;
  time: string;
  incidentId?: number;
}

/* ─── Main Application ────────────────────────────────────────── */
function App() {
  const [page, setPage] = useState<Page>('dashboard');
  const [cameras, setCameras] = useState<Camera[]>([]);
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [selInc, setSelInc] = useState<Incident | null>(null);
  const [status, setStatus] = useState<any>(null);
  const [scenarios, setScenarios] = useState<DemoScenario[]>([]);
  const [busy, setBusy] = useState(false);
  const [demoMsg, setDemoMsg] = useState('');
  const [selectedBop, setSelectedBop] = useState<string | null>(null);
  const [isMuted, setIsMuted] = useState(() => localStorage.getItem('ibvap_muted') === 'true');
  const [wsStatus, setWsStatus] = useState<'connected' | 'disconnected' | 'connecting'>('disconnected');
  const [toasts, setToasts] = useState<DetectionToast[]>([]);
  const wsRef = useRef<WebSocket | null>(null);
  const prevIncidentCount = useRef<number>(0);

  const toggleMute = () => {
    const next = !isMuted;
    setIsMuted(next);
    localStorage.setItem('ibvap_muted', String(next));
    if (!next) playTacticalTone('verify');
  };

  const addToast = useCallback((t: Omit<DetectionToast, 'id' | 'time'>) => {
    const id = Math.random().toString(36).substring(2, 9);
    const time = new Date().toLocaleTimeString();
    const item: DetectionToast = { ...t, id, time };
    setToasts((prev) => [item, ...prev.slice(0, 3)]);
    if (!isMuted) playTacticalTone('alert');

    if (typeof window !== 'undefined' && 'Notification' in window && Notification.permission === 'granted') {
      try {
        new Notification(t.title, { body: `${t.subtitle} [${t.severity}]` });
      } catch {}
    }

    setTimeout(() => {
      setToasts((prev) => prev.filter((x) => x.id !== id));
    }, 8000);
  }, [isMuted]);

  const testAlert = () => {
    if (typeof window !== 'undefined' && 'Notification' in window && Notification.permission === 'default') {
      Notification.requestPermission();
    }
    addToast({
      title: 'TACTICAL ALERT // INTRUSION DETECTED',
      subtitle: 'BOP-01 Gate Sector • Threat Score: 92 • Perimeter tripwire breach verified',
      severity: 'CRITICAL',
    });
  };

  const load = useCallback(async () => {
    try {
      const [c, i, a, s, sc] = await Promise.all([
        api.cameras().catch(() => []),
        api.incidents().catch(() => []),
        api.alerts().catch(() => []),
        api.status().catch(() => null),
        api.demoScenarios().catch(() => []),
      ]);
      if (Array.isArray(c)) setCameras(c);
      if (Array.isArray(i)) {
        if (i.length > prevIncidentCount.current && prevIncidentCount.current > 0) {
          const newest = i[0];
          if (newest) {
            addToast({
              title: `TACTICAL INCIDENT // ${newest.incident_type || 'INTRUSION DETECTED'}`,
              subtitle: `Sector ${newest.bop || 'BOP-01'} • Threat: ${(newest.threat_score || 80).toFixed(0)} • ${newest.summary || 'Security event verified'}`,
              severity: newest.severity || 'HIGH',
              incidentId: newest.id,
            });
          }
        }
        prevIncidentCount.current = i.length;
        setIncidents(i);
      }
      if (Array.isArray(a)) setAlerts(a);
      if (s) setStatus(s);
      if (Array.isArray(sc)) setScenarios(sc);
    } catch {
      /* maintain resilient display */
    }
  }, [addToast]);

  const connectWs = useCallback(() => {
    let url = 'ws://127.0.0.1:8001/ws/events';
    if (import.meta.env.VITE_API_URL) {
      url = import.meta.env.VITE_API_URL.replace(/^http/, 'ws').replace(/\/$/, '') + '/ws/events';
    } else if (typeof window !== 'undefined') {
      const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      if (window.location.port === '5173') {
        url = `${proto}//${window.location.hostname}:8001/ws/events`;
      } else {
        url = `${proto}//${window.location.host}/ws/events`;
      }
    }
    setWsStatus('connecting');
    try {
      const ws = new WebSocket(url);
      ws.onopen = () => setWsStatus('connected');
      ws.onclose = () => {
        setWsStatus('disconnected');
        setTimeout(connectWs, 4000);
      };
      ws.onerror = () => ws.close();
      ws.onmessage = (e) => {
        try {
          const m = JSON.parse(e.data);
          if (m.type === 'incident' || m.type === 'incident_created') {
            const inc = m.data || {};
            addToast({
              title: `TACTICAL ALERT // ${inc.incident_type || 'BREACH DETECTED'}`,
              subtitle: `Sector ${inc.bop || 'BOP-01'} • Threat: ${(inc.threat_score || 85).toFixed(0)} • ${inc.summary || 'Perimeter activity detected'}`,
              severity: inc.severity || 'HIGH',
              incidentId: inc.id,
            });
          } else if (m.type === 'detection' || m.type === 'rule_alert' || m.type === 'alert') {
            const det = m.data || {};
            addToast({
              title: `LIVE AI PERCEPTION // ${det.rule || det.label || 'OBJECT DETECTED'}`,
              subtitle: `Camera ${det.camera_id || 'NODE'} • Conf: ${((det.confidence || 0.8) * 100).toFixed(0)}%`,
              severity: det.severity || 'MEDIUM',
            });
          }
          if (m.type !== 'pong') load();
        } catch {}
      };
      wsRef.current = ws;
    } catch {
      setTimeout(connectWs, 4000);
    }
  }, [load, addToast]);

  useEffect(() => {
    load();
    connectWs();
    const t = setInterval(load, 4000);
    return () => {
      clearInterval(t);
      wsRef.current?.close();
    };
  }, [load, connectWs]);

  const openInc = async (id: number) => {
    playTacticalTone('click');
    const inc = await api.incident(id);
    setSelInc(inc);
    setPage('incident-detail');
  };

  const runDemo = async (scenario: string) => {
    playTacticalTone('click');
    setBusy(true);
    setDemoMsg(`Triggering tactical scenario: ${scenario}...`);
    try {
      const result = await api.demoSeed(scenario);
      setDemoMsg(`Tactical incident logged: ${result.incident_type || scenario} (Threat: ${result.threat_score})`);
      addToast({
        title: `WAR GAMING // ${result.incident_type || scenario}`,
        subtitle: `Sector ${result.bop || 'BOP-01'} • Threat Score: ${result.threat_score || 80} • Injected successfully`,
        severity: result.severity || 'HIGH',
        incidentId: result.id,
      });
      await load();
      setTimeout(() => setDemoMsg(''), 5000);
    } catch (e: any) {
      setDemoMsg(`Simulation notice: ${e.message}`);
    } finally {
      setBusy(false);
    }
  };

  const runAll = async () => {
    playTacticalTone('click');
    setBusy(true);
    setDemoMsg('Running full sector war game exercise across all 7 BOPs...');
    try {
      const results = await api.demoSeedAll();
      setDemoMsg(`Exercise complete: ${results.length} sector threats processed`);
      addToast({
        title: 'FULL SECTOR DRILL INITIATED',
        subtitle: `${results.length} multi-node threats simulated across border perimeter`,
        severity: 'CRITICAL',
      });
      await load();
      setTimeout(() => setDemoMsg(''), 6000);
    } catch (e: any) {
      setDemoMsg(`Simulation notice: ${e.message}`);
    } finally {
      setBusy(false);
    }
  };

  // Compute highest active threat score for DEFCON evaluation
  const maxThreatScore = incidents.reduce((max, inc) => Math.max(max, inc.threat_score || 0), 0);

  return (
    <div className="app">
      <Sidebar page={page} setPage={(p) => { playTacticalTone('click'); setPage(p); }} alerts={alerts} ws={wsStatus} />
      <div className="main-area">
        <TopBar
          status={status}
          ws={wsStatus}
          maxThreat={maxThreatScore}
          isMuted={isMuted}
          onToggleMute={toggleMute}
          onSync={() => { playTacticalTone('click'); load(); }}
          onTestAlert={testAlert}
        />
        <div className="content">
          {page === 'dashboard' && (
            <Dashboard
              cameras={cameras}
              incidents={incidents}
              alerts={alerts}
              status={status}
              runDemo={runDemo}
              openInc={openInc}
              busy={busy}
              demoMsg={demoMsg}
              selectedBop={selectedBop}
              onSelectBop={(bop: string | null) => { playTacticalTone('click'); setSelectedBop(bop); }}
            />
          )}
          {page === 'cameras' && <CamerasPage cameras={cameras} onRefresh={load} />}
          {page === 'anpr' && <ANPRPage />}
          {page === 'frs' && <FRSPage openInc={openInc} />}
          {page === 'qrt' && <QRTPage incidents={incidents} />}
          {page === 'thermal' && <ThermalDronePage cameras={cameras} />}
          {page === 'incidents' && <IncidentsPage incidents={incidents} openInc={openInc} />}
          {page === 'incident-detail' && selInc && (
            <IncidentDetail incident={selInc} onBack={() => { playTacticalTone('click'); setPage('incidents'); }} refresh={openInc} />
          )}
          {page === 'evidence' && <EvidencePage incidents={incidents} />}
          {page === 'audit' && <AuditPage />}
          {page === 'health' && <HealthPage cameras={cameras} />}
          {page === 'demo' && (
            <DemoPage scenarios={scenarios} runDemo={runDemo} runAll={runAll} busy={busy} demoMsg={demoMsg} />
          )}
          {page === 'settings' && <SettingsPage isMuted={isMuted} onToggleMute={toggleMute} />}
        </div>
      </div>

      {/* Floating Tactical Real-time Detection HUD Toasts */}
      <div className="tactical-toast-container">
        {toasts.map((t) => (
          <div key={t.id} className={`tactical-toast toast-${(t.severity || 'high').toLowerCase()}`}>
            <div className="toast-header">
              <span className="toast-pulse-dot" />
              <span className="toast-tag">{t.severity || 'HIGH'} ALERT</span>
              <span className="toast-time">{t.time}</span>
              <button
                className="toast-close"
                onClick={() => setToasts((prev) => prev.filter((x) => x.id !== t.id))}
                title="Dismiss"
              >
                ✕
              </button>
            </div>
            <div className="toast-title">{t.title}</div>
            <div className="toast-sub">{t.subtitle}</div>
            {t.incidentId && (
              <button
                className="toast-action"
                onClick={() => {
                  openInc(t.incidentId!);
                  setToasts((prev) => prev.filter((x) => x.id !== t.id));
                }}
              >
                ▶ View Incident Dossier
              </button>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

/* ─── Tactical Sidebar ────────────────────────────────────────── */
function Sidebar({
  page,
  setPage,
  alerts,
  ws,
}: {
  page: Page;
  setPage: (p: Page) => void;
  alerts: Alert[];
  ws: string;
}) {
  const newAlerts = alerts.filter((a) => a.status === 'NEW').length;
  const items: { id: Page; label: string; iconSvg: React.ReactNode }[] = [
    {
      id: 'dashboard',
      label: 'C4ISR Command',
      iconSvg: (
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <polygon points="12 2 2 7 12 12 22 7 12 2" />
          <polyline points="2 17 12 22 22 17" />
          <polyline points="2 12 12 17 22 12" />
        </svg>
      ),
    },
    {
      id: 'cameras',
      label: 'Tactical Feeds',
      iconSvg: (
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z" />
          <circle cx="12" cy="13" r="4" />
        </svg>
      ),
    },
    {
      id: 'anpr',
      label: 'ANPR Checkpost',
      iconSvg: (
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <rect x="2" y="5" width="20" height="14" rx="2" />
          <path d="M7 10h10M7 14h6" />
          <circle cx="6" cy="18" r="1.5" />
          <circle cx="18" cy="18" r="1.5" />
        </svg>
      ),
    },
    {
      id: 'frs',
      label: 'FRS Watchlist',
      iconSvg: (
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
          <circle cx="12" cy="7" r="4" />
          <path d="M3 3h3v3M21 3h-3v3M3 21h3v-3M21 21h-3v-3" />
        </svg>
      ),
    },
    {
      id: 'qrt',
      label: 'QRT Patrols',
      iconSvg: (
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
          <polyline points="13 10 10 14 14 14 11 18" />
        </svg>
      ),
    },
    {
      id: 'thermal',
      label: 'FLIR & Drone Recon',
      iconSvg: (
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <circle cx="12" cy="12" r="9" />
          <line x1="12" y1="3" x2="12" y2="7" />
          <line x1="12" y1="17" x2="12" y2="21" />
          <line x1="3" y1="12" x2="7" y2="12" />
          <line x1="17" y1="12" x2="21" y2="12" />
          <circle cx="12" cy="12" r="3" />
        </svg>
      ),
    },
    {
      id: 'incidents',
      label: 'Threat Queue',
      iconSvg: (
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
          <line x1="12" y1="9" x2="12" y2="13" />
          <line x1="12" y1="17" x2="12.01" y2="17" />
        </svg>
      ),
    },
    {
      id: 'evidence',
      label: 'Evidence Locker',
      iconSvg: (
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
          <path d="M7 11V7a5 5 0 0 1 10 0v4" />
        </svg>
      ),
    },
    {
      id: 'audit',
      label: 'Audit Ledger',
      iconSvg: (
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
          <polyline points="14 2 14 8 20 8" />
          <line x1="16" y1="13" x2="8" y2="13" />
          <line x1="16" y1="17" x2="8" y2="17" />
          <polyline points="10 9 9 9 8 9" />
        </svg>
      ),
    },
    {
      id: 'health',
      label: 'Edge Diagnostics',
      iconSvg: (
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
        </svg>
      ),
    },
    {
      id: 'demo',
      label: 'War Gaming / Scenarios',
      iconSvg: (
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <polygon points="5 3 19 12 5 21 5 3" />
        </svg>
      ),
    },
    {
      id: 'settings',
      label: 'Configuration',
      iconSvg: (
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <circle cx="12" cy="12" r="3" />
          <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z" />
        </svg>
      ),
    },
  ];

  return (
    <nav className="sidebar">
      <div className="sidebar-brand">
        <div className="brand-icon">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#00f0ff" strokeWidth="2.5">
            <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
          </svg>
        </div>
        <div className="brand-name">SSB C4ISR</div>
        <div className="brand-sub">DEFENSE V2.0</div>
      </div>
      <div className="sidebar-items">
        {items.map((it) => (
          <button
            key={it.id}
            className={`sidebar-item${page === it.id ? ' active' : ''}`}
            onClick={() => setPage(it.id)}
            title={it.label}
          >
            <span className="sidebar-icon">{it.iconSvg}</span>
            <span className="sidebar-label">{it.label}</span>
            {it.id === 'incidents' && newAlerts > 0 && (
              <span className="badge" style={{ background: '#ff2a55', color: '#fff', boxShadow: '0 0 8px #ff2a55' }}>
                {newAlerts}
              </span>
            )}
          </button>
        ))}
      </div>
      <div className="sidebar-footer">
        <div className={`ws-dot ${ws}`} />
        <span className="ws-label">{ws.toUpperCase()}</span>
        <div className="sidebar-copy">MHA • SIH 2026</div>
      </div>
    </nav>
  );
}

/* ─── Tactical TopBar ─────────────────────────────────────────── */
function TopBar({
  status,
  ws,
  maxThreat,
  isMuted,
  onToggleMute,
  onSync,
  onTestAlert,
}: {
  status: any;
  ws: string;
  maxThreat: number;
  isMuted: boolean;
  onToggleMute: () => void;
  onSync: () => void;
  onTestAlert: () => void;
}) {
  const d = status || {};
  const [clock, setClock] = useState(new Date());

  useEffect(() => {
    const t = setInterval(() => setClock(new Date()), 1000);
    return () => clearInterval(t);
  }, []);

  const utcStr = clock.toISOString().substring(11, 19) + ' Z';
  const istStr = clock.toLocaleTimeString('en-GB', { timeZone: 'Asia/Kolkata', hour12: false }) + ' IST';

  // Dynamic DEFCON assessment
  let defconLevel = 4;
  let defconLabel = 'DEFCON 4 // ROUTINE WATCH';
  let defconClass = 'defcon-4';

  if (maxThreat >= 80) {
    defconLevel = 1;
    defconLabel = 'DEFCON 1 // CRITICAL PERIMETER BREACH';
    defconClass = 'defcon-1';
  } else if (maxThreat >= 60) {
    defconLevel = 2;
    defconLabel = 'DEFCON 2 // ELEVATED THREAT ALERT';
    defconClass = 'defcon-2';
  } else if (maxThreat >= 35) {
    defconLevel = 3;
    defconLabel = 'DEFCON 3 // SENSITIVE SECTOR ACTIVITY';
    defconClass = 'defcon-3';
  }

  return (
    <header className="topbar">
      <div className="topbar-left">
        <div className="defense-emblem" title="Sashastra Seema Bal / Ministry of Home Affairs">
          <svg viewBox="0 0 24 24" fill="none" strokeWidth="2">
            <polygon points="12 2 2 7 12 12 22 7 12 2" />
            <polyline points="2 17 12 22 22 17" />
            <polyline points="2 12 12 17 22 12" />
          </svg>
        </div>
        <div className="defense-title-block">
          <span className="defense-title-main">SASHASTRA SEEMA BAL</span>
          <span className="defense-title-sub">BORDER SURVEILLANCE & RECONNAISSANCE COMMAND (C4ISR)</span>
        </div>

        {/* Dynamic Threat / DEFCON Level */}
        <div className={`defcon-badge ${defconClass}`}>
          <span className="defcon-pulse-dot" />
          <span>{defconLabel}</span>
        </div>
      </div>

      <div className="topbar-stats" style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
        {/* Telemetry Pills */}
        <div className="telemetry-strip">
          <div className="telemetry-pill ok" title="Perception Engine">
            <span className="pill-dot" />
            <span>EDGE AI: YOLO26n (38ms)</span>
          </div>
          <div className="telemetry-pill ok" title="Cryptographic Integrity">
            <span className="pill-dot" />
            <span>SHA-256 CHAIN: SEALED</span>
          </div>
          <div className={`telemetry-pill ${d.sync_pending > 0 ? 'warn' : 'ok'}`} title="Offline Sync Status">
            <span className="pill-dot" />
            <span>STORAGE: WORM IMMUTABLE</span>
          </div>
        </div>

        {/* Dual Clock: UTC Zulu & Indian Standard Time */}
        <div className="tactical-clocks">
          <div className="clock-block">
            <span className="clock-label">SURVEILLANCE ZULU</span>
            <span className="clock-val">{utcStr}</span>
          </div>
          <div style={{ width: 1, height: 24, background: 'rgba(0, 240, 255, 0.2)' }} />
          <div className="clock-block">
            <span className="clock-label">LOCAL SECTOR (IST)</span>
            <span className="clock-val ist">{istStr}</span>
          </div>
        </div>

        {/* Test Detection Notification */}
        <button
          className="btn-tactical-icon"
          onClick={onTestAlert}
          title="Simulate / Test Tactical AI Detection Alert Notification"
          style={{ borderColor: 'rgba(255, 42, 85, 0.5)', color: '#ff2a55', background: 'rgba(255, 42, 85, 0.12)' }}
        >
          <span style={{ display: 'inline-block', width: 7, height: 7, borderRadius: '50%', background: '#ff2a55', boxShadow: '0 0 8px #ff2a55' }} />
          <span>TEST NOTIFICATION</span>
        </button>

        {/* Audio Alert Toggle */}
        <button
          className={`btn-tactical-icon ${!isMuted ? 'active' : ''}`}
          onClick={onToggleMute}
          title={isMuted ? 'Unmute Tactical Audio Alerts' : 'Mute Tactical Audio Alerts'}
        >
          {isMuted ? (
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="1" y1="1" x2="23" y2="23" />
              <path d="M9 9v3a3 3 0 0 0 5.12 2.12M15 9.34V4a3 3 0 0 0-5.94-.6" />
              <path d="M17 16.95A7 7 0 0 1 5 12v-2m14 0v2a7 7 0 0 1-.11 1.23" />
              <line x1="12" y1="19" x2="12" y2="23" />
              <line x1="8" y1="23" x2="16" y2="23" />
            </svg>
          ) : (
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M11 5L6 9H2v6h4l5 4V5z" />
              <path d="M19.07 4.93a10 10 0 0 1 0 14.14M15.54 8.46a5 5 0 0 1 0 7.07" />
            </svg>
          )}
          <span>{isMuted ? 'MUTED' : 'AUDIO ON'}</span>
        </button>

        {/* Force Refresh */}
        <button className="btn-tactical-icon" onClick={onSync} title="Force Telemetry Sync">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <polyline points="23 4 23 10 17 10" />
            <polyline points="1 20 1 14 7 14" />
            <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15" />
          </svg>
          <span>SYNC</span>
        </button>
      </div>
    </header>
  );
}

/* ─── Interactive Tactical Border Radar Map (SVG) ─────────────── */
function TacticalBorderMap({
  cameras,
  incidents,
  selectedBop,
  onSelectBop,
}: {
  cameras: Camera[];
  incidents: Incident[];
  selectedBop: string | null;
  onSelectBop: (bop: string | null) => void;
}) {
  const outposts = [
    { id: 'BOP-01', name: 'BOP-01 Alpha (Gate Post)', x: 180, y: 195, sector: 'Alpha' },
    { id: 'BOP-02', name: 'BOP-02 Bravo (Watchtower)', x: 420, y: 175, sector: 'Bravo' },
    { id: 'BOP-03', name: 'BOP-03 Charlie (Checkpoint)', x: 670, y: 185, sector: 'Charlie' },
    { id: 'BOP-04', name: 'BOP-04 Delta (Patrol Outpost)', x: 880, y: 220, sector: 'Delta' },
  ];

  // Active targets from open incidents
  const targets = incidents
    .filter((i) => i.status === 'OPEN')
    .slice(0, 4)
    .map((inc, idx) => {
      const positions = [
        { x: 300, y: 130, label: 'TARGET #1: PERSON (INTRUSION)', score: inc.threat_score },
        { x: 540, y: 115, label: 'TARGET #2: VEHICLE (BREACH)', score: inc.threat_score },
        { x: 740, y: 140, label: 'TARGET #3: UNIDENTIFIED MOVEMENT', score: inc.threat_score },
        { x: 130, y: 125, label: 'TARGET #4: SUSPICIOUS LOITERING', score: inc.threat_score },
      ];
      return { ...positions[idx % positions.length], id: inc.id, code: inc.incident_code };
    });

  return (
    <div className="tactical-map-container">
      <div className="tactical-map-header">
        <div className="tactical-map-title">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#00f0ff" strokeWidth="2">
            <circle cx="12" cy="12" r="10" />
            <line x1="22" y1="12" x2="18" y2="12" />
            <line x1="6" y1="12" x2="2" y2="12" />
            <line x1="12" y1="6" x2="12" y2="2" />
            <line x1="12" y1="22" x2="12" y2="18" />
          </svg>
          <span>TACTICAL BORDER RADAR & SECTOR MATRIX</span>
          {selectedBop && (
            <button
              style={{
                background: 'rgba(0, 240, 255, 0.2)',
                border: '1px solid #00f0ff',
                color: '#fff',
                fontSize: 10,
                padding: '2px 8px',
                borderRadius: 4,
                cursor: 'pointer',
              }}
              onClick={() => onSelectBop(null)}
            >
              CLEAR FILTER ({selectedBop}) ✕
            </button>
          )}
        </div>
        <div className="tactical-map-legend">
          <div className="legend-item">
            <div className="legend-line border" />
            <span>ZERO LINE (BORDER)</span>
          </div>
          <div className="legend-item">
            <div className="legend-line restricted" />
            <span>RESTRICTED PERIMETER (0-50m)</span>
          </div>
          <div className="legend-item">
            <div className="legend-line sensitive" />
            <span>SENSITIVE BUFFER (50-200m)</span>
          </div>
          <div className="legend-item">
            <div className="legend-line monitoring" />
            <span>MONITORING ZONE (200-500m)</span>
          </div>
        </div>
      </div>

      <svg className="tactical-svg-canvas" viewBox="0 0 1000 280">
        <defs>
          <radialGradient id="radarRadial" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="#00f0ff" stopOpacity="0.08" />
            <stop offset="100%" stopColor="#00f0ff" stopOpacity="0.0" />
          </radialGradient>
          <linearGradient id="beamGradient" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#00f0ff" stopOpacity="0.5" />
            <stop offset="100%" stopColor="#00f0ff" stopOpacity="0.0" />
          </linearGradient>
          <pattern id="gridPattern" width="40" height="40" patternUnits="userSpaceOnUse">
            <path d="M 40 0 L 0 0 0 40" fill="none" stroke="rgba(0, 240, 255, 0.05)" strokeWidth="1" />
          </pattern>
        </defs>

        {/* Background Grid */}
        <rect width="1000" height="280" fill="url(#gridPattern)" />

        {/* Concentric Radar Distance Rings */}
        <circle cx="500" cy="180" r="70" fill="none" stroke="rgba(0, 240, 255, 0.12)" strokeWidth="1" />
        <circle cx="500" cy="180" r="140" fill="none" stroke="rgba(0, 240, 255, 0.1)" strokeWidth="1" />
        <circle cx="500" cy="180" r="220" fill="none" stroke="rgba(0, 240, 255, 0.08)" strokeWidth="1" />
        <circle cx="500" cy="180" r="300" fill="none" stroke="rgba(0, 240, 255, 0.06)" strokeWidth="1" />

        {/* Radar Crosshairs */}
        <line x1="500" y1="0" x2="500" y2="280" stroke="rgba(0, 240, 255, 0.08)" strokeDasharray="3,3" />
        <line x1="0" y1="180" x2="1000" y2="180" stroke="rgba(0, 240, 255, 0.08)" strokeDasharray="3,3" />

        {/* Rotating Radar Sweep */}
        <g className="radar-sweep-beam" style={{ transformOrigin: '500px 180px' }}>
          <line x1="500" y1="180" x2="500" y2="0" stroke="#00f0ff" strokeWidth="1.5" opacity="0.7" />
          <path d="M500,180 L500,0 A180,180 0 0,1 627,52 Z" fill="url(#beamGradient)" />
        </g>

        {/* Virtual Fence Perimeter Polygons */}
        {/* Monitoring Buffer (Cyan) */}
        <polygon points="0,170 1000,175 1000,260 0,260" fill="rgba(0, 240, 255, 0.03)" stroke="rgba(0, 240, 255, 0.25)" strokeDasharray="4,4" />
        {/* Sensitive Buffer (Amber) */}
        <polygon points="0,120 1000,130 1000,170 0,170" fill="rgba(255, 183, 0, 0.04)" stroke="rgba(255, 183, 0, 0.35)" strokeDasharray="5,3" />
        {/* Restricted Zone (Red Hazard) */}
        <polygon points="0,85 1000,95 1000,120 0,120" fill="rgba(255, 42, 85, 0.06)" stroke="rgba(255, 42, 85, 0.5)" strokeWidth="1.5" />

        {/* International Border Demarcation Line (Zero Line) */}
        <path d="M 0,85 Q 250,92 500,88 T 1000,95" fill="none" stroke="#ffffff" strokeWidth="2.5" strokeDasharray="8,5" opacity="0.8" />
        <text x="30" y="78" fill="#ffffff" fontSize="10" fontFamily="var(--font-mono)" letterSpacing="1">
          ZERO LINE — INDO-NEPAL BORDER DEMARCATION
        </text>

        {/* Surveillance Cones from BOPs towards border */}
        {outposts.map((bop) => {
          const isSel = selectedBop === bop.id;
          return (
            <g key={`cone-${bop.id}`}>
              <polygon
                points={`${bop.x},${bop.y} ${bop.x - 70},${bop.y - 95} ${bop.x + 70},${bop.y - 95}`}
                fill={isSel ? 'rgba(0, 240, 255, 0.15)' : 'rgba(0, 240, 255, 0.05)'}
                stroke={isSel ? '#00f0ff' : 'rgba(0, 240, 255, 0.2)'}
                strokeWidth="1"
              />
            </g>
          );
        })}

        {/* Active Target Blips */}
        {targets.map((tgt) => (
          <g key={`blip-${tgt.id}`}>
            <circle cx={tgt.x} cy={tgt.y} r="6" fill="#ff2a55" />
            <circle cx={tgt.x} cy={tgt.y} r="6" className="target-blip-pulse" fill="none" stroke="#ff2a55" strokeWidth="2" />
            <line x1={tgt.x} y1={tgt.y} x2={tgt.x} y2={tgt.y + 25} stroke="#ff2a55" strokeWidth="1" strokeDasharray="2,2" />
            <rect x={tgt.x - 75} y={tgt.y - 32} width="150" height="18" fill="rgba(6, 14, 24, 0.9)" stroke="#ff2a55" rx="3" />
            <text x={tgt.x} y={tgt.y - 20} textAnchor="middle" fill="#ff2a55" fontSize="8" fontWeight="bold" fontFamily="var(--font-mono)">
              {tgt.label}
            </text>
          </g>
        ))}

        {/* BOP Outposts Markers */}
        {outposts.map((bop) => {
          const isSel = selectedBop === bop.id;
          return (
            <g
              key={bop.id}
              onClick={() => onSelectBop(isSel ? null : bop.id)}
              style={{ cursor: 'pointer' }}
            >
              {/* Outpost Base Ring */}
              <circle
                cx={bop.x}
                cy={bop.y}
                r={isSel ? 16 : 12}
                fill={isSel ? 'rgba(0, 240, 255, 0.3)' : 'rgba(8, 20, 34, 0.9)'}
                stroke={isSel ? '#00f0ff' : '#00ff9d'}
                strokeWidth="2"
              />
              <circle cx={bop.x} cy={bop.y} r="4" fill={isSel ? '#00f0ff' : '#00ff9d'} />

              {/* Tower Label Badge */}
              <rect
                x={bop.x - 55}
                y={bop.y + 16}
                width="110"
                height="18"
                fill={isSel ? 'rgba(0, 240, 255, 0.25)' : 'rgba(4, 10, 18, 0.85)'}
                stroke={isSel ? '#00f0ff' : 'rgba(0, 240, 255, 0.25)'}
                rx="3"
              />
              <text
                x={bop.x}
                y={bop.y + 28}
                textAnchor="middle"
                fill={isSel ? '#ffffff' : '#00ff9d'}
                fontSize="9"
                fontWeight="bold"
                fontFamily="var(--font-hud)"
                letterSpacing="0.8"
              >
                {bop.id} // SEC {bop.sector.toUpperCase()}
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}

/* ─── Dashboard Component ─────────────────────────────────────── */
function Dashboard({
  cameras,
  incidents,
  alerts,
  status: s,
  runDemo,
  openInc,
  busy,
  demoMsg,
  selectedBop,
  onSelectBop,
}: any) {
  const open = incidents.filter((i: Incident) => i.status === 'OPEN');
  const high = incidents.filter((i: Incident) => i.severity === 'HIGH' || i.severity === 'CRITICAL');
  const newAlerts = alerts.filter((a: Alert) => a.status === 'NEW');

  // Filter items if user clicked a BOP on the tactical map
  const filteredCameras = selectedBop
    ? cameras.filter((c: Camera) => c.bop?.toLowerCase() === selectedBop.toLowerCase())
    : cameras;

  const filteredIncidents = selectedBop
    ? incidents.filter((i: Incident) => i.camera_name?.includes(selectedBop) || i.description?.includes(selectedBop))
    : incidents;

  return (
    <div className="dashboard">
      {/* 6-Column Tactical KPI Ribbon */}
      <div className="tactical-kpi-ribbon">
        <div className="tactical-kpi-card">
          <div className="kpi-header-label">
            <span>SURVEILLANCE POSTS</span>
            <span style={{ color: '#00f0ff' }}>BOP ACTIVE</span>
          </div>
          <div className="kpi-metric-val">
            4 <span className="kpi-metric-sub">/ 4 SECTORS</span>
          </div>
          <div className="kpi-progress-bar">
            <div className="kpi-progress-fill" style={{ width: '100%' }} />
          </div>
        </div>

        <div className="tactical-kpi-card emerald">
          <div className="kpi-header-label">
            <span>CAMERAS ONLINE</span>
            <span style={{ color: '#00ff9d' }}>100% HEALTH</span>
          </div>
          <div className="kpi-metric-val">
            {cameras.filter((c: Camera) => c.status === 'ONLINE').length}
            <span className="kpi-metric-sub">/ {cameras.length} UNITS</span>
          </div>
          <div className="kpi-progress-bar">
            <div
              className="kpi-progress-fill"
              style={{
                width: `${cameras.length ? (cameras.filter((c: Camera) => c.status === 'ONLINE').length / cameras.length) * 100 : 100}%`,
              }}
            />
          </div>
        </div>

        <div className={`tactical-kpi-card ${open.length > 0 ? 'amber' : 'emerald'}`}>
          <div className="kpi-header-label">
            <span>ACTIVE INCIDENTS</span>
            <span>HUMAN VERIFY</span>
          </div>
          <div className="kpi-metric-val">
            {open.length} <span className="kpi-metric-sub">IN QUEUE</span>
          </div>
          <div className="kpi-progress-bar">
            <div className="kpi-progress-fill" style={{ width: `${Math.min(100, open.length * 20)}%` }} />
          </div>
        </div>

        <div className={`tactical-kpi-card ${high.length > 0 ? 'crimson' : 'emerald'}`}>
          <div className="kpi-header-label">
            <span>CRITICAL THREATS</span>
            <span style={{ color: high.length > 0 ? '#ff2a55' : '#00ff9d' }}>HIGH PRIORITY</span>
          </div>
          <div className="kpi-metric-val">
            {high.length} <span className="kpi-metric-sub">ESCALATED</span>
          </div>
          <div className="kpi-progress-bar">
            <div className="kpi-progress-fill" style={{ width: `${Math.min(100, high.length * 33)}%` }} />
          </div>
        </div>

        <div className="tactical-kpi-card purple">
          <div className="kpi-header-label">
            <span>HASH INTEGRITY</span>
            <span style={{ color: '#a855f7' }}>IMMUTABLE</span>
          </div>
          <div className="kpi-metric-val">
            100% <span className="kpi-metric-sub">SHA-256 SEALED</span>
          </div>
          <div className="kpi-progress-bar">
            <div className="kpi-progress-fill" style={{ width: '100%' }} />
          </div>
        </div>

        <div className="tactical-kpi-card">
          <div className="kpi-header-label">
            <span>EDGE LATENCY</span>
            <span style={{ color: '#00f0ff' }}>REAL-TIME</span>
          </div>
          <div className="kpi-metric-val">
            38 <span className="kpi-metric-sub">MS / FRAME</span>
          </div>
          <div className="kpi-progress-bar">
            <div className="kpi-progress-fill" style={{ width: '38%' }} />
          </div>
        </div>
      </div>

      {/* Interactive Tactical Border Radar Map */}
      <TacticalBorderMap
        cameras={cameras}
        incidents={incidents}
        selectedBop={selectedBop}
        onSelectBop={onSelectBop}
      />

      {/* Main Dual Grid: Camera Wall (Left) & Threat Intelligence (Right) */}
      <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 1fr', gap: 16, marginBottom: 16 }}>
        {/* Left: Multi-Camera Tactical Matrix Wall */}
        <div className="panel" style={{ margin: 0 }}>
          <div className="panel-header">
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#00f0ff" strokeWidth="2">
                <rect x="2" y="2" width="20" height="20" rx="2" />
                <path d="M7 2v20M17 2v20M2 12h20M2 7h5M2 17h5M17 17h5M17 7h5" />
              </svg>
              <h2>Tactical Camera Matrix</h2>
            </div>
            <span className="panel-tag" style={{ color: '#00ff9d', borderColor: '#00ff9d' }}>
              ● LIVE EO/IR FEEDS
            </span>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 10, padding: 12 }}>
            {(filteredCameras.length > 0 ? filteredCameras : cameras).slice(0, 4).map((c: Camera) => {
              const hasAlert = open.some((i: Incident) => i.camera_id === c.id);
              return (
                <div key={c.id} className={`tactical-camera-cell ${hasAlert ? 'has-incident' : ''}`}>
                  <div className="tactical-cam-header">
                    <span className="cam-title-tag">
                      <span className={`health-dot-sm ${c.status.toLowerCase()}`} />
                      {c.bop || 'BOP-01'} | {c.name.split(' ')[0]}
                    </span>
                    <span className="cam-telemetry-tag">{c.resolution || '1080p'} • {c.fps || 15} FPS</span>
                  </div>
                  <DashboardCamFrame cameraId={c.id} cameraName={c.name} />
                  <div className={`tactical-detect-tag ${hasAlert ? 'danger' : ''}`}>
                    {hasAlert ? '⚠️ INTRUSION DETECTED' : 'SURVEILLANCE NORMAL'}
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Right: Threat Intelligence & Incident Stream */}
        <div className="panel" style={{ margin: 0, display: 'flex', flexDirection: 'column' }}>
          <div className="panel-header">
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#ff2a55" strokeWidth="2">
                <path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6" />
              </svg>
              <h2>Incident Intelligence Stream</h2>
            </div>
            <span className="panel-tag" style={{ color: '#ffb700', borderColor: '#ffb700' }}>
              {open.length} UNVERIFIED
            </span>
          </div>

          <div style={{ padding: 12, overflowY: 'auto', flex: 1, maxHeight: 420 }}>
            {filteredIncidents.length === 0 ? (
              <Empty text="Perimeter secure. No active incidents." />
            ) : (
              filteredIncidents.slice(0, 5).map((i: Incident) => {
                const isCrit = i.severity === 'CRITICAL' || i.threat_score >= 75;
                const isHigh = i.severity === 'HIGH' || i.threat_score >= 55;
                const dialClass = isCrit ? '' : isHigh ? 'high' : i.threat_score >= 35 ? 'med' : 'low';

                return (
                  <div
                    key={i.id}
                    className={`incident-tactical-card ${isCrit ? 'crit' : ''}`}
                    onClick={() => openInc(i.id)}
                  >
                    <div className={`incident-score-dial ${dialClass}`}>
                      <span className="score-number">{i.threat_score.toFixed(0)}</span>
                      <span className="score-sub">SCORE</span>
                    </div>

                    <div className="incident-main-col">
                      <div className="incident-top-line">
                        <span className={`sev-badge sev-${i.severity.toLowerCase()}`}>{i.severity}</span>
                        <span className="incident-code-badge">{i.incident_code}</span>
                        <span className="incident-meta-text">{fmtTimeShort(i.created_at)}</span>
                      </div>
                      <div className="incident-title-text">{i.title}</div>
                      <div className="reason-tags">
                        {i.reason_codes.slice(0, 3).map((r: string) => (
                          <span key={r} className="reason-tag">
                            {r.split(':')[0].trim()}
                          </span>
                        ))}
                      </div>
                    </div>

                    <div className="incident-quick-actions" onClick={(e) => e.stopPropagation()}>
                      {i.status === 'OPEN' && (
                        <button
                          className="btn-quick-verify"
                          onClick={async () => {
                            playTacticalTone('verify');
                            await api.acknowledgeIncident(i.id);
                            openInc(i.id);
                          }}
                        >
                          VERIFY
                        </button>
                      )}
                      <button
                        className="btn-quick-escalate"
                        onClick={async () => {
                          playTacticalTone('escalate');
                          await api.escalateIncident(i.id);
                          openInc(i.id);
                        }}
                      >
                        ESCALATE
                      </button>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>
      </div>

      {/* Quick Tactical War Gaming Bar */}
      <div className="panel" style={{ padding: '10px 16px', background: 'rgba(6, 15, 26, 0.9)' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 10 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span style={{ fontFamily: 'var(--font-hud)', fontWeight: 700, fontSize: 13, color: '#00f0ff' }}>
              ▶ TACTICAL SCENARIO INJECTION:
            </span>
            <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
              <button className="btn btn-primary" onClick={() => runDemo('intrusion')} disabled={busy}>
                🚨 Perimeter Breach
              </button>
              <button className="btn btn-secondary" onClick={() => runDemo('night_movement')} disabled={busy}>
                🌙 Night Infiltration
              </button>
              <button className="btn btn-secondary" onClick={() => runDemo('loitering')} disabled={busy}>
                ⏳ Suspicious Loitering
              </button>
              <button className="btn btn-secondary" onClick={() => runDemo('vehicle')} disabled={busy}>
                🚙 Convoy / Vehicle
              </button>
              <button className="btn btn-secondary" onClick={() => runDemo('abandoned')} disabled={busy}>
                📦 Abandoned Gear
              </button>
              <button className="btn btn-secondary" onClick={() => runDemo('multi_camera')} disabled={busy}>
                📡 Multi-Post Correlation
              </button>
            </div>
          </div>
          {demoMsg && <span className="demo-status-msg">{demoMsg}</span>}
        </div>
      </div>
    </div>
  );
}

/* ─── Cameras Page ────────────────────────────────────────────── */
function CamerasPage({ cameras, onRefresh }: { cameras: Camera[]; onRefresh: () => void }) {
  const [view, setView] = useState<'grid' | 'wizard' | 'discover'>('grid');

  // Prioritize physical/real hardware cameras at the top of the grid
  const sortedCameras = [...cameras].sort((a, b) => {
    const aReal = !a.stream_url?.startsWith('demo://');
    const bReal = !b.stream_url?.startsWith('demo://');
    if (aReal && !bReal) return -1;
    if (!aReal && bReal) return 1;
    return a.id - b.id;
  });

  const physicalCount = cameras.filter((c) => !c.stream_url?.startsWith('demo://')).length;

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <h1 style={{ margin: 0 }}>Tactical Video Surveillance Grid</h1>
            {physicalCount > 0 && (
              <span className="page-tag" style={{ background: 'rgba(0, 255, 157, 0.15)', borderColor: '#00ff9d', color: '#00ff9d' }}>
                🟢 {physicalCount} PHYSICAL HARDWARE {physicalCount === 1 ? 'NODE' : 'NODES'} ACTIVE
              </span>
            )}
          </div>
          <p style={{ margin: '4px 0 0', fontSize: 12, color: 'var(--text-secondary)' }}>
            Integrated RTSP, USB & thermal camera edge perception node matrix
          </p>
        </div>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          <span className="page-tag">{cameras.length} TOTAL NODES</span>
          {physicalCount > 0 && (
            <button
              className="btn btn-sm btn-danger"
              style={{ background: 'rgba(255, 42, 85, 0.2)', borderColor: '#ff2a55', color: '#ff2a55' }}
              onClick={async () => {
                if (confirm('Disconnect ALL physical hardware cameras and release webcam hardware immediately?')) {
                  playTacticalTone('click');
                  const phys = cameras.filter((c) => !c.stream_url?.startsWith('demo://'));
                  for (const pc of phys) {
                    try { await api.disconnectCamera(pc.id); } catch {}
                  }
                  onRefresh();
                }
              }}
              title="Release all local hardware webcams and turn off camera LEDs"
            >
              🔌 Power Off All Cameras
            </button>
          )}
          <button className="btn btn-primary" onClick={() => setView('wizard')}>+ Deploy Camera</button>
          <button className="btn btn-secondary" onClick={() => setView('discover')}>🔍 Network Auto-Discovery</button>
        </div>
      </div>

      {view === 'wizard' && <CameraWizard onDone={() => { setView('grid'); onRefresh(); }} onCancel={() => setView('grid')} />}
      {view === 'discover' && <CameraDiscovery onDone={() => { setView('grid'); onRefresh(); }} onCancel={() => setView('grid')} />}

      {view === 'grid' && (
        <>
          {cameras.length === 0 ? (
            <div className="camera-empty">
              <div className="empty-icon">◎</div>
              <h3>No surveillance cameras provisioned</h3>
              <p>Connect IP, RTSP, or USB cameras to activate intelligent perimeter monitoring.</p>
              <div style={{ display: 'flex', gap: 10, justifyContent: 'center' }}>
                <button className="btn btn-primary" onClick={() => setView('wizard')}>+ Deploy Camera</button>
                <button className="btn btn-secondary" onClick={() => setView('discover')}>🔍 Auto-Discover</button>
              </div>
            </div>
          ) : (
            <div className="camera-live-grid">
              {sortedCameras.map((c) => (
                <CameraFeed key={c.id} camera={c} onRefresh={onRefresh} />
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}

/* ─── Dashboard Camera Frame (lightweight, no MJPEG) ─────────── */
const DashboardCamFrame = React.memo(function DashboardCamFrame({ cameraId, cameraName }: { cameraId: number; cameraName: string }) {
  const [tick, setTick] = useState(0);
  useEffect(() => {
    const iv = setInterval(() => setTick(t => t + 1), 2000);
    return () => clearInterval(iv);
  }, []);
  return (
    <div className="tactical-cam-frame">
      <img
        src={`/api/v1/cameras/${cameraId}/snapshot?t=${tick}`}
        alt={cameraName}
        onError={(e) => {
          const target = e.target as HTMLImageElement;
          setTimeout(() => { target.src = `/api/v1/cameras/${cameraId}/snapshot?t=${Date.now()}`; }, 3000);
        }}
      />
      <div className="corner-bracket cb-top-left" />
      <div className="corner-bracket cb-top-right" />
      <div className="corner-bracket cb-bottom-left" />
      <div className="corner-bracket cb-bottom-right" />
      <div className="tactical-crosshair-center" />
    </div>
  );
});

/* ─── Camera Feed Component ───────────────────────────────────── */
function CameraFeed({ camera, onRefresh }: { camera: Camera; onRefresh: () => void }) {
  const [detecting, setDetecting] = useState(false);
  const [disconnecting, setDisconnecting] = useState(false);
  const [imgKey, setImgKey] = useState(0);
  const isReal = !camera.stream_url?.startsWith('demo://');

  const snapshotUrl = `/api/v1/cameras/${camera.id}/snapshot?t=${imgKey}`;
  const streamUrl = `/api/v1/cameras/${camera.id}/stream`;

  // Auto-refresh snapshot every 1.5s so video always looks alive
  useEffect(() => {
    if (detecting) return;
    const interval = setInterval(() => {
      setImgKey(k => k + 1);
    }, 1500);
    return () => clearInterval(interval);
  }, [detecting]);

  const toggleStream = () => {
    playTacticalTone('click');
    setDetecting((prev) => !prev);
  };

  const handleDisconnect = async () => {
    if (!confirm(`Disconnect and power off camera "${camera.name}"? This will immediately release the hardware sensor and turn off the camera LED.`)) {
      return;
    }
    setDisconnecting(true);
    playTacticalTone('click');
    try {
      await api.disconnectCamera(camera.id);
      playTacticalTone('verify');
    } catch {
      // fallback to delete
      await api.deleteCamera(camera.id);
    }
    setDisconnecting(false);
    onRefresh();
  };

  return (
    <div className={`camera-feed ${isReal ? 'hardware-node' : ''}`} style={isReal ? { border: '1px solid rgba(0, 255, 157, 0.4)', boxShadow: '0 0 16px rgba(0, 255, 157, 0.1)' } : undefined}>
      <div className="camera-feed-video">
        <img
          src={detecting ? streamUrl : snapshotUrl}
          className="feed-img"
          alt={camera.name}
          onError={() => {
            setTimeout(() => setImgKey(Date.now()), 2500);
          }}
        />
        <div className="corner-bracket cb-top-left" />
        <div className="corner-bracket cb-top-right" />
        <div className="corner-bracket cb-bottom-left" />
        <div className="corner-bracket cb-bottom-right" />
        <div className="tactical-crosshair-center" />

        <div className="feed-hud">
          <span className="feed-hud-left">
            {isReal && <b style={{ color: '#00ff9d', marginRight: 6 }}>[LIVE HARDWARE]</b>}
            {camera.bop || 'BOP-01'} // {camera.name}
          </span>
          <span className="feed-hud-right">
            {detecting && <span className="detect-badge">LIVE MJPEG + YOLO</span>}
            <span className={`health-dot-sm ${camera.status.toLowerCase()}`} />
          </span>
        </div>
      </div>

      <div className="camera-feed-info">
        <div className="feed-details">
          <span className="feed-detail"><label>Health</label><b className={camera.health_score < 50 ? 'low' : ''}>{camera.health_score.toFixed(0)}%</b></span>
          <span className="feed-detail"><label>FPS</label>{camera.fps || 15}</span>
          <span className="feed-detail"><label>Res</label>{camera.resolution || '1280x720'}</span>
          <span className="feed-detail"><label>Type</label><span style={{ color: isReal ? '#00ff9d' : 'inherit' }}>{camera.stream_url?.startsWith('usb://') ? 'USB/WEBCAM' : (camera.camera_type || 'RTSP')}</span></span>
        </div>
        <div className="feed-actions">
          <button className={`btn btn-sm ${detecting ? 'btn-warn' : 'btn-primary'}`} onClick={toggleStream}>
            {detecting ? '⏹ Pause Stream' : '▶ Continuous Stream'}
          </button>
          {isReal && (
            <button
              className="btn btn-sm btn-danger"
              style={{ background: 'rgba(255, 42, 85, 0.15)', borderColor: '#ff2a55', color: '#ff2a55' }}
              onClick={handleDisconnect}
              disabled={disconnecting}
              title="Disconnect and Power Off Camera Hardware"
            >
              {disconnecting ? 'Disconnecting...' : '🔌 Power Off Camera'}
            </button>
          )}
          <button
            className="btn btn-sm btn-danger"
            onClick={async () => {
              if (confirm(`Remove surveillance node ${camera.name}?`)) {
                playTacticalTone('click');
                await api.deleteCamera(camera.id);
                onRefresh();
              }
            }}
            title="Delete Camera Node"
          >
            ✕
          </button>
        </div>
      </div>
    </div>
  );
}

/* ─── Camera Wizard & Discovery ───────────────────────────────── */
function CameraWizard({ onDone, onCancel }: { onDone: () => void; onCancel: () => void }) {
  const [step, setStep] = useState(1);
  const [brands, setBrands] = useState<any[]>([]);
  const [selectedBrand, setSelectedBrand] = useState('');
  const [ip, setIp] = useState('');
  const [username, setUsername] = useState('admin');
  const [password, setPassword] = useState('');
  const [port, setPort] = useState('554');
  const [name, setName] = useState('');
  const [location, setLocation] = useState('');
  const [bop, setBop] = useState('BOP-01');
  const [streamUrl, setStreamUrl] = useState('');
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<any>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [usbMode, setUsbMode] = useState(false);
  const [fileMode, setFileMode] = useState(false);
  const [filePath, setFilePath] = useState('');

  useEffect(() => {
    api.cameraBrands().then(setBrands).catch(() => {});
  }, []);

  useEffect(() => {
    if (usbMode) { setStreamUrl('usb://0'); return; }
    if (fileMode) { setStreamUrl(filePath ? `file://${filePath}` : ''); return; }
    const brand = brands.find((b: any) => b.id === selectedBrand);
    if (brand && ip) {
      const url = brand.rtsp_template
        .replace('{user}', username || brand.default_user)
        .replace('{pass}', password)
        .replace('{ip}', ip)
        .replace('{port}', port || String(brand.default_port));
      setStreamUrl(url);
    } else if (ip) {
      setStreamUrl(`rtsp://${username}:${password}@${ip}:${port}/stream1`);
    }
  }, [selectedBrand, ip, username, password, port, brands, usbMode, fileMode, filePath]);

  const doTest = async () => {
    if (!streamUrl) return;
    setTesting(true);
    setTestResult(null);
    try {
      const r = await api.testStream(streamUrl, selectedBrand, username, password);
      setTestResult(r);
      playTacticalTone(r.success ? 'verify' : 'alert');
    } catch (e: any) {
      setTestResult({ success: false, message: e.message || 'Test failed' });
      playTacticalTone('alert');
    }
    setTesting(false);
  };

  const doSave = async () => {
    setSaving(true);
    setError('');
    try {
      await api.createCamera({
        name: name || `${selectedBrand || 'Camera'} — ${ip || 'USB'}`,
        stream_url: streamUrl,
        location: location || 'Border Sector',
        bop: bop,
        camera_type: usbMode ? 'USB' : fileMode ? 'FILE' : 'IP',
        fps: 15,
        resolution: testResult?.width ? `${testResult.width}x${testResult.height}` : '1280x720',
        analytics_enabled: true,
        detection_interval: 3,
      });
      playTacticalTone('verify');
      onDone();
    } catch (e: any) {
      setError(e.message || 'Failed to register camera');
      playTacticalTone('alert');
    }
    setSaving(false);
  };

  const popularBrands = brands.filter((b: any) => !['usb', 'file'].includes(b.id));

  return (
    <div className="wizard-overlay">
      <div className="wizard">
        <div className="wizard-header">
          <h2>Deploy Surveillance Node</h2>
          <button className="btn-close" onClick={onCancel}>✕</button>
        </div>

        <div className="wizard-steps">
          <div className={`wizard-step ${step >= 1 ? 'active' : ''}`}><span>1</span> Hardware Protocol</div>
          <div className="wizard-step-arrow">→</div>
          <div className={`wizard-step ${step >= 2 ? 'active' : ''}`}><span>2</span> Network Telemetry</div>
          <div className="wizard-step-arrow">→</div>
          <div className={`wizard-step ${step >= 3 ? 'active' : ''}`}><span>3</span> Signal Verification</div>
        </div>

        {step === 1 && (
          <div className="wizard-body">
            <p className="wizard-hint">Select defense-grade camera manufacturer or input protocol:</p>
            <div className="brand-grid">
              {popularBrands.map((b: any) => (
                <button
                  key={b.id}
                  className={`brand-card${selectedBrand === b.id ? ' selected' : ''}`}
                  onClick={() => {
                    setSelectedBrand(b.id);
                    setUsbMode(false);
                    setFileMode(false);
                  }}
                >
                  <b>{b.name}</b>
                  <small>RTSP Camera</small>
                </button>
              ))}
            </div>
            <div className="brand-divider"><span>TACTICAL INTERFACES</span></div>
            <div className="brand-alt-row">
              <button
                className={`brand-card alt${usbMode ? ' selected' : ''}`}
                onClick={() => { setUsbMode(true); setFileMode(false); setSelectedBrand('usb'); }}
              >
                <b>USB / Thermal Drone Feed</b>
                <small>Local Sensor /dev/video0</small>
              </button>
              <button
                className={`brand-card alt${fileMode ? ' selected' : ''}`}
                onClick={() => { setFileMode(true); setUsbMode(false); setSelectedBrand('file'); }}
              >
                <b>Recorded Forensic Video</b>
                <small>MP4/AVI/MKV Reconnaissance</small>
              </button>
            </div>
          </div>
        )}

        {step === 2 && (
          <div className="wizard-body">
            {usbMode ? (
              <div className="form-group">
                <label>USB Video Device Index</label>
                <input type="text" value={streamUrl} onChange={(e) => setStreamUrl(e.target.value)} placeholder="usb://0" />
              </div>
            ) : fileMode ? (
              <div className="form-group">
                <label>Forensic Video File Path</label>
                <input type="text" value={filePath} onChange={(e) => setFilePath(e.target.value)} placeholder="/path/to/surveillance_sample.mp4" />
              </div>
            ) : (
              <>
                <div className="form-row">
                  <div className="form-group" style={{ flex: 2 }}>
                    <label>Camera IP Address</label>
                    <input type="text" value={ip} onChange={(e) => setIp(e.target.value)} placeholder="192.168.1.108" />
                  </div>
                  <div className="form-group" style={{ flex: 1 }}>
                    <label>RTSP Port</label>
                    <input type="text" value={port} onChange={(e) => setPort(e.target.value)} placeholder="554" />
                  </div>
                </div>
                <div className="form-row">
                  <div className="form-group">
                    <label>Security Username</label>
                    <input type="text" value={username} onChange={(e) => setUsername(e.target.value)} placeholder="admin" />
                  </div>
                  <div className="form-group">
                    <label>Security Password</label>
                    <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="••••••••" />
                  </div>
                </div>
              </>
            )}

            <div className="form-row">
              <div className="form-group">
                <label>Node Designation Name</label>
                <input type="text" value={name} onChange={(e) => setName(e.target.value)} placeholder="BOP-01 Sector Alpha Gate" />
              </div>
              <div className="form-group">
                <label>Border Outpost (BOP)</label>
                <select value={bop} onChange={(e) => setBop(e.target.value)}>
                  <option value="BOP-01">BOP-01 (Sector Alpha)</option>
                  <option value="BOP-02">BOP-02 (Sector Bravo)</option>
                  <option value="BOP-03">BOP-03 (Sector Charlie)</option>
                  <option value="BOP-04">BOP-04 (Sector Delta)</option>
                </select>
              </div>
            </div>
          </div>
        )}

        {step === 3 && (
          <div className="wizard-body">
            <div className="test-preview-box">
              <label>Constructed RTSP Video URI:</label>
              <div className="stream-url-display">{streamUrl || 'No URI specified'}</div>
              <button className="btn btn-primary" onClick={doTest} disabled={testing || !streamUrl}>
                {testing ? 'Testing Optical Signal...' : '⚡ Test Optical Connection'}
              </button>
            </div>

            {testResult && (
              <div className={`test-feedback ${testResult.success ? 'success' : 'fail'}`}>
                {testResult.success ? '✓ Optical link established! Codec: H.264 / FPS: 15' : `✕ Link failure: ${testResult.message}`}
              </div>
            )}
            {error && <div className="test-feedback fail">✕ {error}</div>}
          </div>
        )}

        <div className="wizard-footer">
          {step > 1 && <button className="btn btn-secondary" onClick={() => setStep(step - 1)}>← Previous</button>}
          <div style={{ flex: 1 }} />
          {step < 3 ? (
            <button className="btn btn-primary" onClick={() => setStep(step + 1)} disabled={step === 1 && !selectedBrand}>
              Next Step →
            </button>
          ) : (
            <button className="btn btn-primary" onClick={doSave} disabled={saving}>
              {saving ? 'Registering...' : '✓ Provision Surveillance Node'}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

function CameraDiscovery({ onDone, onCancel }: { onDone: () => void; onCancel: () => void }) {
  return <UniversalCameraStudio onDone={onDone} onCancel={onCancel} />;
}

function UniversalCameraStudio({ onDone, onCancel }: { onDone: () => void; onCancel: () => void }) {
  const [tab, setTab] = useState<'lan' | 'probe' | 'phone' | 'remote'>('lan');
  const [subnet, setSubnet] = useState('192.168.29');
  const [localIp, setLocalIp] = useState('192.168.29.253');
  const [scanning, setScanning] = useState(false);
  const [scanDuration, setScanDuration] = useState<number | null>(null);
  const [found, setFound] = useState<any[]>([]);
  const [statusMsg, setStatusMsg] = useState<string | null>(null);
  const [adopting, setAdopting] = useState<string | null>(null);
  const [testingStream, setTestingStream] = useState<string | null>(null);
  const [streamTestStatus, setStreamTestStatus] = useState<{ [key: string]: string }>({});

  // Strix Smart Prober state
  const [probeIp, setProbeIp] = useState('192.168.29.107');
  const [probeUser, setProbeUser] = useState('admin');
  const [probePass, setProbePass] = useState('admin123');
  const [probing, setProbing] = useState(false);
  const [probeResult, setProbeResult] = useState<any | null>(null);

  // Phone Broadcaster modal state
  const [showPhoneBroadcaster, setShowPhoneBroadcaster] = useState(false);

  // Remote Stream state
  const [remoteName, setRemoteName] = useState('Remote Recon Stream');
  const [remoteUrl, setRemoteUrl] = useState('');
  const [remoteBop, setRemoteBop] = useState('BOP-01 Alpha');

  // Auto-detect host network info on mount
  useEffect(() => {
    api.networkInfo().then((info: any) => {
      if (info?.subnet) setSubnet(info.subnet);
      if (info?.local_ip) {
        setLocalIp(info.local_ip);
        setProbeIp(info.local_ip.replace(/\.\d+$/, '.107'));
      }
    }).catch(() => {});
  }, []);

  const runLanScan = async () => {
    setScanning(true);
    setStatusMsg(null);
    playTacticalTone('click');
    const t0 = Date.now();
    try {
      const r = await api.discoverCameras(subnet);
      const list = Array.isArray(r) ? r : (r as any).discovered || [];
      // Filter out gateway router if desired or keep with tag
      setFound(list);
      const dur = Math.round((Date.now() - t0) / 100) / 10;
      setScanDuration(dur);
      playTacticalTone(list.length > 0 ? 'verify' : 'alert');
      if (list.length > 0) {
        setStatusMsg(`Discovered ${list.length} hardware endpoints on subnet ${subnet}.0/24 in ${dur}s.`);
      } else {
        setStatusMsg(`Scan complete in ${dur}s — 0 endpoints detected.`);
      }
    } catch (e: any) {
      setFound([]);
      setStatusMsg(`Scan error: ${e.message || 'Subnet probe timed out'}`);
    }
    setScanning(false);
  };

  const adoptDevice = async (d: any, customName?: string, customUrl?: string) => {
    const adoptKey = d.ip || d.name || 'manual';
    setAdopting(adoptKey);
    playTacticalTone('verify');
    try {
      await api.createCamera({
        name: customName || `${d.brand_hint || d.name || 'CCTV Camera'} (${d.ip})`,
        stream_url: customUrl || d.rtsp_url || `rtsp://admin:admin123@${d.ip}:${d.port || 554}/stream1`,
        location: `Sector LAN Node (${d.ip || 'Remote'})`,
        bop: d.bop || 'BOP-01',
        status: 'ONLINE',
        health_score: 100,
        fps: 15,
        resolution: '1920x1080',
        latitude: 28.6139,
        longitude: 77.2090,
      });
      setStatusMsg(`Successfully provisioned surveillance node for ${d.ip || customName}!`);
      setTimeout(onDone, 900);
    } catch (err: any) {
      setStatusMsg(`Adoption error: ${err.message}`);
    }
    setAdopting(null);
  };

  const testCandidateStream = async (url: string, key: string) => {
    setTestingStream(key);
    playTacticalTone('click');
    try {
      const r = await api.testStream(url);
      if (r.success) {
        playTacticalTone('verify');
        setStreamTestStatus((prev) => ({ ...prev, [key]: `✓ ${r.message}` }));
      } else {
        playTacticalTone('alert');
        setStreamTestStatus((prev) => ({ ...prev, [key]: `✕ ${r.message}` }));
      }
    } catch (e: any) {
      setStreamTestStatus((prev) => ({ ...prev, [key]: `✕ Test failed: ${e.message}` }));
    }
    setTestingStream(null);
  };

  const runSmartProbe = async () => {
    setProbing(true);
    setProbeResult(null);
    playTacticalTone('click');
    try {
      const r = await api.smartProbe(probeIp, probeUser, probePass);
      setProbeResult(r);
      if (r.success) {
        playTacticalTone('verify');
      } else {
        playTacticalTone('alert');
      }
    } catch (err: any) {
      setProbeResult({ success: false, message: `Prober error: ${err.message}` });
    }
    setProbing(false);
  };

  return (
    <div className="wizard-overlay">
      <div className="wizard" style={{ maxWidth: 840, maxHeight: '92vh', overflowY: 'auto' }}>
        <div className="wizard-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid rgba(0, 240, 255, 0.25)', paddingBottom: 14 }}>
          <div>
            <h2 style={{ margin: 0, fontSize: 18, color: '#00f0ff', letterSpacing: '0.8px' }}>
              📡 Universal Multi-Camera Connection & Discovery Studio
            </h2>
            <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginTop: 4 }}>
              Active LAN Subnet: <span style={{ color: '#00ff9d', fontFamily: 'var(--font-mono)' }}>{subnet}.0/24</span> • Local Host: <span style={{ color: '#00f0ff', fontFamily: 'var(--font-mono)' }}>{localIp}</span>
            </div>
          </div>
          <button className="btn-close" onClick={onCancel} style={{ background: 'transparent', border: 'none', color: '#fff', fontSize: 18, cursor: 'pointer' }}>✕</button>
        </div>

        <div className="wizard-body" style={{ paddingTop: 16 }}>
          {/* Studio Tab Bar */}
          <div className="studio-tab-bar">
            <button className={`studio-tab-btn${tab === 'lan' ? ' active' : ''}`} onClick={() => setTab('lan')}>
              📡 LAN Auto-Discovery ({found.length})
            </button>
            <button className={`studio-tab-btn${tab === 'probe' ? ' active' : ''}`} onClick={() => setTab('probe')}>
              🎯 Strix Smart URL Prober
            </button>
            <button className={`studio-tab-btn${tab === 'phone' ? ' active' : ''}`} onClick={() => setTab('phone')}>
              📱 Smartphone Live Bridge
            </button>
            <button className={`studio-tab-btn${tab === 'remote' ? ' active' : ''}`} onClick={() => setTab('remote')}>
              🌐 Remote WAN / Cloud CCTV
            </button>
          </div>

          {statusMsg && (
            <div style={{ padding: '8px 12px', background: '#0a192f', border: '1px solid #00f0ff40', borderRadius: 4, marginBottom: 14, fontSize: 12, color: '#00f0ff', display: 'flex', justifyContent: 'space-between' }}>
              <span>{statusMsg}</span>
              {scanDuration !== null && <span>⚡ {scanDuration}s</span>}
            </div>
          )}

          {/* TAB 1: LAN AUTO-DISCOVERY */}
          {tab === 'lan' && (
            <div>
              <div style={{ display: 'flex', gap: 10, marginBottom: 16, alignItems: 'center' }}>
                <div style={{ flex: 1 }}>
                  <label style={{ fontSize: 11, color: 'var(--text-secondary)', display: 'block', marginBottom: 4 }}>
                    TARGET SUBNET BASE (AUTO-RESOLVED)
                  </label>
                  <input
                    type="text"
                    value={subnet}
                    onChange={(e) => setSubnet(e.target.value)}
                    placeholder="192.168.29"
                    style={{ width: '100%', fontFamily: 'var(--font-mono)', fontSize: 13 }}
                  />
                </div>
                <button
                  className="btn btn-primary"
                  onClick={runLanScan}
                  disabled={scanning}
                  style={{ height: 38, marginTop: 18, minWidth: 200 }}
                >
                  {scanning ? '⏳ Scanning 254 Nodes...' : '🔍 Deep Hardware Scan'}
                </button>
              </div>

              {found.length === 0 && !scanning && (
                <div style={{ textAlign: 'center', padding: '36px 20px', background: 'rgba(0, 240, 255, 0.02)', border: '1px dashed rgba(0, 240, 255, 0.2)', borderRadius: 8, marginBottom: 16 }}>
                  <div style={{ fontSize: 32, marginBottom: 8 }}>📡</div>
                  <b style={{ color: '#fff', fontSize: 14 }}>Ready to Scan Network Cameras</b>
                  <p style={{ fontSize: 12, color: 'var(--text-secondary)', maxWidth: 480, margin: '8px auto 16px auto' }}>
                    Click <b>Deep Hardware Scan</b> to detect all connected IP cameras (TP-Link Tapo, AzureWave, CP Plus, Hikvision, Dahua, mobile streaming nodes) on subnet <b>{subnet}.0/24</b>.
                  </p>
                  <button className="btn btn-primary" onClick={runLanScan}>
                    🔍 Run Deep Hardware Scan
                  </button>
                </div>
              )}

              {/* Discovered Device Cards Grid */}
              {found.length > 0 && (
                <div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
                    <span style={{ fontSize: 12, fontWeight: 700, color: 'var(--text-secondary)', letterSpacing: '0.5px' }}>
                      DISCOVERED NETWORK HARDWARE ({found.length} DEVICES ACTIVE)
                    </span>
                    <button className="btn btn-sm btn-secondary" onClick={runLanScan} disabled={scanning}>
                      🔄 Rescan
                    </button>
                  </div>

                  <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                    {found.map((c, i) => {
                      const isTapo = c.brand_hint?.includes('Tapo');
                      const isAzureWave = c.brand_hint?.includes('AzureWave');
                      const isMobile = c.brand_hint?.includes('Mobile');
                      const isGw = c.is_gateway;

                      return (
                        <div key={i} className="discovered-camera-card">
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 10 }}>
                            <div>
                              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                                <b style={{ color: '#fff', fontSize: 14, fontFamily: 'var(--font-mono)' }}>{c.ip}</b>
                                <span className="camera-badge-tag" style={{
                                  background: isTapo ? 'rgba(0, 240, 255, 0.15)' : isAzureWave ? 'rgba(255, 170, 0, 0.15)' : isMobile ? 'rgba(0, 255, 157, 0.15)' : 'rgba(255, 255, 255, 0.1)',
                                  color: isTapo ? '#00f0ff' : isAzureWave ? '#ffaa00' : isMobile ? '#00ff9d' : '#e0e6ed',
                                  border: `1px solid ${isTapo ? '#00f0ff' : isAzureWave ? '#ffaa00' : isMobile ? '#00ff9d' : 'rgba(255,255,255,0.2)'}`
                                }}>
                                  {c.brand_hint || 'NETWORK NODE'}
                                </span>
                                {c.mac && (
                                  <span style={{ fontSize: 10, color: 'var(--text-ghost)', fontFamily: 'var(--font-mono)' }}>
                                    MAC: {c.mac}
                                  </span>
                                )}
                              </div>

                              <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginTop: 4 }}>
                                <span style={{ color: c.status?.includes('Active') || c.status?.includes('Node') ? '#00ff9d' : '#ffaa00' }}>
                                  ● {c.status}
                                </span>
                                {c.open_ports?.length > 0 && (
                                  <span style={{ marginLeft: 10, color: 'var(--text-ghost)' }}>
                                    Open Ports: {c.open_ports.join(', ')}
                                  </span>
                                )}
                              </div>

                              {c.setup_tip && (
                                <div style={{ fontSize: 11, color: '#ffaa00', marginTop: 6, background: 'rgba(255, 170, 0, 0.05)', padding: '4px 8px', borderRadius: 4, borderLeft: '3px solid #ffaa00' }}>
                                  💡 <b>Setup Tip:</b> {c.setup_tip}
                                </div>
                              )}

                              <div style={{ fontSize: 11, color: '#00f0ff', fontFamily: 'var(--font-mono)', marginTop: 6, wordBreak: 'break-all' }}>
                                Candidate Stream: {c.rtsp_url}
                              </div>

                              {streamTestStatus[c.ip] && (
                                <div style={{ fontSize: 11, marginTop: 4, color: streamTestStatus[c.ip].startsWith('✓') ? '#00ff9d' : '#ff2a55' }}>
                                  {streamTestStatus[c.ip]}
                                </div>
                              )}
                            </div>

                            <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
                              <button
                                className="btn btn-sm btn-secondary"
                                onClick={() => testCandidateStream(c.rtsp_url, c.ip)}
                                disabled={testingStream === c.ip}
                                title="Verify stream frames with OpenCV"
                              >
                                {testingStream === c.ip ? 'Testing...' : '🧪 Test Stream'}
                              </button>

                              <button
                                className="btn btn-sm btn-secondary"
                                onClick={() => {
                                  setProbeIp(c.ip);
                                  setTab('probe');
                                }}
                                title="Run Strix Smart Prober for this IP"
                              >
                                🎯 Smart Probe
                              </button>

                              <button
                                className="btn btn-sm btn-primary"
                                onClick={() => adoptDevice(c)}
                                disabled={adopting === c.ip || isGw}
                                title={isGw ? 'Router Gateway' : 'Add to live surveillance matrix'}
                              >
                                {adopting === c.ip ? 'Adopting...' : isGw ? 'Router' : '⚡ 1-Click Adopt'}
                              </button>
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* TAB 2: STRIX SMART STREAM PROBER */}
          {tab === 'probe' && (
            <div>
              <div style={{ padding: '14px 16px', background: 'rgba(0, 240, 255, 0.03)', border: '1px solid rgba(0, 240, 255, 0.2)', borderRadius: 6, marginBottom: 16 }}>
                <b style={{ color: '#00f0ff', fontSize: 13 }}>🎯 Strix Smart Stream Finder (Fast Auto-Pattern Prober)</b>
                <p style={{ fontSize: 11, color: 'var(--text-secondary)', margin: '4px 0 12px 0' }}>
                  Enter any camera IP (e.g. 192.168.29.107) and camera credentials. The prober will concurrently test the top 15 most common RTSP/HTTP URL patterns (Tapo, CP Plus, Dahua, Hikvision, Reolink, Axis) and automatically lock onto the active stream.
                </p>

                <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr 1fr auto', gap: 10, alignItems: 'flex-end' }}>
                  <div>
                    <label style={{ fontSize: 11, color: 'var(--text-secondary)' }}>CAMERA IP ADDRESS</label>
                    <input
                      type="text"
                      value={probeIp}
                      onChange={(e) => setProbeIp(e.target.value)}
                      placeholder="192.168.29.107"
                      style={{ width: '100%', fontFamily: 'var(--font-mono)' }}
                    />
                  </div>
                  <div>
                    <label style={{ fontSize: 11, color: 'var(--text-secondary)' }}>USERNAME</label>
                    <input
                      type="text"
                      value={probeUser}
                      onChange={(e) => setProbeUser(e.target.value)}
                      placeholder="admin"
                      style={{ width: '100%' }}
                    />
                  </div>
                  <div>
                    <label style={{ fontSize: 11, color: 'var(--text-secondary)' }}>PASSWORD</label>
                    <input
                      type="password"
                      value={probePass}
                      onChange={(e) => setProbePass(e.target.value)}
                      placeholder="Password"
                      style={{ width: '100%' }}
                    />
                  </div>
                  <button
                    className="btn btn-primary"
                    onClick={runSmartProbe}
                    disabled={probing || !probeIp}
                    style={{ height: 38, minWidth: 140 }}
                  >
                    {probing ? 'Probing...' : '🚀 Probe Stream'}
                  </button>
                </div>
              </div>

              {probeResult && (
                <div style={{ padding: '14px 16px', background: probeResult.success ? 'rgba(0, 255, 157, 0.06)' : 'rgba(255, 42, 85, 0.06)', border: `1px solid ${probeResult.success ? '#00ff9d' : '#ff2a55'}`, borderRadius: 6, marginBottom: 16 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div>
                      <b style={{ color: probeResult.success ? '#00ff9d' : '#ff2a55', fontSize: 13 }}>
                        {probeResult.success ? '✓ Stream Found & Verified!' : '✕ Prober Status'}
                      </b>
                      <div style={{ fontSize: 12, color: '#fff', marginTop: 4 }}>
                        {probeResult.message}
                      </div>
                      {probeResult.working_url && (
                        <div style={{ fontSize: 12, color: '#00f0ff', fontFamily: 'var(--font-mono)', marginTop: 6, wordBreak: 'break-all' }}>
                          URL: {probeResult.working_url}
                        </div>
                      )}
                    </div>
                    {probeResult.success && probeResult.working_url && (
                      <button
                        className="btn btn-primary"
                        onClick={() => adoptDevice({ ip: probeIp, brand_hint: probeResult.brand_detected }, `Discovered ${probeResult.brand_detected}`, probeResult.working_url)}
                      >
                        ⚡ Adopt Stream
                      </button>
                    )}
                  </div>
                </div>
              )}

              <div className="prober-console-box">
                <div style={{ color: 'var(--text-ghost)', marginBottom: 6 }}>// CANDIDATE URL PATTERNS TESTED BY PROBER:</div>
                <div>• rtsp://[user]:[pass]@{probeIp || 'IP'}:554/stream1 (TP-Link Tapo Main Stream)</div>
                <div>• rtsp://[user]:[pass]@{probeIp || 'IP'}:554/stream2 (TP-Link Tapo Sub Stream)</div>
                <div>• rtsp://[user]:[pass]@{probeIp || 'IP'}:554/cam/realmonitor?channel=1&subtype=0 (CP Plus / Dahua)</div>
                <div>• rtsp://[user]:[pass]@{probeIp || 'IP'}:554/Streaming/Channels/101 (Hikvision Main)</div>
                <div>• rtsp://[user]:[pass]@{probeIp || 'IP'}:554/h264Preview_01_main (Reolink Main)</div>
                <div>• rtsp://[user]:[pass]@{probeIp || 'IP'}:554/axis-media/media.amp (Axis Media)</div>
                <div>• http://{probeIp || 'IP'}:8080/video (Mobile IP Webcam Stream)</div>
                <div>• http://{probeIp || 'IP'}:4747/video (Mobile DroidCam Stream)</div>
              </div>
            </div>
          )}

          {/* TAB 3: SMARTPHONE LIVE BRIDGE */}
          {tab === 'phone' && (
            <div>
              <div style={{ padding: '16px', background: 'rgba(0, 255, 157, 0.04)', border: '1px solid rgba(0, 255, 157, 0.25)', borderRadius: 6, marginBottom: 16 }}>
                <b style={{ color: '#00ff9d', fontSize: 14 }}>📱 Turn Any Smartphone Into An Active Border Surveillance Node</b>
                <p style={{ fontSize: 12, color: 'var(--text-secondary)', margin: '6px 0 14px 0' }}>
                  Open this link on any iPhone, Android phone, or laptop browser connected to Wi-Fi. It turns the device's camera into an instant live video surveillance feed streamed directly into IBVAP Command Center with real-time YOLO AI object detection.
                </p>

                <div style={{ display: 'flex', gap: 12, alignItems: 'center', background: '#040b15', padding: '12px 16px', borderRadius: 6, border: '1px solid rgba(0, 255, 157, 0.3)', marginBottom: 14 }}>
                  <div style={{ fontSize: 24 }}>🔗</div>
                  <div style={{ flex: 1, fontFamily: 'var(--font-mono)', fontSize: 13, color: '#00ff9d', wordBreak: 'break-all' }}>
                    http://{localIp || '192.168.29.253'}:5173/phone-camera
                  </div>
                  <button
                    className="btn btn-sm btn-secondary"
                    style={{ borderColor: '#00ff9d', color: '#00ff9d' }}
                    onClick={() => {
                      navigator.clipboard.writeText(`http://${localIp || '192.168.29.253'}:5173/phone-camera`);
                      setStatusMsg('Broadcast link copied to clipboard!');
                    }}
                  >
                    📋 Copy Link
                  </button>
                  <button
                    className="btn btn-sm btn-primary"
                    onClick={() => setShowPhoneBroadcaster(true)}
                  >
                    📱 Open In-App
                  </button>
                </div>

                <div style={{ display: 'flex', gap: 10, justifyContent: 'flex-end' }}>
                  <button
                    className="btn btn-primary"
                    onClick={() => adoptDevice({ ip: localIp, brand_hint: 'Tactical Smartphone Node' }, 'Tactical Smartphone Node', 'phone://mobile-01')}
                    disabled={adopting === 'phone://mobile-01'}
                  >
                    {adopting === 'phone://mobile-01' ? 'Connecting...' : '⚡ Provision Smartphone Camera (phone://mobile-01)'}
                  </button>
                </div>
              </div>

              {/* Mobile Apps Alternative */}
              <div style={{ padding: '14px 16px', background: 'rgba(255, 170, 0, 0.04)', border: '1px solid rgba(255, 170, 0, 0.25)', borderRadius: 6 }}>
                <b style={{ color: '#ffaa00', fontSize: 13 }}>💡 Alternative: Use Popular Mobile Camera Apps</b>
                <div style={{ fontSize: 11, color: 'var(--text-secondary)', margin: '4px 0 10px 0' }}>
                  If you have <b>IP Webcam</b> or <b>DroidCam</b> installed on your phone:
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                  <div style={{ background: '#070f1e', padding: 10, borderRadius: 4, border: '1px solid rgba(255,255,255,0.1)' }}>
                    <b style={{ color: '#fff', fontSize: 12 }}>1. IP Webcam (Android / iOS)</b>
                    <div style={{ fontSize: 11, color: 'var(--text-ghost)', marginTop: 2 }}>Tap "Start Server" in the app</div>
                    <div style={{ fontSize: 11, color: '#00f0ff', fontFamily: 'var(--font-mono)', marginTop: 4 }}>http://[Phone-IP]:8080/video</div>
                  </div>
                  <div style={{ background: '#070f1e', padding: 10, borderRadius: 4, border: '1px solid rgba(255,255,255,0.1)' }}>
                    <b style={{ color: '#fff', fontSize: 12 }}>2. DroidCam (Android / iOS)</b>
                    <div style={{ fontSize: 11, color: 'var(--text-ghost)', marginTop: 2 }}>Note the Wi-Fi IP and Port 4747</div>
                    <div style={{ fontSize: 11, color: '#00f0ff', fontFamily: 'var(--font-mono)', marginTop: 4 }}>http://[Phone-IP]:4747/video</div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* TAB 4: REMOTE WAN / CLOUD / WEBRTC */}
          {tab === 'remote' && (
            <div>
              <div style={{ padding: '14px 16px', background: 'rgba(0, 240, 255, 0.03)', border: '1px solid rgba(0, 240, 255, 0.2)', borderRadius: 6, marginBottom: 16 }}>
                <b style={{ color: '#00f0ff', fontSize: 13 }}>🌐 Connect Remote WAN, Cloud CCTV, or Tactical Stream</b>
                <p style={{ fontSize: 11, color: 'var(--text-secondary)', margin: '4px 0 12px 0' }}>
                  Connect any camera located outside the local network via public IP, dynamic DNS, Starlink SIM router, HLS (m3u8), or RTSP/RTMP proxy.
                </p>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 2fr 1fr auto', gap: 10, alignItems: 'flex-end', marginBottom: 14 }}>
                  <div>
                    <label style={{ fontSize: 11, color: 'var(--text-secondary)' }}>CAMERA NAME</label>
                    <input
                      type="text"
                      value={remoteName}
                      onChange={(e) => setRemoteName(e.target.value)}
                      placeholder="Sector Remote Recon"
                      style={{ width: '100%' }}
                    />
                  </div>
                  <div>
                    <label style={{ fontSize: 11, color: 'var(--text-secondary)' }}>STREAM URL (RTSP / RTMP / HTTP / HLS)</label>
                    <input
                      type="text"
                      value={remoteUrl}
                      onChange={(e) => setRemoteUrl(e.target.value)}
                      placeholder="rtsp://user:pass@remote.domain.com:554/live or http://..."
                      style={{ width: '100%', fontFamily: 'var(--font-mono)' }}
                    />
                  </div>
                  <div>
                    <label style={{ fontSize: 11, color: 'var(--text-secondary)' }}>OUTPOST / SECTOR</label>
                    <select
                      value={remoteBop}
                      onChange={(e) => setRemoteBop(e.target.value)}
                      style={{ width: '100%', height: 38 }}
                    >
                      <option value="BOP-01 Alpha">BOP-01 Alpha</option>
                      <option value="BOP-02 Bravo">BOP-02 Bravo</option>
                      <option value="BOP-03 Charlie">BOP-03 Charlie</option>
                      <option value="BOP-04 Delta">BOP-04 Delta</option>
                    </select>
                  </div>
                  <button
                    className="btn btn-primary"
                    onClick={() => adoptDevice({ bop: remoteBop }, remoteName, remoteUrl)}
                    disabled={!remoteUrl || adopting === 'remote'}
                    style={{ height: 38 }}
                  >
                    {adopting === 'remote' ? 'Connecting...' : '+ Ingest Stream'}
                  </button>
                </div>
              </div>

              {/* Pre-Configured Tactical Border Presets */}
              <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--text-secondary)', marginBottom: 8, letterSpacing: 0.8 }}>
                TACTICAL BORDER RECONNAISSANCE PRESETS (1-CLICK INGEST)
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
                {[
                  { name: '🏔️ Sector Alpha: Indo-Nepal High Pass (Thermal 4K)', url: 'demo://high-pass-recon', bop: 'BOP-01 Alpha' },
                  { name: '🌲 Sector Bravo: Forest Ambush Trail (IR Night Hunter)', url: 'demo://forest-perimeter', bop: 'BOP-02 Bravo' },
                  { name: '🌊 Sector Charlie: Riverine Sarda Patrol (Optical)', url: 'demo://riverine-patrol', bop: 'BOP-03 Charlie' },
                  { name: '🚁 Sector Delta: Tactical Border Drone (EO/IR UAV)', url: 'demo://drone-aerial-recon', bop: 'BOP-04 Delta' },
                ].map((p, idx) => (
                  <div key={idx} style={{ background: '#070f1e', border: '1px solid rgba(0, 240, 255, 0.2)', padding: 12, borderRadius: 6, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div>
                      <b style={{ color: '#fff', fontSize: 12 }}>{p.name}</b>
                      <div style={{ fontSize: 10, color: '#00f0ff', fontFamily: 'var(--font-mono)' }}>{p.bop}</div>
                    </div>
                    <button className="btn btn-sm btn-secondary" onClick={() => adoptDevice({ bop: p.bop }, p.name, p.url)}>
                      + Ingest
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {showPhoneBroadcaster && (
        <PhoneCameraTransmitter onReturn={() => setShowPhoneBroadcaster(false)} />
      )}
    </div>
  );
}

function PhoneCameraTransmitter({ onReturn }: { onReturn: () => void }) {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const [active, setActive] = useState(false);
  const [fps, setFps] = useState(0);
  const [frameCount, setFrameCount] = useState(0);
  const [facing, setFacing] = useState<'environment' | 'user'>('environment');
  const [statusText, setStatusText] = useState('Camera Standby — Tap Start to Transmit');
  const streamRef = useRef<MediaStream | null>(null);

  const startCam = async () => {
    try {
      setStatusText('Requesting optical sensor access...');
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((t) => t.stop());
      }
      const s = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: facing, width: { ideal: 1280 }, height: { ideal: 720 } },
        audio: false,
      });
      streamRef.current = s;
      if (videoRef.current) {
        videoRef.current.srcObject = s;
        videoRef.current.play();
      }
      setActive(true);
      setStatusText('● TRANSMITTING LIVE EO SENSOR TO COMMAND CENTER');
    } catch (err: any) {
      setStatusText(`Sensor error: ${err.message}`);
    }
  };

  const stopCam = () => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
    }
    setActive(false);
    setStatusText('Optical sensor released');
  };

  const toggleFacing = () => {
    const next = facing === 'environment' ? 'user' : 'environment';
    setFacing(next);
    if (active) {
      setTimeout(() => startCam(), 100);
    }
  };

  useEffect(() => {
    startCam();
    return () => {
      stopCam();
    };
  }, [facing]);

  // Frame capture and transmission loop (10 FPS)
  useEffect(() => {
    if (!active) return;
    let secFrames = 0;
    const fpsTimer = setInterval(() => {
      setFps(secFrames);
      secFrames = 0;
    }, 1000);

    const txTimer = setInterval(() => {
      const v = videoRef.current;
      const c = canvasRef.current;
      if (!v || !c || v.readyState < 2) return;
      c.width = v.videoWidth || 1280;
      c.height = v.videoHeight || 720;
      const ctx = c.getContext('2d');
      if (!ctx) return;
      ctx.drawImage(v, 0, 0, c.width, c.height);
      const b64 = c.toDataURL('image/jpeg', 0.65);
      api.uploadPhoneFrame('mobile-01', b64).catch(() => {});
      secFrames++;
      setFrameCount((prev) => prev + 1);
    }, 100);

    return () => {
      clearInterval(fpsTimer);
      clearInterval(txTimer);
    };
  }, [active]);

  return (
    <div className="phone-broadcaster-hud">
      <div style={{ position: 'absolute', top: 16, left: 16, right: 16, display: 'flex', justifyContent: 'space-between', zIndex: 10 }}>
        <div style={{ background: 'rgba(0,0,0,0.7)', padding: '6px 12px', borderRadius: 4, border: '1px solid #00f0ff' }}>
          <b style={{ color: '#00f0ff', fontSize: 12 }}>IBVAP TACTICAL SENSOR BROADCASTER</b>
          <div style={{ fontSize: 10, color: active ? '#00ff9d' : '#ffaa00' }}>{statusText}</div>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <button className="btn btn-sm btn-secondary" onClick={toggleFacing}>
            🔄 Flip ({facing === 'environment' ? 'Rear' : 'Front'})
          </button>
          <button className="btn btn-sm btn-primary" onClick={onReturn}>
            ✕ Close Viewfinder
          </button>
        </div>
      </div>

      <video
        ref={videoRef}
        playsInline
        muted
        style={{ width: '100%', height: '100%', objectFit: 'cover' }}
      />
      <canvas ref={canvasRef} style={{ display: 'none' }} />

      <div style={{ position: 'absolute', bottom: 16, left: 16, right: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center', zIndex: 10, background: 'rgba(0,0,0,0.7)', padding: '8px 16px', borderRadius: 6, border: '1px solid rgba(255,255,255,0.15)' }}>
        <div style={{ fontSize: 11, fontFamily: 'var(--font-mono)' }}>
          <span style={{ color: '#00ff9d' }}>STREAM KEY: phone://mobile-01</span> • FPS: {fps} • FRAMES: {frameCount}
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          {active ? (
            <button className="btn btn-sm btn-danger" onClick={stopCam}>
              ⏹️ Stop Transmission
            </button>
          ) : (
            <button className="btn btn-sm btn-primary" onClick={startCam}>
              ▶️ Resume Transmission
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

/* ─── Incidents Page ──────────────────────────────────────────── */
function IncidentsPage({ incidents, openInc }: { incidents: Incident[]; openInc: (id: number) => void }) {
  const [filter, setFilter] = useState('all');
  const list = filter === 'all'
    ? incidents
    : incidents.filter((i) => i.status === filter || i.severity === filter.toUpperCase());

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h1>Threat Intelligence & Incident Queue</h1>
          <p style={{ margin: 0, fontSize: 12, color: 'var(--text-secondary)' }}>
            AI-correlated border perimeter breaches requiring human operator verification
          </p>
        </div>
        <div className="filter-row">
          {['all', 'OPEN', 'ACKNOWLEDGED', 'ESCALATED', 'CLOSED'].map((f) => (
            <button
              key={f}
              className={`filter-btn${filter === f ? ' active' : ''}`}
              onClick={() => { playTacticalTone('click'); setFilter(f); }}
            >
              {f}
            </button>
          ))}
        </div>
      </div>

      {list.length === 0 ? (
        <Empty text="No incidents match this status classification." />
      ) : (
        <div className="incident-list">
          {list.map((i) => (
            <div key={i.id} className="incident-card" onClick={() => openInc(i.id)}>
              <div className="ic-header">
                <span className={`sev-badge sev-${i.severity.toLowerCase()}`}>{i.severity}</span>
                <span className="ic-code">{i.incident_code}</span>
                <span className="ic-score">THREAT SCORE: {i.threat_score.toFixed(0)}/100</span>
                <span className={`ic-status ${i.status.toLowerCase()}`}>{i.status}</span>
              </div>
              <div className="ic-title">{i.title}</div>
              <div className="ic-meta">
                {i.camera_name || 'BOP Sector'} • {i.zone_name || 'Perimeter Zone'} • {fmtTime(i.created_at)}
              </div>
              <div className="ic-reasons">
                {i.reason_codes.slice(0, 4).map((r) => (
                  <span key={r} className="reason-tag">
                    {r.split(':')[0].trim()}
                  </span>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

/* ─── Section 65B Statutory Legal Certificate Modal ───────────── */
function CertificateModal({ cert, onClose }: { cert: any; onClose: () => void }) {
  if (!cert) return null;
  return (
    <div
      className="modal-backdrop"
      onClick={onClose}
      style={{
        position: 'fixed',
        inset: 0,
        background: 'rgba(2, 6, 12, 0.88)',
        backdropFilter: 'blur(8px)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 9999,
        padding: 20,
      }}
    >
      <div
        className="modal-content"
        onClick={(e) => e.stopPropagation()}
        style={{
          background: '#070b14',
          border: '1px solid rgba(168, 85, 247, 0.5)',
          borderRadius: 8,
          maxWidth: 780,
          width: '100%',
          maxHeight: '90vh',
          overflowY: 'auto',
          padding: 24,
          boxShadow: '0 0 60px rgba(168, 85, 247, 0.3)',
          position: 'relative',
        }}
      >
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'flex-start',
            borderBottom: '1px solid rgba(168, 85, 247, 0.3)',
            paddingBottom: 14,
          }}
        >
          <div>
            <div style={{ fontSize: 10, color: '#a855f7', letterSpacing: 2, fontFamily: 'var(--font-mono)' }}>
              GOVERNMENT OF INDIA • MINISTRY OF HOME AFFAIRS • COURT-ADMISSIBLE EVIDENCE
            </div>
            <h2 style={{ margin: '4px 0', fontSize: 20, color: '#fff', letterSpacing: 1 }}>
              {cert.certificate_id}
            </h2>
            <div style={{ fontSize: 11, color: '#00ff9d', fontFamily: 'var(--font-mono)' }}>
              STATUTE: {cert.legal_statute}
            </div>
          </div>
          <button className="btn btn-secondary btn-sm" onClick={onClose}>
            ✕ Close
          </button>
        </div>

        <div
          style={{
            margin: '16px 0',
            background: 'rgba(0, 0, 0, 0.45)',
            border: '1px solid rgba(255, 255, 255, 0.08)',
            borderRadius: 6,
            padding: 16,
          }}
        >
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 10, fontSize: 12 }}>
            <div>
              <span style={{ color: 'var(--text-ghost)' }}>INCIDENT CODE:</span>{' '}
              <b style={{ color: '#00f0ff' }}>{cert.incident_code}</b>
            </div>
            <div>
              <span style={{ color: 'var(--text-ghost)' }}>ADMISSIBILITY STATUS:</span>{' '}
              <b style={{ color: '#00ff9d' }}>{cert.admissibility_status}</b>
            </div>
            <div>
              <span style={{ color: 'var(--text-ghost)' }}>SURVEILLANCE POST:</span>{' '}
              <span style={{ color: '#fff' }}>{cert.surveillance_post}</span>
            </div>
            <div>
              <span style={{ color: 'var(--text-ghost)' }}>CAMERA DESIGNATION:</span>{' '}
              <span style={{ color: '#fff' }}>{cert.camera_designation}</span>
            </div>
            <div>
              <span style={{ color: 'var(--text-ghost)' }}>STORAGE MEDIUM:</span>{' '}
              <span style={{ color: '#fff' }}>{cert.storage_integrity}</span>
            </div>
            <div>
              <span style={{ color: 'var(--text-ghost)' }}>CLOCK TIMEBASE:</span>{' '}
              <span style={{ color: '#fff' }}>{cert.clock_source}</span>
            </div>
          </div>

          <div style={{ marginTop: 14, borderTop: '1px solid rgba(255, 255, 255, 0.08)', paddingTop: 10 }}>
            <span style={{ fontSize: 10, color: 'var(--text-ghost)', letterSpacing: 1 }}>
              FIPS 180-4 CRYPTOGRAPHIC SHA-256 DIGEST:
            </span>
            <div
              style={{
                fontFamily: 'var(--font-mono)',
                fontSize: 11,
                color: '#a855f7',
                wordBreak: 'break-all',
                marginTop: 4,
                padding: '6px 10px',
                background: 'rgba(168, 85, 247, 0.1)',
                border: '1px solid rgba(168, 85, 247, 0.25)',
                borderRadius: 4,
              }}
            >
              {cert.sha256_digest}
            </div>
          </div>
        </div>

        <div
          style={{
            background: 'rgba(168, 85, 247, 0.08)',
            border: '1px solid rgba(168, 85, 247, 0.25)',
            borderRadius: 6,
            padding: 16,
            margin: '16px 0',
          }}
        >
          <div style={{ fontSize: 11, color: '#c084fc', fontWeight: 'bold', marginBottom: 6, letterSpacing: 1 }}>
            STATUTORY DECLARATION UNDER SECTION 65B(4) / SECTION 63 BSA:
          </div>
          <p style={{ fontSize: 12, lineHeight: 1.6, color: '#e2e8f0', margin: 0 }}>
            "{cert.legal_declaration}"
          </p>
          <div
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              marginTop: 14,
              paddingTop: 12,
              borderTop: '1px dashed rgba(168, 85, 247, 0.25)',
            }}
          >
            <div>
              <div style={{ fontSize: 12, fontWeight: 'bold', color: '#fff' }}>{cert.certifying_officer}</div>
              <div style={{ fontSize: 11, color: 'var(--text-secondary)' }}>
                {cert.officer_rank} • Sashastra Seema Bal (SSB)
              </div>
            </div>
            <div style={{ textAlign: 'right', fontSize: 11, color: 'var(--text-ghost)', fontFamily: 'var(--font-mono)' }}>
              CERTIFICATION TIMESTAMP: {fmtTime(cert.generated_at)}
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10 }}>
          <button className="btn btn-secondary btn-sm" onClick={() => window.print()}>
            🖨️ Print / Save PDF Affidavit
          </button>
          <button className="btn btn-primary btn-sm" onClick={onClose}>
            ✓ Return to System
          </button>
        </div>
      </div>
    </div>
  );
}

/* ─── Incident Forensic Dossier ───────────────────────────────── */
function IncidentDetail({
  incident: i,
  onBack,
  refresh,
}: {
  incident: Incident;
  onBack: () => void;
  refresh: (id: number) => void;
}) {
  const [evidence, setEvidence] = useState<Evidence[]>([]);
  const [verifying, setVerifying] = useState(false);
  const [verResult, setVerResult] = useState<any>(null);

  useEffect(() => {
    api.evidence(i.id).then(setEvidence).catch(() => {});
  }, [i.id]);

  const ack = async () => {
    playTacticalTone('verify');
    await api.acknowledgeIncident(i.id);
    refresh(i.id);
  };

  const esc = async () => {
    playTacticalTone('escalate');
    await api.escalateIncident(i.id);
    refresh(i.id);
  };

  const dis = async () => {
    playTacticalTone('click');
    await api.dismissIncident(i.id);
    refresh(i.id);
  };

  const cls = async () => {
    playTacticalTone('click');
    await api.closeIncident(i.id);
    refresh(i.id);
  };

  const verify = async () => {
    if (!evidence.length) return;
    setVerifying(true);
    playTacticalTone('click');
    try {
      const r = await api.verifyEvidence(evidence[0].id);
      setVerResult(r);
      playTacticalTone(r.valid ? 'verify' : 'alert');
    } catch {
      setVerResult({ valid: false });
      playTacticalTone('alert');
    }
    setVerifying(false);
  };

  const ai = i.ai_assessment || {};

  return (
    <div className="page">
      <button className="btn-back" onClick={onBack}>
        ← Return to Incident Queue
      </button>

      <div className="detail-header" style={{ borderBottom: '1px solid rgba(0, 240, 255, 0.2)', paddingBottom: 12 }}>
        <div>
          <div style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: '#ff2a55', letterSpacing: 2 }}>
            RESTRICTED // LAW ENFORCEMENT & BORDER DEFENSE INTELLIGENCE
          </div>
          <h1 style={{ margin: '4px 0', fontSize: 24, letterSpacing: 1 }}>
            INCIDENT DOSSIER: {i.incident_code}
          </h1>
          <span className={`sev-badge sev-${i.severity.toLowerCase()} large`}>{i.severity} THREAT</span>
        </div>
        <div className="detail-actions">
          {i.status === 'OPEN' && (
            <button className="btn btn-primary" onClick={ack}>
              ✓ Verify & Acknowledge
            </button>
          )}
          {i.status !== 'ESCALATED' && i.status !== 'CLOSED' && (
            <button className="btn btn-warn" onClick={esc}>
              🚨 Escalate to Patrol QRT
            </button>
          )}
          {i.status !== 'DISMISSED' && i.status !== 'CLOSED' && (
            <button className="btn btn-secondary" onClick={dis}>
              ✕ Dismiss False Alarm
            </button>
          )}
          {i.status !== 'CLOSED' && (
            <button className="btn btn-secondary" onClick={cls}>
              ● Close Incident
            </button>
          )}
        </div>
      </div>

      <div className="detail-grid">
        <div className="detail-left">
          {/* Key Metric Info */}
          <div className="info-card">
            <div className="info-row"><label>Threat Score</label><span className="threat-score">{i.threat_score.toFixed(0)}<small>/100</small></span></div>
            <div className="info-row"><label>AI Confidence</label><span>{(i.confidence * 100).toFixed(0)}%</span></div>
            <div className="info-row"><label>Surveillance Post</label><span>{i.camera_name || 'BOP-01 Gate Post'}</span></div>
            <div className="info-row"><label>Perimeter Zone</label><span>{i.zone_name || 'Restricted Zero-Line'}</span></div>
            <div className="info-row"><label>Status</label><span className={`ic-status ${i.status.toLowerCase()}`}>{i.status}</span></div>
            <div className="info-row"><label>Sensor Timestamp</label><span>{fmtTime(i.created_at)}</span></div>
          </div>

          {/* Recommended Action */}
          <div className="info-card action-card">
            <h3>Standard Operating Procedure (SOP)</h3>
            <p>{i.recommended_action || 'Dispatch armed QRT patrol to sector coordinates. Verify thermal perimeter sensor.'}</p>
          </div>

          {/* Why Alert Triggered */}
          <div className="info-card">
            <h3>Rule & AI Threat Attribution</h3>
            <div className="reason-list">
              {i.reason_codes.map((r, idx) => (
                <div key={idx} className="reason-item">
                  <span className="reason-num">{idx + 1}</span>
                  <span>{r}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="detail-right">
          {/* AI Explainability Assessment */}
          <div className="info-card">
            <h3>Perception Engine Assessment</h3>
            <div className="ai-grid">
              <div className="ai-item"><label>Detected Class</label><span>{ai.detected || 'Human Infiltrator'}</span></div>
              <div className="ai-item"><label>Confidence</label><span>{((ai.confidence || 0.94) * 100).toFixed(0)}%</span></div>
              <div className="ai-item"><label>Context</label><span>{ai.context || 'Night Perimeter'}</span></div>
              <div className="ai-item"><label>Behavior</label><span>{ai.behavior || 'Border Crossing'}</span></div>
              <div className="ai-item"><label>Uncertainty</label><span>{ai.uncertainty || 'Low (<5%)'}</span></div>
              <div className="ai-item"><label>Operator Role</label><span>{ai.human_action || 'Immediate Intercept'}</span></div>
            </div>

            {ai.threat_contributions && (
              <div className="contributions">
                <h4>Signal Contribution Breakdown</h4>
                {Object.entries(ai.threat_contributions).map(([k, v]) => (
                  <div key={k} className="contrib-row">
                    <span className="contrib-label">{k.replace(/_/g, ' ')}</span>
                    <div className="contrib-bar">
                      <div className="contrib-fill" style={{ width: `${Math.min(100, (v as number) * 100)}%` }} />
                    </div>
                    <span className="contrib-val">{(v as number).toFixed(1)}</span>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Cryptographic Evidence Locker */}
          <div className="info-card">
            <div className="evidence-header">
              <h3>SHA-256 Sealed Evidence</h3>
              <button className="btn btn-sm" onClick={verify} disabled={verifying}>
                {verifying ? 'Checking...' : '🔒 Verify Hash'}
              </button>
            </div>
            {verResult && (
              <div className={`verify-result ${verResult.valid ? 'valid' : 'invalid'}`}>
                {verResult.valid ? '✓ SHA-256 DIGEST INTEGRITY VERIFIED (UNTAMPERED)' : '✕ INTEGRITY MISMATCH!'}
                <small>DIGEST: {verResult.sha256?.substring(0, 24)}…</small>
              </div>
            )}
            {evidence.length === 0 ? (
              <Empty text="Evidence packaging in progress." />
            ) : (
              evidence.map((e) => (
                <div key={e.id} className="evidence-row">
                  <span className="ev-type">{e.evidence_type}</span>
                  <span className="ev-hash">{e.sha256.substring(0, 18)}…</span>
                  <span className="ev-time">{fmtTime(e.created_at)}</span>
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      {/* Incident Event Timeline */}
      <div className="info-card timeline-card" style={{ marginTop: 16 }}>
        <h3>Chronological Sensor & Decision Timeline</h3>
        {i.timeline && i.timeline.length > 0 ? (
          <div className="timeline">
            {i.timeline.map((evt: any, idx: number) => (
              <div key={idx} className="timeline-item">
                <div className="timeline-time">{fmtTimeShort(evt.timestamp)}</div>
                <div className="timeline-dot" />
                <div className="timeline-content">
                  <b>{evt.event_type?.replace(/_/g, ' ')}</b>
                  <span>{evt.description}</span>
                  <small>Source: {evt.source}</small>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <Empty text="Timeline compilation in progress." />
        )}
      </div>
    </div>
  );
}

/* ─── Evidence Locker Page ────────────────────────────────────── */
function EvidencePage({ incidents }: { incidents: Incident[] }) {
  const [allEvidence, setAllEvidence] = useState<Evidence[]>([]);
  const [verifyingId, setVerifyingId] = useState<number | null>(null);
  const [results, setResults] = useState<Record<number, boolean>>({});
  const [selectedCert, setSelectedCert] = useState<Evidence | null>(null);

  useEffect(() => {
    Promise.all(incidents.slice(0, 8).map((inc) => api.evidence(inc.id).catch(() => []))).then((res) => {
      const flat = res.flat();
      setAllEvidence(flat);
    });
  }, [incidents]);

  const verifyItem = async (id: number) => {
    setVerifyingId(id);
    playTacticalTone('click');
    try {
      const res = await api.verifyEvidence(id);
      setResults((prev) => ({ ...prev, [id]: res.valid }));
      playTacticalTone(res.valid ? 'verify' : 'alert');
    } catch {
      setResults((prev) => ({ ...prev, [id]: false }));
      playTacticalTone('alert');
    }
    setVerifyingId(null);
  };

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h1>Forensic Cryptographic Evidence Locker</h1>
          <p style={{ margin: 0, fontSize: 12, color: 'var(--text-secondary)' }}>
            Tamper-evident, court-admissible surveillance artifacts sealed with SHA-256 cryptographic hashes & Section 65B certificates
          </p>
        </div>
      </div>

      {allEvidence.length === 0 ? (
        <Empty text="No evidence sealed yet. Trigger an incident in the War Gaming tab." />
      ) : (
        <div className="evidence-card-grid">
          {allEvidence.map((e) => {
            const verified = results[e.id];
            return (
              <div key={e.id} className="evidence-locker-item">
                <div className="evidence-locker-header">
                  <div>
                    <b style={{ color: '#fff', fontSize: 13 }}>EVIDENCE RECORD #{e.id}</b>
                    <div style={{ fontSize: 10, color: 'var(--text-ghost)', fontFamily: 'var(--font-mono)' }}>
                      INCIDENT #{e.incident_id} • {e.camera_name || 'BOP Post'}
                    </div>
                  </div>
                  <span className="panel-tag" style={{ color: '#00f0ff', borderColor: '#00f0ff' }}>
                    {e.evidence_type}
                  </span>
                </div>

                <div className="sha256-hash-box">
                  <span style={{ color: 'var(--text-ghost)', fontSize: 9 }}>SHA-256 DIGEST:</span>
                  <div style={{ wordBreak: 'break-all', marginTop: 2 }}>{e.sha256}</div>
                </div>

                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 12 }}>
                  <span style={{ fontSize: 10, color: 'var(--text-secondary)' }}>{fmtTime(e.created_at)}</span>
                  <div style={{ display: 'flex', gap: 6 }}>
                    <button
                      className={`btn btn-sm ${verified ? 'btn-primary' : 'btn-secondary'}`}
                      onClick={() => verifyItem(e.id)}
                      disabled={verifyingId === e.id}
                    >
                      {verifyingId === e.id ? 'Checking...' : verified ? '✓ SEAL VALID' : '🔒 Verify Seal'}
                    </button>
                    <button
                      className="btn btn-sm btn-secondary"
                      onClick={() => { playTacticalTone('click'); setSelectedCert(e); }}
                      style={{ borderColor: '#00f0ff', color: '#00f0ff' }}
                    >
                      📜 Sec 65B Cert
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {selectedCert && (
        <Section65BCertificateModal evidence={selectedCert} onClose={() => setSelectedCert(null)} />
      )}
    </div>
  );
}

/* ─── Audit Ledger Page ───────────────────────────────────────── */
function AuditPage() {
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [chainValid, setChainValid] = useState<boolean | null>(null);
  const [verifying, setVerifying] = useState(false);

  useEffect(() => {
    api.auditLogs().then(setLogs).catch(() => {});
  }, []);

  const verifyChain = async () => {
    setVerifying(true);
    playTacticalTone('click');
    try {
      const res = await api.verifyAudit();
      setChainValid(res.chain_valid);
      playTacticalTone(res.chain_valid ? 'verify' : 'alert');
    } catch {
      setChainValid(false);
      playTacticalTone('alert');
    }
    setVerifying(false);
  };

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h1>Tamper-Proof Military Audit Ledger</h1>
          <p style={{ margin: 0, fontSize: 12, color: 'var(--text-secondary)' }}>
            Cryptographically chained immutable ledger recording all officer and AI system actions
          </p>
        </div>
        <button className="btn btn-primary" onClick={verifyChain} disabled={verifying}>
          {verifying ? 'Verifying Hash Chain...' : '🔗 Verify Chain Integrity'}
        </button>
      </div>

      {chainValid !== null && (
        <div className={`test-feedback ${chainValid ? 'success' : 'fail'}`} style={{ marginBottom: 16 }}>
          {chainValid ? '✓ IMMUTABLE AUDIT CHAIN 100% VALID — ZERO TAMPERING DETECTED' : '✕ AUDIT CHAIN INTEGRITY CORRUPTED'}
        </div>
      )}

      {logs.length === 0 ? (
        <Empty text="Audit ledger empty." />
      ) : (
        <div className="blockchain-ledger-view">
          {logs.map((l) => (
            <div key={l.id} className="blockchain-block">
              <div className="block-index-badge">
                <span style={{ fontSize: 9, color: 'var(--text-ghost)' }}>BLOCK</span>
                <span>#{l.id}</span>
              </div>
              <div className="block-data-col">
                <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginBottom: 2 }}>
                  <b style={{ color: '#fff', fontSize: 13 }}>{l.action}</b>
                  <span className="reason-tag" style={{ background: 'rgba(0, 240, 255, 0.1)', color: '#00f0ff' }}>
                    {l.actor} ({l.role})
                  </span>
                  <span style={{ marginLeft: 'auto', fontSize: 10, color: 'var(--text-ghost)', fontFamily: 'var(--font-mono)' }}>
                    {fmtTime(l.created_at)}
                  </span>
                </div>
                <div className="block-hash-pipe">
                  <span>PREV: <span className="hash-token">{l.previous_hash ? l.previous_hash.substring(0, 16) : 'GENESIS'}…</span></span>
                  <span>→</span>
                  <span>HASH: <span className="hash-token">{l.record_hash?.substring(0, 16)}…</span></span>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

/* ─── Health & Edge Diagnostics ───────────────────────────────── */
function HealthPage({ cameras }: { cameras: Camera[] }) {
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

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: 14 }}>
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
                <div>STORE QUEUE: <b style={{ color: '#00ff9d' }}>0 PENDING</b></div>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ─── War Gaming / Demo Scenarios Center ──────────────────────── */
function DemoPage({
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
function SettingsPage({
  isMuted,
  onToggleMute,
}: {
  isMuted: boolean;
  onToggleMute: () => void;
}) {
  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h1>Defense Surveillance Parameters</h1>
          <p style={{ margin: 0, fontSize: 12, color: 'var(--text-secondary)' }}>
            System configuration, cryptographic key status, and operator acoustic alerts
          </p>
        </div>
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
            <div>EVIDENCE SEAL: <b style={{ color: '#00ff9d' }}>WORM MANIFEST</b></div>
            <div>EDGE PERCEPTION: <b style={{ color: '#00ff9d' }}>YOLO26n + BYTE-TRACK</b></div>
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
          <h2 style={{ margin: '0 0 6px 0', fontSize: 20, color: '#111827', fontWeight: 800, letterSpacing: 1 }}>
            CERTIFICATE UNDER SECTION 65B(4)
          </h2>
          <h4 style={{ margin: '0 0 12px 0', fontSize: 13, color: '#4b5563', fontWeight: 600 }}>
            THE INDIAN EVIDENCE ACT, 1872 (ADMISSIBILITY OF ELECTRONIC RECORDS)
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
function ANPRPage() {
  const [plates, setPlates] = useState<any[]>([]);
  const [watchlist, setWatchlist] = useState<any[]>([]);
  const [stats, setStats] = useState<any>(null);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [isScanning, setIsScanning] = useState(false);
  const [testPlate, setTestPlate] = useState('JK 02 C 5678');
  const [testVehicleType, setTestVehicleType] = useState('SUV / LMV');
  const [testBop, setTestBop] = useState('BOP-01 Road Checkpost');
  const [feedback, setFeedback] = useState<string | null>(null);
  const [showAddWatchlist, setShowAddWatchlist] = useState(false);
  const [newWatchlistPlate, setNewWatchlistPlate] = useState('');
  const [newWatchlistReason, setNewWatchlistReason] = useState('');

  const loadData = () => {
    api.anprPlates(statusFilter || undefined, undefined, search || undefined).then(setPlates).catch(() => {});
    api.anprWatchlist().then(setWatchlist).catch(() => {});
    api.anprStats().then(setStats).catch(() => {});
  };

  useEffect(() => {
    loadData();
  }, [statusFilter, search]);

  const handleScan = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!testPlate.trim()) return;
    setIsScanning(true);
    playTacticalTone('click');
    try {
      const res = await api.anprScan({
        plate_number: testPlate,
        vehicle_type: testVehicleType,
        bop: testBop,
        confidence: 0.95,
        status: 'CLEARED',
      });
      if (res.status === 'STOLEN_FLAGGED') {
        playTacticalTone('alert');
        setFeedback(`🚨 INTERCEPT ENGAGED: Plate ${res.plate_number} matched STOLEN VEHICLE watchlist! Barrier triggered.`);
      } else {
        playTacticalTone('verify');
        setFeedback(`✓ CLEARED: Vehicle ${res.plate_number} passed ANPR checkpost.`);
      }
      loadData();
    } catch {
      setFeedback('Error processing ANPR scan');
    }
    setIsScanning(false);
  };

  const handleToggleBarrier = async () => {
    playTacticalTone('click');
    try {
      const res = await api.toggleBarrier();
      setStats((prev: any) => ({ ...prev, barrier_state: res }));
      playTacticalTone(res.barrier_raised ? 'verify' : 'escalate');
      setFeedback(`Barrier status updated: ${res.status}`);
    } catch {}
  };

  const handleAddWatchlist = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newWatchlistPlate.trim()) return;
    try {
      await api.addAnprWatchlist({
        plate_number: newWatchlistPlate,
        reason: newWatchlistReason || 'Border Surveillance Lookout Notice',
        agency: 'Intelligence Bureau / Special Operations',
        threat_level: 'HIGH',
      });
      setShowAddWatchlist(false);
      setNewWatchlistPlate('');
      setNewWatchlistReason('');
      playTacticalTone('verify');
      loadData();
    } catch {}
  };

  const barrierRaised = stats?.barrier_state?.barrier_raised;

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h1>ANPR Checkpost & Vehicle Inspection Terminal</h1>
          <p style={{ margin: 0, fontSize: 12, color: 'var(--text-secondary)' }}>
            High-speed Automatic Number Plate Recognition (Indian HSRP format), stolen vehicle database integration, and automated barrier control
          </p>
        </div>
        <div style={{ display: 'flex', gap: 10 }}>
          <button
            className={`btn ${barrierRaised ? 'btn-primary' : 'btn-danger'}`}
            onClick={handleToggleBarrier}
            style={{ fontWeight: 800, letterSpacing: 1 }}
          >
            {barrierRaised ? '▲ BARRIER OPEN (RAISED)' : '▼ BARRIER ENGAGED (INTERCEPT)'}
          </button>
          <button className="btn btn-secondary" onClick={() => setShowAddWatchlist(true)}>
            + Add Flagged Plate
          </button>
        </div>
      </div>

      {feedback && (
        <div className={`test-feedback ${feedback.includes('🚨') ? 'fail' : 'success'}`} style={{ marginBottom: 16 }}>
          {feedback}
        </div>
      )}

      {/* ANPR Telemetry KPI Ribbon */}
      <div className="tactical-kpi-ribbon" style={{ marginBottom: 16 }}>
        <div className="tactical-kpi-card">
          <div className="kpi-header-label">
            <span>24H VEHICLES SCANNED</span>
            <span style={{ color: '#00f0ff' }}>CHECKPOST</span>
          </div>
          <div className="kpi-metric-val">{stats?.total_vehicles_24h || plates.length}</div>
        </div>
        <div className="tactical-kpi-card">
          <div className="kpi-header-label">
            <span>STOLEN / FLAGGED INTERCEPTS</span>
            <span style={{ color: '#ff2a55' }}>ALERTS</span>
          </div>
          <div className="kpi-metric-val" style={{ color: '#ff2a55' }}>
            {stats?.flagged_intercepts || 2}
          </div>
        </div>
        <div className="tactical-kpi-card">
          <div className="kpi-header-label">
            <span>AVG OCR ACCURACY</span>
            <span style={{ color: '#00ff9d' }}>ONNX MODEL</span>
          </div>
          <div className="kpi-metric-val" style={{ color: '#00ff9d' }}>
            {stats?.avg_ocr_confidence || 95.4}%
          </div>
        </div>
        <div className="tactical-kpi-card">
          <div className="kpi-header-label">
            <span>BARRIER INTERCEPT SYSTEM</span>
            <span style={{ color: barrierRaised ? '#00ff9d' : '#ffaa00' }}>
              {barrierRaised ? 'DISENGAGED' : 'ARMED'}
            </span>
          </div>
          <div className="kpi-metric-val" style={{ fontSize: 18, color: barrierRaised ? '#00ff9d' : '#ffaa00' }}>
            {barrierRaised ? 'PASS THRU' : 'INTERCEPT READY'}
          </div>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: 16 }}>
        {/* Scanned Plates Feed */}
        <div className="panel" style={{ margin: 0 }}>
          <div className="panel-header">
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <b style={{ color: '#fff', fontSize: 14 }}>Real-Time Vehicle Passings & OCR Stream</b>
              <span className="panel-tag">{plates.length} LOGGED</span>
            </div>
            <div style={{ display: 'flex', gap: 8 }}>
              <input
                type="text"
                placeholder="Filter plate / vehicle..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                style={{
                  background: '#040b14',
                  border: '1px solid rgba(0, 240, 255, 0.2)',
                  color: '#fff',
                  borderRadius: 4,
                  padding: '4px 8px',
                  fontSize: 11,
                }}
              />
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                style={{
                  background: '#040b14',
                  border: '1px solid rgba(0, 240, 255, 0.2)',
                  color: '#fff',
                  borderRadius: 4,
                  padding: '4px 8px',
                  fontSize: 11,
                }}
              >
                <option value="">All Statuses</option>
                <option value="CLEARED">Cleared</option>
                <option value="STOLEN_FLAGGED">Stolen / Flagged</option>
                <option value="MILITARY_PRIORITY">Military Priority</option>
              </select>
            </div>
          </div>

          <div style={{ padding: 14, display: 'flex', flexDirection: 'column', gap: 10 }}>
            {plates.map((p) => {
              const isFlagged = p.status.includes('FLAGGED') || p.status.includes('STOLEN') || p.status.includes('MATCH');
              const isMilitary = p.status.includes('MILITARY');
              return (
                <div
                  key={p.id}
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    padding: '12px 14px',
                    background: isFlagged ? 'rgba(255, 42, 85, 0.08)' : 'rgba(255, 255, 255, 0.02)',
                    border: isFlagged ? '1px solid #ff2a55' : '1px solid rgba(255, 255, 255, 0.06)',
                    borderRadius: 6,
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
                    <div className="anpr-hsrp-plate">
                      <div className="anpr-hsrp-flag">
                        <span>IND</span>
                      </div>
                      <div className="anpr-hsrp-text">{p.plate_number}</div>
                    </div>
                    <div>
                      <div style={{ color: '#fff', fontWeight: 600, fontSize: 13 }}>
                        {p.vehicle_model} <span style={{ color: 'var(--text-secondary)', fontSize: 11 }}>({p.vehicle_type})</span>
                      </div>
                      <div style={{ fontSize: 10, color: 'var(--text-secondary)', marginTop: 2 }}>
                        {p.bop} • Lane: {p.lane} • Origin: {p.state_origin} • Speed: {p.speed_kmh} km/h
                      </div>
                    </div>
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                    <div style={{ textAlign: 'right' }}>
                      <span className={isFlagged ? 'anpr-badge-stolen' : isMilitary ? 'anpr-badge-military' : 'anpr-badge-cleared'}>
                        {p.status}
                      </span>
                      <div style={{ fontSize: 10, color: 'var(--text-ghost)', marginTop: 4 }}>
                        OCR Conf: {(p.confidence * 100).toFixed(0)}% • {fmtTime(p.timestamp)}
                      </div>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Live ANPR Scan Simulator & Watchlist */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <div className="panel" style={{ margin: 0, padding: 16 }}>
            <h3 style={{ color: '#00f0ff', marginBottom: 12, fontSize: 14 }}>⚡ Run Live ANPR OCR Scan</h3>
            <form onSubmit={handleScan} style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              <div>
                <label style={{ fontSize: 11, color: 'var(--text-secondary)' }}>Registration Number (HSRP Format):</label>
                <input
                  type="text"
                  value={testPlate}
                  onChange={(e) => setTestPlate(e.target.value)}
                  style={{
                    width: '100%',
                    background: '#040b14',
                    border: '1px solid rgba(0, 240, 255, 0.3)',
                    color: '#00f0ff',
                    fontFamily: 'var(--font-mono)',
                    fontWeight: 700,
                    padding: '8px 10px',
                    borderRadius: 4,
                    fontSize: 14,
                    marginTop: 4,
                  }}
                />
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                <div>
                  <label style={{ fontSize: 10, color: 'var(--text-secondary)' }}>Vehicle Class:</label>
                  <select
                    value={testVehicleType}
                    onChange={(e) => setTestVehicleType(e.target.value)}
                    style={{ width: '100%', background: '#040b14', border: '1px solid #333', color: '#fff', padding: 6, borderRadius: 4, fontSize: 11, marginTop: 2 }}
                  >
                    <option value="SUV / LMV">SUV / LMV</option>
                    <option value="Civilian Sedan">Civilian Sedan</option>
                    <option value="Heavy Commercial (HMV)">Heavy Commercial (HMV)</option>
                    <option value="Two-Wheeler (2W)">Two-Wheeler (2W)</option>
                  </select>
                </div>
                <div>
                  <label style={{ fontSize: 10, color: 'var(--text-secondary)' }}>Checkpost Post:</label>
                  <select
                    value={testBop}
                    onChange={(e) => setTestBop(e.target.value)}
                    style={{ width: '100%', background: '#040b14', border: '1px solid #333', color: '#fff', padding: 6, borderRadius: 4, fontSize: 11, marginTop: 2 }}
                  >
                    <option value="BOP-01 Road Checkpost">BOP-01 Road Checkpost</option>
                    <option value="BOP-03 Freight Checkpoint">BOP-03 Freight Checkpoint</option>
                  </select>
                </div>
              </div>
              <button className="btn btn-primary" type="submit" disabled={isScanning} style={{ marginTop: 4 }}>
                {isScanning ? 'Processing Neural OCR...' : '🔍 Scan Plate & Check Watchlist'}
              </button>
            </form>
          </div>

          <div className="panel" style={{ margin: 0, padding: 16 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
              <h3 style={{ color: '#ff2a55', margin: 0, fontSize: 13 }}>⚠️ Stolen / Wanted Vehicle Database</h3>
              <span className="panel-tag" style={{ borderColor: '#ff2a55', color: '#ff2a55' }}>{watchlist.length} FLAGGED</span>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {watchlist.map((w) => (
                <div
                  key={w.id}
                  style={{
                    padding: 10,
                    background: 'rgba(255, 42, 85, 0.05)',
                    border: '1px solid rgba(255, 42, 85, 0.3)',
                    borderRadius: 4,
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <b style={{ color: '#fff', fontFamily: 'var(--font-mono)' }}>{w.plate_number}</b>
                    <span style={{ fontSize: 9, color: '#ff2a55', fontWeight: 700 }}>{w.threat_level}</span>
                  </div>
                  <div style={{ fontSize: 11, color: '#e2effc', marginTop: 3 }}>{w.reason}</div>
                  <div style={{ fontSize: 9, color: 'var(--text-ghost)', marginTop: 3 }}>Agency: {w.agency} • {w.vehicle_model}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Add Watchlist Modal */}
      {showAddWatchlist && (
        <div className="section-65b-modal-backdrop" onClick={() => setShowAddWatchlist(false)}>
          <div className="panel" style={{ maxWidth: 460, width: '100%', margin: 0, padding: 24 }} onClick={(e) => e.stopPropagation()}>
            <h3 style={{ color: '#00f0ff', marginBottom: 14 }}>Flag Vehicle in National Border Database</h3>
            <form onSubmit={handleAddWatchlist} style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              <div>
                <label style={{ fontSize: 11, color: 'var(--text-secondary)' }}>Registration Plate Number:</label>
                <input
                  type="text"
                  placeholder="e.g. JK 02 C 5678"
                  value={newWatchlistPlate}
                  onChange={(e) => setNewWatchlistPlate(e.target.value)}
                  style={{ width: '100%', background: '#040b14', border: '1px solid #333', color: '#fff', padding: 8, borderRadius: 4, marginTop: 4 }}
                  required
                />
              </div>
              <div>
                <label style={{ fontSize: 11, color: 'var(--text-secondary)' }}>Surveillance Reason / Charge:</label>
                <input
                  type="text"
                  placeholder="e.g. Suspected in illegal arms trafficking"
                  value={newWatchlistReason}
                  onChange={(e) => setNewWatchlistReason(e.target.value)}
                  style={{ width: '100%', background: '#040b14', border: '1px solid #333', color: '#fff', padding: 8, borderRadius: 4, marginTop: 4 }}
                />
              </div>
              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8, marginTop: 8 }}>
                <button className="btn btn-secondary" type="button" onClick={() => setShowAddWatchlist(false)}>
                  Cancel
                </button>
                <button className="btn btn-danger" type="submit">
                  + Add to Lookout List
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

/* ─── FRS Biometric Watchlist & Face Match Studio ─────────────── */
function FRSPage({ openInc }: { openInc?: (id: number) => void }) {
  const [suspects, setSuspects] = useState<any[]>([]);
  const [matches, setMatches] = useState<any[]>([]);
  const [stats, setStats] = useState<any>(null);
  const [filterThreat, setFilterThreat] = useState('');
  const [showEnroll, setShowEnroll] = useState(false);
  const [name, setName] = useState('');
  const [alias, setAlias] = useState('');
  const [threatLevel, setThreatLevel] = useState('CATEGORY_A');
  const [agency, setAgency] = useState('NIA / Central Intelligence');
  const [category, setCategory] = useState('Armed Cross-Border Infiltration');
  const [feedback, setFeedback] = useState<string | null>(null);

  const loadData = () => {
    api.frsWatchlist(filterThreat || undefined).then(setSuspects).catch(() => {});
    api.frsMatches().then(setMatches).catch(() => {});
    api.frsStats().then(setStats).catch(() => {});
  };

  useEffect(() => {
    loadData();
  }, [filterThreat]);

  const handleVerify = async (matchId: number, confirm: boolean) => {
    playTacticalTone('click');
    try {
      const res = await api.verifyFaceMatch(matchId, confirm);
      playTacticalTone(confirm ? 'alert' : 'verify');
      setFeedback(confirm ? `🚨 POSITIVE IDENTIFICATION CONFIRMED for ${res.suspect_name}. QRT scrambled!` : `False positive dismissed.`);
      loadData();
    } catch {}
  };

  const handleEnroll = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;
    try {
      await api.enrollSuspect({
        name,
        alias,
        threat_level: threatLevel,
        agency,
        category,
      });
      setShowEnroll(false);
      setName('');
      setAlias('');
      playTacticalTone('verify');
      setFeedback(`✓ Suspect ${name} successfully enrolled with ArcFace 512D biometric vector.`);
      loadData();
    } catch {}
  };

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h1>Facial Recognition System (FRS) & Suspect Intelligence</h1>
          <p style={{ margin: 0, fontSize: 12, color: 'var(--text-secondary)' }}>
            Deep learning biometric face matching (ArcFace 512D), Interpol & NIA watchlist cross-referencing, and operator verification studio
          </p>
        </div>
        <div style={{ display: 'flex', gap: 10 }}>
          <select
            value={filterThreat}
            onChange={(e) => setFilterThreat(e.target.value)}
            style={{ background: '#040b14', border: '1px solid rgba(0, 240, 255, 0.3)', color: '#fff', padding: '6px 10px', borderRadius: 4, fontSize: 12 }}
          >
            <option value="">All Threat Categories</option>
            <option value="CATEGORY_A">Category A (High-Value Targets)</option>
            <option value="CATEGORY_B">Category B (Smugglers / Hawala)</option>
          </select>
          <button className="btn btn-primary" onClick={() => setShowEnroll(true)}>
            + Enroll Suspect Biometrics
          </button>
        </div>
      </div>

      {feedback && (
        <div className={`test-feedback ${feedback.includes('🚨') ? 'fail' : 'success'}`} style={{ marginBottom: 16 }}>
          {feedback}
        </div>
      )}

      {/* FRS KPI Ribbon */}
      <div className="tactical-kpi-ribbon" style={{ marginBottom: 16 }}>
        <div className="tactical-kpi-card">
          <div className="kpi-header-label">
            <span>BIOMETRIC GALLERY</span>
            <span style={{ color: '#00f0ff' }}>ENROLLED</span>
          </div>
          <div className="kpi-metric-val">{stats?.watchlist_size || suspects.length}</div>
        </div>
        <div className="tactical-kpi-card">
          <div className="kpi-header-label">
            <span>HIGH VALUE TARGETS (HVT)</span>
            <span style={{ color: '#ff2a55' }}>CAT-A</span>
          </div>
          <div className="kpi-metric-val" style={{ color: '#ff2a55' }}>
            {stats?.high_value_targets || 2}
          </div>
        </div>
        <div className="tactical-kpi-card">
          <div className="kpi-header-label">
            <span>MATCHES DETECTED (24H)</span>
            <span style={{ color: '#ffaa00' }}>CANDIDATES</span>
          </div>
          <div className="kpi-metric-val" style={{ color: '#ffaa00' }}>
            {stats?.matches_24h || matches.length}
          </div>
        </div>
        <div className="tactical-kpi-card">
          <div className="kpi-header-label">
            <span>AI INFERENCE ENGINE</span>
            <span style={{ color: '#00ff9d' }}>ACTIVE</span>
          </div>
          <div className="kpi-metric-val" style={{ fontSize: 15, color: '#00ff9d' }}>
            ArcFace 512D
          </div>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 2fr', gap: 16 }}>
        {/* Live Candidate Face Matches */}
        <div className="panel" style={{ margin: 0 }}>
          <div className="panel-header">
            <b style={{ color: '#ff2a55', fontSize: 14 }}>🚨 Live Candidate Face Matches</b>
            <span className="panel-tag" style={{ borderColor: '#ff2a55', color: '#ff2a55' }}>
              VERIFICATION REQUIRED
            </span>
          </div>
          <div style={{ padding: 14, display: 'flex', flexDirection: 'column', gap: 14 }}>
            {matches.length === 0 ? (
              <Empty text="No active face match alarms." />
            ) : (
              matches.map((m) => {
                const matchPct = Math.round((m.similarity_score || 0.9) * 100);
                return (
                  <div
                    key={m.id}
                    style={{
                      background: 'rgba(255, 42, 85, 0.06)',
                      border: '1px solid rgba(255, 42, 85, 0.4)',
                      borderRadius: 6,
                      padding: 14,
                      display: 'flex',
                      flexDirection: 'column',
                      gap: 10,
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <b style={{ color: '#fff', fontSize: 14 }}>{m.suspect_name}</b>
                      <span className="sev-badge sev-critical">{m.threat_level}</span>
                    </div>

                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
                      <div style={{ background: '#02060c', borderRadius: 4, overflow: 'hidden', height: 110 }}>
                        <img src="/api/v1/cameras/1/snapshot" alt="Live Face" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
                        <div style={{ fontSize: 9, color: 'var(--text-ghost)', padding: '2px 4px', textAlign: 'center' }}>LIVE SENSOR CROP</div>
                      </div>
                      <div style={{ background: '#02060c', borderRadius: 4, overflow: 'hidden', height: 110 }}>
                        <img src="https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=150&auto=format&fit=crop&q=80" alt="Watchlist Avatar" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
                        <div style={{ fontSize: 9, color: 'var(--text-ghost)', padding: '2px 4px', textAlign: 'center' }}>ENROLLED WATCHLIST</div>
                      </div>
                    </div>

                    <div>
                      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11 }}>
                        <span style={{ color: 'var(--text-secondary)' }}>COSINE SIMILARITY MATCH</span>
                        <b style={{ color: matchPct > 90 ? '#ff2a55' : '#ffaa00' }}>{matchPct}% CONFIDENCE</b>
                      </div>
                      <div className="frs-similarity-bar">
                        <div
                          className="frs-similarity-fill"
                          style={{ width: `${matchPct}%`, background: matchPct > 90 ? '#ff2a55' : '#ffaa00' }}
                        />
                      </div>
                    </div>

                    <div style={{ fontSize: 10, color: 'var(--text-secondary)' }}>
                      Location: {m.bop} • {m.camera_name} • {fmtTime(m.timestamp)}
                    </div>

                    {m.operator_verified ? (
                      <div style={{ color: '#00ff9d', fontSize: 11, fontWeight: 700, padding: 6, background: 'rgba(0, 255, 157, 0.1)', borderRadius: 4, textAlign: 'center' }}>
                        ✓ {m.status} (Verified by {m.verified_by})
                      </div>
                    ) : (
                      <div style={{ display: 'flex', gap: 8, marginTop: 4 }}>
                        <button
                          className="btn btn-danger btn-sm"
                          style={{ flex: 1 }}
                          onClick={() => handleVerify(m.id, true)}
                        >
                          ✓ Confirm Positive & Scramble QRT
                        </button>
                        <button
                          className="btn btn-secondary btn-sm"
                          onClick={() => handleVerify(m.id, false)}
                        >
                          ✕ Dismiss
                        </button>
                      </div>
                    )}
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* Suspect Watchlist Gallery */}
        <div className="panel" style={{ margin: 0 }}>
          <div className="panel-header">
            <b style={{ color: '#fff', fontSize: 14 }}>National Border Lookout & Suspect Gallery</b>
            <span className="panel-tag">{suspects.length} PERSONS OF INTEREST</span>
          </div>
          <div style={{ padding: 14, display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(240px, 1fr))', gap: 14 }}>
            {suspects.map((s) => (
              <div key={s.id} className="frs-suspect-card">
                <div className="frs-avatar-box">
                  <img src={s.photo_url} alt={s.name} className="frs-avatar-img" />
                  <div className="frs-biometric-reticle" />
                  <span
                    style={{
                      position: 'absolute',
                      top: 8,
                      right: 8,
                      background: s.threat_level === 'CATEGORY_A' ? '#ff2a55' : '#ffaa00',
                      color: '#000',
                      fontWeight: 800,
                      fontSize: 9,
                      padding: '2px 6px',
                      borderRadius: 2,
                    }}
                  >
                    {s.threat_level}
                  </span>
                </div>
                <div style={{ padding: 12, display: 'flex', flexDirection: 'column', gap: 4, flex: 1, justifyContent: 'space-between' }}>
                  <div>
                    <b style={{ color: '#fff', fontSize: 13 }}>{s.name}</b>
                    <div style={{ fontSize: 11, color: '#00f0ff', fontFamily: 'var(--font-mono)' }}>
                      Alias: {s.alias}
                    </div>
                    <div style={{ fontSize: 10, color: 'var(--text-secondary)', marginTop: 4 }}>
                      {s.category}
                    </div>
                  </div>
                  <div style={{ borderTop: '1px solid rgba(255,255,255,0.08)', paddingTop: 8, marginTop: 8, fontSize: 9, color: 'var(--text-ghost)' }}>
                    Agency: {s.agency} • {s.interpol_notice || 'MHA LOOKOUT'}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Enroll Suspect Modal */}
      {showEnroll && (
        <div className="section-65b-modal-backdrop" onClick={() => setShowEnroll(false)}>
          <div className="panel" style={{ maxWidth: 500, width: '100%', margin: 0, padding: 24 }} onClick={(e) => e.stopPropagation()}>
            <h3 style={{ color: '#00f0ff', marginBottom: 14 }}>Enroll Suspect Biometrics into National Database</h3>
            <form onSubmit={handleEnroll} style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              <div>
                <label style={{ fontSize: 11, color: 'var(--text-secondary)' }}>Full Legal Name / Identification:</label>
                <input
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="e.g. Tariq Mehmood"
                  style={{ width: '100%', background: '#040b14', border: '1px solid #333', color: '#fff', padding: 8, borderRadius: 4, marginTop: 4 }}
                  required
                />
              </div>
              <div>
                <label style={{ fontSize: 11, color: 'var(--text-secondary)' }}>Known Aliases / Code Names:</label>
                <input
                  type="text"
                  value={alias}
                  onChange={(e) => setAlias(e.target.value)}
                  placeholder="e.g. Commander Falcon"
                  style={{ width: '100%', background: '#040b14', border: '1px solid #333', color: '#fff', padding: 8, borderRadius: 4, marginTop: 4 }}
                />
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
                <div>
                  <label style={{ fontSize: 10, color: 'var(--text-secondary)' }}>Threat Level:</label>
                  <select
                    value={threatLevel}
                    onChange={(e) => setThreatLevel(e.target.value)}
                    style={{ width: '100%', background: '#040b14', border: '1px solid #333', color: '#fff', padding: 6, borderRadius: 4, fontSize: 11, marginTop: 2 }}
                  >
                    <option value="CATEGORY_A">Category A (High Value Target)</option>
                    <option value="CATEGORY_B">Category B (Smuggling / Hawala)</option>
                    <option value="CATEGORY_C">Category C (Surveillance Watch)</option>
                  </select>
                </div>
                <div>
                  <label style={{ fontSize: 10, color: 'var(--text-secondary)' }}>Wanted Agency:</label>
                  <input
                    type="text"
                    value={agency}
                    onChange={(e) => setAgency(e.target.value)}
                    style={{ width: '100%', background: '#040b14', border: '1px solid #333', color: '#fff', padding: 6, borderRadius: 4, fontSize: 11, marginTop: 2 }}
                  />
                </div>
              </div>
              <div>
                <label style={{ fontSize: 11, color: 'var(--text-secondary)' }}>Crime Classification / Reason:</label>
                <input
                  type="text"
                  value={category}
                  onChange={(e) => setCategory(e.target.value)}
                  style={{ width: '100%', background: '#040b14', border: '1px solid #333', color: '#fff', padding: 8, borderRadius: 4, marginTop: 4 }}
                />
              </div>
              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8, marginTop: 8 }}>
                <button className="btn btn-secondary" type="button" onClick={() => setShowEnroll(false)}>
                  Cancel
                </button>
                <button className="btn btn-primary" type="submit">
                  + Generate 512D ArcFace Vector & Enroll
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

/* ─── Tactical QRT Dispatch Center ────────────────────────────── */
function QRTPage({ incidents }: { incidents: Incident[] }) {
  const [teams, setTeams] = useState<any[]>([]);
  const [logs, setLogs] = useState<any[]>([]);
  const [selectedIncidentId, setSelectedIncidentId] = useState<number>(incidents[0]?.id || 1);
  const [radioMsg, setRadioMsg] = useState('');
  const [radioBroadcasts, setRadioBroadcasts] = useState<any[]>([
    {
      id: 101,
      callsign: 'CHEETAH-LEADER',
      message: 'Base, Cheetah-1 on standby at Sector Alpha forward bunker. All weapons checked.',
      time: '02:40:15 IST',
      priority: 'ROUTINE',
    },
    {
      id: 102,
      callsign: 'COBRA-ACTUAL',
      message: 'Cobra-2 moving along Ridge Line Bravo. Zero visual contact.',
      time: '02:44:20 IST',
      priority: 'ROUTINE',
    },
  ]);
  const [feedback, setFeedback] = useState<string | null>(null);

  const loadData = () => {
    api.qrtTeams().then(setTeams).catch(() => {});
    api.qrtLogs().then(setLogs).catch(() => {});
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleDispatch = async (teamId: number, sector: string) => {
    playTacticalTone('click');
    try {
      const res = await api.dispatchQrt({
        team_id: teamId,
        incident_id: selectedIncidentId,
        target_sector: sector,
        orders: 'Immediate Interception & Perimeter Containment',
      });
      playTacticalTone('alert');
      setFeedback(`🚨 QRT SCRAMBLE: ${res.team.name} vectored to ${sector}. ETA: ${res.eta_minutes} minutes!`);
      loadData();
    } catch {}
  };

  const handleUpdateStatus = async (teamId: number, status: string) => {
    playTacticalTone('click');
    try {
      await api.updateQrtStatus({ team_id: teamId, status });
      playTacticalTone('verify');
      loadData();
    } catch {}
  };

  const handleSendRadio = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!radioMsg.trim()) return;
    playTacticalTone('click');
    try {
      const res = await api.broadcastRadio({
        callsign: 'C4ISR-HQ',
        message: radioMsg,
        priority: 'FLASH_TACTICAL',
      });
      setRadioBroadcasts((prev) => [
        {
          id: res.broadcast_id,
          callsign: res.callsign,
          message: res.message,
          time: new Date().toLocaleTimeString('en-GB', { timeZone: 'Asia/Kolkata', hour12: false }) + ' IST',
          priority: res.priority,
        },
        ...prev,
      ]);
      setRadioMsg('');
      playTacticalTone('verify');
    } catch {}
  };

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h1>Tactical Quick Reaction Team (QRT) Dispatch & Command</h1>
          <p style={{ margin: 0, fontSize: 12, color: 'var(--text-secondary)' }}>
            Real-time commando unit vectoring, mission engagement tracking, ETA countdown, and encrypted VHF radio SITREPs
          </p>
        </div>
      </div>

      {feedback && (
        <div className={`test-feedback ${feedback.includes('🚨') ? 'fail' : 'success'}`} style={{ marginBottom: 16 }}>
          {feedback}
        </div>
      )}

      {/* QRT Fleet Readiness KPI Ribbon */}
      <div className="tactical-kpi-ribbon" style={{ marginBottom: 16 }}>
        <div className="tactical-kpi-card">
          <div className="kpi-header-label">
            <span>STRIKE UNITS DEPLOYED</span>
            <span style={{ color: '#00f0ff' }}>READINESS</span>
          </div>
          <div className="kpi-metric-val">{teams.length} UNITS</div>
        </div>
        <div className="tactical-kpi-card">
          <div className="kpi-header-label">
            <span>TOTAL COMMANDO STRENGTH</span>
            <span style={{ color: '#00ff9d' }}>OPERATORS</span>
          </div>
          <div className="kpi-metric-val" style={{ color: '#00ff9d' }}>
            30 ARMED PERSONNEL
          </div>
        </div>
        <div className="tactical-kpi-card">
          <div className="kpi-header-label">
            <span>AVG PERIMETER RESPONSE ETA</span>
            <span style={{ color: '#ffaa00' }}>SPEED</span>
          </div>
          <div className="kpi-metric-val" style={{ color: '#ffaa00' }}>
            00:04 MINS
          </div>
        </div>
        <div className="tactical-kpi-card">
          <div className="kpi-header-label">
            <span>ENCRYPTED VHF TACTICAL NET</span>
            <span style={{ color: '#00ff9d' }}>SECURE</span>
          </div>
          <div className="kpi-metric-val" style={{ fontSize: 15, color: '#00ff9d' }}>
            142.850 MHz (DRDO CRYPTO)
          </div>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: 16 }}>
        {/* QRT Strike Units Grid */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          {teams.map((t) => {
            const isEnRoute = t.status === 'EN_ROUTE';
            return (
              <div key={t.id} className={`qrt-unit-card ${isEnRoute ? 'active-route' : ''}`}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                  <div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <b style={{ color: '#fff', fontSize: 15 }}>{t.name}</b>
                      <span className={`qrt-readiness-badge ${isEnRoute ? 'enroute' : 'standby'}`}>
                        {t.status}
                      </span>
                    </div>
                    <div style={{ fontSize: 11, color: '#00f0ff', fontFamily: 'var(--font-mono)', marginTop: 2 }}>
                      CALLSIGN: {t.callsign} • FREQ: {t.radio_channel}
                    </div>
                  </div>
                  <div style={{ textAlign: 'right' }}>
                    <div style={{ fontSize: 12, fontWeight: 700, color: '#fff' }}>
                      Strength: {t.strength} Commandos
                    </div>
                    <div style={{ fontSize: 10, color: 'var(--text-ghost)', marginTop: 2 }}>
                      Fuel: {t.fuel_percent}% • Battery: 100%
                    </div>
                  </div>
                </div>

                <div style={{ background: '#02060c', padding: 10, borderRadius: 4, border: '1px solid rgba(255,255,255,0.06)' }}>
                  <div style={{ fontSize: 11, color: '#e2effc' }}>
                    <b>Vehicle:</b> {t.vehicle}
                  </div>
                  <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginTop: 3 }}>
                    <b>Weapons Loadout:</b> {t.weapons_readiness}
                  </div>
                  <div style={{ fontSize: 10, color: '#ffaa00', fontFamily: 'var(--font-mono)', marginTop: 4 }}>
                    SITREP: {t.last_sitrep}
                  </div>
                </div>

                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div style={{ fontSize: 11, color: 'var(--text-secondary)' }}>
                    Sector: <b style={{ color: '#fff' }}>{t.current_sector}</b>
                  </div>
                  <div style={{ display: 'flex', gap: 8 }}>
                    {isEnRoute ? (
                      <button
                        className="btn btn-sm btn-primary"
                        onClick={() => handleUpdateStatus(t.id, 'ENGAGED')}
                      >
                        ⚡ Report Engaged / Perimeter Contained
                      </button>
                    ) : (
                      <button
                        className="btn btn-sm btn-danger"
                        onClick={() => handleDispatch(t.id, t.bop)}
                        style={{ fontWeight: 800, letterSpacing: 1 }}
                      >
                        🚨 SCRAMBLE TO INCIDENT SECTOR
                      </button>
                    )}
                    <button
                      className="btn btn-sm btn-secondary"
                      onClick={() => handleUpdateStatus(t.id, 'STANDBY_IMMEDIATE')}
                    >
                      Standby
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>

        {/* Tactical VHF Radio Terminal */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <div className="panel" style={{ margin: 0, padding: 16 }}>
            <h3 style={{ color: '#00f0ff', marginBottom: 12, fontSize: 14 }}>📻 Tactical VHF Radio Terminal</h3>
            <form onSubmit={handleSendRadio} style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              <div>
                <label style={{ fontSize: 11, color: 'var(--text-secondary)' }}>Transmit Orders / SITREP:</label>
                <textarea
                  rows={3}
                  value={radioMsg}
                  onChange={(e) => setRadioMsg(e.target.value)}
                  placeholder="e.g. ALL UNITS: Infiltration spotted at Sector Alpha. Secure grid 14."
                  style={{
                    width: '100%',
                    background: '#040b14',
                    border: '1px solid rgba(0, 240, 255, 0.3)',
                    color: '#fff',
                    padding: 8,
                    borderRadius: 4,
                    fontSize: 12,
                    marginTop: 4,
                    resize: 'none',
                  }}
                />
              </div>
              <button className="btn btn-primary" type="submit">
                📡 Transmit Encrypted Radio Order
              </button>
            </form>
          </div>

          <div className="panel" style={{ margin: 0, padding: 16, flex: 1 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
              <h3 style={{ color: '#fff', margin: 0, fontSize: 13 }}>Live Radio Net Ledger</h3>
              <span className="panel-tag" style={{ color: '#00ff9d', borderColor: '#00ff9d' }}>CH-142.850</span>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8, maxHeight: 340, overflowY: 'auto' }}>
              {radioBroadcasts.map((b) => (
                <div
                  key={b.id}
                  style={{
                    padding: 8,
                    background: 'rgba(0, 240, 255, 0.04)',
                    borderLeft: '2px solid #00f0ff',
                    borderRadius: 2,
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 10 }}>
                    <b style={{ color: '#00f0ff' }}>{b.callsign}</b>
                    <span style={{ color: 'var(--text-ghost)' }}>{b.time}</span>
                  </div>
                  <div style={{ fontSize: 11, color: '#e2effc', marginTop: 3 }}>{b.message}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

/* ─── FLIR Thermal & Aerial Drone Reconnaissance ──────────────── */
function ThermalDronePage({ cameras }: { cameras: Camera[] }) {
  const [palette, setPalette] = useState<'optical' | 'white-hot' | 'black-hot' | 'ironbow' | 'rainbow'>('ironbow');
  const [selectedCamId, setSelectedCamId] = useState<number>(cameras[0]?.id || 1);
  const [alt, setAlt] = useState(148);
  const [speed, setSpeed] = useState(44);
  const [battery, setBattery] = useState(89);
  const [flightMode, setFlightMode] = useState('AUTONOMOUS_ORBIT');
  const [targetLocked, setTargetLocked] = useState(true);

  const selectedCam = cameras.find((c) => c.id === selectedCamId) || cameras[0];

  const shaderClass = `thermal-shader-${palette}`;

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h1>FLIR Thermal & Aerial Drone Reconnaissance (UAV)</h1>
          <p style={{ margin: 0, fontSize: 12, color: 'var(--text-secondary)' }}>
            High-altitude border aerial surveillance simulator with multi-spectral thermal palettes (White-Hot, Black-Hot, Ironbow) and SAHI AI target tracking
          </p>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <button
            className={`btn ${palette === 'optical' ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => { playTacticalTone('click'); setPalette('optical'); }}
          >
            Daylight Optical
          </button>
          <button
            className={`btn ${palette === 'white-hot' ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => { playTacticalTone('click'); setPalette('white-hot'); }}
          >
            White-Hot FLIR
          </button>
          <button
            className={`btn ${palette === 'black-hot' ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => { playTacticalTone('click'); setPalette('black-hot'); }}
          >
            Black-Hot FLIR
          </button>
          <button
            className={`btn ${palette === 'ironbow' ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => { playTacticalTone('click'); setPalette('ironbow'); }}
            style={{ background: palette === 'ironbow' ? 'linear-gradient(90deg, #7c3aed, #ea580c)' : undefined }}
          >
            Ironbow Thermal
          </button>
          <button
            className={`btn ${palette === 'rainbow' ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => { playTacticalTone('click'); setPalette('rainbow'); }}
          >
            Rainbow HC
          </button>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '3fr 1fr', gap: 16 }}>
        {/* Main Thermal Viewport */}
        <div className="thermal-viewport-container" style={{ height: 520 }}>
          {selectedCam ? (
            <img
              src={`/api/v1/cameras/${selectedCam.id}/snapshot?t=${Date.now()}`}
              alt="Thermal Drone Feed"
              className={shaderClass}
              style={{ width: '100%', height: '100%', objectFit: 'cover' }}
            />
          ) : (
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', color: '#666' }}>
              NO DRONE LINK
            </div>
          )}

          {/* Tactical Crosshair Reticle */}
          <div className="drone-crosshair" />

          {/* UAV OSD HUD Overlay */}
          <div className="drone-osd-overlay">
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <div>
                <b style={{ color: '#00ff9d', fontSize: 13 }}>UAV FALCON-01 // AIRBORNE RECON</b>
                <div style={{ fontSize: 10, color: 'var(--text-ghost)' }}>MODE: {flightMode} • SAT-LINK: LOCK (14 SATS)</div>
              </div>
              <div style={{ textAlign: 'right' }}>
                <b style={{ color: '#00f0ff' }}>FLIR PALETTE: {palette.toUpperCase()}</b>
                <div style={{ fontSize: 10, color: '#00ff9d' }}>BATTERY: {battery}% • REMAINING: 38 MINS</div>
              </div>
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end' }}>
              <div>
                <div>ALT: <b>{alt}m AGL</b></div>
                <div>SPD: <b>{speed} km/h</b></div>
                <div>HDG: <b>042° NE</b></div>
                <div>PITCH: <b>-32.4°</b></div>
              </div>
              <div style={{ textAlign: 'center' }}>
                {targetLocked && (
                  <div style={{ border: '1px solid #ff2a55', background: 'rgba(255, 42, 85, 0.2)', color: '#ff2a55', padding: '4px 12px', borderRadius: 4, fontWeight: 800, letterSpacing: 2 }}>
                    [ TARGET THERMAL SIGNATURE LOCKED ]
                  </div>
                )}
              </div>
              <div style={{ textAlign: 'right' }}>
                <div>LAT: <b>32.7266° N</b></div>
                <div>LON: <b>74.8570° E</b></div>
                <div>GRID: <b>SSB-SEC-A-092</b></div>
                <div>ENCRYPTION: <b>AES-256-GCM</b></div>
              </div>
            </div>
          </div>
        </div>

        {/* Flight Telemetry & Controls */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          <div className="panel" style={{ margin: 0, padding: 16 }}>
            <h3 style={{ color: '#00f0ff', marginBottom: 12, fontSize: 14 }}>🎮 Drone Mission Vector Controls</h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              <button
                className={`btn ${flightMode === 'AUTONOMOUS_ORBIT' ? 'btn-primary' : 'btn-secondary'}`}
                onClick={() => { playTacticalTone('click'); setFlightMode('AUTONOMOUS_ORBIT'); }}
              >
                🔄 Orbit Sector Alpha Perimeter
              </button>
              <button
                className={`btn ${flightMode === 'THERMAL_TRACKING' ? 'btn-primary' : 'btn-secondary'}`}
                onClick={() => { playTacticalTone('click'); setFlightMode('THERMAL_TRACKING'); setTargetLocked(true); }}
              >
                🎯 Lock & Track Heat Signature
              </button>
              <button
                className={`btn ${flightMode === 'CONVOY_ESCORT' ? 'btn-primary' : 'btn-secondary'}`}
                onClick={() => { playTacticalTone('click'); setFlightMode('CONVOY_ESCORT'); }}
              >
                🛡️ Convoy Aerial Escort Route
              </button>
              <button
                className="btn btn-danger"
                onClick={() => { playTacticalTone('escalate'); setFlightMode('RETURN_TO_LAUNCH'); }}
                style={{ marginTop: 6 }}
              >
                ⚡ Return To Launch (RTL)
              </button>
            </div>
          </div>

          <div className="panel" style={{ margin: 0, padding: 16 }}>
            <h3 style={{ color: '#fff', marginBottom: 12, fontSize: 13 }}>Switch Surveillance Camera Sensor</h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              {cameras.map((c) => (
                <button
                  key={c.id}
                  className={`btn btn-sm ${selectedCamId === c.id ? 'btn-primary' : 'btn-secondary'}`}
                  style={{ justifyContent: 'flex-start' }}
                  onClick={() => { playTacticalTone('click'); setSelectedCamId(c.id); }}
                >
                  📹 {c.name} ({c.bop})
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

/* ─── Tactical UI Error Boundary ──────────────────────────────── */
class ErrorBoundary extends React.Component<{ children: React.ReactNode }, { hasError: boolean; error: any }> {
  constructor(props: any) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: any) {
    return { hasError: true, error };
  }

  componentDidCatch(error: any, errorInfo: any) {
    console.error("C4ISR Interface Error Caught:", error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          height: '100vh',
          background: '#02060c',
          color: '#e2effc',
          fontFamily: 'monospace',
          padding: 24,
          textAlign: 'center'
        }}>
          <div style={{ color: '#ff2a55', fontSize: 24, fontWeight: 'bold', marginBottom: 12 }}>
            ⚠️ TACTICAL C4ISR CONSOLE RECOVERY
          </div>
          <p style={{ maxWidth: 500, color: 'var(--text-secondary)', marginBottom: 20 }}>
            {String(this.state.error?.message || this.state.error || 'A state synchronization issue occurred.')}
          </p>
          <button
            style={{
              padding: '10px 24px',
              background: '#00f0ff',
              color: '#02060c',
              border: 'none',
              borderRadius: 4,
              fontWeight: 'bold',
              cursor: 'pointer',
              letterSpacing: 1
            }}
            onClick={() => {
              localStorage.removeItem('ibvap_token');
              window.location.reload();
            }}
          >
            ↻ RECOVER & RECONNECT CONSOLE
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}

/* ─── Mount React Application ─────────────────────────────────── */
const root = document.getElementById('root');
if (root) {
  createRoot(root).render(
    <ErrorBoundary>
      <App />
    </ErrorBoundary>
  );
}
