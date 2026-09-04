/* IBVAP TypeScript type definitions */

export interface Camera {
  id: number;
  name: string;
  stream_url: string;
  location: string;
  bop: string;
  camera_type: string;
  fps: number;
  resolution: string;
  status: string;
  health_score: number;
  last_heartbeat: string | null;
  latitude: number;
  longitude: number;
  analytics_enabled: boolean;
  detection_interval: number;
  description: string;
  active: boolean;
  created_at: string;
  updated_at: string | null;
}

export interface Zone {
  id: number;
  camera_id: number;
  name: string;
  zone_type: string;
  polygon: number[][];
  active: boolean;
  severity: number;
  dwell_threshold_seconds: number;
  color: string;
  description: string;
  created_at: string | null;
}

export interface Incident {
  id: number;
  incident_code: string;
  title: string;
  description: string;
  severity: string;
  threat_score: number;
  confidence: number;
  status: string;
  reason_codes: string[];
  event_ids: number[];
  detection_ids: number[];
  track_ids: number[];
  camera_id: number | null;
  camera_name: string;
  zone_name: string;
  fingerprint: string;
  correlated_ids: number[];
  recommended_action: string;
  ai_assessment: Record<string, any>;
  created_at: string;
  acknowledged_at: string | null;
  acknowledged_by: string | null;
  closed_at: string | null;
  closed_by: string | null;
  escalated_at: string | null;
  escalated_by: string | null;
  timeline: TimelineEvent[];
}

export interface TimelineEvent {
  timestamp: string;
  event_type: string;
  description: string;
  source: string;
  confidence: number | null;
  payload: Record<string, any>;
}

export interface Alert {
  id: number;
  incident_id: number;
  priority: string;
  status: string;
  message: string;
  created_at: string;
  acknowledged_by: string | null;
  acknowledged_at: string | null;
}

export interface Evidence {
  id: number;
  incident_id: number;
  evidence_type: string;
  file_path: string;
  sha256: string;
  manifest_path: string;
  manifest_data: Record<string, any>;
  file_size_bytes: number;
  threat_score: number;
  camera_id: number | null;
  camera_name: string;
  detection_metadata: Record<string, any>;
  created_at: string;
}

export interface AuditLog {
  id: number;
  actor: string;
  actor_role: string;
  action: string;
  target_type: string;
  target_id: string;
  details: Record<string, any>;
  ip_address: string;
  previous_hash: string;
  entry_hash: string;
  created_at: string;
}

export interface DemoScenario {
  id: string;
  name: string;
  description: string;
  severity: string;
}

export interface SystemStatus {
  status: string;
  version: string;
  uptime_seconds: number;
  cameras_online: number;
  cameras_total: number;
  active_incidents: number;
  active_alerts: number;
  edge_nodes: number;
  sync_pending: number;
}

export interface Metrics {
  cameras_online: number;
  cameras_total: number;
  camera_fps: Record<string, number>;
  detections_total: number;
  tracks_active: number;
  incidents_total: number;
  alerts_total: number;
  events_total: number;
  queue_depth: number;
  sync_failures: number;
}

export interface SyncStatus {
  mode: string;
  pending: number;
  synced: number;
  failed: number;
  total: number;
}
