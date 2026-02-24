# AI-Medicine: multi-stage build — frontend (Vite/React) + backend (FastAPI)
# Best practice: single image serving API + static frontend on one port

# -----------------------------------------------------------------------------
# Stage 1: Build frontend
# -----------------------------------------------------------------------------
FROM node:20-alpine AS frontend-builder

WORKDIR /app/frontend

COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci

# API base URL when served from same origin (relative /api)
ARG VITE_API_URL=/api
ENV VITE_API_URL=${VITE_API_URL}

COPY frontend/ ./
RUN npm run build

# -----------------------------------------------------------------------------
# Stage 2: Backend + serve frontend static files
# -----------------------------------------------------------------------------
FROM python:3.12-slim AS backend

# System deps for audio (ffmpeg for whisper/video), optional
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps (no venv in container)
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend and config
COPY api.py ./
COPY backend/ ./backend/
COPY config/ ./config/
COPY data/ ./data/
COPY models/ ./models/
COPY scripts/ ./scripts/

# Copy built frontend from stage 1
COPY --from=frontend-builder /app/frontend/dist ./frontend_dist

# Non-root user for security
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Single port: API + static frontend (PORT from env for Railway, Render, Fly.io)
ENV PORT=8000
EXPOSE 8000

# Health check (API at /api/health; uses PORT for cloud platforms)
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c "import os,urllib.request; urllib.request.urlopen('http://127.0.0.1:'+os.environ.get('PORT','8000')+'/api/health')" || exit 1

# Shell form so PORT env is expanded (cloud platforms set PORT)
CMD ["sh", "-c", "uvicorn api:app --host 0.0.0.0 --port ${PORT:-8000}"]
