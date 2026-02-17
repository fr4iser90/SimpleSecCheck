# Docker Build und Push Anleitung

Diese Anleitung erklärt, wie du das SimpleSecCheck Docker Image lokal baust und zu Docker Hub pushst.

## Voraussetzungen

1. **Docker Hub Account** - Du musst bei [Docker Hub](https://hub.docker.com) registriert sein
2. **Docker CLI** - Installiert und konfiguriert
3. **Docker Hub Login** - Bereits eingeloggt oder bereit zum Einloggen

## Schritt 1: Docker Hub Login

```bash
# Login zu Docker Hub
docker login

# Oder mit Username (wenn nicht interaktiv)
docker login -u fr4iser
```

## Schritt 2: Image lokal bauen

### Option A: Mit docker-compose (empfohlen)

```bash
# Build mit Version 1.4.0 (aus docker-compose.yml)
docker-compose build scanner

# Oder mit expliziter Version
docker-compose build --build-arg VERSION=1.4.0 scanner
```

### Option B: Mit docker build direkt

```bash
# Build mit Version 1.4.0
docker build \
  --build-arg VERSION=1.4.0 \
  -t fr4iser/simpleseccheck:1.4.0 \
  -t fr4iser/simpleseccheck:latest \
  .

# Oder kürzer (Version aus Dockerfile ARG)
docker build -t fr4iser/simpleseccheck:1.4.0 -t fr4iser/simpleseccheck:latest .
```

## Schritt 3: Image testen (optional)

```bash
# Test ob Image funktioniert
docker run --rm fr4iser/simpleseccheck:1.4.0 --help

# Oder mit docker-compose
docker-compose run --rm scanner --help
```

## Schritt 4: Image zu Docker Hub pushen

### Option A: Einzelne Tags pushen

```bash
# Push Version Tag
docker push fr4iser/simpleseccheck:1.4.0

# Push Latest Tag
docker push fr4iser/simpleseccheck:latest
```

### Option B: Alle Tags auf einmal pushen

```bash
# Push alle Tags des Images
docker push fr4iser/simpleseccheck:1.4.0
docker push fr4iser/simpleseccheck:latest
```

### Option C: Mit docker-compose

```bash
# Tag und Push (wenn image bereits gebaut)
docker tag simpleseccheck_scanner:latest fr4iser/simpleseccheck:1.4.0
docker tag simpleseccheck_scanner:latest fr4iser/simpleseccheck:latest
docker push fr4iser/simpleseccheck:1.4.0
docker push fr4iser/simpleseccheck:latest
```

## Schritt 5: Verifizierung

```bash
# Prüfe ob Image auf Docker Hub verfügbar ist
docker pull fr4iser/simpleseccheck:1.4.0

# Oder im Browser
# https://hub.docker.com/r/fr4iser/simpleseccheck/tags
```

## Vollständiges Beispiel (One-Liner)

```bash
# Alles in einem: Build + Tag + Push
docker build --build-arg VERSION=1.4.0 -t fr4iser/simpleseccheck:1.4.0 -t fr4iser/simpleseccheck:latest . && \
docker push fr4iser/simpleseccheck:1.4.0 && \
docker push fr4iser/simpleseccheck:latest
```

## Mit GitHub Actions (automatisch)

Alternativ kannst du auch GitHub Actions verwenden:

1. **GitHub Secrets einrichten:**
   - `DOCKERHUB_USERNAME`: `fr4iser`
   - `DOCKERHUB_TOKEN`: Dein Docker Hub Personal Access Token

2. **Workflow manuell starten:**
   - Gehe zu GitHub → Actions
   - Wähle "Build and Push Docker Image"
   - Klicke "Run workflow"

Die Workflow-Datei (`.github/workflows/docker-build-push.yml`) ist bereits konfiguriert mit Version 1.4.0.

## Troubleshooting

### "denied: requested access to the resource is denied"
- Stelle sicher, dass du eingeloggt bist: `docker login`
- Prüfe ob der Repository-Name korrekt ist: `fr4iser/simpleseccheck`

### "unauthorized: authentication required"
- Docker Hub Token könnte abgelaufen sein
- Erstelle neuen Token: https://hub.docker.com/settings/security

### Build dauert sehr lange
- Das ist normal - das Image enthält viele Tools
- Erste Builds dauern ~15-30 Minuten
- Nachfolgende Builds sind schneller durch Layer Caching

## Version Management

Wenn du eine neue Version pushen willst:

1. **Version in Dateien updaten:**
   - `VERSION` → neue Version (z.B. `1.4.0`)
   - `Dockerfile` → `ARG VERSION=1.4.0`
   - `docker-compose.yml` → `VERSION: 1.4.0`
   - `.github/workflows/docker-build-push.yml` → `VERSION=1.4.0`

2. **Build und Push:**
   ```bash
   docker build --build-arg VERSION=1.4.0 -t fr4iser/simpleseccheck:1.4.0 -t fr4iser/simpleseccheck:latest . && \
   docker push fr4iser/simpleseccheck:1.4.0 && \
   docker push fr4iser/simpleseccheck:latest
   ```

3. **Git Tag erstellen (optional):**
   ```bash
   git tag -a v1.4.0 -m "Release version 1.4.0"
   git push origin v1.4.0
   ```
