import React, { useEffect, useState, useRef } from 'react';
import { api } from '../api';
import type { Camera, Incident } from '../types';
import { playTacticalTone } from '../utils/audio';

export interface MapData {
  status: string;
  cameras: {
    id: number;
    name: string;
    bop: string;
    sector: string;
    latitude: number;
    longitude: number;
    status: string;
    health_score: number;
    stream_url: string;
    fps: number;
    bearing?: number;
  }[];
  incidents: {
    id: number;
    incident_code: string;
    title: string;
    severity: string;
    threat_score: number;
    confidence: number;
    zone_name: string;
    camera_id?: number;
    latitude: number;
    longitude: number;
    evidence_snapshot?: string;
    sha256?: string;
    created_at: string;
  }[];
  sectors: {
    sector: string;
    total_cameras: number;
    online_cameras: number;
    incidents: number;
  }[];
  summary: {
    total_cameras: number;
    online_cameras: number;
    open_incidents: number;
  };
}

export type TileLayerType = 'local' | 'esri' | 'osm' | 'grid';

export function getTileLayerConfig(layerType: TileLayerType): { url: string; maxZoom: number; isGrid: boolean } {
  if (layerType === 'local') {
    return { url: '/tiles/{z}/{x}/{y}.png', maxZoom: 18, isGrid: false };
  }
  if (layerType === 'esri') {
    return {
      url: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
      maxZoom: 19,
      isGrid: false,
    };
  }
  if (layerType === 'osm') {
    return { url: 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', maxZoom: 19, isGrid: false };
  }
  return { url: '', maxZoom: 19, isGrid: true };
}

interface MapViewProps {
  onSelectIncident?: (incidentId: number) => void;
  onSelectCamera?: (cameraId: number) => void;
  initialLat?: number;
  initialLng?: number;
  initialZoom?: number;
}

export function MapView({ onSelectIncident, onSelectCamera, initialLat, initialLng, initialZoom }: MapViewProps) {
  const [data, setData] = useState<MapData | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedCamera, setSelectedCamera] = useState<any | null>(null);
  const [selectedIncident, setSelectedIncident] = useState<any | null>(null);
  const [selectedSector, setSelectedSector] = useState<string>('ALL');
  const [tileSource, setTileSource] = useState<TileLayerType>('esri');
  const [tileError, setTileError] = useState(false);
  const [forceGrid, setForceGrid] = useState(false);

  // Coordinate editing state
  const [isEditingCoords, setIsEditingCoords] = useState(false);
  const [editLat, setEditLat] = useState('28.6139');
  const [editLng, setEditLng] = useState('77.2090');
  const [editSector, setEditSector] = useState('Sector Alpha');

  const mapContainerRef = useRef<HTMLDivElement>(null);
  const leafletMapRef = useRef<any>(null);

  const loadData = async () => {
    try {
      setLoading(true);
      const res = await api.getMapData();
      setData(res);
    } catch (err) {
      console.error('Failed to load map data:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 10000);
    return () => clearInterval(interval);
  }, []);

  // Initialize Leaflet map if possible and not forcing grid
  useEffect(() => {
    if (forceGrid || !data || !mapContainerRef.current) return;

    let mapInstance: any = null;

    async function initLeaflet() {
      try {
        const L = (await import('leaflet')).default;

        if (leafletMapRef.current) {
          leafletMapRef.current.remove();
          leafletMapRef.current = null;
        }

        // Center on average of cameras or default border coordinates
        let centerLat = initialLat || 28.6139;
        let centerLng = initialLng || 77.2090;
        const validCams = data?.cameras.filter((c) => c.latitude !== 0 && c.longitude !== 0) || [];
        if (!initialLat && validCams.length > 0) {
          centerLat = validCams.reduce((sum, c) => sum + c.latitude, 0) / validCams.length;
          centerLng = validCams.reduce((sum, c) => sum + c.longitude, 0) / validCams.length;
        }

        const map = L.map(mapContainerRef.current!, {
          center: [centerLat, centerLng],
          zoom: initialZoom || 13,
          zoomControl: true,
          attributionControl: false,
        });

        // Layer selection with offline priority fallback
        const cfg = getTileLayerConfig(tileSource);
        if (!cfg.isGrid) {
          const tileLayer = L.tileLayer(cfg.url, {
            maxZoom: cfg.maxZoom,
            timeout: 4000,
          });

          tileLayer.on('tileerror', () => {
            console.warn(`Tile load failed for source: ${tileSource}. Degrading fallback.`);
            setTileError(true);
            if (tileSource === 'local') setTileSource('esri');
            else if (tileSource === 'esri') setTileSource('osm');
            else if (tileSource === 'osm') setForceGrid(true);
          });

          tileLayer.addTo(map);
        } else {
          setForceGrid(true);
          return;
        }

        // Add Camera Markers with FOV Direction Cones (Task 4.3)
        data?.cameras.forEach((cam) => {
          if (selectedSector !== 'ALL' && cam.sector !== selectedSector) return;

          const lat = cam.latitude || (28.6139 + (cam.id * 0.005));
          const lng = cam.longitude || (77.2090 + (cam.id * 0.005));
          const bearing = cam.bearing ?? 0;
          const isOnline = cam.status === 'ONLINE';

          const markerHtml = `
            <div style="position: relative; width: 34px; height: 34px; display: flex; align-items: center; justify-content: center; cursor: pointer;">
              <!-- Directional FOV Cone -->
              <svg style="position: absolute; width: 48px; height: 48px; transform: rotate(${bearing}deg); pointer-events: none; z-index: 1;" viewBox="0 0 100 100">
                <path d="M50 50 L20 8 A50 50 0 0 1 80 8 Z" fill="rgba(0, 240, 255, 0.3)" stroke="#00f0ff" stroke-width="1.5" stroke-dasharray="2,2"/>
              </svg>
              <!-- Center Camera Pin -->
              <div style="
                position: relative;
                z-index: 2;
                background: ${isOnline ? '#10b981' : '#f59e0b'};
                color: #000;
                width: 22px;
                height: 22px;
                border-radius: 50%;
                border: 2px solid #ffffff;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 10px;
                font-weight: bold;
                box-shadow: 0 0 10px ${isOnline ? '#10b981' : '#f59e0b'};
              ">
                ${cam.id}
              </div>
            </div>
          `;

          const customIcon = L.divIcon({
            html: markerHtml,
            className: 'tactical-cam-marker',
            iconSize: [34, 34],
            iconAnchor: [17, 17],
          });

          const marker = L.marker([lat, lng], { icon: customIcon }).addTo(map);
          marker.on('click', () => {
            playTacticalTone('click');
            setSelectedCamera(cam);
            setSelectedIncident(null);
          });
        });

        // Add Pulsing Threat Incident Markers (Task 4.3)
        data?.incidents.forEach((inc) => {
          const lat = inc.latitude || 28.6150;
          const lng = inc.longitude || 77.2100;

          const incHtml = `
            <div style="position: relative; width: 28px; height: 28px; display: flex; align-items: center; justify-content: center; cursor: pointer;">
              <span style="position: absolute; width: 100%; height: 100%; border-radius: 50%; background: rgba(239, 68, 68, 0.4); animation: pulse 1.5s infinite;"></span>
              <span style="width: 14px; height: 14px; border-radius: 50%; background: #ef4444; border: 2px solid #fff; box-shadow: 0 0 8px #ef4444;"></span>
            </div>
          `;

          const incIcon = L.divIcon({
            html: incHtml,
            className: 'tactical-inc-marker',
            iconSize: [28, 28],
            iconAnchor: [14, 14],
          });

          const marker = L.marker([lat, lng], { icon: incIcon }).addTo(map);
          marker.on('click', () => {
            playTacticalTone('alert');
            setSelectedIncident(inc);
            setSelectedCamera(null);
          });
        });

        leafletMapRef.current = map;
        mapInstance = map;
      } catch (e) {
        console.warn('Leaflet load failed, using offline tactical grid fallback:', e);
        setTileError(true);
      }
    }

    initLeaflet();

    return () => {
      if (mapInstance) {
        mapInstance.remove();
      }
    };
  }, [data, forceGrid, selectedSector, tileSource]);

  const handleSaveCoordinates = async () => {
    if (!selectedCamera) return;
    try {
      const lat = parseFloat(editLat);
      const lng = parseFloat(editLng);
      await api.patchCamera(selectedCamera.id, {
        latitude: lat,
        longitude: lng,
        sector: editSector,
      });
      playTacticalTone('click');
      setIsEditingCoords(false);
      loadData();
    } catch (err) {
      alert('Failed to update camera coordinates');
    }
  };

  const filteredCameras = (data?.cameras || []).filter(
    (c) => selectedSector === 'ALL' || c.sector === selectedSector
  );

  return (
    <div className="page" style={{ height: 'calc(100vh - 64px)', display: 'flex', flexDirection: 'column' }}>
      {/* Top Header Strip */}
      <div className="page-header" style={{ marginBottom: 8, paddingBottom: 8 }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <h1 style={{ margin: 0, fontSize: 18 }}>Geospatial Situational Awareness Map</h1>
            <span
              className="page-tag"
              style={{
                background: forceGrid ? 'rgba(255, 170, 0, 0.15)' : 'rgba(0, 240, 255, 0.15)',
                borderColor: forceGrid ? '#ffaa00' : '#00f0ff',
                color: forceGrid ? '#ffaa00' : '#00f0ff',
                fontWeight: 'bold',
              }}
            >
              {forceGrid ? '⚡ SCHEMATIC TACTICAL GRID' : `🛰 ${tileSource.toUpperCase()} BASEMAP`}
            </span>
          </div>
          <p style={{ margin: '2px 0 0', fontSize: 11, color: 'var(--text-secondary)' }}>
            Real-time geospatial deployment matrix with FOV bearing cones, sector boundaries, and BSA §63 incidents
          </p>
        </div>

        {/* Layer Controls & Actions */}
        <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
          {/* Base Layer Switcher (Task 4.1) */}
          <div style={{ display: 'flex', background: '#090e17', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 4, padding: 2 }}>
            <button
              onClick={() => { setForceGrid(false); setTileSource('esri'); }}
              style={{
                background: !forceGrid && tileSource === 'esri' ? 'rgba(0, 240, 255, 0.2)' : 'transparent',
                color: !forceGrid && tileSource === 'esri' ? '#00f0ff' : '#94a3b8',
                border: 'none',
                padding: '4px 8px',
                fontSize: 10,
                cursor: 'pointer',
                borderRadius: 3,
                fontWeight: 600,
              }}
              title="Esri Aerial Satellite Imagery (Default)"
            >
              🛰 Esri Satellite
            </button>
            <button
              onClick={() => { setForceGrid(false); setTileSource('local'); }}
              style={{
                background: !forceGrid && tileSource === 'local' ? 'rgba(0, 240, 255, 0.2)' : 'transparent',
                color: !forceGrid && tileSource === 'local' ? '#00f0ff' : '#94a3b8',
                border: 'none',
                padding: '4px 8px',
                fontSize: 10,
                cursor: 'pointer',
                borderRadius: 3,
                fontWeight: 600,
              }}
              title="Cached Offline Tiles (/tiles/{z}/{x}/{y}.png)"
            >
              💾 Local Cached
            </button>
            <button
              onClick={() => { setForceGrid(false); setTileSource('osm'); }}
              style={{
                background: !forceGrid && tileSource === 'osm' ? 'rgba(0, 240, 255, 0.2)' : 'transparent',
                color: !forceGrid && tileSource === 'osm' ? '#00f0ff' : '#94a3b8',
                border: 'none',
                padding: '4px 8px',
                fontSize: 10,
                cursor: 'pointer',
                borderRadius: 3,
                fontWeight: 600,
              }}
              title="OpenStreetMap Topo Layer"
            >
              🗺 OSM
            </button>
            <button
              onClick={() => setForceGrid(true)}
              style={{
                background: forceGrid ? 'rgba(255, 170, 0, 0.2)' : 'transparent',
                color: forceGrid ? '#ffaa00' : '#94a3b8',
                border: 'none',
                padding: '4px 8px',
                fontSize: 10,
                cursor: 'pointer',
                borderRadius: 3,
                fontWeight: 600,
              }}
              title="Air-Gapped Dark Tactical Schematic Grid"
            >
              ⚡ Dark Grid
            </button>
          </div>

          {/* Sector Filter */}
          <select
            value={selectedSector}
            onChange={(e) => setSelectedSector(e.target.value)}
            style={{
              background: '#090e17',
              border: '1px solid rgba(255,255,255,0.15)',
              color: '#fff',
              padding: '4px 8px',
              fontSize: 11,
              borderRadius: 4,
            }}
          >
            <option value="ALL">All Sectors ({data?.cameras.length || 0})</option>
            {(data?.sectors || []).map((s) => (
              <option key={s.sector} value={s.sector}>
                {s.sector} ({s.total_cameras})
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Main Map Container */}
      <div style={{ flex: 1, display: 'flex', position: 'relative', overflow: 'hidden', borderRadius: 6, border: '1px solid rgba(0, 240, 255, 0.2)' }}>
        <div style={{ flex: 1, position: 'relative' }}>
          {forceGrid ? (
            /* Tactical Schematic Dark Grid Fallback */
            <div
              style={{
                width: '100%',
                height: '100%',
                background: '#070c16',
                position: 'relative',
                overflow: 'hidden',
              }}
            >
              <div
                style={{
                  position: 'absolute',
                  inset: 0,
                  backgroundImage:
                    'radial-gradient(#1e293b 1px, transparent 1px), radial-gradient(#1e293b 1px, #070c16 1px)',
                  backgroundSize: '40px 40px',
                  backgroundPosition: '0 0, 20px 20px',
                  opacity: 0.6,
                }}
              />
              {/* Tactical Radar Rings */}
              <div
                style={{
                  position: 'absolute',
                  top: '50%',
                  left: '50%',
                  transform: 'translate(-50%, -50%)',
                  width: '400px',
                  height: '400px',
                  borderRadius: '50%',
                  border: '1px dashed rgba(0,240,255,0.2)',
                  pointerEvents: 'none',
                }}
              />
              <div
                style={{
                  position: 'absolute',
                  top: '50%',
                  left: '50%',
                  transform: 'translate(-50%, -50%)',
                  width: '200px',
                  height: '200px',
                  borderRadius: '50%',
                  border: '1px dashed rgba(0,240,255,0.3)',
                  pointerEvents: 'none',
                }}
              />
              <div
                style={{
                  position: 'absolute',
                  top: 12,
                  left: 12,
                  background: 'rgba(15,23,42,0.85)',
                  padding: '6px 12px',
                  borderRadius: '4px',
                  border: '1px solid #00f0ff',
                  fontSize: '11px',
                  color: '#00f0ff',
                  fontFamily: 'monospace',
                }}
              >
                📡 OFFLINE TACTICAL SCHEMATIC GRID — AIR-GAPPED DEPLOYMENT
              </div>

              {/* Cameras Placed on Relative Tactical Plane */}
              {filteredCameras.map((cam, idx) => {
                const total = filteredCameras.length || 1;
                const angle = (idx / total) * Math.PI * 2;
                const radius = 140;
                const x = 50 + (Math.cos(angle) * radius) / 5;
                const y = 50 + (Math.sin(angle) * radius) / 5;
                const isOnline = cam.status === 'ONLINE';

                return (
                  <div
                    key={cam.id}
                    onClick={() => {
                      playTacticalTone('click');
                      setSelectedCamera(cam);
                      setSelectedIncident(null);
                    }}
                    style={{
                      position: 'absolute',
                      top: `${Math.max(10, Math.min(90, y))}%`,
                      left: `${Math.max(10, Math.min(90, x))}%`,
                      transform: 'translate(-50%, -50%)',
                      cursor: 'pointer',
                      display: 'flex',
                      flexDirection: 'column',
                      alignItems: 'center',
                      zIndex: 10,
                    }}
                  >
                    <div
                      style={{
                        width: '26px',
                        height: '26px',
                        borderRadius: '50%',
                        background: isOnline ? '#10b981' : '#f59e0b',
                        border: '2px solid #fff',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        fontWeight: 'bold',
                        fontSize: '11px',
                        color: '#000',
                        boxShadow: `0 0 12px ${isOnline ? '#10b981' : '#f59e0b'}`,
                      }}
                    >
                      {cam.id}
                    </div>
                    <div
                      style={{
                        fontSize: '10px',
                        color: '#e2e8f0',
                        background: 'rgba(0,0,0,0.7)',
                        padding: '1px 6px',
                        borderRadius: '3px',
                        marginTop: '2px',
                        whiteSpace: 'nowrap',
                      }}
                    >
                      {cam.name}
                    </div>
                  </div>
                );
              })}

              {/* Incidents on Schematic Plane */}
              {(data?.incidents || []).map((inc, i) => (
                <div
                  key={inc.id}
                  onClick={() => {
                    playTacticalTone('alert');
                    setSelectedIncident(inc);
                    setSelectedCamera(null);
                  }}
                  style={{
                    position: 'absolute',
                    top: `${30 + i * 12}%`,
                    left: `${40 + i * 15}%`,
                    transform: 'translate(-50%, -50%)',
                    cursor: 'pointer',
                    zIndex: 20,
                  }}
                >
                  <div
                    style={{
                      width: '18px',
                      height: '18px',
                      borderRadius: '50%',
                      background: '#ef4444',
                      border: '2px solid #fff',
                      boxShadow: '0 0 15px #ef4444',
                      animation: 'pulse 1.2s infinite',
                    }}
                  />
                  <div
                    style={{
                      fontSize: '9px',
                      color: '#fca5a5',
                      background: 'rgba(0,0,0,0.85)',
                      padding: '1px 4px',
                      borderRadius: '2px',
                      marginTop: '2px',
                      whiteSpace: 'nowrap',
                    }}
                  >
                    🚨 {inc.incident_code}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            /* Leaflet Map with Active Tile Layer */
            <div ref={mapContainerRef} style={{ width: '100%', height: '100%' }} />
          )}
        </div>

        {/* Tactical Inspector Drawer (Task 4.3) */}
        {(selectedCamera || selectedIncident) && (
          <div
            style={{
              width: '350px',
              background: '#090e17',
              borderLeft: '1px solid rgba(0, 240, 255, 0.2)',
              padding: '16px',
              display: 'flex',
              flexDirection: 'column',
              gap: '12px',
              overflowY: 'auto',
              fontFamily: 'var(--font-mono)',
            }}
          >
            <div
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                borderBottom: '1px solid rgba(255, 255, 255, 0.1)',
                paddingBottom: '8px',
              }}
            >
              <div style={{ fontSize: '12px', fontWeight: 'bold', color: '#00f0ff' }}>
                {selectedCamera ? '📹 CAMERA TELEMETRY' : '🚨 THREAT INCIDENT'}
              </div>
              <button
                onClick={() => {
                  setSelectedCamera(null);
                  setSelectedIncident(null);
                }}
                style={{
                  background: 'transparent',
                  border: 'none',
                  color: '#94a3b8',
                  fontSize: '14px',
                  cursor: 'pointer',
                }}
              >
                ✕
              </button>
            </div>

            {selectedCamera && (
              <>
                <div style={{ fontSize: '14px', fontWeight: 'bold', color: '#fff' }}>{selectedCamera.name}</div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px', fontSize: '11px' }}>
                  <div style={{ background: 'rgba(0,0,0,0.4)', padding: '6px', borderRadius: '4px' }}>
                    <span style={{ color: '#94a3b8' }}>ID:</span> #{selectedCamera.id}
                  </div>
                  <div style={{ background: 'rgba(0,0,0,0.4)', padding: '6px', borderRadius: '4px' }}>
                    <span style={{ color: '#94a3b8' }}>STATUS:</span>{' '}
                    <b style={{ color: selectedCamera.status === 'ONLINE' ? '#10b981' : '#f59e0b' }}>
                      {selectedCamera.status}
                    </b>
                  </div>
                  <div style={{ background: 'rgba(0,0,0,0.4)', padding: '6px', borderRadius: '4px' }}>
                    <span style={{ color: '#94a3b8' }}>SECTOR:</span> {selectedCamera.sector || 'Sector Alpha'}
                  </div>
                  <div style={{ background: 'rgba(0,0,0,0.4)', padding: '6px', borderRadius: '4px' }}>
                    <span style={{ color: '#94a3b8' }}>HEALTH:</span> {selectedCamera.health_score || 100}%
                  </div>
                </div>

                {/* GPS Coordinates & Quick Update */}
                <div style={{ background: 'rgba(0,0,0,0.4)', padding: '10px', borderRadius: '4px', fontSize: '11px' }}>
                  <div style={{ color: '#94a3b8', marginBottom: '4px' }}>GEOGRAPHIC COORDINATES (WGS84):</div>
                  {!isEditingCoords ? (
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <span style={{ color: '#38bdf8', fontFamily: 'monospace' }}>
                        {selectedCamera.latitude !== undefined && selectedCamera.latitude !== null && selectedCamera.latitude !== 0
                          ? `${selectedCamera.latitude.toFixed(4)}° N, ${selectedCamera.longitude?.toFixed(4)}° E`
                          : '-- / --'}
                      </span>
                      <button
                        onClick={() => {
                          setEditLat(String(selectedCamera.latitude || 28.6139));
                          setEditLng(String(selectedCamera.longitude || 77.2090));
                          setEditSector(selectedCamera.sector || 'Sector Alpha');
                          setIsEditingCoords(true);
                        }}
                        style={{
                          background: '#0284c7',
                          color: '#fff',
                          border: 'none',
                          borderRadius: '3px',
                          padding: '3px 8px',
                          fontSize: '10px',
                          cursor: 'pointer',
                        }}
                      >
                        ✏️ Edit GPS
                      </button>
                    </div>
                  ) : (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', marginTop: '6px' }}>
                      <div>
                        <label style={{ color: '#94a3b8', fontSize: '10px' }}>Latitude:</label>
                        <input
                          type="text"
                          value={editLat}
                          onChange={(e) => setEditLat(e.target.value)}
                          style={{
                            width: '100%',
                            background: '#0f172a',
                            border: '1px solid #334155',
                            color: '#fff',
                            padding: '4px',
                            fontSize: '11px',
                            borderRadius: '3px',
                          }}
                        />
                      </div>
                      <div>
                        <label style={{ color: '#94a3b8', fontSize: '10px' }}>Longitude:</label>
                        <input
                          type="text"
                          value={editLng}
                          onChange={(e) => setEditLng(e.target.value)}
                          style={{
                            width: '100%',
                            background: '#0f172a',
                            border: '1px solid #334155',
                            color: '#fff',
                            padding: '4px',
                            fontSize: '11px',
                            borderRadius: '3px',
                          }}
                        />
                      </div>
                      <div>
                        <label style={{ color: '#94a3b8', fontSize: '10px' }}>Sector:</label>
                        <input
                          type="text"
                          value={editSector}
                          onChange={(e) => setEditSector(e.target.value)}
                          style={{
                            width: '100%',
                            background: '#0f172a',
                            border: '1px solid #334155',
                            color: '#fff',
                            padding: '4px',
                            fontSize: '11px',
                            borderRadius: '3px',
                          }}
                        />
                      </div>
                      <div style={{ display: 'flex', gap: '6px', marginTop: '4px' }}>
                        <button
                          onClick={handleSaveCoordinates}
                          style={{
                            flex: 1,
                            background: '#10b981',
                            color: '#000',
                            border: 'none',
                            padding: '4px',
                            borderRadius: '3px',
                            fontWeight: 'bold',
                            fontSize: '10px',
                            cursor: 'pointer',
                          }}
                        >
                          Save
                        </button>
                        <button
                          onClick={() => setIsEditingCoords(false)}
                          style={{
                            flex: 1,
                            background: '#475569',
                            color: '#fff',
                            border: 'none',
                            padding: '4px',
                            borderRadius: '3px',
                            fontSize: '10px',
                            cursor: 'pointer',
                          }}
                        >
                          Cancel
                        </button>
                      </div>
                    </div>
                  )}
                </div>

                {/* Live Snapshot */}
                <div
                  style={{
                    background: '#000',
                    borderRadius: '4px',
                    overflow: 'hidden',
                    height: '140px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    border: '1px solid #334155',
                  }}
                >
                  <img
                    src={`/api/v1/cameras/${selectedCamera.id}/snapshot?t=${Date.now()}`}
                    alt="Camera Live Feed"
                    style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                    onError={(e) => {
                      (e.target as any).style.display = 'none';
                    }}
                  />
                </div>
              </>
            )}

            {selectedIncident && (
              <>
                <div style={{ fontSize: '14px', fontWeight: 'bold', color: '#ff2a55' }}>
                  {selectedIncident.title}
                </div>
                <div style={{ fontSize: '10px', color: '#cbd5e1' }}>
                  CODE: {selectedIncident.incident_code}
                </div>

                {/* Statutory Seal Tag */}
                <div style={{ display: 'flex', gap: 6, margin: '2px 0' }}>
                  <span
                    style={{
                      background: 'rgba(0, 255, 157, 0.15)',
                      color: '#00ff9d',
                      padding: '2px 6px',
                      borderRadius: '3px',
                      border: '1px solid #00ff9d',
                      fontSize: '9px',
                      fontWeight: 'bold',
                    }}
                  >
                    BSA 2023 §63 SEALED
                  </span>
                  {selectedIncident.zone_name && (
                    <span
                      style={{
                        background: 'rgba(0, 240, 255, 0.15)',
                        color: '#00f0ff',
                        padding: '2px 6px',
                        borderRadius: '3px',
                        border: '1px solid #00f0ff',
                        fontSize: '9px',
                      }}
                    >
                      ZONE: {selectedIncident.zone_name}
                    </span>
                  )}
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px', fontSize: '11px' }}>
                  <div style={{ background: 'rgba(0,0,0,0.4)', padding: '6px', borderRadius: '4px' }}>
                    <span style={{ color: '#94a3b8' }}>SEVERITY:</span>{' '}
                    <b style={{ color: '#ff2a55' }}>{selectedIncident.severity}</b>
                  </div>
                  <div style={{ background: 'rgba(0,0,0,0.4)', padding: '6px', borderRadius: '4px' }}>
                    <span style={{ color: '#94a3b8' }}>THREAT:</span> {selectedIncident.threat_score} / 100
                  </div>
                </div>

                {/* Evidence Snapshot */}
                {selectedIncident.evidence_snapshot && (
                  <div style={{ marginTop: '4px' }}>
                    <div style={{ fontSize: '10px', color: '#94a3b8', marginBottom: '4px' }}>
                      EVIDENCE KEYFRAME:
                    </div>
                    <img
                      src={`/${selectedIncident.evidence_snapshot}`}
                      alt="Incident Evidence"
                      style={{
                        width: '100%',
                        height: '130px',
                        objectFit: 'cover',
                        borderRadius: '4px',
                        border: '1px solid #ff2a55',
                      }}
                      onError={(e) => {
                        (e.target as any).style.display = 'none';
                      }}
                    />
                  </div>
                )}

                {/* SHA-256 Digest */}
                <div
                  style={{
                    background: 'rgba(0,0,0,0.5)',
                    padding: '6px',
                    borderRadius: '4px',
                    fontSize: '9px',
                    color: '#00ff9d',
                    wordBreak: 'break-all',
                  }}
                >
                  SHA-256: {selectedIncident.sha256 || '--'}
                </div>

                {onSelectIncident && (
                  <button
                    className="btn btn-sm btn-primary"
                    style={{ marginTop: '6px', width: '100%', padding: '6px' }}
                    onClick={() => onSelectIncident(selectedIncident.id)}
                  >
                    🔍 Inspect Full Evidence Triage
                  </button>
                )}
              </>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
