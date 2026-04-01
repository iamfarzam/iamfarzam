# Contributing

Thanks for your interest in contributing! Here's how to get started.

## Development Setup

1. Fork and clone the repository
2. Copy `.env.example` to `.env` and configure values
3. Start the development stack:
   ```bash
   docker compose up --build
   ```
4. Run migrations:
   ```bash
   docker compose exec backend python manage.py migrate
   docker compose exec backend python manage.py createsuperuser
   ```

## Workflow

1. Create a feature branch from `master`:
   ```bash
   git checkout -b feat/your-feature
   ```
2. Make your changes
3. Ensure the backend passes checks:
   ```bash
   cd backend && python manage.py check
   ```
4. Ensure the frontend builds:
   ```bash
   cd frontend && npm run build
   ```
5. Commit with a clear message following [Conventional Commits](https://www.conventionalcommits.org/):
   - `feat:` for new features
   - `fix:` for bug fixes
   - `docs:` for documentation
   - `refactor:` for code restructuring
   - `chore:` for maintenance tasks
6. Push and open a pull request against `master`

## Guidelines

- Keep PRs focused — one feature or fix per PR
- No secrets or credentials in commits
- Frontend changes must be mobile-responsive
- Follow existing code patterns and conventions
- Update documentation when adding features

## Code Style

- **Python**: Follow PEP 8, use type hints where practical
- **TypeScript**: Strict mode, prefer named exports for components
- **CSS**: Use Tailwind utility classes, avoid custom CSS unless necessary
