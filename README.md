# Portfolio

A full-stack, open-source portfolio website built with **Next.js** and **Django REST Framework**. All content is managed through a themed Django admin panel and served via a RESTful API — no hardcoded data, fully customizable.

## Tech Stack

**Frontend:** Next.js 14 (App Router), TypeScript, Tailwind CSS v4, Framer Motion
**Backend:** Django 5, Django REST Framework, Unfold Admin
**Database:** PostgreSQL 16
**Deployment:** Docker Compose, Nginx, Gunicorn

## Features

- **Dynamic Content** — Manage everything from the admin panel (profile, skills, projects, experience, education)
- **Dark/Light Mode** — System-aware theme toggle with smooth transitions
- **Interactive UI** — Scroll animations, typewriter hero, animated skill bars, project filtering
- **SEO Optimized** — Server-side rendering, JSON-LD structured data, dynamic sitemap, OpenGraph meta tags
- **Mobile Responsive** — Fully responsive across all breakpoints
- **Contact Form** — Rate-limited form submissions stored in the database
- **Modern Admin Panel** — Themed Django admin (Unfold) with sidebar navigation, status badges, unread message counts
- **Dockerized** — One command to run the entire stack

## Quick Start

```bash
git clone https://github.com/iamfarzam/iamfarzam.git portfolio
cd portfolio
cp .env.example .env        # configure your secrets
docker compose up --build    # start the stack
```

Then run migrations and create your admin user:

```bash
docker compose exec backend python manage.py migrate
docker compose exec backend python manage.py createsuperuser
```

- **Frontend**: http://localhost:3000
- **Admin Panel**: http://localhost:8000/admin/
- **API**: http://localhost:8000/api/v1/

## Documentation

| Document | Description |
|----------|-------------|
| [Getting Started](docs/getting-started.md) | Setup, installation, and first run |
| [Architecture](docs/architecture.md) | Project structure, tech decisions, data flow |
| [API Reference](docs/api.md) | All REST API endpoints with request/response examples |
| [Deployment](docs/deployment.md) | Docker, production, and Vercel deployment guides |

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](.github/CONTRIBUTING.md) for guidelines.

## Author

Created and maintained by [Farzam Mehdi](https://github.com/iamfarzam).

## License

[MIT](LICENSE)
