# SimpleSecCheck WebUI

Optional web interface for SimpleSecCheck. **Frontend-only (nginx)** that proxies API calls to the backend worker.

## Overview

The WebUI provides a **user-friendly interface** for interacting with security scan results. It is **frontend-only**, stateless, and communicates with the backend via REST APIs.

## Features

* **Start scans via web interface** – Intuitive forms for configuring and launching scans
* **Live progress and logs** – Real-time monitoring with Server-Sent Events (SSE)
* **View HTML reports** – Interactive security reports with filtering and search
* **Browse local results** – File browser for scan outputs and logs

### Excluded by design

* No history or dashboards – single-shot scans only
* No persistent backend – fully stateless

---

## Architecture

### Frontend Stack

* **Framework:** React + TypeScript
* **Build Tool:** Vite
* **Styling:** CSS-in-JS, responsive design
* **i18n:** English, German, Chinese
* **Web Server:** Nginx

### Container Architecture

```
WebUI Container (nginx)
├── Static frontend files
├── Nginx configuration
└── API proxy to backend worker
```

**Note:** The backend worker container handles scan orchestration, results processing, and API endpoints – this is outside the WebUI container.

---

## Usage

### Start WebUI

```bash
# Development mode
docker compose --profile dev up --build

# Production mode
docker compose up --build

# Access at http://localhost:8080
```

### Development

```bash
# Frontend development
cd frontend/app
npm install
npm run dev
# Vite dev server at http://localhost:5173
```

### Production Build

```bash
cd frontend/app
npm run build

docker compose build
docker compose up -d
```

---

## Configuration

| Variable     | Default | Description            |
| ------------ | ------- | ---------------------- |
| API_BASE_URL | `/api`  | Backend API base URL   |
| LOG_LEVEL    | `info`  | Frontend logging level |
| ENABLE_DEBUG | `false` | Enable debug mode      |

**Nginx handles:**

* Static frontend serving
* Proxying API requests to worker
* SSL termination (optional)
* Caching static files

**Security:**

* CORS headers for API communication
* Content Security Policy
* CSRF protection
* Secure cookies

---

## Development Guidelines

* Use TypeScript for type safety
* Follow React best practices
* Responsive design
* Add i18n for new text
* Unit tests for components
* Proper API error handling and input validation

---

## Troubleshooting

* **WebUI not loading:**

  ```bash
  docker ps | grep frontend
  docker logs simpleseccheck-frontend
  ```
* **API requests failing:**

  ```bash
  curl http://localhost:8000/api/health
  ```
* **Live logs not updating:**

  ```bash
  curl -N -H "Accept: text/event-stream" http://localhost:8000/api/scan/logs
  ```

**Debug mode:**

```bash
export ENABLE_DEBUG=true
docker compose restart frontend
```

---

## Performance Optimization

* Code splitting for faster loading
* Lazy loading of images
* Minimized bundle size
* Efficient state management

---

## Integration & CI/CD

```yaml
- name: Build Frontend
  run: |
    cd frontend/app
    npm install
    npm run build

- name: Build Docker Image
  run: docker build -f frontend/Dockerfile -t simpleseccheck/frontend:latest .

- name: Deploy
  run: docker compose up -d
```

---

## Notes

* WebUI is **completely optional** – CLI works independently
* Stateless, single-shot scans
* Designed **only for scan interaction and results viewing**
* Production mode: Docker image scans use Docker Hub images
