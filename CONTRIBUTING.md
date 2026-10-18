# Contributing to DUX Vault

This project is maintained by a small team, so the goal is to keep changes small, easy to review, and easy to extend later.

## Before You Start

1. Read [docs/app-spec.md](docs/app-spec.md) to understand the business rules.
2. Read [docs/technical-spec.md](docs/technical-spec.md) to understand the actual code structure.
3. Check for existing work before adding a new file or folder.
4. Keep secrets out of git. Use `.env.development` locally and never commit real credentials.

## Where To Put New Code

Use these conventions when adding or moving code:

- Backend request handlers belong in `backend/app/api/routes`.
- Backend auth/session logic belongs in `backend/app/auth`.
- Backend SQL belongs in `backend/app/db/queries`.
- Backend pure helper functions belong in `backend/app/utils`.
- Backend file/path I/O belongs in `backend/app/services`.
- Shared backend response models belong in `backend/app/schemas`.
- Frontend page-specific config and page shells belong in `frontend/src/pages`.
- Frontend reusable UI belongs in `frontend/src/components`.
- Frontend shared UI primitives (Button, Card) belong in `frontend/src/components/ui`.
- Frontend icons belong in `frontend/src/components/icons` as inline SVG components.
- Frontend API wrappers belong in `frontend/src/api`.
- Frontend shared types belong in `frontend/src/types`.
- Frontend route definitions belong in `frontend/src/router.tsx`.

If a function has no side effects and can be unit tested without the database, filesystem, or network, prefer `backend/app/utils` over colocating it with a route or service.

## Git Workflow

Keep git simple:

1. Start from a clean `main` branch.
2. Create a short-lived branch for the change, for example `feature/docs-refresh` or `fix/results-grid`.
3. Make one logical change per commit when possible.
4. Use `git status` before committing and `git diff` before opening a PR.
5. Do not commit generated files, secrets, or local environment files.
6. If you need to update docs and code together, keep them in the same branch so reviewers see the full context.

Useful commands:

```bash
git checkout main
git pull
git checkout -b feature/my-change
git status
git diff
git add .
git commit -m "Describe the change"
```

If your branch gets messy, stop and simplify it before adding more changes.

## Validation Expectations

Run the smallest relevant checks before asking for review:

- Backend changes: `make py-compile` or `make check`, then `make test` if behavior changed.
- Frontend changes: `npm run build`, and `npm run lint` when UI code changed.
- If you touch both sides, validate both sides.

## Review Checklist

Before opening a PR, make sure:

- the change matches the App Spec
- new files are in the correct folder
- the app still runs locally
- tests or build checks pass
- the change is understandable to someone who did not write it

## When To Ask For Help

Ask for help instead of guessing when:

- a database column or table name is unclear
- an auth group or Active Directory value is unknown
- a new UI pattern would duplicate existing components
- you are not sure whether a helper belongs in `utils` or `services`

When in doubt, keep the change smaller.
