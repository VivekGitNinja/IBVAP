# Privacy Policy

## IBVAP Privacy by Design

## Principles
1. **Minimize personal data** — Only collect what's necessary for surveillance
2. **Human oversight** — AI provides recommendations, humans decide
3. **No autonomous identification** — Face analytics is candidate matching only
4. **Configurable retention** — Evidence and data retention is configurable
5. **Audit trail** — All access to sensitive data is logged

## Face Analytics
- Face detection: Bounding box + confidence only
- Face matching: Candidate matching / decision support only
- NOT autonomous identification
- Requires human verification
- Audit logged

## ANPR (Number Plate Recognition)
- Plate detection + OCR (when available)
- Candidate results with confidence
- NOT autonomous enforcement
- Requires human verification
- Evidence preserved

## Data Retention
- Default: 30 days for events and detections
- Incidents: Until operator closes
- Evidence: Configurable expiration
- Audit logs: 90 days minimum

## Data Storage
- Raw video NOT stored in manifests
- Only metadata, hashes, and evidence references
- Database supports SQLite (local) or PostgreSQL (deployment)
- Evidence files stored in configurable directory

## Access Control
- Role-based access control (RBAC)
- All evidence access is logged
- Audit trail for all operations
- No unrestricted access

## Known Limitations
- Prototype does not implement full data retention automation
- Face recognition module not implemented
- ANPR module not implemented
- No data anonymization pipeline
- No geographic data protection compliance

## Operational Requirements
- Deploy in secure network segment
- Configure TLS/reverse proxy for production
- Set appropriate retention policies
- Train operators on privacy implications
- Regular security audits
