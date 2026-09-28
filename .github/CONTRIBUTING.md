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
2. Enable the privacy pre-commit hook once per checkout:
   ```bash
   git config --local core.hooksPath .githooks
   ```
3. Make your changes
4. Ensure the backend passes the same checks as CI:
   ```bash
   cd backend && python manage.py check && \
       python manage.py makemigrations --check --dry-run && \
       python manage.py test portfolio.tests
   ```
5. Ensure the frontend passes the same checks as CI:
   ```bash
   cd frontend && npm test && npm run lint && npm run build
   ```
6. For deployment or infrastructure changes, also run:
   ```bash
   bash -n deploy.sh
   node --test scripts/deployment.test.mjs scripts/check-private-files.test.mjs
   docker compose -f docker-compose.prod.yml config --quiet
   ```
7. Commit with a clear message following [Conventional Commits](https://www.conventionalcommits.org/):
   - `feat:` for new features
   - `fix:` for bug fixes
   - `docs:` for documentation
   - `refactor:` for code restructuring
   - `chore:` for maintenance tasks
8. Push and open a pull request against `master`

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
