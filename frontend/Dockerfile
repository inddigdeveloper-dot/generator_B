FROM node:22-alpine AS builder

WORKDIR /app

# Build args injected by docker-compose
ARG VITE_API_URL=http://localhost:8000
ARG VITE_GOOGLE_CLIENT_ID=placeholder

COPY package*.json ./
RUN npm ci

COPY . .

# Bake the env vars into the Vite build
RUN VITE_API_URL=$VITE_API_URL \
    VITE_GOOGLE_CLIENT_ID=$VITE_GOOGLE_CLIENT_ID \
    npm run build

# ── Production image (nginx) ─────────────────────────────────────────────────
FROM nginx:alpine

COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
