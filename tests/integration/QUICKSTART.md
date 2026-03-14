# Quick Start: Setup Wizard Tests

## Schnellstart

### 1. Dependencies installieren
```bash
pip install -r tests/requirements.txt
```

### 2. Tests ausführen

**Einfachste Variante (ohne Cleanup):**
```bash
pytest tests/integration/test_setup_wizard.py -v -s
```

**Mit Cleanup (sauberer, aber langsamer):**
```bash
pytest tests/integration/test_setup_wizard.py --cleanup -v -s
```

**Oder mit Script:**
```bash
./tests/integration/run_setup_tests.sh --cleanup
```

## Was passiert?

1. ✅ Docker Compose startet (backend, worker, redis, postgres)
2. ✅ Wartet bis alle Services ready sind
3. ✅ Extrahiert Setup-Token aus Backend-Logs
4. ✅ Verifiziert Token → bekommt Session-ID
5. ✅ Erstellt Admin-User
6. ✅ Schließt Setup ab
7. ✅ Validiert dass Setup erfolgreich war

## Wann `--cleanup` verwenden?

### ✅ **MIT Cleanup** (`--cleanup`):
- CI/CD Pipeline
- Tests die einen sauberen Zustand brauchen
- Wenn du sicherstellen willst, dass keine alten Daten stören

**Nachteil:** Langsamer (Docker muss jedes Mal neu starten)

### ✅ **OHNE Cleanup** (Standard):
- Lokale Entwicklung
- Schnelle Iteration
- Wenn Docker bereits läuft

**Nachteil:** Tests können sich gegenseitig beeinflussen

## Häufige Fragen

### Muss ich jedes Mal `docker compose down -v` machen?

**Nein!** Die Tests machen das automatisch wenn du `--cleanup` verwendest.

**Ohne `--cleanup`:**
- Docker läuft weiter
- Datenbank bleibt erhalten
- Schneller für lokale Entwicklung

**Mit `--cleanup`:**
- Docker wird nach jedem Test gestoppt
- Volumes werden gelöscht (`-v`)
- Sauberer Zustand für jeden Test

### Wie teste ich verschiedene Modi?

```bash
# Dev Mode (Standard)
pytest tests/integration/test_setup_wizard.py::test_setup_flow_dev -v -s

# Prod Mode
pytest tests/integration/test_setup_wizard.py::test_setup_flow_prod -v -s
```

### Was wenn Tests hängen?

1. **Services starten nicht:**
   ```bash
   docker compose --profile dev logs
   docker compose --profile dev ps
   ```

2. **Token wird nicht gefunden:**
   ```bash
   docker compose --profile dev logs backend | grep "Setup Token"
   ```

3. **Port-Konflikte:**
   ```bash
   lsof -i :8080
   docker compose --profile dev down
   ```

## Beispiel-Ausgabe

```
🚀 Starting Docker Compose (profile: dev)...
⏳ Waiting for services to be ready: backend, worker, redis, postgres...
✅ All services are ready!
📋 Extracting setup token from logs...
✅ Found setup token: 1d8877c022a4650...
🔐 Verifying setup token...
✅ Token verified, session ID: abc123...
⚙️ Initializing setup...
✅ Setup initialized, admin user ID: 123e4567-e89b-12d3-a456-426614174000
✅ Setup flow completed successfully in dev mode!
```

## Nächste Schritte

- Siehe `tests/integration/README.md` für detaillierte Dokumentation
- Siehe `tests/integration/test_setup_wizard.py` für alle verfügbaren Tests
