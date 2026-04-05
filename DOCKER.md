# Docker Setup for Chore Checklist App

This document covers running the app with Docker Compose (no manual Python/Node.js installation needed).

## Prerequisites

**Install Docker & Docker Compose:**
- **Windows:** [Docker Desktop](https://www.docker.com/products/docker-desktop) (includes Docker Compose)
- **Mac/Linux:** [Docker](https://docs.docker.com/get-docker/) + [Docker Compose](https://docs.docker.com/compose/install/)

Verify installation:
```bash
docker --version
docker-compose --version
```

## Quick Start

### 1. Build and Run All Services

From the `Chores/` directory:

```bash
docker-compose up --build
```

This will:
- Build the Flask API container
- Build the Angular app container (compiles with Node.js, then serves from nginx)
- Start nginx reverse proxy
- Wait for services to be healthy

**First build may take 2-3 minutes** (Node.js dependencies take time).

### 2. Access the App

- **App:** http://localhost:4200 (or http://localhost via nginx)
- **API directly:** http://localhost:5000
- **API via proxy:** http://localhost/api

### 3. Test the App

1. Open http://localhost:4200 in your browser
2. Drag-drop `Chores/chores.json` into the import area
3. View the weekly checklist, navigate weeks, check items, export/print

### Stopping the App

```bash
docker-compose down
```

To also remove volumes (data):
```bash
docker-compose down -v
```

## Development Workflow

### Hot Reload (Flask API only)

The `docker-compose.yml` mounts the Flask API code locally, so changes to `app/api/*.py` will auto-reload.

**To change Flask code:**
1. Edit `app/api/main.py`, `checklist_service.py`, etc.
2. Save the file
3. Flask will auto-reload within seconds
4. Test via http://localhost:5000/health or http://localhost/api/health

### Rebuilding Angular (After Frontend Changes)

The Angular build happens once during `docker-compose up`. To rebuild:

```bash
docker-compose down
docker-compose up --build
```

Or rebuild just the Angular service:
```bash
docker-compose up --build angular
```

## Production Deployment

The Dockerfile setup is **production-ready** for cloud platforms:

### AWS (ECS/Fargate)
1. Push images to ECR
2. Create ECS task definition with both services
3. Point load balancer to nginx

### Heroku/Railway/Render
1. Merge Dockerfiles into single image if needed
2. Add production environment variables
3. Deploy via container registry

### Docker Hub
```bash
docker build -f Dockerfile.api -t yourname/chore-api .
docker build -f Dockerfile.angular -t yourname/chore-angular .
docker push yourname/chore-api
docker push yourname/chore-angular
```

## Troubleshooting

### Port 80/4200 Already in Use

Check what's using the port:
```bash
# On Windows (PowerShell)
netstat -ano | findstr :4200

# On Mac/Linux
lsof -i :4200
```

Change ports in `docker-compose.yml`:
```yaml
services:
  angular:
    ports:
      - "8200:80"  # Access at http://localhost:8200
```

### Build Fails

Clear cache and rebuild:
```bash
docker-compose down
docker system prune -a
docker-compose up --build
```

### API Not Responding

Check Flask logs:
```bash
docker-compose logs api
```

Health check:
```bash
curl http://localhost:5000/health
```

### Angular Not Loading

Check nginx logs:
```bash
docker-compose logs nginx
```

Verify Angular built correctly:
```bash
docker-compose logs angular
```

## Architecture

```
┌─────────────────────────────────────────────┐
│         User Browser                        │
│     (http://localhost:4200)                 │
└────────────┬────────────────────────────────┘
             │
             ▼
    ┌────────────────────┐
    │  nginx (port 80)   │ ◄─── Reverse Proxy
    └────────┬───────┬───┘
             │       │
        /api │       │ /
             │       │
    ┌────────▼──┐  ┌─▼──────────────┐
    │ Flask API │  │ nginx + Angular │
    │ (port5000)│  │  (port 80)      │
    └───────────┘  └─────────────────┘
```

**Data Flow:**
- User requests http://localhost/api/chores/import
- nginx proxies to Flask at `http://api:5000/chores/import`
- Angular serves from nginx at http://localhost/

## Files Reference

| File | Purpose |
|------|---------|
| `Dockerfile.api` | Flask Python container |
| `Dockerfile.angular` | Angular multi-stage build (Node → nginx) |
| `docker-compose.yml` | Orchestrates both services + nginx |
| `nginx.conf` | Reverse proxy configuration |
| `.dockerignore` | Excludes unnecessary files from build |
| `.env.example` | Environment variable template |

## Environment Variables

Copy `.env.example` to `.env` and customize:

```bash
cp .env.example .env
```

Variables available:
- `FLASK_ENV` — `development` or `production`
- `API_PORT` — Flask port (default 5000)
- `ANGULAR_PORT` — Angular port (default 4200)
- `API_BASE_URL` — URL for Angular to call API

## Next Steps

- **Phase 2:** Add in-app CRUD forms in Angular
- **Phase 3:** LLM transformation endpoints in Flask
- **CI/CD:** Set up GitHub Actions to auto-build and push Docker images
