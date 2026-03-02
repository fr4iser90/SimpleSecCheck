# SimpleSecCheck: Production & Development Roadmap

## Übersicht

Dieses Dokument beschreibt die geplante Trennung zwischen **Development** und **Production** Umgebungen für SimpleSecCheck, sowie die spezifischen Features und Anforderungen für die Production-Version.

---

## 🎯 Ziele

### Development (Self-Hosted)
- **Vollständige Funktionalität**: Alle Features verfügbar
- **Mehr Capabilities**: Erweiterte Docker Capabilities für Entwicklung
- **Flexibilität**: Alle Scan-Typen (Code, Website, Network)
- **Lokale Nutzung**: Für Entwickler und interne Tests

### Production (Public Service)
- **Eingeschränkte Funktionalität**: Nur GitHub/GitLab Scans
- **Single-Repo Queue**: Nur ein Repository pro Scan, mit Warteschlange
- **Keine User-Logins**: Unique Sessions pro Nutzer
- **Metadata Collection**: Immer aktiviert
- **Scan-Deduplizierung**: Intelligente Prüfung auf bereits existierende Scans
- **Statistiken**: Aggregierte Findings-Statistiken
- **ZIP Upload**: Optional für Codebase-Upload
- **Öffentliche Queue**: Sichtbare Warteschlange (anonymisiert)

---

## 📋 Feature-Übersicht

### Development Features (Dev Mode)

#### ✅ Alle aktuellen Features
- Code Scans (lokale Pfade)
- Website Scans
- Network Scans
- Git Repository Scans (GitHub/GitLab)
- Batch Scans
- Alle Scan-Typen verfügbar
- Vollständige Docker Capabilities
- Keine Einschränkungen

#### 🔧 Erweiterte Capabilities
- Privileged Mode (optional)
- Erweiterte Docker Capabilities
- Volle System-Zugriffe für Entwicklung

---

### Production Features (Prod Mode)

#### 🔒 Sicherheit & Zugriff
- **Unique Session Management**
  - Jede Session bekommt eine eindeutige ID (UUID)
  - Keine User-Logins oder Authentifizierung
  - Sessions sind temporär (z.B. 24h Gültigkeit)
  - Session-Tracking für Rate-Limiting

#### 📦 Scan-Einschränkungen
- **Nur GitHub/GitLab Scans**
  - Blockierung aller anderen Scan-Typen (Website, Network, lokale Pfade)
  - Nur Git Repository URLs erlaubt
  - Validierung der URL-Formate

- **Single-Repo Queue System**
  - Nur ein Repository pro Scan-Request
  - Warteschlange für eingehende Scans
  - Priorisierung (FIFO oder nach Priorität)
  - Queue-Status für alle sichtbar

#### 📊 Metadata & Tracking
- **Metadata Collection (Immer Aktiv)**
  - Automatische Sammlung von Git-Informationen
  - Commit-Hash, Branch, Repository-URL
  - Scan-Zeitstempel, Scan-ID
  - Projekt-Name, Scan-Typ

- **Scan-Deduplizierung**
  - Prüfung auf bereits existierende Scans für dasselbe Repository
  - Vergleich von Commit-Hash und Branch
  - Wenn identischer Commit bereits gescannt → Ergebnis wiederverwenden
  - Wenn neuer Commit → Neuer Scan
  - Metadata-basierte Entscheidung

#### 📈 Statistiken
- **Findings-Statistiken**
  - Aggregierte Anzahl von Findings pro Scan
  - False-Positive Tracking (wenn markiert)
  - Statistiken nach Severity (Critical, High, Medium, Low, Info)
  - Statistiken nach Tool (Semgrep, Trivy, etc.)
  - Zeitliche Entwicklung (optional)

#### 📤 Upload-Funktionalität
- **ZIP File Upload**
  - Upload von Codebase als ZIP-Datei
  - Automatische Extraktion
  - Temporäre Speicherung
  - Cleanup nach Scan
  - Größenlimit (z.B. 100MB)

#### 👁️ Öffentliche Queue
- **Queue-Liste für alle sichtbar**
  - Öffentlicher Endpoint: `/api/queue`
  - Anonymisierte Informationen:
    - Repository-Name (anonymisiert: `repo_abc123`)
    - Position in Queue
    - Status (pending, running, completed, failed)
    - Geschätzte Wartezeit
  - Keine persönlichen Daten
  - Keine Commit-Hashes oder Branches

---

## 🏗️ Architektur-Änderungen

### Docker Compose Files & Dockerfiles

#### Dockerfile-Struktur (Aktuell - GUT so!)

**Zwei Dockerfiles sind normal und korrekt:**
1. **`Dockerfile`** (Root) - Scanner Image
   - Enthält alle Security Tools (Semgrep, Trivy, CodeQL, etc.)
   - Wird von Dev UND Prod verwendet (gleiches Image)
   - Unterschiede nur über Environment-Variablen

2. **`webui/Dockerfile.compose`** - WebUI Image
   - FastAPI Backend + React Frontend
   - Wird von Dev UND Prod verwendet (gleiches Image)
   - Unterschiede nur über Environment-Variablen

**Warum diese Struktur gut ist:**
- ✅ **Standard-Praxis**: Ein Dockerfile pro Service
- ✅ **DRY-Prinzip**: Keine Code-Duplikation
- ✅ **Einfach**: Unterschiede über Environment-Variablen, nicht über separate Dockerfiles
- ✅ **Wartbar**: Änderungen nur an einer Stelle

**Empfehlung: BEHALTEN!**
- ❌ **NICHT** separate Dockerfiles für Dev/Prod machen
- ✅ Unterschiede über Environment-Variablen steuern
- ✅ Separate docker-compose Files für Dev/Prod (haben wir schon)

#### `docker-compose.dev.yml` (Development)

**Services:**
- `scanner` - Scanner Container (gleiches Image wie Prod)
- `webui` - WebUI Container (gleiches Image wie Prod)

**Features:**
- Alle Scan-Typen erlaubt (über `ENVIRONMENT=dev`)
- Erweiterte Docker Capabilities (optional)
- Auto-Shutdown aktiv (`WEBUI_AUTO_SHUTDOWN=true`)
- File-Based Database (`DATABASE_TYPE=file`)
- Keine Einschränkungen

**Environment-Variablen:**
```yaml
environment:
  - ENVIRONMENT=dev
  - WEBUI_AUTO_SHUTDOWN=true
  - DATABASE_TYPE=file
  - ENABLE_ALL_SCAN_TYPES=true
```

#### `docker-compose.prod.yml` (Production)

**Services:**
- `scanner` - Scanner Container (gleiches Image wie Dev)
- `webui` - WebUI Container (gleiches Image wie Dev)
- `postgres` - PostgreSQL Database (NEU für Production)

**Features:**
- Nur GitHub/GitLab Scans (über `ENVIRONMENT=prod`)
- Eingeschränkte Docker Capabilities
- Auto-Shutdown deaktiviert (`WEBUI_AUTO_SHUTDOWN=false`)
- PostgreSQL Database (`DATABASE_TYPE=postgresql`)
- Rate-Limiting
- Session-Management
- Queue-System
- Metadata-Collection (immer aktiv)

**Environment-Variablen:**
```yaml
environment:
  - ENVIRONMENT=prod
  - WEBUI_AUTO_SHUTDOWN=false
  - DATABASE_TYPE=postgresql
  - DATABASE_URL=postgresql://ssc_user:${POSTGRES_PASSWORD}@postgres:5432/simpleseccheck
```

**PostgreSQL Service (NEU):**
```yaml
postgres:
  image: postgres:16-alpine
  environment:
    POSTGRES_DB: simpleseccheck
    POSTGRES_USER: ssc_user
    POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
  volumes:
    - postgres_data:/var/lib/postgresql/data
  networks:
    - SimpleSecCheck_network
  restart: unless-stopped
```

### Environment Variables

**Wichtig**: 
- **Nur `ENVIRONMENT=dev` oder `ENVIRONMENT=prod` ist erforderlich!**
- Das System erkennt automatisch den Modus und aktiviert/deaktiviert Features entsprechend

**Feature-Status in Production Mode:**

| Feature | Status | Deaktivierbar? | Hinweis |
|---------|--------|----------------|---------|
| `ONLY_GIT_SCANS` | ✅ Pflicht | ❌ Nein | Immer aktiv in Prod |
| `SESSION_MANAGEMENT` | ✅ Pflicht | ❌ Nein | Immer aktiv in Prod |
| `METADATA_COLLECTION` | ✅ Pflicht | ❌ Nein | Immer aktiv in Prod |
| `QUEUE_ENABLED` | ✅ Pflicht | ❌ Nein | **Immer aktiv in Prod - ESSENTIELL für Stabilität!** |
| `WEBUI_AUTO_SHUTDOWN` | ❌ Deaktiviert | ❌ Nein | **Immer deaktiviert in Prod - Service muss dauerhaft laufen!** |
| `STATISTICS_ENABLED` | 📊 Optional | ✅ Ja | Kann frei deaktiviert werden |
| `ZIP_UPLOAD_ENABLED` | 📤 Optional | ✅ Ja | Kann frei deaktiviert werden |
| `MAX_ZIP_UPLOAD_SIZE` | ⚙️ Konfigurierbar | ✅ Ja | Größenlimit für ZIP Upload (Standard: 100MB) |
| `MAX_GIT_REPO_SIZE` | ⚙️ Konfigurierbar | ✅ Ja | Größenlimit für Git Repos (Standard: 500MB) |
| `MAX_SCAN_DISK_USAGE` | ⚙️ Konfigurierbar | ✅ Ja | Max. Disk-Space pro Scan (Standard: 2GB) |

#### Dev Mode
```bash
# Minimal: Nur diese Variable reicht
ENVIRONMENT=dev

# Optional: Spezifische Features explizit setzen
ENABLE_ALL_SCAN_TYPES=true
DOCKER_CAPABILITIES=extended
WEBUI_AUTO_SHUTDOWN=true         # Auto-Shutdown aktiv (lokale, temporäre Nutzung)
```

**Verhalten in Dev Mode:**
- Alle Scan-Typen erlaubt (Code, Website, Network, Git)
- Erweiterte Docker Capabilities
- Auto-Shutdown aktiv (Service schaltet sich nach Inaktivität ab)
- Keine Einschränkungen

#### Prod Mode
```bash
# Minimal: Nur diese Variable reicht
ENVIRONMENT=prod

# Optional: Spezifische Features explizit setzen/überschreiben
ONLY_GIT_SCANS=true          # Pflicht in Prod (kann nicht deaktiviert werden)
SESSION_MANAGEMENT=true      # Pflicht in Prod (kann nicht deaktiviert werden)
METADATA_COLLECTION=always   # Pflicht in Prod (kann nicht deaktiviert werden)
QUEUE_ENABLED=true           # Pflicht in Prod (kann nicht deaktiviert werden - ESSENTIELL!)
WEBUI_AUTO_SHUTDOWN=false    # Automatisch deaktiviert in Prod (Service muss dauerhaft laufen!)
STATISTICS_ENABLED=true      # Optional
ZIP_UPLOAD_ENABLED=true      # Optional
```

**Verhalten in Prod Mode:**

**Pflicht-Features** (können NICHT deaktiviert werden):
- ✅ Nur GitHub/GitLab Scans erlaubt (`ONLY_GIT_SCANS` ist immer aktiv)
- ✅ Session Management aktiv (`SESSION_MANAGEMENT` ist immer aktiv)
- ✅ Metadata Collection immer aktiv (`METADATA_COLLECTION=always` ist immer aktiv)
- ✅ **Queue System aktiv** (`QUEUE_ENABLED` ist immer aktiv - **ESSENTIELL für Stabilität!**)
- ✅ **Auto-Shutdown DEAKTIVIERT** (`WEBUI_AUTO_SHUTDOWN=false` ist immer aktiv - **Service muss dauerhaft laufen!**)
- ✅ Eingeschränkte Docker Capabilities

**Warum Queue Pflicht ist:**
- **Schutz vor Überlastung**: Verhindert Server-Crash bei vielen gleichzeitigen Scans
- **Fairness**: Alle Scans werden fair behandelt (FIFO)
- **Kontrollierbarkeit**: Max. 2-3 Scans parallel (konfigurierbar)
- **DoS-Schutz**: Verhindert Angriffe durch viele gleichzeitige Requests
- **Stabilität**: System bleibt auch bei hoher Last stabil

**Optionale Features** (können frei deaktiviert werden):
- 📊 Statistiken (`STATISTICS_ENABLED=false` möglich)
- 📤 ZIP Upload (`ZIP_UPLOAD_ENABLED=false` möglich)

**Deaktivierte Features in Production** (automatisch deaktiviert):
- ❌ **Auto-Shutdown** (`WEBUI_AUTO_SHUTDOWN=false` - Service muss dauerhaft laufen)
  - **Warum deaktiviert?** 
    - Production-Service muss 24/7 verfügbar sein
    - Nutzer erwarten, dass Service immer erreichbar ist
    - Auto-Shutdown würde Service nach Inaktivität beenden
    - In Production: Service wird durch Docker/systemd/Container-Orchestrator verwaltet
  - **In Dev**: Auto-Shutdown aktiv (lokale, temporäre Nutzung, schützt vor vergessenen Instanzen)
  - **In Prod**: Auto-Shutdown deaktiviert (dauerhafter Service, wird extern verwaltet)

---

## 🔐 Session Management (Production)

### Konzept
- **Keine User-Logins**: Jede Session ist anonym
- **Unique Session IDs**: UUID-basiert
- **Session-Lebensdauer**: 24 Stunden (konfigurierbar)
- **Session-Tracking**: In-Memory oder Redis (optional)

### Implementierung
```python
# Session-Struktur
{
    "session_id": "uuid-v4",
    "created_at": "2026-02-17T10:00:00Z",
    "expires_at": "2026-02-18T10:00:00Z",
    "scans_requested": 0,
    "rate_limit": 10,  # Scans pro Stunde
    "ip_address": "anonymized"  # Optional, für Rate-Limiting
}
```

### Session-Übertragung: Header vs. Cookie

#### Option 1: HTTP Header (Empfohlen für API)

**Vorteile:**
- ✅ **Einfacher für API-Clients**: Direkt im Header setzen
- ✅ **Keine CORS-Probleme**: Cookies haben komplexe CORS-Regeln
- ✅ **Klarer für Entwickler**: Explizit im Code sichtbar
- ✅ **Keine SameSite-Probleme**: Cookies haben SameSite-Restrictions
- ✅ **Einfacher für Mobile Apps**: Keine Cookie-Handling nötig
- ✅ **Besser für REST APIs**: Standard-Praxis für API-Tokens

**Nachteile:**
- ⚠️ **Nicht automatisch**: Frontend muss Session-ID manuell speichern (localStorage)
- ⚠️ **XSS-Risiko**: Wenn localStorage verwendet wird (aber Session-ID ist nicht sensitiv)

**Implementierung:**
```python
# Backend: Header-basiert
@app.middleware("http")
async def session_middleware(request: Request, call_next):
    session_id = request.headers.get("X-Session-ID")
    if not session_id:
        # Erstelle neue Session
        session_id = str(uuid.uuid4())
    
    # Validiere Session
    if not is_valid_session(session_id):
        return JSONResponse({"error": "Invalid session"}, status_code=401)
    
    # Füge Session-ID zu Request hinzu
    request.state.session_id = session_id
    response = await call_next(request)
    response.headers["X-Session-ID"] = session_id
    return response
```

```typescript
// Frontend: Header-basiert
const sessionId = localStorage.getItem('session_id') || generateSessionId();
localStorage.setItem('session_id', sessionId);

fetch('/api/scan/start', {
  headers: {
    'X-Session-ID': sessionId
  }
});
```

#### Option 2: HTTP Cookie

**Vorteile:**
- ✅ **Automatisch**: Browser sendet Cookie automatisch mit
- ✅ **Einfacher für Frontend**: Kein manuelles Handling nötig
- ✅ **HttpOnly möglich**: Schutz vor XSS (wenn HttpOnly gesetzt)

**Nachteile:**
- ❌ **CORS-Komplexität**: `credentials: 'include'` nötig, spezifische Origins
- ❌ **SameSite-Probleme**: Cross-Site-Requests können blockiert werden
- ❌ **Schwieriger für API-Clients**: Manuelles Cookie-Handling nötig
- ❌ **Mobile Apps**: Komplexeres Cookie-Management

**Implementierung:**
```python
# Backend: Cookie-basiert
@app.middleware("http")
async def session_middleware(request: Request, call_next):
    session_id = request.cookies.get("session_id")
    if not session_id:
        session_id = str(uuid.uuid4())
    
    if not is_valid_session(session_id):
        return JSONResponse({"error": "Invalid session"}, status_code=401)
    
    request.state.session_id = session_id
    response = await call_next(request)
    response.set_cookie(
        "session_id",
        session_id,
        max_age=86400,  # 24 Stunden
        httponly=True,  # Schutz vor XSS
        samesite="lax",  # CSRF-Schutz
        secure=True  # Nur HTTPS (in Production)
    )
    return response
```

```typescript
// Frontend: Cookie-basiert (automatisch)
fetch('/api/scan/start', {
  credentials: 'include'  // Wichtig für Cookies!
});
```

#### Option 3: Beide unterstützen (Hybrid - Beste Lösung!)

**Empfehlung: Beide Methoden unterstützen**

**Warum Hybrid?**
- ✅ **Flexibilität**: Frontend kann Cookie verwenden (einfach)
- ✅ **API-Clients**: Können Header verwenden (Standard)
- ✅ **Best of both worlds**: Jeder kann die passende Methode wählen

**Implementierung:**
```python
# Backend: Hybrid (Cookie ODER Header)
@app.middleware("http")
async def session_middleware(request: Request, call_next):
    # Prüfe zuerst Cookie, dann Header
    session_id = request.cookies.get("session_id") or request.headers.get("X-Session-ID")
    
    if not session_id:
        session_id = str(uuid.uuid4())
    
    if not is_valid_session(session_id):
        return JSONResponse({"error": "Invalid session"}, status_code=401)
    
    request.state.session_id = session_id
    response = await call_next(request)
    
    # Setze beides: Cookie für Browser, Header für API-Clients
    response.set_cookie(
        "session_id",
        session_id,
        max_age=86400,
        httponly=True,
        samesite="lax",
        secure=True
    )
    response.headers["X-Session-ID"] = session_id
    return response
```

### Empfehlung: Hybrid-Ansatz

**Für Production:**
1. **Primär: Cookie** (für Browser-Frontend)
   - Automatisch, einfach
   - HttpOnly für XSS-Schutz
   - SameSite für CSRF-Schutz

2. **Sekundär: Header** (für API-Clients)
   - Standard für REST APIs
   - Keine CORS-Probleme
   - Einfacher für Mobile Apps

3. **Validierung:**
   - Prüfe zuerst Cookie, dann Header
   - Wenn beide vorhanden, müssen sie übereinstimmen
   - Wenn keine vorhanden, erstelle neue Session

### API-Änderungen

**Alle Endpoints:**
- Session-ID wird automatisch erstellt beim ersten Request
- Session-Validation Middleware prüft bei jedem Request
- Session wird in Response zurückgegeben (Cookie + Header)

**Session-Endpoints:**
- `GET /api/session` - Aktuelle Session-Info
- `POST /api/session/refresh` - Session verlängern
- `DELETE /api/session` - Session beenden (optional)

### Frontend-Integration

**Automatisch:**
- Browser sendet Cookie automatisch mit
- Frontend muss nichts tun (außer `credentials: 'include'`)

**Manuell (wenn Header gewünscht):**
- Session-ID aus Cookie lesen
- In Header `X-Session-ID` setzen
- Oder localStorage verwenden (wenn Cookie nicht gewünscht)

---

## 🌐 Öffentliche API-Nutzung

### Konzept
- **Öffentliche REST API** für externe Clients
- **Session-basiert** (keine API-Keys nötig)
- **OpenAPI/Swagger-Dokumentation** automatisch verfügbar
- Für Browser, Mobile Apps, CI/CD, Scripts, etc.

### API-Dokumentation

**Automatisch verfügbar:**
- `GET /docs` - Swagger UI (interaktive API-Dokumentation)
- `GET /redoc` - ReDoc (alternative API-Dokumentation)
- `GET /openapi.json` - OpenAPI Schema (JSON)

**Beispiel:**
```
https://your-service.com/docs          # Swagger UI
https://your-service.com/redoc         # ReDoc
https://your-service.com/openapi.json  # OpenAPI Schema
```

### API-Endpoints (Öffentlich verfügbar)

**Session Management:**
- `GET /api/session` - Aktuelle Session-Info
- `POST /api/session/refresh` - Session verlängern
- `DELETE /api/session` - Session beenden (optional)

**Scan Management:**
- `POST /api/scan/start` - Scan starten
- `GET /api/scan/status` - Scan-Status abfragen
- `GET /api/scan/logs` - Scan-Logs abrufen
- `GET /api/scan/report` - HTML-Report abrufen
- `POST /api/scan/stop` - Scan stoppen

**Queue Management:**
- `POST /api/queue/add` - Scan zur Queue hinzufügen
- `GET /api/queue` - Öffentliche Queue-Liste (anonymisiert)
- `GET /api/queue/{queue_id}/status` - Status eines Scans
- `GET /api/queue/my-scans` - Eigene Scans (via Session-ID)

**GitHub/GitLab Integration:**
- `GET /api/git/branches?url=...` - Branches abrufen
- `GET /api/github/repos?username=...` - Repositories auflisten
- `GET /api/github/rate-limit` - Rate-Limit-Info
- `POST /api/github/validate-token` - GitHub Token validieren

**Statistiken:**
- `GET /api/statistics/overview` - Gesamt-Übersicht
- `GET /api/statistics/by-severity` - Nach Severity
- `GET /api/statistics/by-tool` - Nach Tool
- `GET /api/statistics/false-positives` - False-Positive Rate

**Upload:**
- `POST /api/upload/zip` - ZIP-Datei hochladen

**Health:**
- `GET /api/health` - Health-Check (keine Session nötig)

### Authentifizierung

**Session-basiert (keine API-Keys):**
1. Erste Anfrage → automatisch neue Session
2. Session-ID in Cookie oder Header `X-Session-ID`
3. Session-ID bei jeder Anfrage mitsenden

**Beispiel (curl):**
```bash
# 1. Erste Anfrage - Session wird automatisch erstellt
curl -X GET https://your-service.com/api/health

# Response enthält Session-ID im Cookie oder Header
# Cookie: session_id=abc123...
# Oder Header: X-Session-ID: abc123...

# 2. Weitere Anfragen mit Session-ID
curl -X POST https://your-service.com/api/scan/start \
  -H "X-Session-ID: abc123..." \
  -H "Content-Type: application/json" \
  -d '{"type": "code", "target": "https://github.com/user/repo"}'

# Oder mit Cookie:
curl -X POST https://your-service.com/api/scan/start \
  -H "Cookie: session_id=abc123..." \
  -H "Content-Type: application/json" \
  -d '{"type": "code", "target": "https://github.com/user/repo"}'
```

### Beispiel-Nutzung

**Python:**
```python
import requests

# Base URL
BASE_URL = "https://your-service.com"

# Session-ID wird automatisch erstellt beim ersten Request
session = requests.Session()
response = session.get(f"{BASE_URL}/api/health")
# Session-ID ist jetzt im Cookie gespeichert

# Scan starten
scan_response = session.post(
    f"{BASE_URL}/api/scan/start",
    json={
        "type": "code",
        "target": "https://github.com/user/repo",
        "git_branch": "main"
    }
)

# Status abfragen
status = session.get(f"{BASE_URL}/api/scan/status").json()
print(f"Scan Status: {status['status']}")
```

**JavaScript/TypeScript:**
```typescript
// Session-ID wird automatisch im Cookie gespeichert
const response = await fetch('https://your-service.com/api/scan/start', {
  method: 'POST',
  credentials: 'include',  // Wichtig für Cookies!
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    type: 'code',
    target: 'https://github.com/user/repo',
    git_branch: 'main'
  })
});
```

**CI/CD (GitHub Actions):**
```yaml
- name: Scan Repository
  run: |
    # Session-ID aus Secret (oder automatisch erstellen)
    SESSION_ID=$(curl -s -X GET https://your-service.com/api/health | jq -r '.session_id')
    
    # Scan starten
    curl -X POST https://your-service.com/api/scan/start \
      -H "X-Session-ID: $SESSION_ID" \
      -H "Content-Type: application/json" \
      -d '{"type": "code", "target": "${{ github.repositoryUrl }}"}'
```

### CORS-Konfiguration

**Production:**
```python
# Erlaubte Origins (konfigurierbar via Environment-Variable)
ALLOWED_ORIGINS = os.getenv("CORS_ALLOWED_ORIGINS", "").split(",")
# Beispiel: CORS_ALLOWED_ORIGINS=https://your-frontend.com,https://app.your-service.com

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS if ALLOWED_ORIGINS else ["*"],  # In Prod: spezifische Origins!
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"],
)
```

**Environment-Variable:**
```bash
# .env.prod
CORS_ALLOWED_ORIGINS=https://your-frontend.com,https://app.your-service.com
```

### Rate-Limiting

**Pro Session:**
- Max. 10 Scans/Stunde
- Max. 100 API-Requests/Minute

**Pro IP (optional):**
- Max. 50 Scans/Tag
- Max. 1000 API-Requests/Stunde

**Konfigurierbar:**
```bash
# .env.prod
RATE_LIMIT_PER_SESSION_SCANS=10        # Scans pro Stunde
RATE_LIMIT_PER_SESSION_REQUESTS=100    # Requests pro Minute
RATE_LIMIT_PER_IP_SCANS=50             # Scans pro Tag
RATE_LIMIT_PER_IP_REQUESTS=1000        # Requests pro Stunde
```

### API-Versionierung

**Empfehlung:**
- `/api/v1/...` für zukünftige Versionen
- Aktuell: `/api/...` (v1, implizit)
- Bei Breaking Changes: `/api/v2/...`

**Implementierung:**
```python
# Router für Versionierung
from fastapi import APIRouter

v1_router = APIRouter(prefix="/api/v1")
v1_router.post("/scan/start", ...)

app.include_router(v1_router)
# Legacy: app.post("/api/scan/start", ...)  # Weiterhin unterstützt
```

### Öffentliche Dokumentation

**Was sollte öffentlich sein:**
- ✅ API-Endpoints dokumentiert
- ✅ Request/Response-Schemas
- ✅ Beispiel-Code
- ✅ Rate-Limits dokumentiert
- ✅ Fehler-Codes dokumentiert
- ✅ OpenAPI/Swagger automatisch generiert

**Was sollte nicht öffentlich sein:**
- ❌ Interne Implementierungsdetails
- ❌ Admin-Endpoints
- ❌ Sensitive Konfiguration
- ❌ Session-IDs in Logs (anonymisiert)

### Fehlerbehandlung

**Standard HTTP Status Codes:**
- `200 OK` - Erfolgreich
- `201 Created` - Ressource erstellt
- `400 Bad Request` - Ungültige Anfrage
- `401 Unauthorized` - Ungültige Session
- `403 Forbidden` - Keine Berechtigung
- `404 Not Found` - Ressource nicht gefunden
- `409 Conflict` - Konflikt (z.B. Scan läuft bereits)
- `429 Too Many Requests` - Rate-Limit überschritten
- `500 Internal Server Error` - Server-Fehler

**Fehler-Response Format:**
```json
{
  "error": "Error message",
  "error_code": "ERROR_CODE",
  "details": {
    "field": "additional info"
  }
}
```

### API-Sicherheit

**Empfohlene Maßnahmen:**
- ✅ HTTPS nur (kein HTTP in Production)
- ✅ Rate-Limiting aktiv
- ✅ Session-Validation bei jedem Request
- ✅ Input-Validierung (Pydantic Models)
- ✅ CORS auf spezifische Origins beschränken
- ✅ Keine sensiblen Daten in Logs

---

## 📦 Queue System (Production)

### Warum Queue wichtig ist

**Problem ohne Queue:**
Wenn mehrere User gleichzeitig scannen wollen und die Queue deaktiviert ist:

```
User 1: Startet Scan → Läuft sofort
User 2: Startet Scan → Läuft sofort (parallel)
User 3: Startet Scan → Läuft sofort (parallel)
User 4: Startet Scan → Läuft sofort (parallel)
...
User 100: Startet Scan → Läuft sofort (parallel)
```

**Folgen:**
- ❌ **Server-Überlastung**: 100 gleichzeitige Scans = CPU/Memory/Disk voll
- ❌ **DoS-Risiko**: Ein Angreifer kann Server mit vielen Scans lahmlegen
- ❌ **Unfairness**: Erste Scans blockieren Ressourcen, spätere warten ewig
- ❌ **Keine Kontrolle**: Keine Möglichkeit, Scans zu priorisieren oder zu limitieren
- ❌ **Docker-Overload**: Zu viele Container gleichzeitig = System-Crash

**Mit Queue:**
```
User 1: Scan → Position 1 in Queue → Startet sofort
User 2: Scan → Position 2 in Queue → Wartet
User 3: Scan → Position 3 in Queue → Wartet
...
User 100: Scan → Position 100 in Queue → Wartet

System: Verarbeitet 1-3 Scans parallel (konfigurierbar)
        → Fair, kontrolliert, keine Überlastung
```

### Architektur
- **In-Memory Queue** (für Start)
- **Optional: Redis Queue** (für Skalierung)
- **Single-Repo Constraint**: Nur ein Repo pro Request
- **Parallel-Limit**: Max. 1-3 Scans gleichzeitig (konfigurierbar, abhängig von Server-Kapazität)

### Queue-Struktur
```python
{
    "queue_id": "uuid-v4",
    "session_id": "uuid-v4",  # Anonymisiert (nur Hash in öffentlicher Queue)
    "repository_url": "https://github.com/user/repo",  # Intern, nicht in öffentlicher Queue!
    "repository_name": "repo_abc123",  # Anonymisiert (Hash der URL)
    "status": "pending",  # pending, running, completed, failed
    "position": 5,
    "created_at": "2026-02-17T10:00:00Z",
    "started_at": null,
    "completed_at": null,
    "estimated_wait_time": 300  # Sekunden
}
```

### Queue-Anonymisierung

**Empfehlung: SHA256 Hash der Repository-URL**

**Warum Hash statt UUID?**
- ✅ **Deterministisch**: Gleiche URL = gleicher Hash (für Deduplizierung)
- ✅ **Anonym**: Keine Rückschlüsse auf Repository möglich
- ✅ **Kurz**: Hash kann gekürzt werden (z.B. erste 8 Zeichen)
- ✅ **Konsistent**: Gleiche URL hat immer gleichen Hash

**Implementierung:**
```python
import hashlib

def anonymize_repository_url(url: str) -> str:
    """Anonymisiert Repository-URL mit SHA256 Hash"""
    # Normalisiere URL
    normalized = normalize_url(url)
    
    # Hash
    hash_obj = hashlib.sha256(normalized.encode())
    hash_hex = hash_obj.hexdigest()
    
    # Kürze auf 8 Zeichen für Lesbarkeit
    short_hash = hash_hex[:8]
    
    return f"repo_{short_hash}"

# Beispiel:
# https://github.com/user/repo → repo_a1b2c3d4
```

**Öffentliche Queue-Liste (anonymisiert):**
```json
{
  "queue": [
    {
      "queue_id": "uuid-1",
      "repository_name": "repo_a1b2c3d4",  // Anonymisiert!
      "status": "pending",
      "position": 1,
      "estimated_wait_time": 300
    },
    {
      "queue_id": "uuid-2",
      "repository_name": "repo_e5f6g7h8",  // Anonymisiert!
      "status": "running",
      "position": 2,
      "estimated_wait_time": 150
    }
  ]
}
```

**Was wird NICHT angezeigt:**
- ❌ Original Repository-URL
- ❌ Session-ID (nur Hash in öffentlicher Liste)
- ❌ Branch-Name (optional, kann anonymisiert werden)
- ❌ Commit-Hash (optional, kann anonymisiert werden)

### Queue-Endpoints
- `POST /api/queue/add` - Scan zur Queue hinzufügen
- `GET /api/queue` - Öffentliche Queue-Liste (anonymisiert)
- `GET /api/queue/{queue_id}/status` - Status eines Scans
- `GET /api/queue/my-scans` - Eigene Scans (via Session-ID)

### Queue-Länge: Maximale Größe

**Empfehlung: Maximale Queue-Länge setzen!**

**Warum maximale Länge?**
- ❌ **Ohne Limit**: Queue kann unendlich wachsen → Memory-Problem
- ❌ **DoS-Risiko**: Angreifer kann Queue mit vielen Requests füllen
- ❌ **Sinnlose Wartezeiten**: Bei 10.000 Scans in Queue = Stunden/Jahre Wartezeit
- ✅ **Mit Limit**: Schutz vor Überlastung, realistische Wartezeiten

**Empfohlene Limits:**
```bash
# Environment-Variable
MAX_QUEUE_LENGTH=1000  # Max. 1000 Scans in Queue (Standard)
```

**Verhalten bei voller Queue:**
```python
# Wenn Queue voll ist:
if queue_length >= MAX_QUEUE_LENGTH:
    return {
        "error": "Queue is full",
        "message": f"Maximum queue length ({MAX_QUEUE_LENGTH}) reached. Please try again later.",
        "current_queue_length": queue_length,
        "estimated_wait_time": calculate_wait_time(queue_length),
        "retry_after": 3600  # Sekunden (1 Stunde)
    }
```

**Konfigurierbare Limits:**

| Limit | Development | Production | Hinweis |
|-------|-------------|------------|---------|
| `MAX_QUEUE_LENGTH` | 5000 | 1000 | Max. Scans in Queue |
| `MAX_CONCURRENT_SCANS` | 3-5 | 1-2 | Parallel laufende Scans (⚠️ noch nicht getestet! Werte sind Vorschläge) |

**Warum 1000 in Production?**
- Realistische Wartezeit: Bei 1-2 Scans parallel = ~8-12 Stunden max. Wartezeit (⚠️ noch zu testen)
- Memory: ~1KB pro Queue-Item = ~1MB für 1000 Items (akzeptabel)
- Fairness: Verhindert, dass Queue zu voll wird

### Gerechte Verteilung (Fairness)

**FIFO-Prinzip (First In, First Out):**
- ✅ **Fair**: Wer zuerst kommt, wird zuerst bedient
- ✅ **Einfach**: Keine komplexe Priorisierung nötig
- ✅ **Vorhersagbar**: Nutzer sehen ihre Position

**Alternative: Priorisierung (Optional)**
- **High Priority**: Bezahlte Nutzer, Premium-Features
- **Normal Priority**: Standard-Nutzer
- **Low Priority**: Free-Tier, Test-Scans

**Implementierung (FIFO - Standard):**
```python
# Einfache FIFO-Queue
queue = deque()  # First In, First Out

# Scan hinzufügen
queue.append(scan_request)

# Scan verarbeiten
next_scan = queue.popleft()  # Ältester zuerst
```

**Implementierung (Priorisierung - Optional):**
```python
# Priorisierte Queue
from queue import PriorityQueue

queue = PriorityQueue()

# Scan hinzufügen (niedrigere Zahl = höhere Priorität)
queue.put((priority, timestamp, scan_request))

# Scan verarbeiten
priority, timestamp, scan = queue.get()  # Höchste Priorität zuerst
```

### Deduplizierung: Gleiches Repo/Branch

**Problem:**
```
User 1: Scan für github.com/user/repo (branch: main, commit: abc123)
User 2: Scan für github.com/user/repo (branch: main, commit: abc123)  # Identisch!
User 3: Scan für github.com/user/repo (branch: main, commit: abc123)  # Identisch!
```

**Lösung: Deduplizierung in Queue + Scan-Deduplizierung**

#### 1. Queue-Deduplizierung (Vor dem Scan)

**Wenn identisches Repo/Branch/Commit bereits in Queue:**
```python
# Prüfe ob identischer Scan bereits in Queue
existing_scan = find_duplicate_in_queue(
    repository_url="https://github.com/user/repo",
    branch="main",
    commit_hash="abc123"
)

if existing_scan:
    # Option A: Neue Queue-Item erstellen, aber auf bestehenden Scan verweisen
    return {
        "queue_id": new_queue_id,
        "status": "duplicate",
        "duplicate_of": existing_scan.queue_id,
        "message": "Identical scan already in queue. You will receive the same results.",
        "estimated_wait_time": existing_scan.estimated_wait_time
    }
    
    # Option B: Direkt bestehenden Scan-Status zurückgeben
    return {
        "queue_id": existing_scan.queue_id,
        "status": existing_scan.status,
        "message": "Identical scan already in queue. You will receive the same results.",
        "position": existing_scan.position
    }
```

**Empfehlung: Option B (Direkt bestehenden Scan zurückgeben)**
- ✅ **Einfacher**: Keine doppelten Queue-Items
- ✅ **Fairer**: Alle bekommen dasselbe Ergebnis
- ✅ **Effizienter**: Kein doppelter Scan nötig

#### 2. Scan-Deduplizierung (Nach dem Scan)

**Wenn identischer Scan bereits existiert:**
```python
# Prüfe ob identischer Scan bereits existiert
existing_result = find_duplicate_scan(
    repository_url="https://github.com/user/repo",
    branch="main",
    commit_hash="abc123"
)

if existing_result and existing_result.age < 7_days:
    # Ergebnis wiederverwenden
    return {
        "scan_id": existing_result.scan_id,
        "status": "completed",
        "message": "Scan result reused from previous scan",
        "scan_date": existing_result.scan_date,
        "report_url": f"/api/results/{existing_result.scan_id}/report"
    }
else:
    # Neuer Scan nötig
    start_new_scan(...)
```

### Vollständiges Szenario: Mehrere User scannen dasselbe Repo

**Szenario:**
```
10:00:00 - User 1: Scan für github.com/user/repo (main, commit abc123)
10:00:05 - User 2: Scan für github.com/user/repo (main, commit abc123)  # Identisch!
10:00:10 - User 3: Scan für github.com/user/repo (main, commit abc123)  # Identisch!
10:00:15 - User 4: Scan für github.com/user/repo (main, commit abc123)  # Identisch!
```

**Ablauf:**

**1. User 1 (10:00:00):**
```json
{
  "queue_id": "queue-001",
  "status": "pending",
  "position": 1,
  "repository": "github.com/user/repo",
  "branch": "main",
  "commit": "abc123"
}
```
→ Scan startet sofort

**2. User 2 (10:00:05):**
```json
{
  "queue_id": "queue-001",  // Gleiche Queue-ID!
  "status": "running",      // Scan läuft bereits
  "message": "Identical scan already in progress. You will receive the same results.",
  "duplicate_of": "queue-001",
  "estimated_completion": "10:15:00"
}
```
→ **Kein neuer Scan!** User 2 bekommt dasselbe Ergebnis wie User 1

**3. User 3 (10:00:10):**
```json
{
  "queue_id": "queue-001",  // Gleiche Queue-ID!
  "status": "running",
  "message": "Identical scan already in progress. You will receive the same results.",
  "duplicate_of": "queue-001"
}
```
→ **Kein neuer Scan!** User 3 bekommt dasselbe Ergebnis

**4. Scan abgeschlossen (10:15:00):**
```json
{
  "queue_id": "queue-001",
  "status": "completed",
  "scan_id": "repo_20260217_101500",
  "report_url": "/api/results/repo_20260217_101500/report",
  "message": "Scan completed. All users who requested this scan will receive the same results."
}
```

**Alle User (1, 2, 3, 4) bekommen:**
- ✅ Dasselbe Scan-Ergebnis
- ✅ Derselbe Report-URL
- ✅ Kein doppelter Scan nötig
- ✅ Effizient und fair

### Deduplizierungs-Logik

**Vergleichs-Kriterien:**
```python
def is_duplicate(scan1, scan2):
    """Prüft ob zwei Scans identisch sind"""
    return (
        normalize_url(scan1.repository_url) == normalize_url(scan2.repository_url) and
        scan1.branch == scan2.branch and
        scan1.commit_hash == scan2.commit_hash
    )
```

**Normalisierung:**
```python
def normalize_url(url):
    """Normalisiert Repository-URL"""
    # https://github.com/user/repo.git → https://github.com/user/repo
    # https://github.com/user/repo/ → https://github.com/user/repo
    # git@github.com:user/repo.git → https://github.com/user/repo
    return normalized_url
```

### Konfiguration

**Environment-Variablen:**
```bash
# Queue-Konfiguration
MAX_QUEUE_LENGTH=1000              # Max. Scans in Queue
MAX_CONCURRENT_SCANS=1              # Parallel laufende Scans (Standard: 1)
                                    # ⚠️ HINWEIS: Noch nicht getestet! Werte sind Vorschläge.
                                    # Vorschläge (zu testen):
                                    # - Kleiner Server (2-4 Cores, 8GB): 1
                                    # - Mittlerer Server (4-8 Cores, 16GB): 1-2
                                    # - Großer Server (8+ Cores, 32GB+): 2-3
                                    # Nach Tests: Konkrete Werte basierend auf gemessenen Ressourcen
QUEUE_DEDUPLICATION=true            # Deduplizierung aktivieren (Standard: true)
QUEUE_FAIRNESS_MODE=fifo            # fifo oder priority (Standard: fifo)

# Deduplizierung
SCAN_DEDUPLICATION_ENABLED=true     # Scan-Deduplizierung aktivieren
SCAN_DEDUPLICATION_AGE_DAYS=7       # Max. Alter für Wiederverwendung (7 Tage)
```

### ⚠️ WICHTIG: Queue ist in Production NICHT deaktivierbar!

**Queue ist ein Pflicht-Feature in Production Mode!**

#### Warum Queue Pflicht ist:

**Ohne Queue würde passieren:**
```
User 1: Scan → Startet sofort
User 2: Scan → Startet sofort (parallel)
User 3: Scan → Startet sofort (parallel)
...
User 100: Scan → Startet sofort (parallel)

= 100 Scans gleichzeitig = Server-Crash! 💥
```

**Mit Queue (Pflicht):**
```
User 1: Scan → Position 1 → Startet sofort
User 2: Scan → Position 2 → Wartet fair
User 3: Scan → Position 3 → Wartet fair
...
User 100: Scan → Position 100 → Wartet fair

System: Verarbeitet nur 2-3 Scans parallel (konfigurierbar)
= Fair, kontrolliert, stabil ✅
```

#### Warum Queue nicht deaktivierbar sein sollte:

1. **Server-Stabilität**: Verhindert Überlastung und Crashes
2. **DoS-Schutz**: Verhindert Angriffe durch viele gleichzeitige Requests
3. **Fairness**: Alle Scans werden fair behandelt (FIFO)
4. **Kontrollierbarkeit**: Max. 2-3 Scans parallel (konfigurierbar)
5. **Vorhersagbarkeit**: Nutzer sehen ihre Position und Wartezeit

#### Was wenn externer Queue-Service verwendet wird?

**Option 1: Interne Queue + Externer Service**
- Interne Queue bleibt aktiv (als Fallback)
- Externer Service (Redis, RabbitMQ) kann zusätzlich verwendet werden
- Beste Lösung: Doppelte Absicherung

**Option 2: Nur externer Service (nur für Experten)**
- Nur wenn wirklich erforderlich (z.B. Kubernetes mit Job-Queue)
- Erfordert eigene Implementierung
- **Nicht empfohlen** für Standard-Production-Setup

---

## 🔍 Scan-Deduplizierung

### Logik
1. **Metadata-Vergleich**
   - Repository-URL normalisieren
   - Commit-Hash extrahieren
   - Branch extrahieren

2. **Datenbank-Abfrage** (Metadata-Storage)
   - Suche nach identischem Repository + Commit-Hash
   - Wenn gefunden:
     - Prüfe Scan-Alter (z.B. < 7 Tage)
     - Wenn aktuell → Ergebnis wiederverwenden
     - Wenn alt → Neuer Scan

3. **Neuer Scan bei:**
   - Neuer Commit-Hash
   - Neuer Branch
   - Alter Scan (> 7 Tage)
   - Expliziter Request (Force-Rescan)

### Metadata-Storage
```python
{
    "repository_url": "https://github.com/user/repo",
    "commit_hash": "abc123...",
    "branch": "main",
    "scan_id": "EventPromoter_20260301_223827",
    "scan_date": "2026-02-17T10:00:00Z",
    "findings_count": 42,
    "metadata_file": "/results/.../scan-metadata.json"
}
```

---

## 📊 Statistiken-System

### Aggregierte Statistiken (Empfehlung: Nur aggregiert für Datenschutz)

**Was wird gesammelt:**
- ✅ **Gesamt-Findings**: Anzahl aller Findings (aggregiert)
- ✅ **Nach Severity**: Critical, High, Medium, Low, Info (aggregiert)
- ✅ **Nach Tool**: Semgrep, Trivy, OWASP, etc. (aggregiert)
- ✅ **False-Positive Rate**: Wenn markiert (aggregiert)
- ❌ **KEINE Repository-Level-Statistiken**: Aus Datenschutz-Gründen

**Warum nur aggregiert?**
- ✅ **Datenschutz**: Keine Rückschlüsse auf einzelne Repositories möglich
- ✅ **DSGVO-konform**: Minimale Daten-Sammlung
- ✅ **Anonym**: Keine persönlichen Daten

**Endpoints:**
- `GET /api/statistics/overview` - Gesamt-Übersicht (aggregiert)
- `GET /api/statistics/by-severity` - Nach Severity (aggregiert)
- `GET /api/statistics/by-tool` - Nach Tool (aggregiert)
- `GET /api/statistics/false-positives` - False-Positive Rate (aggregiert)

**Beispiel-Response:**
```json
{
  "total_scans": 1234,
  "total_findings": 5678,
  "findings_by_severity": {
    "critical": 123,
    "high": 456,
    "medium": 1234,
    "low": 2345,
    "info": 1520
  },
  "findings_by_tool": {
    "semgrep": 2345,
    "trivy": 1234,
    "owasp": 567,
    "other": 1532
  },
  "false_positive_rate": 0.15  // 15%
}
```

**Datenschutz:**
- ✅ **Anonymisiert**: Keine Repository-Namen
- ✅ **Aggregiert**: Nur Gesamt-Zahlen
- ✅ **Keine persönlichen Daten**
- ✅ **Keine Zeitreihen**: Keine zeitliche Entwicklung (optional, wenn gewünscht)

---

## 📤 ZIP Upload Feature

### Funktionalität
- **Upload-Endpoint**: `POST /api/upload/zip`
- **Validierung**:
  - Dateityp: ZIP
  - Größenlimit: Konfigurierbar via Environment-Variable
  - Virus-Scan (optional)

### Größenlimits (Konfigurierbar)

**Environment-Variablen:**
```bash
# ZIP Upload Größenlimit (Standard: 100MB)
MAX_ZIP_UPLOAD_SIZE=100M          # 100MB, 500MB, 1G, etc.

# Git Repository Clone Größenlimit (Standard: 500MB)
MAX_GIT_REPO_SIZE=500M            # Maximale Größe nach Clone

# Gesamter Disk-Space pro Scan (Standard: 2GB)
MAX_SCAN_DISK_USAGE=2G            # Max. Disk-Space pro Scan
```

**Warum Größenlimits wichtig sind:**
1. **DoS-Schutz**: Verhindert Angriffe durch riesige Uploads/Repos
2. **Disk-Space**: Verhindert, dass System voll läuft
3. **Performance**: Große Repos brauchen sehr lange zum Scannen
4. **Fairness**: Verhindert, dass ein großer Scan alle Ressourcen blockiert
5. **Kosten**: Große Scans verbrauchen mehr Ressourcen

**Empfohlene Limits:**

| Limit | Development | Production | Hinweis |
|-------|-------------|------------|---------|
| `MAX_ZIP_UPLOAD_SIZE` | 500MB | 100MB | ZIP Upload Limit |
| `MAX_GIT_REPO_SIZE` | 1GB | 500MB | Nach Git Clone |
| `MAX_SCAN_DISK_USAGE` | 5GB | 2GB | Gesamter Disk-Space pro Scan |

**Implementierung:**
- Validierung beim Upload (ZIP)
- Validierung nach Git Clone (Repository-Größe)
- Monitoring während Scan (Disk-Usage)
- Automatisches Cleanup bei Überschreitung

### Workflow
1. ZIP-Upload via API
2. Temporäre Speicherung in `/tmp/uploads/`
3. Automatische Extraktion
4. Scan des extrahierten Codes
5. Cleanup nach Scan

### Sicherheit
- **Sandbox**: Extraktion in isoliertem Verzeichnis
- **Time-Limit**: Automatisches Cleanup nach 1 Stunde
- **Größenlimit**: Verhindert DoS-Angriffe
- **Virus-Scan**: Optional, aber empfohlen

### ⚠️ Sicherheitsüberlegung: ZIP Upload vs. Git-Only

**Empfehlung: ZIP Upload deaktivieren (`ZIP_UPLOAD_ENABLED=false`)**

**Warum Git-Only sicherer ist:**
- ✅ **Nachverfolgbarkeit**: Bei Git Scans kann der GitHub/GitLab User identifiziert und gebannt werden
- ✅ **Weniger Angriffsfläche**: Keine Möglichkeit, beliebigen Code hochzuladen
- ✅ **Bessere Kontrolle**: Git Repositories sind öffentlich sichtbar, weniger Anonymität
- ✅ **Einfachere Moderation**: Bei malicious code kann der Git User gebannt werden

**Warum ZIP Upload riskanter ist:**
- ⚠️ **Anonymität**: User kann beliebigen Code hochladen ohne Git-Account
- ⚠️ **Schlechtere Nachverfolgbarkeit**: Nur Session kann gebannt werden, nicht der Git User
- ⚠️ **Höheres Risiko**: Mehr Möglichkeiten für malicious code upload
- ⚠️ **Schwierigere Moderation**: Keine direkte Verbindung zu Git User

**Empfehlung:**
- **Initial**: ZIP Upload deaktivieren (`ZIP_UPLOAD_ENABLED=false`)
- **Später**: Nur aktivieren, wenn wirklich benötigt
- **Wenn aktiviert**: Virus-Scan implementieren und Rate-Limiting verschärfen

---

## ⚖️ Rechtliche Aspekte

### Service-Angebot

#### ✅ Erlaubt
- **GitHub/GitLab Public Repositories**: Öffentliche Repositories scannen ist grundsätzlich erlaubt
- **Eigene Repositories**: Nutzer scannen ihre eigenen Repositories
- **Mit Einverständnis**: Explizite Zustimmung des Repository-Owners

#### ⚠️ Zu beachten
- **Terms of Service**: GitHub/GitLab ToS prüfen
- **Rate-Limiting**: API-Rate-Limits respektieren
- **Datenschutz**: Keine persönlichen Daten speichern
- **Haftung**: Disclaimer für Scan-Ergebnisse

#### ❌ Nicht erlaubt
- **Private Repositories ohne Token**: Nur mit expliziter Autorisierung
- **DDoS-Angriffe**: Rate-Limiting verhindern
- **Daten-Speicherung**: Keine langfristige Speicherung von Code

### Empfehlungen

1. **Terms of Service**
   - Klare Nutzungsbedingungen
   - Disclaimer für Scan-Ergebnisse
   - Haftungsausschluss

2. **Datenschutz (DSGVO/GDPR)**
   - Privacy Policy
   - Daten-Minimierung
   - Anonymisierung von Daten
   - Recht auf Löschung

3. **Rate-Limiting**
   - Pro Session: Max. 10 Scans/Stunde
   - Pro IP: Max. 50 Scans/Tag
   - Queue-basiert: Fairness

4. **Disclaimer**
   - "Scan-Ergebnisse sind nicht rechtsverbindlich"
   - "Keine Garantie für Vollständigkeit"
   - "Nutzer haftet für eigene Scans"

---

## 🗂️ Datenbank-Überlegungen

### Entscheidung: PostgreSQL für Production

**Empfehlung: PostgreSQL für Production, File-Based für Development**

### Development: File-Based (Einfach)

**Warum File-Based in Dev?**
- ✅ **Einfach**: Keine externe Dependency nötig
- ✅ **Schnell**: Keine Datenbank-Setup nötig
- ✅ **Lokale Nutzung**: Für Entwickler ausreichend
- ✅ **Keine Persistenz nötig**: Dev ist temporär

**Implementierung:**
- **Metadata**: JSON-Dateien in `results/metadata/`
- **Queue**: In-Memory (bei Restart verloren - OK für Dev)
- **Statistiken**: Aggregiert aus Metadata-Dateien
- **Sessions**: In-Memory (bei Restart verloren - OK für Dev)

### Production: PostgreSQL (Empfohlen)

**Warum PostgreSQL in Production?**
- ✅ **Skalierbar**: Unterstützt mehrere Worker-Instanzen
- ✅ **Robust**: ACID-Compliance, Transaktionen
- ✅ **Persistenz**: Daten überleben Restarts
- ✅ **Performance**: Optimiert für viele gleichzeitige Zugriffe
- ✅ **Queue**: PostgreSQL Listen/Notify für Queue-Updates
- ✅ **Statistiken**: Effiziente SQL-Queries
- ✅ **Backup**: Einfaches Backup und Restore

**Was wird in PostgreSQL gespeichert?**
- **Sessions**: Session-Daten, Rate-Limiting-Info
- **Queue**: Queue-Items, Status, Position
- **Metadata**: Repository-Info, Commit-Hashes, Scan-IDs
- **Statistiken**: Aggregierte Findings-Statistiken

**Docker Compose Integration (für Production):**
```yaml
# docker-compose.prod.yml
services:
  # PostgreSQL Database (nur für Production)
  postgres:
    image: postgres:16-alpine
    container_name: SimpleSecCheck_postgres
    environment:
      POSTGRES_DB: simpleseccheck
      POSTGRES_USER: ssc_user
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    networks:
      - SimpleSecCheck_network
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ssc_user"]
      interval: 10s
      timeout: 5s
      retries: 5

  webui:
    depends_on:
      postgres:
        condition: service_healthy
    environment:
      - ENVIRONMENT=prod
      - DATABASE_TYPE=postgresql
      - DATABASE_URL=postgresql://ssc_user:${POSTGRES_PASSWORD}@postgres:5432/simpleseccheck
      - WEBUI_AUTO_SHUTDOWN=false
      # ... weitere Prod-spezifische Variablen

volumes:
  postgres_data:
```

### Migration: Dev → Prod

**Code-Änderungen:**
- **Abstraktion**: Database-Adapter-Pattern
- **Dev**: File-Based Backend
- **Prod**: PostgreSQL Backend
- **Environment-Variable**: `DATABASE_TYPE=file|postgresql`

**Implementierung:**
```python
# Database Adapter Pattern
class DatabaseAdapter:
    def save_session(self, session): ...
    def get_session(self, session_id): ...
    def add_to_queue(self, scan): ...
    def get_queue_item(self, queue_id): ...

# Dev: File-Based
class FileDatabase(DatabaseAdapter):
    ...

# Prod: PostgreSQL
class PostgreSQLDatabase(DatabaseAdapter):
    ...

# Factory
def get_database():
    if os.getenv("DATABASE_TYPE") == "postgresql":
        return PostgreSQLDatabase()
    else:
        return FileDatabase()  # Default für Dev
```

### Eigenes Repo?

**Empfehlung: NEIN, im gleichen Repo bleiben**

**Warum im gleichen Repo?**
- ✅ **Einfacher**: Alles an einem Ort
- ✅ **Weniger Overhead**: Keine Multi-Repo-Verwaltung
- ✅ **Code-Sharing**: Dev und Prod teilen Code
- ✅ **Einfachere Wartung**: Eine Codebase

**Wenn doch separates Repo:**
- ⚠️ **Nur wenn**: Production-Service wird komplett unabhängig entwickelt
- ⚠️ **Nur wenn**: Anderes Team, andere Deployment-Pipeline
- ⚠️ **Nachteil**: Code-Duplikation, schwierigere Wartung

**Empfehlung:**
- **Gleiches Repo**: Dev und Prod Code zusammen
- **Feature-Flags**: Environment-Variablen für Dev/Prod-Unterschiede
- **Docker Compose**: Separate Files (`docker-compose.dev.yml`, `docker-compose.prod.yml`)

### Datenbank-Schema (PostgreSQL)

**Grundlegende Tabellen:**
```sql
-- Sessions
CREATE TABLE sessions (
    session_id UUID PRIMARY KEY,
    created_at TIMESTAMP NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    scans_requested INTEGER DEFAULT 0,
    rate_limit_scans INTEGER DEFAULT 10,
    rate_limit_requests INTEGER DEFAULT 100
);

-- Queue
CREATE TABLE queue (
    queue_id UUID PRIMARY KEY,
    session_id UUID REFERENCES sessions(session_id),
    repository_url TEXT NOT NULL,
    repository_name TEXT NOT NULL,  -- Anonymisiert
    branch TEXT,
    commit_hash TEXT,
    status TEXT NOT NULL,  -- pending, running, completed, failed
    position INTEGER,
    created_at TIMESTAMP NOT NULL,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    scan_id TEXT
);

-- Metadata (für Deduplizierung)
CREATE TABLE scan_metadata (
    id SERIAL PRIMARY KEY,
    repository_url TEXT NOT NULL,
    branch TEXT NOT NULL,
    commit_hash TEXT NOT NULL,
    scan_id TEXT NOT NULL,
    scan_date TIMESTAMP NOT NULL,
    findings_count INTEGER,
    metadata_file_path TEXT,
    UNIQUE(repository_url, branch, commit_hash)
);

-- Statistiken (optional, für Performance)
CREATE TABLE statistics (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    total_scans INTEGER DEFAULT 0,
    total_findings INTEGER DEFAULT 0,
    findings_by_severity JSONB,
    findings_by_tool JSONB
);
```

### Environment-Variablen

**Development:**
```bash
DATABASE_TYPE=file  # File-Based (Standard)
```

**Production:**
```bash
DATABASE_TYPE=postgresql
DATABASE_URL=postgresql://ssc_user:password@postgres:5432/simpleseccheck
POSTGRES_PASSWORD=your-secure-password
```

---

## 📝 Implementierungs-Plan

### Phase 1: Grundlagen
1. ✅ Environment-Variable für Dev/Prod Mode
2. ✅ Docker Compose Files trennen
3. ✅ Session-Management (Basic)
4. ✅ Scan-Typ-Validierung (nur Git in Prod)

### Phase 2: Queue System
1. ✅ In-Memory Queue
2. ✅ Queue-Endpoints
3. ✅ Öffentliche Queue-Liste (anonymisiert)
4. ✅ Queue-Status-Tracking

### Phase 3: Metadata & Deduplizierung
1. ✅ Metadata immer sammeln (Prod)
2. ✅ Database-Adapter-Pattern implementieren (File-Based für Dev, PostgreSQL für Prod)
3. ✅ PostgreSQL-Schema erstellen
4. ✅ Metadata-Storage (PostgreSQL für Prod, File-Based für Dev)
5. ✅ Scan-Deduplizierung-Logik
6. ✅ Commit-Hash-Vergleich

### Phase 4: Statistiken
1. ✅ Statistiken-Aggregation
2. ✅ Statistiken-Endpoints
3. ✅ False-Positive-Tracking

### Phase 5: ZIP Upload
1. ✅ Upload-Endpoint
2. ✅ ZIP-Extraktion
3. ✅ Sandbox-Sicherheit
4. ✅ Cleanup-Logik

### Phase 6: Rechtliches & Dokumentation
1. ✅ Terms of Service
2. ✅ Privacy Policy
3. ✅ Disclaimer
4. ✅ Dokumentation

---

## 🔄 Migration von Dev zu Prod

### Code-Änderungen
- **Feature-Flags**: Environment-Variablen für Features
- **Middleware**: Session-Validation, Rate-Limiting
- **Validierung**: Scan-Typ-Checks
- **Metadata**: Immer sammeln in Prod

### Konfiguration
- **docker-compose.prod.yml**: Produktions-Config
- **.env.prod**: Produktions-Umgebungsvariablen
- **nginx/traefik**: Reverse Proxy (optional)

---

## 🚀 Deployment-Strategie

### Development
```bash
docker-compose -f docker-compose.dev.yml up
```

### Production
```bash
docker-compose -f docker-compose.prod.yml up -d
```

### Environment-Variablen
```bash
# .env.dev (Development)
ENVIRONMENT=dev
ENABLE_ALL_SCAN_TYPES=true
DOCKER_CAPABILITIES=extended
WEBUI_AUTO_SHUTDOWN=true         # Auto-Shutdown aktiv (lokale Nutzung)

# Größenlimits (Development - großzügiger)
MAX_ZIP_UPLOAD_SIZE=500M    # Max. ZIP Upload Größe (500MB)
MAX_GIT_REPO_SIZE=1G       # Max. Git Repo Größe nach Clone (1GB)
MAX_SCAN_DISK_USAGE=5G     # Max. Disk-Space pro Scan (5GB)

# .env.prod (Production) - Standard
ENVIRONMENT=prod
# Alle Pflicht-Features sind automatisch aktiv:
# - ONLY_GIT_SCANS=true
# - SESSION_MANAGEMENT=true
# - METADATA_COLLECTION=always
# - QUEUE_ENABLED=true
# - WEBUI_AUTO_SHUTDOWN=false (automatisch deaktiviert in Prod!)
# Optionale Features können überschrieben werden:
STATISTICS_ENABLED=true     # Optional
ZIP_UPLOAD_ENABLED=true     # Optional

# Datenbank (Production - PostgreSQL)
DATABASE_TYPE=postgresql         # PostgreSQL für Production
DATABASE_URL=postgresql://ssc_user:${POSTGRES_PASSWORD}@postgres:5432/simpleseccheck
POSTGRES_PASSWORD=your-secure-password  # In Production: Aus Secret-Manager laden!

# Größenlimits (empfohlen zu setzen!)
MAX_ZIP_UPLOAD_SIZE=100M    # Max. ZIP Upload Größe (100MB)
MAX_GIT_REPO_SIZE=500M      # Max. Git Repo Größe nach Clone (500MB)
MAX_SCAN_DISK_USAGE=2G      # Max. Disk-Space pro Scan (2GB)

# Datenbank-Konfiguration
DATABASE_TYPE=file           # file oder postgresql (Standard: file für Dev)
DATABASE_URL=                # PostgreSQL Connection String (nur wenn DATABASE_TYPE=postgresql)
                             # Format: postgresql://user:password@host:port/database
POSTGRES_PASSWORD=           # PostgreSQL Password (nur für Production)

# Session-Konfiguration
SESSION_DURATION=86400       # Session-Dauer in Sekunden (24h, Standard)
SESSION_STORAGE=memory      # memory, redis, postgresql (Standard: memory für Dev, postgresql für Prod)
SESSION_COOKIE_NAME=session_id  # Cookie-Name (Standard: session_id)
SESSION_HEADER_NAME=X-Session-ID  # Header-Name (Standard: X-Session-ID)
SESSION_COOKIE_HTTPONLY=true      # HttpOnly Cookie (Standard: true)
SESSION_COOKIE_SECURE=true        # Nur HTTPS (Standard: true, Production)
SESSION_COOKIE_SAMESITE=lax       # SameSite (Standard: lax)

# API-Konfiguration
CORS_ALLOWED_ORIGINS=https://your-frontend.com,https://app.your-service.com  # Erlaubte Origins für CORS
RATE_LIMIT_PER_SESSION_SCANS=10        # Scans pro Stunde pro Session
RATE_LIMIT_PER_SESSION_REQUESTS=100    # API-Requests pro Minute pro Session
RATE_LIMIT_PER_IP_SCANS=50             # Scans pro Tag pro IP
RATE_LIMIT_PER_IP_REQUESTS=1000        # API-Requests pro Stunde pro IP

# Queue-Konfiguration
MAX_QUEUE_LENGTH=1000                  # Max. Scans in Queue (Standard: 1000)
MAX_CONCURRENT_SCANS=1                 # Parallel laufende Scans (Standard: 1)
                                        # ⚠️ HINWEIS: Noch nicht getestet! Werte sind Vorschläge.
                                        # Vorschläge (zu testen):
                                        # - Kleiner Server (2-4 Cores, 8GB): 1
                                        # - Mittlerer Server (4-8 Cores, 16GB): 1-2
                                        # - Großer Server (8+ Cores, 32GB+): 2-3
                                        # Nach Tests: Konkrete Werte basierend auf gemessenen Ressourcen
QUEUE_DEDUPLICATION=true               # Deduplizierung aktivieren (Standard: true)
QUEUE_FAIRNESS_MODE=fifo               # fifo oder priority (Standard: fifo)

# Scan-Deduplizierung
SCAN_DEDUPLICATION_ENABLED=true        # Scan-Deduplizierung aktivieren
SCAN_DEDUPLICATION_AGE_DAYS=7          # Max. Alter für Wiederverwendung (7 Tage)

# .env.prod (Production) - Mit Overrides
ENVIRONMENT=prod
# Pflicht-Features können NICHT deaktiviert werden:
# - QUEUE_ENABLED (immer aktiv)
# - WEBUI_AUTO_SHUTDOWN (immer false in Prod)
STATISTICS_ENABLED=false    # Optional deaktiviert
ZIP_UPLOAD_ENABLED=false    # Optional deaktiviert
```

**Hinweis**: 
- Nur `ENVIRONMENT=dev` oder `ENVIRONMENT=prod` ist erforderlich
- **Pflicht-Features** können **NICHT** deaktiviert werden:
  - `ONLY_GIT_SCANS` - Immer aktiv
  - `SESSION_MANAGEMENT` - Immer aktiv
  - `METADATA_COLLECTION` - Immer aktiv
  - `QUEUE_ENABLED` - **Immer aktiv (ESSENTIELL für Stabilität!)**
- **Automatisch deaktiviert in Production:**
  - `WEBUI_AUTO_SHUTDOWN` - **Immer false in Prod (Service muss dauerhaft laufen!)**
- Optionale Features können frei deaktiviert werden:
  - `STATISTICS_ENABLED`
  - `ZIP_UPLOAD_ENABLED`

---

## 📋 Checkliste

### Development
- [ ] Docker Compose Dev File
- [ ] Alle Features aktiviert
- [ ] Erweiterte Capabilities
- [ ] Keine Einschränkungen

### Production
- [ ] Docker Compose Prod File
- [ ] Session Management
- [ ] Queue System
- [ ] Scan-Typ-Validierung
- [ ] Metadata Collection (immer)
- [ ] Scan-Deduplizierung
- [ ] Statistiken
- [ ] ZIP Upload
- [ ] Öffentliche Queue
- [ ] Rate-Limiting
- [ ] Terms of Service
- [ ] Privacy Policy
- [ ] Disclaimer

---

## ❓ Offene Fragen

### ✅ Bereits entschieden:
1. ✅ **ZIP-Upload**: Größenlimit: 100MB (Standard, konfigurierbar via `MAX_ZIP_UPLOAD_SIZE`)
2. ✅ **Git-Repo-Größe**: Größenlimit: 500MB (Standard, konfigurierbar via `MAX_GIT_REPO_SIZE`)
3. ✅ **Disk-Space-Limit**: Max. 2GB pro Scan (Standard, konfigurierbar via `MAX_SCAN_DISK_USAGE`)
4. ✅ **Session-Dauer**: 24 Stunden (Standard: `SESSION_DURATION=86400`)
5. ✅ **Rate-Limiting**: 
   - Pro Session: 10 Scans/Stunde, 100 Requests/Minute
   - Pro IP: 50 Scans/Tag, 1000 Requests/Stunde
6. ✅ **Metadata-Speicherung**: 7 Tage (Standard: `SCAN_DEDUPLICATION_AGE_DAYS=7`)
7. ✅ **Skalierung**: 1-2 parallel laufende Scans (⚠️ noch zu testen, Standard: `MAX_CONCURRENT_SCANS=1`)

### ❓ Noch offen (können während Implementierung entschieden werden):
1. **Queue-Anonymisierung**: Wie anonymisiert? (Hash, UUID, etc.) - **Empfehlung: Hash (SHA256) der Repository-URL**
2. **Statistiken**: Wie detailliert? (nur aggregiert oder auch Repository-Level?) - **Empfehlung: Nur aggregiert (Datenschutz)**
3. **Frontend-Anpassungen**: Welche UI-Änderungen für Production? (siehe unten)

---

## 📚 Weitere Überlegungen

### Skalierung
- **Horizontal Scaling**: Mehrere Worker-Instanzen
- **Load Balancer**: Nginx/Traefik
- **Queue-Backend**: Redis für verteilte Queues

### Monitoring
- **Health Checks**: `/api/health`
- **Metrics**: Prometheus (optional)
- **Logging**: Structured Logging

### Sicherheit
- **HTTPS**: TLS-Zertifikate
- **CORS**: Eingeschränkte Origins
- **Input Validation**: Strikte Validierung
- **Rate-Limiting**: Pro Session, Pro IP
- **Docker Socket**: **NIEMALS in Production!**
  - **Warum kein Docker Socket in Production?**
    - Docker Socket gibt Root-Zugriff auf den Host
    - In Production nur Git-Scans erlaubt (keine Network-Scans)
    - Git-Scans benötigen keinen Docker Socket (nur Network-Scans für Docker Bench)
    - **WebUI**: Kein Docker Socket (nur Queue-Management)
    - **Scanner**: Kein Docker Socket (nur Git-Scans, keine Network-Scans)
  - **Development**: Docker Socket erlaubt (für alle Scan-Typen inkl. Network-Scans)

---

## ✅ Finale Checkliste: Bereit für Implementierung?

### Backend-Architektur
- ✅ Dev/Prod Trennung definiert
- ✅ Environment-Variablen definiert
- ✅ Session-Management konzipiert (Hybrid: Cookie + Header)
- ✅ Queue-System spezifiziert (FIFO, Deduplizierung, Max-Länge)
- ✅ Database-Adapter-Pattern definiert (File-Based Dev, PostgreSQL Prod)
- ✅ API-Struktur dokumentiert
- ✅ Rate-Limiting definiert
- ✅ Größenlimits definiert

### Frontend-Architektur
- ✅ Feature-Flags konzipiert
- ✅ Neue Komponenten identifiziert (QueueView, StatisticsView)
- ✅ Entfernte Features identifiziert (Batch, Website/Network Scans)
- ⚠️ **Noch zu implementieren**: Frontend-Komponenten

### Offene Entscheidungen (können während Implementierung getroffen werden)
- ⚠️ **Queue-Anonymisierung**: Hash vs. UUID (Empfehlung: Hash)
- ⚠️ **Statistiken-Details**: Finale UI-Design (kann iterativ verbessert werden)

### Rechtliches
- ✅ Legal Considerations dokumentiert
- ⚠️ **Noch zu erstellen**: Terms of Service, Privacy Policy, Disclaimer

### Bereit für Implementierung?

**✅ JA, grundsätzlich bereit!**

**Was kann sofort starten:**
1. ✅ Backend: Session-Management
2. ✅ Backend: Queue-System
3. ✅ Backend: Database-Adapter-Pattern
4. ✅ Backend: API-Endpoints
5. ✅ Docker Compose: Dev/Prod Files

**Was kann parallel/iterativ:**
- ⚠️ Frontend: Neue Komponenten (kann iterativ entwickelt werden)
- ⚠️ Rechtliches: ToS/Privacy Policy (kann während Implementierung erstellt werden)
- ⚠️ Tests: Concurrent Scans (wird während Implementierung getestet)

**Empfehlung:**
- **Start mit Backend**: Core-Funktionalität implementieren
- **Dann Frontend**: UI-Komponenten iterativ entwickeln
- **Parallel**: Rechtliches vorbereiten

---

## 📅 Timeline (Vorschlag)

- **Phase 1-2**: 2-3 Wochen (Grundlagen + Queue)
- **Phase 3-4**: 2-3 Wochen (Metadata + Statistiken)
- **Phase 5**: 1-2 Wochen (ZIP Upload)
- **Phase 6**: 1 Woche (Rechtliches)

**Gesamt**: ~6-9 Wochen

---

## 🎯 Erfolgs-Kriterien

### Development
- ✅ Alle Features funktionieren
- ✅ Keine Einschränkungen
- ✅ Einfache Nutzung

### Production
- ✅ Nur GitHub/GitLab Scans
- ✅ Queue funktioniert
- ✅ Session-Management aktiv
- ✅ Metadata wird gesammelt
- ✅ Scan-Deduplizierung funktioniert
- ✅ Statistiken verfügbar
- ✅ Rechtlich abgesichert

---

**Stand**: 2026-02-17  
**Status**: Planungsphase  
**Nächste Schritte**: Diskussion der offenen Fragen, dann Implementierung
