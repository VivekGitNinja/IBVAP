import React from 'react';
import type { Camera, Incident } from '../types';

interface TacticalBorderMapProps {
  cameras: Camera[];
  incidents: Incident[];
  selectedBop: string | null;
  onSelectBop: (bop: string | null) => void;
}

export function TacticalBorderMap({
  cameras,
  incidents,
  selectedBop,
  onSelectBop,
}: TacticalBorderMapProps) {
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

        {/* Active QRT Armed Patrol Units (Live Vectoring) */}
        <g key="qrt-cheetah">
          <line x1="330" y1="230" x2="300" y2="150" stroke="#00ff9d" strokeWidth="1.5" strokeDasharray="3,3" opacity="0.7" />
          <circle cx="330" cy="230" r="7" fill="#00ff9d" />
          <circle cx="330" cy="230" r="12" fill="none" stroke="#00ff9d" strokeWidth="1.2" opacity="0.6" />
          <rect x="260" y="242" width="140" height="18" fill="rgba(4, 16, 24, 0.9)" stroke="#00ff9d" strokeWidth="1" rx="3" />
          <text x="330" y="254" textAnchor="middle" fill="#00ff9d" fontSize="8" fontWeight="bold" fontFamily="var(--font-mono)">
            ⚡ QRT: CHEETAH-1 (INTERCEPTING)
          </text>
        </g>

        <g key="qrt-cobra">
          <circle cx="610" cy="225" r="6" fill="#00ff9d" />
          <rect x="550" y="237" width="120" height="18" fill="rgba(4, 16, 24, 0.9)" stroke="#00ff9d" strokeWidth="1" rx="3" />
          <text x="610" y="249" textAnchor="middle" fill="#00ff9d" fontSize="8" fontWeight="bold" fontFamily="var(--font-mono)">
            ⚡ QRT: COBRA-2 (STANDBY)
          </text>
        </g>
      </svg>
    </div>
  );
}
