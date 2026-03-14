# Integration Tests für Setup Wizard

Diese Tests validieren den kompletten Setup-Flow:
1. Docker Compose startet alle Services
2. Setup-Token wird aus Logs extrahiert
3. Token-Verifikation
4. Admin-User wird erstellt
5. Setup wird abgeschlossen
6. Tests in verschiedenen Modi (dev, prod)

## Voraussetzungen

```bash
# Dependencies installieren
pip install -r tests/requirements.txt

# Docker muss laufen
docker ps
```

## Tests ausführen

### Alle Setup-Tests

```bash
# Standard (ohne Cleanup)
pytest tests/integration/test_setup_wizard.py -v -s

# Mit Cleanup (docker compose down -v nach jedem Test)
pytest tests/integration/test_setup_wizard.py --cleanup -v -s
```

### Spezifische Tests

```bash
# Nur Dev-Mode Test
pytest tests/integration/test_setup_wizard.py::test_setup_flow_dev -v -s

# Nur Prod-Mode Test
pytest tests/integration/test_setup_wizard.py::test_setup_flow_prod -v -s

# Nur Token-Extraktion Test
pytest tests/integration/test_setup_wizard.py::test_setup_token_extraction -v -s
```

### Mit parallelen Tests

```bash
# Mehrere Tests parallel (wenn mehrere Docker Compose Instanzen möglich)
pytest tests/integration/test_setup_wizard.py -n auto -v -s
```

## Test-Strategien

### 1. **Mit Cleanup (`--cleanup`)**
```bash
pytest tests/integration/test_setup_wizard.py --cleanup -v -s
```
- ✅ Sauberer Zustand vor jedem Test
- ✅ Keine Daten-Leaks zwischen Tests
- ❌ Langsamer (Docker muss neu starten)
- ❌ Datenbank wird jedes Mal neu initialisiert

**Wann verwenden:**
- CI/CD Pipeline
- Tests die einen sauberen Zustand brauchen
- Finale Validierung vor Release

### 2. **Ohne Cleanup (Standard)**
```bash
pytest tests/integration/test_setup_wizard.py -v -s
```
- ✅ Schneller (Docker läuft weiter)
- ✅ Datenbank bleibt erhalten
- ❌ Tests können sich gegenseitig beeinflussen
- ❌ Setup muss bereits abgeschlossen sein

**Wann verwenden:**
- Lokale Entwicklung
- Schnelle Iteration
- Tests die auf existierendem Setup aufbauen

### 3. **Manuelles Cleanup**
```bash
# Vor Tests
docker compose --profile dev down -v

# Tests ausführen
pytest tests/integration/test_setup_wizard.py -v -s

# Nach Tests (optional)
docker compose --profile dev down -v
```

## Test-Struktur

### `DockerComposeManager`
- Startet/stoppt Docker Compose
- Wartet auf Service-Ready-Status
- Extrahiert Logs
- Prüft Service-Gesundheit

### `SetupWizardTester`
- Extrahiert Setup-Token aus Logs
- Verifiziert Token
- Führt Setup durch
- Validiert Setup-Status

## Was wird getestet?

### ✅ `test_setup_flow_dev`
- Kompletter Setup-Flow in Dev-Mode
- Token-Extraktion
- Admin-User Erstellung
- Setup-Abschluss

### ✅ `test_setup_flow_prod`
- Kompletter Setup-Flow in Prod-Mode
- Andere Konfiguration
- Session-basierte Auth

### ✅ `test_setup_token_extraction`
- Token wird korrekt aus Logs extrahiert
- Token-Format ist korrekt (64 Zeichen hex)

### ✅ `test_setup_token_verification`
- Token-Verifikation funktioniert
- Session-ID wird zurückgegeben

### ✅ `test_setup_status_check`
- Status-Endpoint funktioniert
- Korrekte Status-Informationen

### ✅ `test_invalid_token`
- Ungültige Tokens werden abgelehnt
- Security-Validierung funktioniert

### ✅ `test_setup_without_session`
- Setup ohne Session wird abgelehnt
- Security-Validierung funktioniert

## Troubleshooting

### Services starten nicht
```bash
# Logs prüfen
docker compose --profile dev logs

# Services manuell starten
docker compose --profile dev up -d

# Prüfen ob Services laufen
docker compose --profile dev ps
```

### Token wird nicht gefunden
```bash
# Backend Logs prüfen
docker compose --profile dev logs backend | grep -i "setup token"

# Mehr Logs anzeigen
docker compose --profile dev logs backend --tail 500
```

### Tests hängen
```bash
# Timeout erhöhen in test_setup_wizard.py
MAX_WAIT_TIME = 180  # Statt 120

# Oder Services manuell prüfen
curl http://localhost:8080/api/health
curl http://localhost:8081/api/scanners
```

### Port-Konflikte
```bash
# Prüfen welche Ports belegt sind
lsof -i :8080
lsof -i :8081

# Docker Compose stoppen
docker compose --profile dev down
```

## Best Practices

1. **Immer `--cleanup` in CI/CD** verwenden
2. **Lokale Entwicklung ohne Cleanup** für Speed
3. **Tests isoliert** schreiben (keine Abhängigkeiten)
4. **Timeouts** großzügig setzen (Docker startet langsam)
5. **Logs** bei Fehlern ausgeben für Debugging

## Erweiterte Nutzung

### Custom Test-Config
```python
@pytest.mark.asyncio
@pytest.mark.parametrize("docker_compose", ["dev"], indirect=True)
async def test_custom_setup(api_client, docker_compose):
    tester = SetupWizardTester(api_client, docker_compose)
    
    # Custom config
    result = await tester.complete_setup_flow(
        admin_username="custom",
        admin_email="custom@test.com",
        admin_password="CustomPass123!",
        system_config={
            "auth_mode": "session",
            "scanner_timeout": 600
        }
    )
    
    assert result["success"]
```

### Mehrere Setups testen
```python
@pytest.mark.parametrize("auth_mode", ["free", "session", "oauth"])
async def test_setup_different_auth_modes(api_client, docker_compose, auth_mode):
    tester = SetupWizardTester(api_client, docker_compose)
    
    result = await tester.complete_setup_flow(
        system_config={"auth_mode": auth_mode}
    )
    
    assert result["success"]
```
