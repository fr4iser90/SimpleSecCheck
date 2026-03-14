[Worker] Starting SimpleSecCheck Worker
[Worker] Max concurrent jobs: 3
[Backend] API started successfully
[Backend] Setup token generated: xxxx
[Redis] Ready to accept connections
[Postgres] Ready to accept connections


Ziel-Logging für SimpleSecCheck
1. Allgemeines Log-Format

Alle Application-Logs (Backend + Worker) nutzen exakt dieses Format:

[Service] Event: Details

Beispiele:

[Backend] API started
[Backend] Setup token generated: 4f0d6c...
[Worker] Worker started
[Worker] Max concurrent jobs: 3

Eigenschaften:

Ein Service pro Prefix

Ein Event pro Zeile

Keine technischen Stackinfos

Keine Framework-Namen

Keine Timestamp-Spam (Docker hat bereits timestamps)

2. Welche Container loggen was
Backend Container (FastAPI)

Der Backend-Container loggt nur Systemevents der API.

Er loggt:

[Backend] API started
[Backend] Setup token generated: xxxx
[Backend] Database connected

Er loggt auch Fehler:

[Backend] ERROR: Database connection failed

Er loggt NICHT:

❌ Uvicorn Request Logs
❌ Stacktraces bei normalen Requests
❌ Middleware Debug Logs

Also kein:

INFO:     127.0.0.1:42342 - "GET /api/health HTTP/1.1" 200 OK
Worker Container

Der Worker loggt nur Worker-Systemzustände.

Er loggt:

[Worker] Worker started
[Worker] Queue adapter: redis
[Worker] Max concurrent jobs: 3

Wenn ein Job startet:

[Worker] Job started: scan_container

Wenn ein Job endet:

[Worker] Job finished: scan_container

Fehler:

[Worker] ERROR: Docker connection failed

Er loggt NICHT:

❌ Python module names
❌ Infrastructure class names

Also kein:

worker.infrastructure.docker_adapter - ERROR
Redis Container

Redis soll nur eine einzige relevante Startmeldung zeigen.

[Redis] Ready to accept connections

Nicht loggen:

❌ Version
❌ Memory warnings
❌ AOF creation
❌ jemalloc Hinweise

PostgreSQL Container

Postgres soll nur melden, dass die DB bereit ist.

[Postgres] Ready to accept connections

Nicht loggen:

❌ bootstrap messages
❌ locale warnings
❌ checkpoint spam

Frontend Container (Nginx)

Frontend soll nur melden, dass es läuft.

[Frontend] Nginx started

Oder optional:

[Frontend] Serving static frontend

Nicht loggen:

❌ Worker processes
❌ epoll messages
❌ signal events

Also kein:

start worker process 29
start worker process 30
3. Gesamte erwartete Startup-Logs

Wenn docker compose up läuft, sollen die Logs ungefähr so aussehen:

[Redis] Ready to accept connections
[Postgres] Ready to accept connections
[Backend] Database connected
[Backend] API started
[Backend] Setup token generated: xxxx
[Worker] Worker started
[Worker] Queue adapter: redis
[Worker] Max concurrent jobs: 3
[Frontend] Nginx started

Mehr nicht.

4. Logging Levels

Nur drei Levels werden genutzt:

Level	Nutzung
INFO	wichtige Events
WARNING	mögliche Probleme
ERROR	echte Fehler

DEBUG existiert nur für Development und ist standardmäßig aus.

5. Wichtigste Regel

Logs sind keine Debug-Ausgabe.

Logs sind:

Systemstatus

wichtige Events

Fehler

Alles andere gehört nicht ins Log.

💡 Mein ehrlicher Tipp aus Erfahrung:

Dein aktuelles Log ist riesig, weil 5 verschiedene Systeme gleichzeitig ungefiltert loggen:

Docker

Nginx

Uvicorn

Postgres

Redis

Python

Enterprise-Systeme lösen das immer so:

Application logs minimal – Infrastructure logs stark reduziert.