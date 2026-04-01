# Deployment

## Docker Compose (Self-Hosted)

### Production Setup

```bash
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

## Vercel + Railway (Cloud)

For a serverless deployment, split the stack:

| Service | Platform | Hosts |
|---------|----------|-------|
| Frontend | Vercel | Next.js |
| Backend + DB | Railway | Django + PostgreSQL |

### Backend on Railway

1. Create a new project on [Railway](https://railway.app/)
2. Add a **PostgreSQL** database
3. Add a **service** pointing to the `backend/` directory
4. Set environment variables:
   ```
   DJANGO_SECRET_KEY=<random-key>
   DJANGO_SETTINGS_MODULE=config.settings.prod
   DATABASE_URL=<railway-postgres-url>
   ALLOWED_HOSTS=your-backend.railway.app
   CORS_ALLOWED_ORIGINS=https://yourdomain.vercel.app
   CSRF_TRUSTED_ORIGINS=https://yourdomain.vercel.app
   ```
5. Set the start command: `gunicorn config.wsgi:application --bind 0.0.0.0:$PORT`
6. Run migrations via Railway CLI or shell:
   ```bash
   python manage.py migrate
   python manage.py createsuperuser
   ```

### Frontend on Vercel

1. Import the repository on [Vercel](https://vercel.com/)
2. Set the **root directory** to `frontend`
3. Set environment variables:
   ```
   INTERNAL_API_URL=https://your-backend.railway.app/api/v1
   NEXT_PUBLIC_API_URL=https://your-backend.railway.app/api/v1
   NEXT_PUBLIC_SITE_URL=https://yourdomain.vercel.app
   ```
4. Deploy — Vercel auto-detects Next.js

### Custom Domain

Point your domain to Vercel for the frontend. The backend runs on a Railway subdomain (or add a custom domain on Railway too).

---

## Updating Content

Regardless of deployment method:

1. Log into Django admin at `/admin/`
2. Add or edit content
3. Changes appear on the frontend within 1 hour (ISR revalidation)
4. For immediate updates, redeploy the frontend or trigger an on-demand revalidation
