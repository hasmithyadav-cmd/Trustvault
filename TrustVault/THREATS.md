# TrustVault Threat Model

## Assets
- User credentials and account identities.
- Uploaded documents.
- Document ownership and permission records.
- Audit events and their hash chain.
- Application secret key and database.

## Trust boundaries
- Browser to Flask application.
- Authenticated user to another user's documents.
- Application process to private upload storage.
- Application database to administrator/operator.
- Deployment environment to persistent storage.

## Threats and mitigations

| Threat | Example | Current mitigation | Remaining risk |
|---|---|---|---|
| Unauthorized document read | User guesses another document ID | Authenticated detail route checks owner/admin/active view permission | Admin is trusted; no external security review |
| Unauthorized download | Viewer calls download URL directly | Download route independently checks current permission | Bytes already downloaded cannot be recalled |
| Stale access after revoke | User retains an old link | Permission is queried from DB on every request; revoke is POST-only | In-flight response may already have started |
| Path traversal | Crafted filename such as `../../secret` | Original name is sanitized; storage key is random; storage path is server-generated | No malware/content scanning |
| Oversized upload | Very large file consumes disk | 10 MB request/file size limit | Deployment-level quotas still needed |
| CSRF | Attacker tricks logged-in user into sharing/revoking | Flask-WTF CSRF tokens on forms | Token/session compromise remains possible |
| Password disclosure | Database leak exposes passwords | Werkzeug password hashing | Password reuse and weak user choices remain possible |
| Audit modification | Operator edits an audit row | Hash-linked entries and verification | Full database rewrite can recompute the chain; external anchoring is absent |
| Session theft | Stolen browser session | HttpOnly, SameSite cookies; Secure cookie configurable for HTTPS | TLS and strong session/secret operations required |
| Login guessing | Repeated password attempts | Not fully mitigated in MVP | Add rate limiting, lockout/monitoring before production |

## Security decisions
- New registrations are `viewer`, not `admin` or `owner`.
- Role checks and per-document permission checks occur on the server.
- Upload storage is not placed in `/static`.
- Original filenames are display metadata only; random generated storage names are used.
- The download endpoint re-checks permission for each request.

## Out of scope
End-to-end encryption, malware scanning, MFA, enterprise SSO, immutable external audit anchoring, antivirus, DLP, backups, disaster recovery, and production compliance certification.
