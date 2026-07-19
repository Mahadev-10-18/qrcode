# Deployment Guide

## Prerequisites
- Server with Docker 24+ and Docker Compose v2
- Domain name (e.g. `tagmaster.io`)
- SMTP credentials for email delivery (optional)

---

## Step 1 — DNS

Point an A record to your server's public IP:

```
@    A    <server-ip>
```

No subdomain needed — Caddy handles both the app and `/api/*` routing on the same domain.

---

## Step 2 — Configure `.env`

Copy `.env.example` to `.env` and set:

```env
APP_ENV=production
DOMAIN=tagmaster.io
FRONTEND_URL=https://tagmaster.io
APP_DOMAIN=https://tagmaster.io
SECRET_KEY=<openssl rand -base64 64>
POSTGRES_PASSWORD=<random 32+ chars>
SMTP_HOST=smtp.yourprovider.com
SMTP_PORT=587
SMTP_USER=your@email.com
SMTP_PASSWORD=your-smtp-password
EMAIL_FROM=noreply@tagmaster.io
```

- Twilio fields can be left blank (Twilio is optional)
- `SENTRY_DSN` is optional (leave blank to disable)

---

## Step 3 — Deploy

```bash
docker compose up -d
```

Caddy automatically provisions a Let's Encrypt TLS certificate on first request.

---

## Step 4 — Verify

```bash
# Check all services are healthy
docker compose ps

# View logs
docker compose logs backend
docker compose logs caddy

# Health endpoint
curl https://tagmaster.io/health
```

Expected response: `{"status":"ok","database":"up","cache":"up"}`

---

## Step 5 — Test the flow

1. Visit `https://tagmaster.io` — sign up
2. Create a tag — download the QR code
3. Scan the QR with your phone — it opens the public tag page
4. Submit a message — owner receives email alert
5. Log into dashboard — message appears in Inbox

---

## Production Checklist

- [ ] Domain DNS configured and propagated
- [ ] `.env` has a strong `SECRET_KEY`
- [ ] `.env` has a strong `POSTGRES_PASSWORD`
- [ ] SMTP configured for email alerts and password resets
- [ ] Database backups enabled (`docker compose --profile backup up -d`)
- [ ] Server firewall allows ports 80 and 443 only

---

## Backup & Restore

### Automated daily backup (enabled with profile)

```bash
docker compose --profile backup up -d
```

Backups are written to `./backups/` as compressed dumps.

### Manual restore

```bash
docker compose exec -T postgres pg_restore -U postgres -d lostitem < backup.dump
```

---

## Updating

```bash
git pull
docker compose build --no-cache
docker compose up -d
```

Migrations run automatically via `alembic upgrade head` on backend startup.
