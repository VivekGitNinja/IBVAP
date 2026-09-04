import React, { useState, useEffect } from 'react';
import { ENABLE_HUD_STYLING } from '../config';

export interface TacticalHUDProps {
  cameraId?: number | string | null;
  cameraName?: string | null;
  sector?: string | null;
  latitude?: number | null;
  longitude?: number | null;
  status?: string | null;
  fps?: number | null;
  resolution?: string | null;
  isRecording?: boolean;
  recTimestamp?: string | null;
  defconLevel?: number | null;
  defconLabel?: string | null;
  children?: React.ReactNode;
  showScanlines?: boolean;
  variant?: 'card' | 'panel' | 'header';
  className?: string;
}

export function TacticalHUD({
  cameraId,
  cameraName,
  sector,
  latitude,
  longitude,
  status,
  fps,
  resolution,
  isRecording = true,
  recTimestamp,
  defconLevel,
  defconLabel,
  children,
  showScanlines = true,
  variant = 'card',
  className = '',
}: TacticalHUDProps) {
  const [clock, setClock] = useState(new Date());

  useEffect(() => {
    const timer = setInterval(() => setClock(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  // Format dual clock (UTC Zulu + Indian Standard Time IST)
  const utcStr = clock.toISOString().replace('T', ' ').substring(0, 19) + ' Z';
  const istStr = clock.toLocaleTimeString('en-GB', {
    timeZone: 'Asia/Kolkata',
    hour12: false,
  }) + ' IST';

  // Format real GPS coordinates (zero mock: strictly "--" if absent)
  const hasCoords =
    latitude !== null &&
    latitude !== undefined &&
    longitude !== null &&
    longitude !== undefined &&
    !(latitude === 0 && longitude === 0);

  const coordsStr = hasCoords
    ? `${latitude! >= 0 ? latitude!.toFixed(4) + '°N' : Math.abs(latitude!).toFixed(4) + '°S'}, ${
        longitude! >= 0 ? longitude!.toFixed(4) + '°E' : Math.abs(longitude!).toFixed(4) + '°W'
      }`
    : '-- / --';

  // DEFCON display fallback
  const dLevel = defconLevel ?? 4;
  const dLabel = defconLabel ?? (dLevel === 1 ? 'CRITICAL' : dLevel === 2 ? 'ELEVATED' : dLevel === 3 ? 'SENSITIVE' : 'ROUTINE');

  const isOnline = status?.toUpperCase() === 'ONLINE' || status?.toUpperCase() === 'CONNECTED';
  const statusStr = status ? status.toUpperCase() : '--';

  const resStr = resolution || (fps ? `${fps.toFixed(1)} FPS` : '--');

  return (
    <div className={`tactical-hud-container tactical-hud-${variant} ${className}`}>
      {/* Corner Bracket Accents (pure CSS/canvas, toggleable) */}
      {ENABLE_HUD_STYLING && (
        <>
          <div className="corner-bracket cb-top-left" />
          <div className="corner-bracket cb-top-right" />
          <div className="corner-bracket cb-bottom-left" />
          <div className="corner-bracket cb-bottom-right" />
          {showScanlines && <div className="tactical-hud-scanlines" />}
        </>
      )}

      {/* Top HUD Telemetry Bar */}
      <div className="tactical-hud-header">
        {/* Left: Node Identifier & Location */}
        <div className="tactical-hud-left">
          <span className="tactical-hud-node">
            {cameraId !== null && cameraId !== undefined ? `CAM-${cameraId}` : 'NODE: --'}
          </span>
          {cameraName && <span className="tactical-hud-name">{cameraName}</span>}
          {sector && <span className="tactical-hud-sector">[{sector}]</span>}
          <span className="tactical-hud-coords" title="Geographic Coordinates (WGS84)">
            📍 {coordsStr}
          </span>
        </div>

        {/* Center: Dual UTC / IST Military Clock */}
        <div className="tactical-hud-clock" title={`Zulu (UTC): ${utcStr} | Local: ${istStr}`}>
          <span className="tactical-clock-utc">{utcStr}</span>
          <span className="tactical-clock-divider">|</span>
          <span className="tactical-clock-ist">{istStr}</span>
        </div>

        {/* Right: Telemetry, DEFCON, REC status */}
        <div className="tactical-hud-right">
          {/* DEFCON Badge */}
          <div className={`tactical-hud-defcon defcon-${dLevel}`} title={`Readiness Posture: DEFCON ${dLevel} (${dLabel})`}>
            <span className="defcon-dot" />
            <span>DEFCON {dLevel}</span>
          </div>

          {/* Connection Status */}
          <span className={`tactical-hud-status ${isOnline ? 'online' : 'offline'}`}>
            ● {statusStr}
          </span>

          {/* Recording Dot */}
          {isRecording && (
            <span className="tactical-hud-rec" title="Real Frame Stream Ingestion Active">
              <span className="rec-dot" />
              <span>REC</span>
              {recTimestamp && <span className="rec-time">{recTimestamp}</span>}
            </span>
          )}

          {/* Resolution & FPS */}
          <span className="tactical-hud-fps">{resStr}</span>
        </div>
      </div>

      {/* Main Wrapped Content (Video Player, Canvas, Card body) */}
      <div className="tactical-hud-content">{children}</div>
    </div>
  );
}
