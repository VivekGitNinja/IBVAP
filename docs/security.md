# Security

## Authentication
- JWT tokens with HS256 signing
- Configurable expiration (default 60 minutes)
- Token passed via Authorization header

## Password Hashing
- PBKDF2-HMAC-SHA256 with 100,000 iterations
- 16-byte random salt per password
- Constant-time comparison via hmac.compare_digest

## Role-Based Access Control

| Role | Permissions |
|------|------------|
| ADMIN | Full access + user management |
| COMMANDER | Read/write, camera/zone management, escalation |
| OPERATOR | Read/write, acknowledge incidents |
| AUDITOR | Read-only + audit trail access |
| VIEWER | Read-only |

## Security Headers
- X-Content-Type-Options: nosniff
- X-Frame-Options: DENY
- X-XSS-Protection: 1; mode=block
- Cache-Control: no-store, no-cache, must-revalidate

## Evidence Integrity
- SHA-256 manifest hashing
- Hash chain for tamper evidence
- Deterministic JSON serialization
- No raw video in manifests

## Audit Trail
- All significant actions logged
- Hash chain for tamper detection
- Actor, role, action, target, timestamp
- Previous hash linking

## Configuration
- Environment variables for secrets
- No hardcoded credentials
- .env file for development
- Separate production defaults

## Known Limitations
- No TLS (use reverse proxy in production)
- No rate limiting in demo mode
- No IP-based access control
- JWT secret must be configured for production
