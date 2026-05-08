# ARCHITECTURE.md — GMB Review Generator

> Generated: 2026-04-29 | Reverse-engineered from source.

---

## 1. High-Level Overview

**GMB Review Generator** is a two-tier SaaS web application that helps local businesses solicit and generate Google My Business (GMB) reviews from their customers. A business owner registers an account, enters their business metadata (name, description, SEO keywords, Google Place ID), and receives a QR code linking to a review-generation page. When a customer scans the QR code, they select a star rating and optionally describe their experience; the backend calls Google Gemini 1.5 Flash to produce a short, tone-matched review draft. The customer copies the text and pastes it manually into the Google review form — Google's policy forbids automated posting.

The backend is a stateless FastAPI REST API backed by PostgreSQL. Authentication supports two providers: local (email/username/mobile + argon2-hashed password) and Google OAuth 2.0 (ID token verification). Sessions are managed entirely via short-lived JWT access tokens (30 min) and long-lived refresh tokens (7 days); no server-side session storage is used. The frontend is a React 19 single-page application served by Vite, communicating with the backend via Axios with an automatic token-refresh interceptor.

---

## 2. Tech Stack & Infrastructure

### Backend

| Concern           | Library / Version                          |
|-------------------|--------------------------------------------|
| Web framework     | FastAPI 0.136.0                            |
| ASGI server       | Uvicorn 0.34.0 + standard extras           |
| ORM               | SQLAlchemy 2.0.49                          |
| Database          | PostgreSQL (psycopg2-binary 2.9.10)        |
| Migrations        | Alembic 1.16.1                             |
| Auth tokens       | PyJWT 2.12.1 (HS256)                       |
| Password hashing  | pwdlib 0.3.0 with Argon2 backend           |
| Settings          | pydantic-settings 2.9.1 + python-dotenv    |
| Validation        | Pydantic 2.11.4, email-validator 2.3.0     |
| Google OAuth      | google-auth 2.40.1                         |
| AI generation     | google-generativeai 0.8.5 (Gemini 1.5 Flash) |
| QR codes          | qrcode 8.2 + Pillow                        |
| Rate limiting     | slowapi 0.1.9                              |

### Frontend

| Concern        | Library / Version              |
|----------------|-------------------------------|
| UI framework   | React 19.2.4                  |
| Build tool     | Vite 8.0.4                    |
| Routing        | react-router-dom 7.14.2       |
| HTTP client    | axios 1.15.2                  |
| Google OAuth UI | @react-oauth/google 0.13.5   |

### Infrastructure

- No Docker or docker-compose configuration present.
- No CI/CD pipeline configured.
- Static files (QR PNGs) served directly by FastAPI's `StaticFiles` mount at `/static`.
- Database migrations managed by Alembic; `create_all()` retained as a dev fallback in the lifespan hook.

---

## 3. Directory Structure Map

```
generator/
├── .gitignore                  # Covers .env, __pycache__, node_modules, static/, *.png
├── .python-version             # Pins Python 3.12
├── README.md                   # Setup instructions, API reference, env variable table
├── ARCHITECTURE.md             # This file
│
├── backend/                    # FastAPI application root
│   ├── .env                    # Live secrets — never commit (gitignored)
│   ├── .env.example            # Template for all required env variables
│   ├── requirements.txt        # Direct dependencies only, UTF-8 no-BOM
│   ├── alembic.ini             # Alembic config; DB URL set dynamically in env.py
│   │
│   ├── alembic/                # Database migration system
│   │   ├── env.py              # Wires settings.database_url + Base.metadata to Alembic
│   │   ├── script.py.mako      # Template for auto-generated migration files
│   │   └── versions/
│   │       └── 0001_initial_schema.py  # Creates user_business + generated_reviews tables
│   │
│   ├── app/                    # Application package
│   │   ├── main.py             # App factory: lifespan, middleware, router registration
│   │   │
│   │   ├── core/               # Cross-cutting configuration
│   │   │   ├── settings.py     # Pydantic BaseSettings — single source of truth for config
│   │   │   └── limiter.py      # Shared slowapi Limiter instance (avoids circular imports)
│   │   │
│   │   ├── db/                 # Database layer
│   │   │   ├── database.py     # Engine, SessionLocal, Base, get_db() dependency
│   │   │   └── models.py       # ORM models: UserBusiness, GeneratedReview
│   │   │
│   │   ├── schemas/            # Pydantic request/response contracts
│   │   │   ├── user.py         # Auth schemas: BusinessRegister, LoginBusiness, Token, UserProfile
│   │   │   └── review.py       # Review schemas: ReviewGenerateRequest, ReviewOut, ReviewListResponse
│   │   │
│   │   ├── services/           # Pure business logic (no HTTP concerns)
│   │   │   ├── auth.py         # Password hashing, JWT lifecycle, user lookup, get_current_user
│   │   │   ├── review.py       # Gemini prompt construction + AI text generation
│   │   │   └── qr.py           # QR PNG generation via qrcode + Pillow
│   │   │
│   │   └── routers/            # FastAPI route handlers (thin — delegate to services)
│   │       ├── auth.py         # /auth/*: register, login, google, refresh, me
│   │       └── reviews.py      # /reviews/*: generate, history, qr
│   │
│   └── tests/                  # Pytest test suite
│       ├── conftest.py         # SQLite test DB, client fixture with get_db override
│       └── test_auth.py        # 10 tests: hashing, tokens, register, login, /me, /refresh
│
└── frontend/                   # React SPA
    ├── .env.example            # VITE_GOOGLE_CLIENT_ID, VITE_API_URL
    ├── package.json            # npm dependencies
    ├── vite.config.js          # Vite + React plugin + Babel React Compiler
    └── src/
        ├── main.jsx            # React DOM root, wraps App in GoogleOAuthProvider
        ├── App.jsx             # BrowserRouter, routes: / /login /register /dashboard
        ├── api/
        │   └── client.js       # Axios: env baseURL, auth interceptor, 401 refresh interceptor
        ├── context/
        │   └── AuthContext.jsx # Auth state: user, login(), logout(), loading
        ├── hooks/
        │   └── useAuth.js      # useContext(AuthContext) with guard
        ├── components/         # Navbar, LoginForm, RegisterForm, GoogleLoginButton, ProtectedRoute
        ├── pages/              # LandingPage, LoginPage, RegisterPage, DashboardPage
        └── styles/             # Per-component CSS files
```

---

## 4. Core Architecture & Data Flow

### Architectural Pattern

**Layered monolith** on the backend (Router → Service → DB), **React SPA** on the frontend. No microservices, no message queues, no WebSockets. All communication is synchronous REST over HTTP.

### Boot Sequence

1. `uvicorn app.main:app --reload` starts the ASGI server.
2. FastAPI imports `main.py`, which imports `settings` (reads `.env`), `engine` (opens PG connection pool: `pool_size=10`, `max_overflow=20`, `pool_pre_ping=True`), both routers, and the shared limiter.
3. The `lifespan` async context manager fires on startup: creates `static/` directory, runs `Base.metadata.create_all(bind=engine)` as a dev convenience fallback.
4. Middleware stack is applied: `StaticFiles` mount at `/static`, `CORSMiddleware` with origins from `settings.allowed_origins`, and the slowapi exception handler.
5. FastAPI generates the OpenAPI schema from all registered routes.

### Primary Request Lifecycle — `POST /reviews/generate`

```
[React DashboardPage]
  → calls generateReview({customer_name, rating, experience})
    → client.js POST /reviews/generate
      (request interceptor adds: Authorization: Bearer <access_token>)

[FastAPI /reviews/generate]
  → OAuth2PasswordBearer extracts token from Authorization header
  → get_current_user(token, db):
      → decode_token(token)           # verifies HS256 signature, expiry, type="access"
      → get_user(db, username)        # SELECT * FROM user_business WHERE user_name = ?
      → returns UserBusiness ORM obj
  → guard: google_place_id must be present (400 if missing)
  → guard: GEMINI_API_KEY must be set  (503 if missing)
  → review_service.generate_review_text(business, rating, customer_name, experience):
      → _build_prompt() → tone-mapped prompt (positive / balanced / constructive)
      → genai.GenerativeModel("gemini-1.5-flash")
            .generate_content(prompt, generation_config={temperature=0.7, max_output_tokens=150},
                              request_options={timeout=10})
      → strips surrounding quotes / backticks from output
  → INSERT INTO generated_reviews (user_id, customer_name, rating, review_text)
  → returns ReviewOut {id, customer_name, rating, review_text, google_review_url, created_at}

[client.js 401 interceptor — only if token expired]
  → POST /auth/refresh {refresh_token}
  → replaces stored tokens
  → retries original request
```

### Authentication Flow — JWT Token Lifecycle

```
Registration → POST /auth/register
  → validates email uniqueness, username uniqueness
  → hashes password with Argon2
  → INSERT INTO user_business
  → returns BusinessOut (id, user_name, email, business_name)

Local Login → POST /auth/login  {login_id, password}
  → authenticate_user: searches user_name | email | mobile_no
    (timing-attack-safe: DUMMY_HASH verify runs even when user not found)
  → create_access_token  → {sub: username, type: "access",  exp: now+30min}
  → create_refresh_token → {sub: username, type: "refresh", exp: now+7days}
  → Token {access_token, refresh_token, token_type: "bearer"}

Google OAuth → POST /auth/google  {credential: <Google ID token>}
  → verify_google_token() → google-auth library verifies against google_client_id
  → upserts UserBusiness (creates on first login, updates on subsequent)
  → issues same Token pair as local login

AuthContext.login(accessToken, refreshToken):
  → stores both in localStorage
  → calls GET /auth/me → UserProfile → populates React user state

Token Refresh → POST /auth/refresh  {refresh_token}
  → decode_token validates signature, expiry, type="refresh"
  → issues new access_token + refresh_token (rotation)

Refresh token expired:
  → all queued requests rejected
  → localStorage cleared → redirect to /login
```

### Database Schema

```sql
user_business
  id              SERIAL PRIMARY KEY
  name            VARCHAR NOT NULL
  user_name       VARCHAR NOT NULL UNIQUE
  business_name   VARCHAR NOT NULL
  email           VARCHAR NOT NULL UNIQUE
  seo_keyword     VARCHAR[] NOT NULL          -- PostgreSQL ARRAY
  mobile_no       VARCHAR NOT NULL DEFAULT ''
  hashed_password VARCHAR                     -- NULL for Google-only accounts
  review_link     VARCHAR NOT NULL DEFAULT ''
  business_desc   TEXT    NOT NULL DEFAULT ''
  qr_code_url     VARCHAR                     -- NULL until first /reviews/qr call
  google_id       VARCHAR UNIQUE              -- NULL for local accounts
  google_place_id VARCHAR                     -- NULL until profile updated
  auth_provider   VARCHAR NOT NULL DEFAULT 'local'

generated_reviews
  id            SERIAL PRIMARY KEY
  user_id       INTEGER NOT NULL REFERENCES user_business(id) ON DELETE CASCADE
  customer_name VARCHAR NOT NULL
  rating        INTEGER NOT NULL              -- 1–5
  review_text   TEXT    NOT NULL
  created_at    TIMESTAMPTZ DEFAULT now()
```

### Rate Limits

| Endpoint           | Limit   |
|--------------------|---------|
| `POST /auth/register` | 5 / minute / IP  |
| `POST /auth/login`    | 10 / minute / IP |
| `POST /auth/google`   | 10 / minute / IP |
| All other endpoints   | Unlimited (no decorator) |

---

## 5. Technical Debt & Blind Spots

### Missing Features (blocking production use)

| Gap | Impact |
|-----|--------|
| No `PATCH /auth/profile` endpoint | Google OAuth users cannot set `google_place_id`, `seo_keyword`, or `review_link` — review generation always fails with 400 |
| No email verification | Any email address accepted at registration with no ownership proof |
| No password reset flow | Users who forget their password have no recovery path |
| No customer-facing public QR landing page | QR code links directly to `review_link`; no branded star-selector UI |
| No pagination on `GET /reviews/history` | Will return unbounded rows as review volume grows |

### Test Suite Issues

- `conftest.py` uses **SQLite** as the test database, but `UserBusiness.seo_keyword` is typed `ARRAY(String)` — a PostgreSQL-specific type. Tests will fail with `CompileError: Dialect must support arrays`. The fixture must either target a PostgreSQL test DB, or `seo_keyword` must be abstracted behind a dialect-agnostic type.
- Register payload is reused across test functions without database teardown between tests. Duplicate-key errors will cascade if tests run in an unexpected order.

### Security

- `SECRET_KEY` in `.env` is a weak static string. It should be `secrets.token_hex(32)` and rotated before any deployment.
- Live Google OAuth client secret is committed to `.env` — must be rotated if this repository is ever pushed to a public remote.
- No HTTPS enforcement — all JWTs and OAuth credentials travel in plaintext over HTTP in development.
- Refresh token rotation is implemented, but there is **no revocation mechanism** — a stolen refresh token remains valid until its 7-day expiry.
- `static/` QR code PNGs are served unauthenticated (anyone with the URL can download any QR code).

### Code Quality

- The lazy import `from app.core.settings import settings as _settings` inside the `generate` endpoint body is unconventional. The module-level import in `services/review.py` is the correct pattern.
- `create_all()` in the lifespan hook is a dev shortcut that bypasses Alembic history — it must be removed before production deployment.
- No structured logging; `print()` / default Uvicorn logs only.
- No health check endpoint (`GET /health`) for load-balancer or container orchestration use.

---

## 6. Environment Variables Reference

### Backend (`backend/.env`)

```env
DATABASE_URL=postgresql+psycopg2://user:password@localhost/dbname
SECRET_KEY=<64-char hex: python -c "import secrets; print(secrets.token_hex(32))">
GOOGLE_CLIENT_ID=<from Google Cloud Console>
GOOGLE_CLIENT_SECRET=<from Google Cloud Console>
GEMINI_API_KEY=<from Google AI Studio>
ALLOWED_ORIGINS=http://localhost:5173   # optional, this is the default
ACCESS_TOKEN_EXPIRE_MINUTES=30          # optional
REFRESH_TOKEN_EXPIRE_DAYS=7             # optional
```

### Frontend (`frontend/.env.local`)

```env
VITE_GOOGLE_CLIENT_ID=<same value as backend GOOGLE_CLIENT_ID>
VITE_API_URL=http://127.0.0.1:8000      # optional, this is the default
```

---

## 7. Running the Project

### Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env   # fill in your values

# Apply migrations
alembic upgrade head

# Start dev server
uvicorn app.main:app --reload
# API available at http://127.0.0.1:8000
# Interactive docs at http://127.0.0.1:8000/docs
```

### Frontend

```bash
cd frontend
npm install
cp .env.example .env.local   # fill in your values
npm run dev
# App available at http://localhost:5173
```

### Tests

```bash
cd backend
pytest tests/ -v
# Note: tests require a PostgreSQL-compatible fixture — see §5 Test Suite Issues
```
