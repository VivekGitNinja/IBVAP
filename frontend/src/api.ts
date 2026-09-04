/* IBVAP API client */

function getApiBase(): string {
  if (import.meta.env.VITE_API_URL) {
    return `${import.meta.env.VITE_API_URL.replace(/\/$/, '')}/api/v1`;
  }
  // Relative /api/v1 routes seamlessly through Vite proxy on port 5173 and FastAPI on port 8001
  return '/api/v1';
}

const BASE = getApiBase();

async function request<T>(path: string, opts?: RequestInit): Promise<T> {
  const token = localStorage.getItem('ibvap_token');
  const headers: Record<string, string> = { ...(opts?.headers as Record<string, string> || {}) };
  if (token) headers['Authorization'] = `Bearer ${token}`;
  const res = await fetch(BASE + path, { ...opts, headers });
  if (!res.ok) {
    const err = await res.text();
    throw new Error(`API ${res.status}: ${err}`);
  }
  return res.json();
}

function post<T>(path: string, body?: any): Promise<T> {
  const headers: Record<string, string> = {};
  if (body) headers['Content-Type'] = 'application/json';
  return request<T>(path, {
    method: 'POST',
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });
}

function get<T>(path: string): Promise<T> { return request<T>(path); }

export const api = {
  // Auth
  login: (u: string, p: string) => {
    const form = new URLSearchParams();
    form.append('username', u);
    form.append('password', p);
    return request<{ access_token: string; token_type: string }>('/auth/token', {
      method: 'POST', body: form,
    });
  },
  me: () => get<{ id: number; username: string; role: string }>('/auth/me'),

  // Status
  status: () => get<any>('/status'),
  health: () => get<any>('/health'),
  healthDetailed: () => get<any>('/health/detailed'),
  metrics: () => get<any>('/metrics'),

  // Cameras
  cameras: () => get<any[]>('/cameras'),
  camera: (id: number) => get<any>(`/cameras/${id}`),
  createCamera: (d: any) => post<any>('/cameras', d),
  updateCamera: (id: number, d: any) => request<any>(`/cameras/${id}`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(d) }),
  deleteCamera: (id: number) => request<any>(`/cameras/${id}`, { method: 'DELETE' }),
  disconnectCamera: (id: number) => post<any>(`/cameras/${id}/disconnect`),
  cameraHealth: (id: number) => get<any[]>(`/cameras/${id}/health`),
  cameraBrands: () => get<any[]>('/cameras/brands'),
  networkInfo: () => get<any>('/cameras/network-info'),
  discoverCameras: (range?: string) => post<any[]>('/cameras/discover', { ip_range: range || '', start: 1, end: 254 }),
  smartProbe: (ip: string, user?: string, pass?: string, brand?: string) => post<any>('/cameras/smart-probe', { ip, username: user || 'admin', password: pass || '', brand: brand || 'auto' }),
  testStream: (url: string, brand?: string, user?: string, pass?: string) => post<any>('/cameras/test-stream', { stream_url: url, brand: brand || 'generic', username: user || 'admin', password: pass || '' }),
  uploadPhoneFrame: (camId: string, imageB64: string) => post<any>(`/cameras/phone-stream/${camId}/frame`, { image: imageB64 }),
  startAllPipelines: () => post<any>('/cameras/pipeline/start-all'),
  powerOffAllHardware: () => post<any>('/cameras/hardware/power-off-all'),

  // Zones
  zones: (cameraId?: number) => get<any[]>(cameraId ? `/zones?camera_id=${cameraId}` : '/zones'),
  createZone: (d: any) => post<any>('/zones', d),
  deleteZone: (id: number) => request<any>(`/zones/${id}`, { method: 'DELETE' }),

  // Incidents
  incidents: (status?: string, severity?: string) => {
    let q = '/incidents?';
    if (status) q += `status=${status}&`;
    if (severity) q += `severity=${severity}&`;
    return get<any[]>(q);
  },
  incident: (id: number) => get<any>(`/incidents/${id}`),
  acknowledgeIncident: (id: number) => post<any>(`/incidents/${id}/acknowledge`),
  escalateIncident: (id: number) => post<any>(`/incidents/${id}/escalate`),
  dismissIncident: (id: number) => post<any>(`/incidents/${id}/dismiss`),
  closeIncident: (id: number) => post<any>(`/incidents/${id}/close`),
  incidentTimeline: (id: number) => get<any>(`/incidents/${id}/timeline`),

  // Alerts
  alerts: (status?: string) => get<any[]>(status ? `/incidents/alerts?status=${status}` : '/incidents/alerts'),

  // Evidence
  evidence: (incidentId: number) => get<any[]>(`/evidence/${incidentId}`),
  verifyEvidence: (id: number) => get<any>(`/evidence/verify/${id}`),
  verifyChain: (incidentId: number) => get<any>(`/evidence/chain/${incidentId}`),
  certificate: (id: number) => get<any>(`/evidence/certificate/${id}`),

  // Events
  events: (cameraId?: number, limit?: number) => {
    let q = '/events?';
    if (cameraId) q += `camera_id=${cameraId}&`;
    if (limit) q += `limit=${limit}&`;
    return get<any[]>(q);
  },

  // Audit
  audit: (limit?: number) => get<any[]>(`/audit?limit=${limit || 100}`),
  verifyAuditChain: () => get<any>('/audit/verify'),

  // Sync
  syncStatus: () => get<any>('/sync/status'),

  // Demo
  demoScenarios: () => get<any[]>('/demo/scenarios'),
  demoSeed: (scenario?: string) => post<any>(`/demo/seed?scenario=${scenario || 'intrusion'}`),
  demoSeedAll: () => post<any>('/demo/seed/all'),

  // ANPR Checkpost Terminal
  anprPlates: (status?: string, bop?: string, search?: string) => {
    let q = '/anpr/plates?';
    if (status) q += `status=${status}&`;
    if (bop) q += `bop=${encodeURIComponent(bop)}&`;
    if (search) q += `search=${encodeURIComponent(search)}&`;
    return get<any[]>(q);
  },
  anprScan: (d: any) => post<any>('/anpr/scan', d),
  anprWatchlist: () => get<any[]>('/anpr/watchlist'),
  addAnprWatchlist: (d: any) => post<any>('/anpr/watchlist', d),
  toggleBarrier: () => post<any>('/anpr/barrier/toggle'),
  anprStats: () => get<any>('/anpr/stats'),

  // FRS Facial Recognition Watchlist
  frsWatchlist: (threatLevel?: string) => get<any[]>(threatLevel ? `/frs/watchlist?threat_level=${threatLevel}` : '/frs/watchlist'),
  enrollSuspect: (d: any) => post<any>('/frs/watchlist', d),
  frsMatches: () => get<any[]>('/frs/matches'),
  verifyFaceMatch: (matchId: number, confirm: boolean) => post<any>(`/frs/matches/${matchId}/verify?confirm=${confirm}`),
  frsStats: () => get<any>('/frs/stats'),

  // QRT Tactical Dispatch Center
  qrtTeams: () => get<any[]>('/qrt/teams'),
  dispatchQrt: (d: any) => post<any>('/qrt/dispatch', d),
  updateQrtStatus: (d: any) => post<any>('/qrt/status', d),
  qrtLogs: () => get<any[]>('/qrt/logs'),
  broadcastRadio: (d: any) => post<any>('/qrt/radio/broadcast', d),
};
