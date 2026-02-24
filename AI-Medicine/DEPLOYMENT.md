# AI-Medicine: Deployment Guide

Best-practice packaging and deployment for **open-source platforms** (Railway, Render, Fly.io), **AWS**, and **self-hosted** environments. The app runs as a **single container**: FastAPI backend + built React frontend on one port.

---

## Quick start (Docker)

```bash
cd AI-Medicine
docker compose up -d
```

Open **http://localhost:8000** — UI and API (Swagger at `/api/docs`) are served from the same origin.

---

## Deploy to a public URL (free tiers)

| Platform | Config file | Deploy | Get URL |
|----------|-------------|--------|---------|
| **Railway** | `railway.json` | Connect GitHub → Auto-deploy | `*.railway.app` |
| **Render** | `render.yaml` | Connect GitHub or `render deploy` | `*.onrender.com` |
| **Fly.io** | `fly.toml` | `fly launch` then `fly deploy` | `*.fly.dev` |

### Railway

1. Push code to GitHub.
2. Go to [railway.app](https://railway.app) → New Project → Deploy from GitHub.
3. Select your repo and the `AI-Medicine` directory (or root if repo is AI-Medicine).
4. Railway detects the Dockerfile and deploys. Set env `CORS_ALLOW_ALL=1` if needed.
5. Your app gets a URL like `https://ai-medicine-production-xxxx.up.railway.app`.

### Render

1. Push code to GitHub.
2. Go to [render.com](https://render.com) → New → Web Service.
3. Connect your repo. Render detects `render.yaml` (Blueprint) or set **Runtime: Docker** manually.
4. Deploy. Your app gets a URL like `https://ai-medicine.onrender.com`.
5. **Note:** Free tier spins down after ~15 min idle; first request may take 30–60s to wake.

### Fly.io

```bash
cd AI-Medicine
fly auth login
fly launch   # first time: creates app, use existing fly.toml
fly deploy   # subsequent deploys
fly open     # open your URL (e.g. https://ai-medicine.fly.dev)
```

Set `CORS_ALLOW_ALL=1` in env (already in `fly.toml`). Free tier includes 3 shared VMs; app may sleep when idle.

---

## Packaging overview

| Artifact | Purpose |
|----------|--------|
| **Dockerfile** | Multi-stage: build frontend (Vite/React), then backend (Python/FastAPI) + static files. Single image, one port. |
| **docker-compose.yml** | Run the app locally or on any host; optional volume for models. |
| **railway.json** | Railway deploy config (Dockerfile, health check). |
| **render.yaml** | Render Blueprint for Docker web service. |
| **fly.toml** | Fly.io app config (port, health check, VM size). |
| **.dockerignore** | Excludes `.venv`, `node_modules`, docs, logs so the image stays small. |
| **.env.example** | Template for `CORS_ORIGINS`, `VITE_API_URL` (and optional `PORT`). |

**Design choices:**

- **Single port:** API at `/api/*` (e.g. `/api/chat`, `/api/diet-plan`, `/api/health`); frontend at `/`, `/diet-plan`, etc. No CORS issues in production.
- **PORT from env:** Railway, Render, and Fly.io set `PORT`; the container uses it automatically.
- **CORS:** Set `CORS_ALLOW_ALL=1` to allow any origin, or `CORS_ORIGINS=https://your-app.fly.dev` for specific domains.
- **Non-root user** in the container; **health check** on `/api/health`.

---

## 1. Docker (any Linux / VM / open-source)

### Build and run

```bash
docker build -t ai-medicine:latest .
docker run -p 8000:8000 --name ai-medicine ai-medicine:latest
```

Or with Compose:

```bash
docker compose up -d
docker compose logs -f app
```

### Optional: mount models

If model checkpoints are large and stored outside the image:

```yaml
# docker-compose.yml
services:
  app:
    ...
    volumes:
      - ./models:/app/models:ro
```

Ensure `backend/model.py` and inference code load from `/app/models` (default project layout already does).

---

## 2. AWS deployment options

### Option A: AWS App Runner (simplest)

- **Fully managed**, auto-scaling, one container.
- Push image to **Amazon ECR**, create App Runner service from that image, set port **8000**.
- No cluster to manage; good for low/medium traffic.

**Steps (high level):**

1. Build and tag:  
   `docker build -t ai-medicine .`  
   Tag for ECR:  
   `docker tag ai-medicine:latest <account>.dkr.ecr.<region>.amazonaws.com/ai-medicine:latest`
2. Push to ECR (create repo if needed, authenticate, push).
3. In **App Runner** → Create service → Container registry (ECR) → select image → set port **8000** → deploy.

### Option B: Amazon ECS (Fargate)

- Run the same Docker image as an ECS task; Fargate = no EC2 to manage.
- Put image in **ECR**. Create ECS cluster, task definition (port 8000, health check `/health`), and service behind an **Application Load Balancer (ALB)**.
- Use **secrets** or **SSM** for any env vars; set `CORS_ORIGINS` to your front-end domain if you ever split UI.

**Task definition (relevant parts):**

- Container port: **8000**
- Health check: `GET http://localhost:8000/api/health` (or use ALB health check on the same path).
- Env: `CORS_ORIGINS` if needed.

### Option C: EC2 + Docker

- Launch an EC2 instance (e.g. Amazon Linux 2 or Ubuntu), install Docker, pull/run the image:

```bash
docker run -d -p 8000:8000 --restart unless-stopped ai-medicine:latest
```

- Put a **reverse proxy** (e.g. Nginx or ALB) in front for HTTPS and optional static caching.
- Use **security groups** so only 80/443 (and optionally 22 for SSH) are open.

---

## 3. Environment variables

| Variable | Used by | Description |
|----------|--------|-------------|
| **CORS_ORIGINS** | Backend (api.py) | Comma-separated origins allowed for CORS (e.g. `https://your-domain.com`). Default includes localhost. |
| **VITE_API_URL** | Frontend (build time) | API base URL. Use `/api` when UI is served from same origin (Docker default). |
| **PORT** | Optional | Override port (default 8000). Adjust CMD in Dockerfile if you use it. |

Copy `.env.example` to `.env` and set values for local or Compose; for AWS, set env in the task definition, App Runner config, or EC2/systemd.

---

## 4. Health check and monitoring

- **Endpoint:** `GET /api/health` → `{"status":"ok"}`.
- **Docker:** `HEALTHCHECK` in the Dockerfile hits `/api/health` inside the container.
- **Railway / Render / Fly.io:** Config files use `/api/health` for health checks.
- **AWS:** Use the same URL for ALB/App Runner health checks so unhealthy tasks are replaced.

---

## 5. Security checklist

- Container runs as **non-root** user (`appuser`).
- **.dockerignore** keeps secrets and dev artifacts out of the image.
- Do **not** bake secrets into the image; use env vars or AWS Secrets Manager/SSM.
- In production, set **CORS_ORIGINS** to your real front-end origin(s) only.
- Prefer **HTTPS** (ALB/App Runner/CloudFront) in front of the container.

---

## 6. Build args (Docker)

For a frontend served from a **different host** than the API:

```bash
docker build --build-arg VITE_API_URL=https://api.your-domain.com -t ai-medicine .
```

Default `VITE_API_URL=/api` is correct when UI and API are on the same origin (single container).

---

## Summary

| Goal | Command / approach |
|------|--------------------|
| **Run locally** | `docker compose up -d` → http://localhost:8000 |
| **Open-source / self-hosted** | Same image on any Docker host; optional Compose. |
| **AWS (easiest)** | ECR + **App Runner**, port 8000. |
| **AWS (flexible)** | ECR + **ECS Fargate** + ALB. |
| **AWS (VM)** | EC2 + Docker + Nginx/ALB. |

All options use the **same Docker image**; only orchestration and env (e.g. CORS, domain) differ.
