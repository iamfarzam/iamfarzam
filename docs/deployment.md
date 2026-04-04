# Deployment

## Docker Compose (Self-Hosted VPS)

### Prerequisites

- A VPS with Docker and Docker Compose installed
- A domain name (optional, but recommended for HTTPS)

### Production Setup

```bash
# Clone the repository
git clone https://github.com/iamfarzam/iamfarzam.git portfolio
cd portfolio

# Configure environment
cp .env.example .env
# Edit .env with production values (see below)

# Build and start all services
docker compose -f docker-compose.prod.yml up --build -d

# Run migrations and collect static files
docker compose -f docker-compose.prod.yml exec backend python manage.py migrate
docker compose -f docker-compose.prod.yml exec backend python manage.py collectstatic --noinput
docker compose -f docker-compose.prod.yml exec backend python manage.py createsuperuser
```

### Production Environment Variables

Update `.env` with production values:

```env
DJANGO_SECRET_KEY=<generate-a-strong-random-key>
DJANGO_SETTINGS_MODULE=config.settings.prod
DATABASE_URL=postgres://portfolio:<strong-password>@postgres:5432/portfolio
POSTGRES_PASSWORD=<strong-password>
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
CORS_ALLOWED_ORIGINS=https://yourdomain.com
CSRF_TRUSTED_ORIGINS=https://yourdomain.com
NEXT_PUBLIC_API_URL=https://yourdomain.com/api/v1
INTERNAL_API_URL=http://backend:8000/api/v1
NEXT_PUBLIC_SITE_URL=https://yourdomain.com
```

### Architecture

```
                    ┌──────────┐
    Port 80/443 ───►│  Nginx   │
                    └────┬─────┘
                         │
              ┌──────────┼──────────┐
              ▼          ▼          ▼
         /api/, /admin/  /    /media/, /static/
              │          │          │
        ┌─────┴─────┐ ┌─┴────┐  ┌──┴──────┐
        │  Gunicorn  │ │Next.js│  │ Volumes │
        │  (Django)  │ │Server │  │         │
        └─────┬──────┘ └──────┘  └─────────┘
              │
        ┌─────┴──────┐
        │ PostgreSQL  │
        └─────────────┘
```

### SSL/TLS

For HTTPS, add your SSL certificates to the Nginx configuration. Update `nginx/default.conf`:

```nginx
server {
    listen 443 ssl;
    ssl_certificate     /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;
    # ... rest of config
}

server {
    listen 80;
    return 301 https://$host$request_uri;
}
```

---

## Updating Content

1. Log into Django admin at `/admin/`
2. Add or edit content
3. Changes appear on the frontend within 1 hour (ISR revalidation)
4. For immediate updates, redeploy the frontend or trigger an on-demand revalidation
