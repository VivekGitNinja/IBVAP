import React, { useState, useEffect } from 'react';
import { api } from '../api';

interface Props {
  cameraId: number;
  cameraName: string;
  onClose?: () => void;
}

export const PTZController: React.FC<Props> = ({ cameraId, cameraName, onClose }) => {
  const [speed, setSpeed] = useState(0.5);
  const [presets, setPresets] = useState<any[]>([]);
  const [currentPreset, setCurrentPreset] = useState('HOME');
  const [lastAction, setLastAction] = useState<string>('READY');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    api.ptzPresets(cameraId)
      .then((res) => {
        if (res.presets) setPresets(res.presets);
        if (res.current_preset) setCurrentPreset(res.current_preset);
      })
      .catch(() => {});
  }, [cameraId]);

  const sendCommand = async (direction: string) => {
    setLastAction(direction.toUpperCase());
    try {
      const res = await api.ptzCommand(cameraId, direction, speed);
      if (res.ptz_state?.preset) {
        setCurrentPreset(res.ptz_state.preset);
      }
    } catch {
      setLastAction('ERR');
    }
  };

  const handleGotoPreset = async (presetId: string) => {
    setLoading(true);
    setLastAction(`GOTO ${presetId}`);
    try {
      await api.ptzGoto(cameraId, presetId);
      setCurrentPreset(presetId);
    } catch {
      setLastAction('PRESET ERR');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      className="ptz-tactical-controller"
      style={{
        background: 'rgba(5, 15, 20, 0.95)',
        border: '1px solid #00f0ff',
        boxShadow: '0 0 20px rgba(0, 240, 255, 0.25)',
        borderRadius: 6,
        padding: 12,
        color: '#c0e0e8',
        fontFamily: 'monospace',
        width: 260,
        position: 'relative',
        zIndex: 10,
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8, borderBottom: '1px solid rgba(0, 240, 255, 0.2)', paddingBottom: 6 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <span style={{ width: 8, height: 8, borderRadius: '50%', background: '#00ff9d', boxShadow: '0 0 8px #00ff9d' }} />
          <span style={{ fontSize: 12, fontWeight: 'bold', color: '#00f0ff' }}>PTZ JOYSTICK // {cameraName.split(' ')[0]}</span>
        </div>
        {onClose && (
          <button
            onClick={onClose}
            style={{
              background: 'transparent',
              border: 'none',
              color: '#ff2a55',
              cursor: 'pointer',
              fontWeight: 'bold',
              fontSize: 14,
            }}
          >
            ✕
          </button>
        )}
      </div>

      {/* Cross D-Pad */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 4, width: 140, margin: '8px auto' }}>
        <div />
        <button
          className="btn btn-sm"
          onClick={() => sendCommand('up')}
          style={{ background: 'rgba(0, 240, 255, 0.15)', border: '1px solid #00f0ff', color: '#00f0ff', height: 36 }}
          title="Tilt Up"
        >
          ▲
        </button>
        <div />

        <button
          className="btn btn-sm"
          onClick={() => sendCommand('left')}
          style={{ background: 'rgba(0, 240, 255, 0.15)', border: '1px solid #00f0ff', color: '#00f0ff', height: 36 }}
          title="Pan Left"
        >
          ◀
        </button>
        <button
          className="btn btn-sm"
          onClick={() => sendCommand('home')}
          style={{ background: 'rgba(0, 255, 157, 0.2)', border: '1px solid #00ff9d', color: '#00ff9d', height: 36, fontSize: 10 }}
          title="Reset to Center"
        >
          HOME
        </button>
        <button
          className="btn btn-sm"
          onClick={() => sendCommand('right')}
          style={{ background: 'rgba(0, 240, 255, 0.15)', border: '1px solid #00f0ff', color: '#00f0ff', height: 36 }}
          title="Pan Right"
        >
          ▶
        </button>

        <div />
        <button
          className="btn btn-sm"
          onClick={() => sendCommand('down')}
          style={{ background: 'rgba(0, 240, 255, 0.15)', border: '1px solid #00f0ff', color: '#00f0ff', height: 36 }}
          title="Tilt Down"
        >
          ▼
        </button>
        <div />
      </div>

      {/* Zoom Bar */}
      <div style={{ display: 'flex', gap: 6, margin: '8px 0', alignItems: 'center' }}>
        <button
          className="btn btn-sm"
          onClick={() => sendCommand('zoom_in')}
          style={{ flex: 1, background: 'rgba(0, 240, 255, 0.15)', border: '1px solid #00f0ff', color: '#00f0ff', fontSize: 11 }}
        >
          🔍 ZOOM +
        </button>
        <button
          className="btn btn-sm"
          onClick={() => sendCommand('zoom_out')}
          style={{ flex: 1, background: 'rgba(0, 240, 255, 0.15)', border: '1px solid #00f0ff', color: '#00f0ff', fontSize: 11 }}
        >
          🔍 ZOOM −
        </button>
      </div>

      {/* Speed Slider */}
      <div style={{ margin: '8px 0', fontSize: 10 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', color: '#7095a5', marginBottom: 2 }}>
          <span>SLEW SPEED:</span>
          <span style={{ color: '#00f0ff' }}>{(speed * 100).toFixed(0)}%</span>
        </div>
        <input
          type="range"
          min="0.1"
          max="1.0"
          step="0.1"
          value={speed}
          onChange={(e) => setSpeed(parseFloat(e.target.value))}
          style={{ width: '100%', accentColor: '#00f0ff' }}
        />
      </div>

      {/* Tactical Presets */}
      <div style={{ marginTop: 6, fontSize: 10 }}>
        <div style={{ color: '#7095a5', marginBottom: 4 }}>TACTICAL PRESETS:</div>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
          {presets.map((p) => (
            <button
              key={p.id}
              onClick={() => handleGotoPreset(p.id)}
              disabled={loading}
              className={`btn btn-sm ${currentPreset === p.id ? 'btn-primary' : 'btn-secondary'}`}
              style={{
                fontSize: 9,
                padding: '2px 6px',
                flex: '1 1 45%',
                background: currentPreset === p.id ? 'rgba(0, 255, 157, 0.25)' : 'rgba(20, 40, 50, 0.6)',
                borderColor: currentPreset === p.id ? '#00ff9d' : 'rgba(0, 240, 255, 0.3)',
                color: currentPreset === p.id ? '#00ff9d' : '#8ab0be',
              }}
            >
              {p.id}
            </button>
          ))}
        </div>
      </div>

      {/* Status Footer */}
      <div style={{ marginTop: 8, paddingTop: 4, borderTop: '1px solid rgba(0, 240, 255, 0.1)', fontSize: 9, display: 'flex', justifyContent: 'space-between', color: '#557585' }}>
        <span>LAST CMD: <b style={{ color: '#00ff9d' }}>{lastAction}</b></span>
        <span>PROTOCOL: <b style={{ color: '#00f0ff' }}>ONVIF PROFILE S</b></span>
      </div>
    </div>
  );
};
