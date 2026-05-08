# GMB Review Generator — Frontend

React 19 + Vite frontend for the GMB Review Generator.

## Setup

```bash
npm install
cp .env.example .env.local   # fill in VITE_GOOGLE_CLIENT_ID
npm run dev                   # http://localhost:5173
```

## Key environment variables

| Variable | Description |
|---|---|
| `VITE_GOOGLE_CLIENT_ID` | Google OAuth client ID |
| `VITE_API_URL` | Backend base URL (default: `http://127.0.0.1:8000`) |

## Scripts

| Command | Description |
|---|---|
| `npm run dev` | Start dev server with HMR |
| `npm run build` | Production build to `dist/` |
| `npm run lint` | Run ESLint |
| `npm run preview` | Preview production build |
