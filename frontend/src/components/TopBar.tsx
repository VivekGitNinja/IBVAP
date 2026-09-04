import React, { useState, useEffect } from 'react';
import { copyShareLink } from '../utils/shareLinks';
import { playTacticalTone } from '../utils/audio';

interface TopBarProps {
  status: any;
  ws: string;
  maxThreat: number;
  isMuted: boolean;
  onToggleMute: () => void;
  onSync: () => void;
  onTestAlert: () => void;
  onOpenSearch: () => void;
  selectedBop?: string | null;
  onSelectBop?: (bop: string | null) => void;
  currentUser?: { username: string; role: string } | null;
  onOpenLogin?: () => void;
  onTogglePatrol?: () => void;
  isPatrolActive?: boolean;
}

export function TopBar({
  status,
  ws,
  maxThreat,
  isMuted,
  onToggleMute,
  onSync,
  onTestAlert,
  onOpenSearch,
  currentUser,
  onOpenLogin,
  onTogglePatrol,
  isPatrolActive,
}: TopBarProps) {
  const [clock, setClock] = useState(new Date());
  const [copiedLink, setCopiedLink] = useState(false);

  useEffect(() => {
    const t = setInterval(() => setClock(new Date()), 1000);
    return () => clearInterval(t);
  }, []);

  const utcStr = clock.toISOString().substring(11, 19) + ' Z';
  const istStr = clock.toLocaleTimeString('en-GB', { timeZone: 'Asia/Kolkata', hour12: false }) + ' IST';

  // Dynamic DEFCON assessment
  let defconLevel = 4;
  let defconShort = 'ROUTINE';
  let defconClass = 'defcon-4';

  if (maxThreat >= 80) {
    defconLevel = 1;
    defconShort = 'CRITICAL';
    defconClass = 'defcon-1';
  } else if (maxThreat >= 60) {
    defconLevel = 2;
    defconShort = 'ELEVATED';
    defconClass = 'defcon-2';
  } else if (maxThreat >= 35) {
    defconLevel = 3;
    defconShort = 'SENSITIVE';
    defconClass = 'defcon-3';
  }

  return (
    <header className="topbar">
      {/* ─── Left: Brand & Threat Level ──────────────────────── */}
      <div className="topbar-left">
        <div className="defense-emblem" title="Sashastra Seema Bal / Ministry of Home Affairs">
          <svg viewBox="0 0 24 24" fill="none" strokeWidth="2.2">
            <polygon points="12 2 2 7 12 12 22 7 12 2" />
            <polyline points="2 17 12 22 22 17" />
            <polyline points="2 12 12 17 22 12" />
          </svg>
        </div>
        <div className="defense-title-block">
          <span className="defense-title-main">SSB C4ISR</span>
          <span className="defense-title-sub">BORDER SURVEILLANCE</span>
        </div>

        {/* Dynamic DEFCON Level */}
        <div className={`defcon-badge ${defconClass}`} title={`Defense Readiness Condition (Sector Threat Score: ${maxThreat.toFixed(0)}/100)`}>
          <span className="defcon-pulse-dot" />
          <span className="defcon-title">DEFCON {defconLevel}</span>
          <span className="defcon-divider">•</span>
          <span className="defcon-label">{defconShort}</span>
        </div>
      </div>

      {/* ─── Center: Global Spotlight Search ─────────────────── */}
      <div className="topbar-center">
        <button
          className="topbar-search-trigger"
          onClick={onOpenSearch}
          title="Global Command & Surveillance Search (Cmd+K / Ctrl+K)"
        >
          <div className="search-trigger-content">
            <span style={{ fontSize: 12 }}>🔍</span>
            <span>Quick Search...</span>
          </div>
          <span className="cmd-k-kbd">⌘K</span>
        </button>
      </div>

      {/* ─── Right: Telemetry, Clock, Controls & Profile ─────── */}
      <div className="topbar-right">
        {/* Core System Telemetry */}
        <div className="telemetry-strip">
          <div className="telemetry-pill ok" title="Perception Engine Active (YOLO26 & ByteTrack)">
            <span className="pill-dot" />
            <span>AI: YOLO26</span>
          </div>
          <div className="telemetry-pill ok" title="Bharatiya Sakshya Adhiniyam 2023 Section 63 Forensics Vault Sealed">
            <span className="pill-dot" />
            <span>BSA §63 SEALED</span>
          </div>
        </div>

        {/* Single Line Clean Military Clock */}
        <div className="tactical-clocks" title={`Local IST: ${istStr} | Zulu (UTC): ${utcStr}`}>
          <span className="clock-icon">⏱</span>
          <span className="clock-val ist">{istStr}</span>
        </div>

        {/* Tactical Sound Synthesizer */}
        <button
          className={`audio-wave-btn ${isMuted ? 'muted' : ''}`}
          onClick={onToggleMute}
          title={isMuted ? 'Unmute Tactical Audio Alerts' : 'Mute Tactical Audio Alerts'}
        >
          <div className="audio-wave-bars">
            <span className="audio-bar" />
            <span className="audio-bar" />
            <span className="audio-bar" />
          </div>
          <span>{isMuted ? 'MUTED' : 'AUDIO'}</span>
        </button>

        {/* Test Alert Button */}
        <button
          className="btn-tactical-icon btn-test-breach"
          onClick={onTestAlert}
          title="Simulate / Inject Test Breach Alert"
        >
          <span className="test-alert-dot" />
          <span>TEST</span>
        </button>

        {/* Copy Share Link Button (Task 5.2) */}
        <button
          className="btn-tactical-icon"
          onClick={async () => {
            playTacticalTone('click');
            const ok = await copyShareLink();
            if (ok) {
              setCopiedLink(true);
              setTimeout(() => setCopiedLink(false), 2000);
            }
          }}
          title="Copy Deep Share Link for Current Tactical View"
          style={{ width: 'auto', padding: '0 8px', gap: 4 }}
        >
          <span>{copiedLink ? '✓' : '🔗'}</span>
          <span style={{ fontSize: 10 }}>{copiedLink ? 'COPIED' : 'SHARE'}</span>
        </button>

        {/* Patrol Mode Tour Button (Task 6.1) */}
        {onTogglePatrol && (
          <button
            className={`btn-tactical-icon ${isPatrolActive ? 'active' : ''}`}
            onClick={onTogglePatrol}
            title={isPatrolActive ? 'Exit Tactical Patrol Tour' : 'Launch Scripted Patrol Mode Tour (Real Data)'}
            style={{
              width: 'auto',
              padding: '0 8px',
              gap: 4,
              borderColor: isPatrolActive ? '#00ff9d' : '#00f0ff',
              color: isPatrolActive ? '#00ff9d' : '#00f0ff',
              background: isPatrolActive ? 'rgba(0, 255, 157, 0.2)' : 'rgba(0, 240, 255, 0.1)',
            }}
          >
            <span>🚨</span>
            <span style={{ fontSize: 10 }}>{isPatrolActive ? 'IN PATROL' : 'PATROL'}</span>
          </button>
        )}

        {/* Force Refresh */}
        <button className="btn-tactical-icon btn-sync" onClick={onSync} title="Force Telemetry Sync">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4">
            <polyline points="23 4 23 10 17 10" />
            <polyline points="1 20 1 14 7 14" />
            <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15" />
          </svg>
        </button>

        {/* Operator Profile Badge */}
        <div
          className="operator-chip"
          onClick={onOpenLogin}
          style={{ cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 6 }}
          title={`Active Clearance: ${currentUser?.role || 'UNAUTHENTICATED'} (${currentUser?.username || 'GUEST'}). Click to switch user.`}
        >
          <div className="operator-avatar">{currentUser?.role?.substring(0, 3) || 'SSB'}</div>
          <span className="operator-status-dot" style={{ background: currentUser ? '#00f0ff' : '#ffaa00' }} />
          <span style={{ fontSize: 10, color: currentUser ? '#00f0ff' : '#ffaa00', fontWeight: 'bold' }}>
            {currentUser?.username ? currentUser.username.toUpperCase() : 'AUTH'}
          </span>
        </div>
      </div>
    </header>
  );
}
