# AGENTS.md

## Stack
- **Frontend**: React (Vite)
- **Backend**: FastAPI (Python)
- **Database**: PostgreSQL
- **QR Generation**: `qrcode` Python library
- **PDF Generation**: xhtml2pdf
- **Communication Relay**: Twilio (call/text)
- **Authentication**: JWT‑based auth

## Database Schema (source of truth)
```
users: id (uuid, pk), email, phone_number (private, never exposed), plan (free|paid, default free), created_at

tags: id (uuid, pk — encoded in the QR), owner_id (fk), label, status (active|paused|lost_confirmed), created_at

contact_events: id (uuid, pk), tag_id (fk), finder_contact_method (call|text), created_at, relay_session_id
```

## Standing Invariants
- `tags.id` is always a random UUID/nanoid, **NEVER** sequential.
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
- Enforce rate limiting on contact events as specified.
- Enforce that no phone_number or authentication token is logged.


*End of AGENTS.md*
