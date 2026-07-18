# AGENTS.md

## Stack
- **Frontend**: React (Vite 8), React Router v7, oxlint
- **Backend**: FastAPI (Python 3.12+), asyncpg, SQLModel, xhtml2pdf, sentry-sdk, Twilio
- **Database**: PostgreSQL 15+ (via asyncpg)
- **Cache**: Redis 7+ (optional, falls back to in-memory)
- **Monitoring**: Sentry (with PII scrubbing via `before_send`)
- **QR Generation**: `qrcode` Python library (QRCodeDetector for tests)
- **PDF Generation**: xhtml2pdf
- **Communication Relay**: Twilio Proxy (call/text with retry logic)
- **Authentication**: Stub (X-User-Id header), JWT planned

## Database Schema (source of truth)
```
users: id (uuid, pk), email, phone_number (private, never exposed), plan (free|paid, default free), created_at

tags: id (uuid, pk — encoded in the QR), owner_id (fk), label, status (active|paused|lost_confirmed), created_at

contact_events: id (uuid, pk), tag_id (fk), finder_contact_method (call|text), created_at, relay_session_id, is_blocked, is_failed

rate_limit_events: id (uuid, pk), key (indexed), created_at

jobs: id (uuid, pk), status (pending|processing|completed|failed), created_at, result (bytes/pdf)
```

## Standing Invariants
- `tags.id` is always a random UUID, **NEVER** sequential.
- `GET /t/{id}` route structure is permanent; it must never change or return 404 for a live tag.
- `phone_number` is never returned in any API response except to its **own owner**.
- Contact requests are rate‑limited per tag (**5 per hour**) once the relay ships.
- No credential or configuration secret is ever committed. The config module `backend/config.py` is the single source from which secrets are read.
- Free-tier users are limited to **2 active tags**. Only `status='active'` counts toward the limit; paused/lost_confirmed tags do not. Enforcement is at `POST /tags`.
- No phone_number or authentication token is ever logged in any format or log level.

## Persistent Rules
These rules must survive every future task. No later agent run may silently violate them.
- Do not expose `phone_number` to any requester other than the owner.
- Do not change the `/t/{id}` endpoint contract.
- Enforce UUID generation for tag IDs.
- Enforce rate limiting on contact events as specified (5/hour per tag).
- Enforce that no phone_number or authentication token is logged.
- `/jobs/{job_id}` requires authentication (via `get_current_user`).
- Health endpoint at `GET /health` checks both DB and cache; returns 503 if either is down.
- Sentry `before_send` scrubs phones, emails, and Twilio SIDs from events before transmission.
- Frontend contact form MUST include `finder_phone` in POST body.
- Use `datetime.now(timezone.utc).replace(tzinfo=None)` for UTC naive datetimes (compatible with `TIMESTAMP WITHOUT TIME ZONE`).
- Use modern FastAPI `lifespan` instead of deprecated `on_event` for startup/shutdown.

## Commands
```bash
# Backend
cd backend && python -m pytest -v --no-header

# Frontend
cd frontend && npm run build && npm run lint

# Docker
docker compose up --build

# CI (GitHub Actions)
# Pushes/PRs to main trigger .github/workflows/ci.yml
```


*End of AGENTS.md*
