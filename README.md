# iamfarzam — Portfolio

A full-stack, dynamic portfolio website built with **Next.js** and **Django REST Framework**. All content is managed through the Django admin panel and served via a RESTful API.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 14 (App Router), TypeScript, Tailwind CSS v4, Framer Motion |
| Backend | Django 5, Django REST Framework, Unfold Admin |
| Database | PostgreSQL 16 |
| Deployment | Docker Compose, Nginx, Gunicorn |

## Features

- **Dynamic Content** — All sections (profile, skills, projects, experience, education) managed via Django admin
- **Dark/Light Mode** — System-aware theme toggle with smooth transitions
- **Interactive UI** — Scroll animations, typewriter hero, animated skill bars, project filtering
- **SEO Optimized** — Server-side rendering, JSON-LD structured data, dynamic sitemap, meta tags
- **Mobile Responsive** — Fully responsive across all breakpoints
- **Contact Form** — Rate-limited form submissions stored in the database
- **Modern Admin Panel** — Themed Django admin (Unfold) with sidebar navigation, status badges, and unread message counts
- **Dockerized** — One command to run the entire stack

## Project Structure

```
iamfarzam/
├── backend/          # Django + DRF API
│   ├── config/       # Project settings (base/dev/prod)
│   └── portfolio/    # Models, serializers, views, admin
├── frontend/         # Next.js application
│   └── src/
│       ├── app/      # Pages (homepage, projects, contact)
│       ├── components/  # Layout, UI primitives, sections
│       └── lib/      # API client, TypeScript types
├── nginx/            # Reverse proxy configuration
├── docker-compose.yml      # Development
└── docker-compose.prod.yml # Production
```

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Git

### Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/iamfarzam/iamfarzam.git
   cd iamfarzam
   ```

2. **Create environment file**
   ```bash
   cp .env.example .env
   ```
   Edit `.env` and set a secure `DJANGO_SECRET_KEY`.

3. **Start the development stack**
   ```bash
   docker compose up --build
   ```

4. **Run migrations and create admin user**
   ```bash
   docker compose exec backend python manage.py migrate
   docker compose exec backend python manage.py createsuperuser
   ```

5. **Access the application**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000/api/v1/
   - Django Admin: http://localhost:8000/admin/

### Adding Content

1. Log into Django admin at `/admin/`
2. Add your **Profile** (personal info, bio, social links, SEO fields)
3. Create **Skill Categories** and **Skills** with proficiency levels
4. Add **Projects** with descriptions, thumbnails, and technology tags
5. Add **Experience** and **Education** entries
6. Content appears on the frontend automatically (refreshes within 1 hour via ISR)

## Production Deployment

```bash
docker compose -f docker-compose.prod.yml up --build -d
docker compose -f docker-compose.prod.yml exec backend python manage.py migrate
docker compose -f docker-compose.prod.yml exec backend python manage.py collectstatic --noinput
docker compose -f docker-compose.prod.yml exec backend python manage.py createsuperuser
```

Update `.env` for production:
- Set `DJANGO_SETTINGS_MODULE=config.settings.prod`
- Set a strong `DJANGO_SECRET_KEY`
- Set `ALLOWED_HOSTS` to your domain
- Set `CORS_ALLOWED_ORIGINS` and `CSRF_TRUSTED_ORIGINS`
- Set `NEXT_PUBLIC_SITE_URL` to your domain

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/profile/` | Personal profile |
| GET | `/api/v1/skills/` | Skill categories with nested skills |
| GET | `/api/v1/projects/` | All active projects |
| GET | `/api/v1/projects/{slug}/` | Project detail |
| GET | `/api/v1/experience/` | Work experience |
| GET | `/api/v1/education/` | Education history |
| POST | `/api/v1/contact/` | Submit contact form |

## Development

### Backend (without Docker)

```bash
cd backend
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

### Frontend (without Docker)

```bash
cd frontend
npm install
npm run dev
```

## Environment Variables

See [`.env.example`](.env.example) for all required variables. Never commit `.env` files with real secrets.

## License

[MIT](LICENSE)
