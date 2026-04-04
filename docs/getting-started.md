# Getting Started

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) and Docker Compose
- [Git](https://git-scm.com/)

For local development without Docker:
- Python 3.12+
- Node.js 20+

## Setup with Docker (Recommended)

### 1. Clone and configure

```bash
git clone https://github.com/iamfarzam/iamfarzam.git portfolio
cd portfolio
cp .env.example .env
```

Open `.env` and set a secure `DJANGO_SECRET_KEY`. See [Environment Variables](#environment-variables) for all options.

### 2. Start the stack

```bash
docker compose up --build
```

This starts three services:
- **PostgreSQL** on port 5432
- **Django backend** on port 8000 (with hot reload)
- **Next.js frontend** on port 3000 (with HMR)

### 3. Initialize the database

```bash
docker compose exec backend python manage.py migrate
docker compose exec backend python manage.py createsuperuser
```

### 4. Add content

1. Open http://localhost:8000/admin/ and log in
2. Add your **Profile** — name, headline, bio, avatar, social links, SEO fields
3. Create **Skill Categories** (e.g. Backend, ML/CV, Tools) with **Skills** inside each
4. Add **Projects** — title, slug, description, thumbnail, technologies, GitHub/live links
5. Add **Experience** and **Education** entries
6. Visit http://localhost:3000 — content appears automatically

Content refreshes within 1 hour via ISR (Incremental Static Regeneration).

## Local Development (Without Docker)

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

The backend uses SQLite in development mode by default.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Set `INTERNAL_API_URL=http://localhost:8000/api/v1` and `NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1` in your environment or a `.env.local` file in the frontend directory.

## Environment Variables

All configuration is via environment variables. Copy `.env.example` to `.env` and adjust:

| Variable | Description | Default |
|----------|-------------|---------|
| `DJANGO_SECRET_KEY` | Django secret key (required) | `change-me-to-a-random-secret-key` |
| `DJANGO_SETTINGS_MODULE` | Settings module | `config.settings.dev` |
| `DATABASE_URL` | PostgreSQL connection string | `postgres://portfolio:portfolio@postgres:5432/portfolio` |
| `POSTGRES_DB` | Database name | `portfolio` |
| `POSTGRES_USER` | Database user | `portfolio` |
| `POSTGRES_PASSWORD` | Database password | `portfolio` |
| `ALLOWED_HOSTS` | Django allowed hosts | `localhost,127.0.0.1` |
| `CORS_ALLOWED_ORIGINS` | Allowed CORS origins | `http://localhost:3000` |
| `CSRF_TRUSTED_ORIGINS` | Trusted CSRF origins | `http://localhost:3000` |
| `NEXT_PUBLIC_API_URL` | API URL for client-side calls | `http://localhost:8000/api/v1` |
| `INTERNAL_API_URL` | API URL for server-side calls | `http://backend:8000/api/v1` |
| `NEXT_PUBLIC_SITE_URL` | Public site URL (for SEO) | `http://localhost:3000` |

**Never commit `.env` files.** Only `.env.example` is tracked.
