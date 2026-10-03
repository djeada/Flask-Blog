# FastAPI Blog API

A compact FastAPI/SQLAlchemy example with JWT authentication, role-based post permissions, SQLite persistence, rate limiting, and generated OpenAPI documentation.

## Run locally

Python 3.11 or newer is recommended.

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements-dev.txt
make run
```

Open <http://localhost:8000/docs>. The database and demo users are created on first startup. Set `BLOG_SEED_DEMO=false` to start without demo content.

The default database is `blog_engine.db`. Configuration can be supplied through environment variables or a repository-root `.env` file:

```env
SECRET_KEY=replace-this-value
BLOG_DATABASE_URL=sqlite:///./blog_engine.db
BLOG_SEED_DEMO=true
API_RATE_LIMIT_PER_MINUTE=120
```

For non-local deployments, always provide a strong `SECRET_KEY`.

## Commands

```bash
make test     # run the test suite
make lint     # ruff
make check    # lint, compile sources and run tests
make clean    # remove caches and local databases
docker compose up --build
```

The API endpoints are under `/api/v1/posts`. Use `/docs` for request schemas and the complete endpoint list. `GET /api/v1/posts` is paginated with `limit` (1-100, default 20) and `offset`.

Admins can list users (`GET /api/v1/users`) and change a role (`PUT /api/v1/users/{id}/role`); the last Admin cannot be demoted. Role permissions: Admin/Editor have full CRUD, Author creates and updates own posts, Contributor creates drafts only, Subscriber and anonymous users are read-only.

## Demo identities

When seeding is enabled, these JWT subjects are available for API exploration: `admin`, `editor`, `author`, `contributor`, and `subscriber`. This repository demonstrates authorization behavior; it does not expose a password/login endpoint. Create a JWT with the configured secret and `sub`, `user_id`, and `exp` claims, as shown in the tests, and send it as `Authorization: Bearer <token>`. `exp` is required, and the role is always read from the database, not the token.

## License

[MIT](LICENSE)
