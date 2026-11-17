# FastAPI Blog

A compact FastAPI/SQLAlchemy blog with a server-rendered Jinja2 site, JWT authentication, role-based post permissions, SQLite persistence, rate limiting, and generated OpenAPI documentation.

## Run locally

Python 3.11 or newer is recommended.

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements-dev.txt
make run
```

Open <http://localhost:8000> for the site or <http://localhost:8000/docs> for the API. `make run` applies database migrations before starting the server, and demo users are seeded on first startup. Set `BLOG_SEED_DEMO=false` to start without demo content.

The default database is `src/blog_engine.db`. The path is resolved from the source tree, so the app uses the same file regardless of the working directory. Configuration can be supplied through environment variables or a repository-root `.env` file:

```env
ENVIRONMENT=development
SECRET_KEY=replace-this-value
BLOG_SEED_DEMO=true
API_RATE_LIMIT_PER_MINUTE=120
ACCESS_TOKEN_EXPIRE_MINUTES=60
SESSION_COOKIE_SECURE=false
# BLOG_DATABASE_URL=sqlite:////absolute/path/to/blog_engine.db
```

## Security and production configuration

`ENVIRONMENT` selects the mode: `development` (default, permissive, demo seeding allowed), `test`, or `production`. In `production` the app **fails fast at startup** unless all of the following hold:

- `SECRET_KEY` is set to a strong value that is not the insecure default (at least 32 characters, e.g. `openssl rand -hex 32`)
- `DEBUG` is disabled
- `SESSION_COOKIE_SECURE` is `true` (serve over HTTPS)
- `BLOG_SEED_DEMO` is `false` — demo accounts ship well-known passwords and are never seeded in production

### Secret rotation

Rotating `SECRET_KEY` invalidates every existing JWT: all users are logged out and CSRF cookies are reissued, so rotation is safe to perform at any time. Set the new value and restart the service; no database changes are required. Never log secrets or commit them to version control.

### Initial admin bootstrap

Because production does not seed demo accounts, create the first admin with environment variables on a fresh database:

```env
BLOG_ADMIN_USERNAME=your-admin-name
BLOG_ADMIN_PASSWORD=a-long-random-password
```

On startup, if no Admin exists yet, one account with `BLOG_ADMIN_USERNAME`/`BLOG_ADMIN_PASSWORD` is created; existing accounts are never modified. Remove both variables after the first boot. Additional users are created by changing roles through `PUT /api/v1/users/{id}/role` (see below) after registering accounts, or by seeding additional identities locally only.

### CSRF protection

All cookie-authenticated browser forms (login, logout, and every admin action) require a CSRF token rendered as a hidden field and validated against a signed HttpOnly `csrf_token` cookie. The JSON API is unaffected: it only accepts `Authorization: Bearer` tokens and is therefore not cookie-authenticated.

## Web interface

- `/` — paginated list of published posts
- `/posts/{id}` — post detail; draft posts are visible only to their author and roles with `posts.read_any_draft`
- `/login` / `/logout` — browser login using an HttpOnly cookie
- `/admin` — role-aware dashboard with counts and recent posts
- `/admin/posts` — searchable, filterable post list for everything the signed-in role can see
- `/admin/posts/new`, `/admin/posts/{id}/edit` — create and edit posts (title, Markdown body, draft/published status, author assignment for Admin/Editor)
- `/admin/users` — Admin-only overview of users, roles and capabilities
- `/docs` — interactive API documentation

Every admin action re-checks server-side permissions; hidden buttons are a UX aid, not a security boundary. Anonymous visitors are redirected to the login page, and direct POSTs cannot bypass authorization.

The browser UI stores its JWT in an HttpOnly, SameSite=Lax cookie. The REST API itself only accepts `Authorization: Bearer <token>` and does not read the cookie.

## Commands

```bash
make migrate  # apply database migrations
make revision m="add example table"  # autogenerate a migration
make test     # run the test suite
make lint     # ruff
make check    # lint, compile sources and run tests
make clean    # remove caches and local databases
docker compose up --build
```

Docker Compose applies migrations automatically before starting the app.

## Database migrations

Schema changes are tracked with Alembic. Migrations live in `migrations/versions`, and `make migrate` applies them to `BLOG_DATABASE_URL`. `make run` runs migrations first, while Docker does the same in its startup command.

After changing SQLAlchemy models, generate and review a revision:

```bash
make revision m="describe the schema change"
make migrate
```

To baseline a database that already has the current schema but no Alembic history, stamp it once with `.venv/bin/alembic stamp head`.

## API and permissions

The API endpoints are under `/api/v1`. Use `/docs` for request schemas and the complete endpoint list. `GET /api/v1/posts` is paginated with `limit` (1-100, default 20) and `offset`. `POST /api/v1/auth/login` exchanges a username and password for a JWT.

Role permissions are stored in the database and enforced from capability assignments. `GET /api/v1/roles` lists each role with its description and current capabilities; `GET /api/v1/capabilities` lists the capability vocabulary. A caller with the `users.manage` capability can update a role with `PUT /api/v1/roles/{role}`, and changes apply immediately to subsequent requests. The Admin role is immutable, so it cannot be edited or locked out. Admins can list users (`GET /api/v1/users`) and change a role (`PUT /api/v1/users/{id}/role`); the last Admin cannot be demoted. Default capabilities: Admin/Editor have full CRUD, Author creates and updates own posts, Contributor creates drafts only, Subscriber and anonymous users are read-only. Drafts are visible to their author (any role) and roles with `posts.read_any_draft`.

## Demo identities

Demo accounts are a **local development convenience only** (`BLOG_SEED_DEMO=true`, the default) and are blocked in production mode. When seeding is enabled, the following accounts are available in the browser UI and through `POST /api/v1/auth/login`:

| Username | Password | Role |
| --- | --- | --- |
| `admin` | `admin123` | Admin |
| `editor` | `editor123` | Editor |
| `author` | `author123` | Author |
| `contributor` | `contributor123` | Contributor |
| `subscriber` | `subscriber123` | Subscriber |

Passwords are stored as PBKDF2-SHA256 hashes. JWTs require `exp` and `sub` claims; the role is always read from the database, not the token. You can still mint tokens directly with the configured secret as shown in the tests.

## License

[MIT](LICENSE)
