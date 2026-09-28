## Summary

<!-- Brief description of what this PR does and why -->

## Changes

<!-- Bulleted list of key changes -->

-

## Type of Change

- [ ] Bug fix (non-breaking change that fixes an issue)
- [ ] New feature (non-breaking change that adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to change)
- [ ] Refactor (code change that neither fixes a bug nor adds a feature)
- [ ] Documentation update
- [ ] Infrastructure / DevOps

## Checklist

These mirror the checks CI runs; run the ones your change touches.

- [ ] Code follows the project's style and conventions
- [ ] Privacy guard passes (`node scripts/check-private-files.mjs`) — no secrets,
      credentials, `.env` values or `demos/` content committed
- [ ] Backend: `python manage.py check`, `python manage.py makemigrations --check --dry-run`
      and `python manage.py test portfolio.tests` pass from `backend/`
- [ ] Frontend: `npm test`, `npm run lint` and `npm run build` pass from `frontend/`
- [ ] Infrastructure/deploy changes: `bash -n deploy.sh`,
      `node --test scripts/deployment.test.mjs scripts/check-private-files.test.mjs`
      and `docker compose -f docker-compose.prod.yml config --quiet` pass
- [ ] Dependency changes: `npm audit --omit=dev` and `pip-audit -r requirements.txt` are clean
- [ ] Documentation has been updated (if applicable)
- [ ] Changes are mobile-responsive (if frontend)

## Screenshots

<!-- If frontend changes, add before/after screenshots. Remove this section otherwise. -->
