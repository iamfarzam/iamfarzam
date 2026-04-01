# Architecture

## Project Structure

```
iamfarzam/
├── README.md                   # GitHub profile (displayed on github.com/iamfarzam)
├── docs/                       # Project documentation
├── backend/                    # Django + DRF API
│   ├── config/
│   │   ├── settings/
│   │   │   ├── base.py         # Shared settings
│   │   │   ├── dev.py          # Development (DEBUG, SQLite)
│   │   │   └── prod.py         # Production (PostgreSQL, security)
│   │   ├── urls.py             # Root URL configuration
│   │   └── wsgi.py             # WSGI entry point
│   └── portfolio/
│       ├── models.py           # Data models (7 models)
│       ├── serializers.py      # DRF serializers
│       ├── views.py            # API views
│       ├── urls.py             # API URL routing
│       └── admin.py            # Unfold admin configuration
├── frontend/                   # Next.js application
│   └── src/
│       ├── app/                # Pages and routes
│       │   ├── layout.tsx      # Root layout (theme, fonts, header/footer)
│       │   ├── page.tsx        # Homepage (assembles all sections)
│       │   ├── projects/       # /projects and /projects/[slug]
│       │   ├── contact/        # /contact
│       │   ├── sitemap.ts      # Dynamic sitemap generation
│       │   └── robots.ts       # Robots.txt
│       ├── components/
│       │   ├── layout/         # Header, Footer, ThemeProvider
│       │   ├── ui/             # Button, Card, Badge, Section, ThemeToggle
│       │   └── sections/       # Hero, About, Skills, Projects, Experience, Education, Contact
│       ├── lib/
│       │   ├── api.ts          # Server-side API client with ISR
│       │   └── types.ts        # TypeScript interfaces
│       └── styles/
│           └── globals.css     # Tailwind v4 theme + dark mode
├── nginx/                      # Reverse proxy configuration
├── docker-compose.yml          # Development environment
└── docker-compose.prod.yml     # Production environment
```

## Data Models

```
Profile (singleton)
├── full_name, headline, bio, avatar, resume
├── email, location, social URLs
└── SEO: meta_title, meta_description, og_image

SkillCategory ──┐
└── Skill       │  (one-to-many)
    ├── name, icon, proficiency
    └── order, is_active

Project
├── title, slug, summary, description
├── thumbnail, image
├── technologies → M2M → Skill
├── github_url, live_url
└── is_featured, order, is_active

Experience
├── company, role, location
├── start_date, end_date (null = Present)
└── description, company_logo

Education
├── institution, degree, field_of_study
├── start_date, end_date
└── description, institution_logo

ContactMessage (write-only from API)
├── name, email, subject, message
└── is_read, created_at
```

All content models include `is_active` (visibility toggle) and `order` (sort order) fields, controlled entirely from the admin panel.

## Data Flow

```
Django Admin → PostgreSQL → DRF API → Next.js Server Components → HTML → Browser
                                  ↓
                            ISR Cache (1 hour)
```

1. Content is created/edited in Django admin
2. Django REST Framework serves it as JSON at `/api/v1/`
3. Next.js server components fetch data at build/request time
4. ISR revalidates every hour — no manual rebuilds needed
5. Contact form is the only client-side POST (via `submitContact`)

## Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| Single `portfolio` Django app | One bounded context — separate apps add import/migration overhead for no gain |
| Singleton Profile model | One profile per site, enforced at model and admin level |
| `is_active` + `order` on all models | Full admin control without code changes |
| Server components for data fetching | HTML arrives complete for SEO — no loading spinners |
| ISR with 1-hour revalidation | Admin changes appear within an hour, no manual rebuild |
| `next-themes` for dark mode | SSR-safe, avoids flash of wrong theme, respects system preference |
| CSS custom properties for theming | Tailwind v4 native approach — dark mode toggles CSS variables |
| Slug-based project URLs | SEO-friendly URLs like `/projects/sample-cv-project` |
| Django Unfold admin | Modern UI consistent with frontend aesthetic |
