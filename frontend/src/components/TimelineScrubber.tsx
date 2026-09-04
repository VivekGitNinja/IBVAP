import React, { useState } from 'react';
import { Incident } from '../types';

interface TimelineScrubberProps {
  incidents: Incident[];
  onSelectIncident: (incidentId: number) => void;
  selectedIncidentId?: number;
}

export function TimelineScrubber({
  incidents,
  onSelectIncident,
  selectedIncidentId,
}: TimelineScrubberProps) {
  const [hoveredInc, setHoveredInc] = useState<{ inc: Incident; x: number } | null>(null);
  const [filterSeverity, setFilterSeverity] = useState<string>('ALL');

  // Filtered incidents
  const filtered = incidents.filter((i) => {
    if (filterSeverity === 'CRITICAL') return i.severity === 'CRITICAL';
    if (filterSeverity === 'HIGH') return i.severity === 'HIGH';
    if (filterSeverity === 'MEDIUM') return i.severity === 'MEDIUM';
    return true;
  });

  // Helper to convert an ISO timestamp to percentage position in a 24-hour day (0 - 100%)
  const getPercentOfDay = (isoString: string): number => {
    try {
      const d = new Date(isoString);
      // Format to IST hours and minutes
      const hours = d.getHours();
      const minutes = d.getMinutes();
      const seconds = d.getSeconds();
      const totalSeconds = hours * 3600 + minutes * 60 + seconds;
      return (totalSeconds / 86400) * 100;
    } catch {
      return 50;
    }
  };

  // Current time in day percentage
  const now = new Date();
  const nowPercent = ((now.getHours() * 3600 + now.getMinutes() * 60 + now.getSeconds()) / 86400) * 100;

  const hoursMarks = [0, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22, 24];

  return (
    <div
      style={{
        background: 'rgba(4, 9, 20, 0.85)',
        border: '1px solid rgba(0, 240, 255, 0.25)',
        borderRadius: 6,
        padding: '12px 16px',
        marginBottom: 16,
        position: 'relative',
        boxShadow: '0 4px 20px rgba(0, 0, 0, 0.4)',
      }}
    >
      {/* Top Header */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: 10,
          flexWrap: 'wrap',
          gap: 8,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{ fontSize: 14 }}>⏱️</span>
          <span
            style={{
              fontSize: 11,
              fontWeight: 800,
              letterSpacing: 1.5,
              color: '#00f0ff',
              fontFamily: 'var(--font-mono)',
            }}
          >
            24-HOUR DEFENSE EVENT SCRUBBER & AUDIT TIMELINE
          </span>
          <span className="badge" style={{ background: 'rgba(0, 240, 255, 0.1)', color: '#00f0ff', fontSize: 10 }}>
            {filtered.length} EVENTS PLOTTED
          </span>
        </div>

        {/* Severity Filter Pills */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <span style={{ fontSize: 10, color: 'var(--text-ghost)', letterSpacing: 1 }}>FILTER:</span>
          {['ALL', 'CRITICAL', 'HIGH', 'MEDIUM'].map((sev) => (
            <button
              key={sev}
              onClick={() => setFilterSeverity(sev)}
              style={{
                background: filterSeverity === sev ? 'rgba(0, 240, 255, 0.2)' : 'transparent',
                border: `1px solid ${
                  filterSeverity === sev
                    ? '#00f0ff'
                    : sev === 'CRITICAL'
                    ? 'rgba(255, 42, 85, 0.4)'
                    : 'rgba(255, 255, 255, 0.1)'
                }`,
                color:
                  sev === 'CRITICAL'
                    ? '#ff2a55'
                    : sev === 'HIGH'
                    ? '#ffaa00'
                    : sev === 'MEDIUM'
                    ? '#00f0ff'
                    : '#e2e8f0',
                padding: '2px 8px',
                borderRadius: 3,
                fontSize: 10,
                fontFamily: 'var(--font-mono)',
                cursor: 'pointer',
                fontWeight: filterSeverity === sev ? 700 : 400,
              }}
            >
              {sev}
            </button>
          ))}
        </div>
      </div>

      {/* Main 24-Hour Scrubber Track */}
      <div
        style={{
          position: 'relative',
          height: 48,
          background: '#02050c',
          borderRadius: 4,
          border: '1px solid rgba(255, 255, 255, 0.08)',
          margin: '12px 0 20px',
          display: 'flex',
          alignItems: 'center',
          overflow: 'visible',
        }}
      >
        {/* Subtle grid background */}
        <div
          style={{
            position: 'absolute',
            inset: 0,
            background:
              'repeating-linear-gradient(90deg, rgba(255, 255, 255, 0.03) 0, rgba(255, 255, 255, 0.03) 1px, transparent 0, transparent 4.166%)',
            pointerEvents: 'none',
          }}
        />

        {/* Center horizontal track line */}
        <div
          style={{
            position: 'absolute',
            left: 0,
            right: 0,
            height: 2,
            background: 'rgba(0, 240, 255, 0.2)',
          }}
        />

        {/* Real-time "NOW" Vertical Beacon */}
        <div
          style={{
            position: 'absolute',
            left: `${nowPercent}%`,
            top: 0,
            bottom: 0,
            width: 2,
            background: '#00ff9d',
            boxShadow: '0 0 10px #00ff9d',
            zIndex: 10,
            pointerEvents: 'none',
          }}
        >
          <div
            style={{
              position: 'absolute',
              top: -16,
              left: -16,
              fontSize: 9,
              fontFamily: 'var(--font-mono)',
              fontWeight: 800,
              color: '#00ff9d',
              letterSpacing: 0.5,
              whiteSpace: 'nowrap',
            }}
          >
            ● NOW
          </div>
        </div>

        {/* Plotted Incident Markers */}
        {filtered.map((inc) => {
          const pct = getPercentOfDay(inc.created_at);
          const isCrit = inc.severity === 'CRITICAL';
          const isHigh = inc.severity === 'HIGH';
          const isSelected = inc.id === selectedIncidentId;
          const color = isCrit ? '#ff2a55' : isHigh ? '#ffaa00' : '#00f0ff';

          return (
            <div
              key={inc.id}
              onClick={() => onSelectIncident(inc.id)}
              onMouseEnter={(e) => {
                const rect = e.currentTarget.parentElement?.getBoundingClientRect();
                if (rect) {
                  setHoveredInc({ inc, x: e.clientX - rect.left });
                }
              }}
              onMouseLeave={() => setHoveredInc(null)}
              style={{
                position: 'absolute',
                left: `calc(${pct}% - 6px)`,
                width: isSelected ? 16 : 12,
                height: isSelected ? 28 : 20,
                background: color,
                borderRadius: 2,
                cursor: 'pointer',
                zIndex: isSelected ? 20 : 15,
                boxShadow: isSelected
                  ? `0 0 14px ${color}`
                  : `0 0 6px ${color}80`,
                border: isSelected ? '2px solid #fff' : '1px solid rgba(0,0,0,0.4)',
                transition: 'all 0.15s ease',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              {isCrit && (
                <div
                  style={{
                    position: 'absolute',
                    inset: -4,
                    borderRadius: 4,
                    border: '1px solid #ff2a55',
                    animation: 'pulse 1.5s infinite',
                    pointerEvents: 'none',
                  }}
                />
              )}
            </div>
          );
        })}

        {/* Interactive Hover Tooltip Card */}
        {hoveredInc && (
          <div
            style={{
              position: 'absolute',
              left: Math.max(10, Math.min(window.innerWidth - 300, hoveredInc.x - 120)),
              bottom: 56,
              background: '#070d1e',
              border: `1px solid ${
                hoveredInc.inc.severity === 'CRITICAL' ? '#ff2a55' : '#00f0ff'
              }`,
              borderRadius: 6,
              padding: '10px 14px',
              boxShadow: '0 8px 30px rgba(0, 0, 0, 0.8)',
              zIndex: 100,
              width: 250,
              pointerEvents: 'none',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span
                style={{
                  fontSize: 9,
                  fontWeight: 800,
                  fontFamily: 'var(--font-mono)',
                  color: hoveredInc.inc.severity === 'CRITICAL' ? '#ff2a55' : '#00f0ff',
                }}
              >
                {hoveredInc.inc.incident_code}
              </span>
              <span
                style={{
                  fontSize: 9,
                  padding: '2px 4px',
                  borderRadius: 2,
                  background:
                    hoveredInc.inc.severity === 'CRITICAL'
                      ? 'rgba(255, 42, 85, 0.2)'
                      : 'rgba(0, 240, 255, 0.2)',
                  color: hoveredInc.inc.severity === 'CRITICAL' ? '#ff2a55' : '#00f0ff',
                  fontWeight: 700,
                }}
              >
                {hoveredInc.inc.severity}
              </span>
            </div>

            <div style={{ fontSize: 11, fontWeight: 700, color: '#fff', margin: '4px 0 2px' }}>
              {hoveredInc.inc.title}
            </div>

            <div style={{ fontSize: 10, color: 'var(--text-secondary)' }}>
              {hoveredInc.inc.camera_name || 'Camera'} • Score:{' '}
              <b style={{ color: '#00ff9d' }}>{hoveredInc.inc.threat_score.toFixed(0)}/100</b>
            </div>

            <div style={{ fontSize: 9, color: 'var(--text-ghost)', marginTop: 4 }}>
              Click marker to inspect Section 65B forensic dossier
            </div>
          </div>
        )}
      </div>

      {/* Hour Markers Label Row */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          fontSize: 9,
          color: 'var(--text-ghost)',
          fontFamily: 'var(--font-mono)',
          padding: '0 4px',
          userSelect: 'none',
        }}
      >
        {hoursMarks.map((hr) => (
          <div key={hr} style={{ textAlign: 'center' }}>
            {hr.toString().padStart(2, '0')}:00
          </div>
        ))}
      </div>
    </div>
  );
}
