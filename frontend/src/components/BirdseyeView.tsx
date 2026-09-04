import React, { useState, useEffect, useRef } from 'react';
import { Camera, Incident } from '../types';
import { WebSocketVideoCanvas } from './WebSocketVideoCanvas';
import { PTZController } from './PTZController';

interface BirdseyeViewProps {
  cameras: Camera[];
  incidents: Incident[];
  onOpenZoneStudio: (camId: number) => void;
  onScrambleQrt?: (incident: Incident) => void;
}

export function BirdseyeView({
  cameras,
  incidents,
  onOpenZoneStudio,
  onScrambleQrt,
}: BirdseyeViewProps) {
  const [activeCamId, setActiveCamId] = useState<number>(cameras[0]?.id || 1);
  const [autoCycle, setAutoCycle] = useState<boolean>(true);
  const [cycleSeconds, setCycleSeconds] = useState<number>(8);
  const [showPTZ, setShowPTZ] = useState<boolean>(false);

  // Find camera with the highest active threat
  const highestThreatIncident = incidents
    .filter((i) => i.status === 'NEW' || i.status === 'ACKNOWLEDGED')
    .sort((a, b) => b.threat_score - a.threat_score)[0];

  const highestThreatCamId = highestThreatIncident?.camera_id;

  // Auto-lock onto threat if one exists
  useEffect(() => {
    if (highestThreatCamId && cameras.some((c) => c.id === highestThreatCamId)) {
      setActiveCamId(highestThreatCamId);
    }
  }, [highestThreatCamId]);

  // Auto-cycle timer when no active DEFCON 1 breach
  useEffect(() => {
    if (!autoCycle || cameras.length <= 1) return;
    if (highestThreatIncident && highestThreatIncident.severity === 'CRITICAL') return;

    const timer = setInterval(() => {
      setCycleSeconds((prev) => {
        if (prev <= 1) {
          setActiveCamId((currentId) => {
            const idx = cameras.findIndex((c) => c.id === currentId);
            const nextIdx = (idx + 1) % cameras.length;
            return cameras[nextIdx].id;
          });
          return 8;
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(timer);
  }, [autoCycle, cameras, highestThreatIncident]);

  const activeCam = cameras.find((c) => c.id === activeCamId) || cameras[0];
  const standbyCameras = cameras.filter((c) => c.id !== activeCamId);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
      {/* Birdseye Control Bar */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          background: 'rgba(0, 240, 255, 0.04)',
          border: '1px solid rgba(0, 240, 255, 0.25)',
          borderRadius: 6,
          padding: '10px 16px',
          flexWrap: 'wrap',
          gap: 10,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <span style={{ fontSize: 18 }}>🦅</span>
          <div>
            <div style={{ fontSize: 10, color: '#00f0ff', letterSpacing: 2, fontFamily: 'var(--font-mono)' }}>
              FRIGATE-GRADE SMART COMPOSITE
            </div>
            <div style={{ fontSize: 13, fontWeight: 800, color: '#fff' }}>
              Dynamic Birdseye Threat Spotlight Mode
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          {/* Auto-cycle toggle */}
          <button
            className={`btn btn-sm ${autoCycle ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => setAutoCycle(!autoCycle)}
            style={{ fontSize: 11 }}
          >
            {autoCycle ? `⟳ Auto-Patrol (${cycleSeconds}s)` : '⏸ Patrol Paused'}
          </button>

          <button
            className="btn btn-sm btn-secondary"
            onClick={() => setShowPTZ(!showPTZ)}
            style={{ fontSize: 11, borderColor: '#00f0ff', color: '#00f0ff' }}
          >
            🕹️ {showPTZ ? 'Hide PTZ Controls' : 'Show PTZ Controls'}
          </button>

          <button
            className="btn btn-sm btn-secondary"
            onClick={() => onOpenZoneStudio(activeCam.id)}
            style={{ fontSize: 11 }}
          >
            📐 Calibrate Zones
          </button>

          {highestThreatIncident && onScrambleQrt && (
            <button
              className="btn btn-sm btn-danger"
              onClick={() => onScrambleQrt(highestThreatIncident)}
              style={{ fontSize: 11, fontWeight: 800, background: '#ff2a55' }}
            >
              ⚡ Scramble QRT Strike
            </button>
          )}
        </div>
      </div>

      {/* Main Birdseye Layout: Large Spotlight + Side Standby Strip */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 340px', gap: 14 }}>
        {/* Featured Viewport */}
        <div
          style={{
            position: 'relative',
            background: '#040712',
            border: `2px solid ${highestThreatCamId === activeCam.id ? '#ff2a55' : 'rgba(0, 240, 255, 0.4)'}`,
            borderRadius: 8,
            overflow: 'hidden',
            boxShadow:
              highestThreatCamId === activeCam.id
                ? '0 0 35px rgba(255, 42, 85, 0.3)'
                : '0 0 25px rgba(0, 240, 255, 0.15)',
          }}
        >
          {/* Reticle / Corner Brackets */}
          <div
            style={{
              position: 'absolute',
              top: 14,
              left: 14,
              width: 24,
              height: 24,
              borderTop: '2px solid #00f0ff',
              borderLeft: '2px solid #00f0ff',
              zIndex: 10,
              pointerEvents: 'none',
            }}
          />
          <div
            style={{
              position: 'absolute',
              top: 14,
              right: 14,
              width: 24,
              height: 24,
              borderTop: '2px solid #00f0ff',
              borderRight: '2px solid #00f0ff',
              zIndex: 10,
              pointerEvents: 'none',
            }}
          />
          <div
            style={{
              position: 'absolute',
              bottom: 14,
              left: 14,
              width: 24,
              height: 24,
              borderBottom: '2px solid #00f0ff',
              borderLeft: '2px solid #00f0ff',
              zIndex: 10,
              pointerEvents: 'none',
            }}
          />
          <div
            style={{
              position: 'absolute',
              bottom: 14,
              right: 14,
              width: 24,
              height: 24,
              borderBottom: '2px solid #00f0ff',
              borderRight: '2px solid #00f0ff',
              zIndex: 10,
              pointerEvents: 'none',
            }}
          />

          {/* HUD Top Bar */}
          <div
            style={{
              position: 'absolute',
              top: 0,
              left: 0,
              right: 0,
              padding: '10px 16px',
              background: 'linear-gradient(to bottom, rgba(2, 6, 14, 0.88), transparent)',
              zIndex: 15,
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <span
                style={{
                  display: 'inline-block',
                  width: 8,
                  height: 8,
                  borderRadius: '50%',
                  background: '#00ff9d',
                  boxShadow: '0 0 8px #00ff9d',
                }}
              />
              <span style={{ fontSize: 13, fontWeight: 800, color: '#fff', letterSpacing: 0.5 }}>
                {activeCam.name}
              </span>
              <span style={{ fontSize: 11, color: '#00f0ff', fontFamily: 'var(--font-mono)' }}>
                {activeCam.bop}
              </span>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              {highestThreatCamId === activeCam.id && (
                <span
                  style={{
                    fontSize: 10,
                    fontWeight: 800,
                    background: '#ff2a55',
                    color: '#fff',
                    padding: '2px 8px',
                    borderRadius: 3,
                    letterSpacing: 1,
                    animation: 'pulse 1.5s infinite',
                  }}
                >
                  🚨 ACTIVE THREAT LOCK
                </span>
              )}
              <span style={{ fontSize: 10, color: 'var(--text-ghost)', fontFamily: 'var(--font-mono)' }}>
                {activeCam.resolution || '1280x720'} • {activeCam.fps} FPS
              </span>
            </div>
          </div>

          {/* Video Canvas */}
          <div style={{ width: '100%', aspectRatio: '16/9' }}>
            <WebSocketVideoCanvas
              cameraId={activeCam.id}
              cameraName={activeCam.name}
              bop={activeCam.bop}
              fps={activeCam.fps}
              resolution={activeCam.resolution}
              status={activeCam.status}
              isMuted={false}
            />
          </div>

          {/* Collapsible PTZ Overlay Drawer */}
          {showPTZ && (
            <div
              style={{
                position: 'absolute',
                bottom: 12,
                left: 12,
                zIndex: 30,
                background: 'rgba(3, 7, 16, 0.94)',
                border: '1px solid rgba(0, 240, 255, 0.4)',
                borderRadius: 6,
                padding: 10,
                boxShadow: '0 4px 20px rgba(0,0,0,0.8)',
              }}
            >
              <PTZController cameraId={activeCam.id} cameraName={activeCam.name} />
            </div>
          )}
        </div>

        {/* Standby Cameras Thumbnail Strip */}
        <div
          style={{
            display: 'flex',
            flexDirection: 'column',
            gap: 10,
            maxHeight: 600,
            overflowY: 'auto',
            paddingRight: 4,
          }}
        >
          <div
            style={{
              fontSize: 11,
              fontWeight: 700,
              color: 'var(--text-secondary)',
              letterSpacing: 1,
              padding: '0 4px',
            }}
          >
            STANDBY PERIMETER NODES ({standbyCameras.length})
          </div>

          {standbyCameras.map((cam) => {
            const hasThreat = incidents.some(
              (i) => i.camera_id === cam.id && (i.status === 'NEW' || i.status === 'ACKNOWLEDGED')
            );
            return (
              <div
                key={cam.id}
                onClick={() => {
                  setActiveCamId(cam.id);
                  setAutoCycle(false);
                }}
                style={{
                  background: '#040816',
                  border: `1px solid ${hasThreat ? '#ff2a55' : 'rgba(255, 255, 255, 0.1)'}`,
                  borderRadius: 6,
                  overflow: 'hidden',
                  cursor: 'pointer',
                  transition: 'all 0.15s ease',
                }}
              >
                {/* Mini Header */}
                <div
                  style={{
                    padding: '6px 10px',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    background: 'rgba(255, 255, 255, 0.02)',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                    <span
                      style={{
                        width: 6,
                        height: 6,
                        borderRadius: '50%',
                        background: cam.status === 'ONLINE' ? '#00ff9d' : '#ff2a55',
                      }}
                    />
                    <b style={{ fontSize: 11, color: '#fff' }}>{cam.name}</b>
                  </div>
                  <span style={{ fontSize: 9, color: 'var(--text-ghost)', fontFamily: 'var(--font-mono)' }}>
                    {cam.bop}
                  </span>
                </div>

                {/* Mini Video Feed */}
                <div style={{ width: '100%', aspectRatio: '16/9', pointerEvents: 'none' }}>
                  <WebSocketVideoCanvas
                    cameraId={cam.id}
                    cameraName={cam.name}
                    bop={cam.bop}
                    fps={cam.fps}
                    resolution={cam.resolution}
                    status={cam.status}
                    isMuted={true}
                  />
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
