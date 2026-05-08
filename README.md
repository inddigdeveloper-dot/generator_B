# GMB Review Generator

AI-powered Google My Business review generation for local businesses. Businesses register, authenticate (local or Google OAuth), and generate star-matched review drafts via Gemini 1.5 Flash. The customer scans a QR code, picks a star rating, optionally adds context, and receives a ready-to-paste review — then manually submits it to Google.

## Project Structure

```
generator/
├── backend/   FastAPI + PostgreSQL + SQLAlchemy
└── frontend/  React 19 + Vite + Axios
```

## Prerequisites

- Python 3.12+
- Node.js 20+
- PostgreSQL 15+
- Google Cloud project with OAuth 2.0 credentials
- Google AI Studio API key (Gemini)

---

## Backend Setup

```bash
cd backend

# Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env — fill in DATABASE_URL, SECRET_KEY, GOOGLE_*, GEMINI_API_KEY

# Run database migrations
alembic upgrade head

# Start the dev server  →  http://127.0.0.1:8000
uvicorn app.main:app --reload
```

Interactive API docs: `http://127.0.0.1:8000/docs`

---

## Frontend Setup

```bash
cd frontend
npm install

cp .env.example .env.local
# Edit .env.local — set VITE_GOOGLE_CLIENT_ID (and optionally VITE_API_URL)

npm run dev    # →  http://localhost:5173
```

---

## API Reference

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/auth/register` | — | Register a business account |
| POST | `/auth/login` | — | Login (email / username / mobile + password) |
| POST | `/auth/google` | — | Google OAuth sign-in |
| POST | `/auth/refresh` | — | Exchange refresh token for new token pair |
| GET  | `/auth/me` | Bearer | Get current user profile |
| POST | `/reviews/generate` | Bearer | Generate a review with Gemini |
| GET  | `/reviews/history` | Bearer | List all generated reviews |
| POST | `/reviews/qr` | Bearer | Get / create QR code for the review link |

---

## Running Tests

```bash
cd backend
pytest -v
```

---

## Environment Variables

| Variable | Where | Required | Description |
|---|---|---|---|
| `DATABASE_URL` | backend | ✅ | PostgreSQL connection string |
| `SECRET_KEY` | backend | ✅ | JWT signing key (64-char hex) |
| `GOOGLE_CLIENT_ID` | backend | ✅ | OAuth client ID |
| `GOOGLE_CLIENT_SECRET` | backend | ✅ | OAuth client secret |
| `GEMINI_API_KEY` | backend | ✅ | Gemini AI key |
| `ALLOWED_ORIGINS` | backend | — | Comma-separated CORS origins |
| `VITE_GOOGLE_CLIENT_ID` | frontend | ✅ | Same OAuth client ID |
| `VITE_API_URL` | frontend | — | Backend base URL (default: `http://127.0.0.1:8000`) |

See [`backend/.env.example`](backend/.env.example) and [`frontend/.env.example`](frontend/.env.example).

---

## ⚠️ Google Review Policy Note

Google does not allow auto-posting reviews via API. This tool generates review text and redirects customers to the Google review page — they paste and submit manually. AI-generated text must be framed as helping customers articulate their genuine experience.
