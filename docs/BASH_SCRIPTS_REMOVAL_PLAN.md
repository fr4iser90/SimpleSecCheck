# Bash-Scripts Entfernung - Plan

## Übersicht
Nach erfolgreicher Migration aller Scanner zu Python-Klassen können die Bash-Scripts entfernt werden. Sie werden nur noch als Fallback verwendet, falls Python-Scanner fehlschlagen.

## Status
✅ **Alle Scanner migriert zu Python-Klassen**
✅ **Orchestrator verwendet Python-Scanner primär**
✅ **Bash-Scripts nur noch als Fallback**

## Zu entfernende Dateien

### 1. Scanner Tool Scripts (28 Dateien)
```
scripts/tools/run_semgrep.sh
scripts/tools/run_detect_secrets.sh
scripts/tools/run_codeql.sh
scripts/tools/run_trivy.sh
scripts/tools/run_trufflehog.sh
scripts/tools/run_burp.sh
scripts/tools/run_gitleaks.sh
scripts/tools/run_nuclei.sh
scripts/tools/run_wapiti.sh
scripts/tools/run_docker_bench.sh
scripts/tools/run_npm_audit.sh
scripts/tools/run_anchore.sh
scripts/tools/run_nikto.sh
scripts/tools/run_eslint.sh
scripts/tools/run_checkov.sh
scripts/tools/run_sonarqube.sh
scripts/tools/run_kube_bench.sh
scripts/tools/run_android_manifest_scanner.sh
scripts/tools/run_snyk.sh
scripts/tools/run_zap.sh
scripts/tools/run_clair.sh
scripts/tools/run_terraform_security.sh
scripts/tools/run_owasp_dependency_check.sh
scripts/tools/run_bandit.sh
scripts/tools/run_safety.sh
scripts/tools/run_ios_plist_scanner.sh
scripts/tools/run_brakeman.sh
scripts/tools/run_kube_hunter.sh
```

### 2. Main Orchestrator Script
```
scripts/security-check.sh
```

### 3. Weitere Scripts (falls vorhanden)
```
scripts/run-docker.sh  # Bereits entfernt
```

## Code-Änderungen erforderlich

### 1. Scanner Registry (`scanner/core/scanner_registry.py`)
**Aktuell:**
- Jeder Scanner hat `script_path` definiert
- Fallback zu Bash-Script wenn Python-Klasse fehlschlägt

**Nach Entfernung:**
- `script_path` kann entfernt werden (optional, für Dokumentation)
- Fallback-Logik im Orchestrator entfernen
- Fehler werfen wenn Python-Klasse nicht verfügbar ist

### 2. Orchestrator (`scanner/core/orchestrator.py`)
**Aktuell:**
```python
# Fallback to Bash script (legacy)
script_path = Path(scanner.script_path)
if not script_path.exists():
    # Error handling
# Execute scanner script
```

**Nach Entfernung:**
```python
# Python scanner is required - no fallback
if not python_scanner_class:
    self.log_message(f"[ORCHESTRATOR ERROR] {scanner.name} Python scanner class not defined")
    self.scanner_statuses[scanner.name] = "FAILED"
    self.step_registry.fail_step(scanner.name, f"Python scanner class not available")
    self.overall_success = False
    return False
```

### 3. Dockerfile (`scanner/Dockerfile`)
**Aktuell:**
- Kopiert `scripts/` Verzeichnis
- Macht Scripts ausführbar

**Nach Entfernung:**
- `COPY scripts/` kann entfernt werden (oder nur noch für andere Scripts)
- `RUN chmod +x` für Scanner-Scripts entfernen

### 4. Docker Compose Files
**Aktuell:**
- Keine direkten Referenzen mehr (bereits entfernt)

**Nach Entfernung:**
- Keine Änderungen nötig

## Test-Plan vor Entfernung

### Phase 1: Verifizierung
1. ✅ Alle Scanner haben Python-Klassen
2. ✅ Orchestrator verwendet Python-Klassen primär
3. ⏳ **Test-Scan durchführen** - alle Scanner müssen funktionieren
4. ⏳ **Fallback-Logik testen** - absichtlich Python-Klasse deaktivieren, sollte Fehler werfen

### Phase 2: Code-Bereinigung
1. Fallback-Logik im Orchestrator entfernen
2. `script_path` aus Scanner Registry entfernen (optional)
3. Dockerfile anpassen

### Phase 3: Dateien entfernen
1. Alle `run_*.sh` Scripts löschen
2. `security-check.sh` löschen
3. Verzeichnis `scripts/tools/` löschen (falls leer)

### Phase 4: Finale Tests
1. Test-Scan mit allen Scannern
2. Verifizieren dass keine Bash-Script-Referenzen mehr existieren
3. Dokumentation aktualisieren

## Risiken und Mitigation

### Risiko 1: Python-Scanner fehlt
**Mitigation:** 
- Alle Scanner haben Python-Klassen
- Registry prüft Verfügbarkeit
- Klarer Fehler wenn Klasse fehlt

### Risiko 2: Dockerfile bricht
**Mitigation:**
- Nur `scripts/tools/` entfernen, andere Scripts behalten
- Oder `scripts/` komplett behalten für andere Zwecke

### Risiko 3: Alte Scans/Referenzen
**Mitigation:**
- Git History behält alte Versionen
- Kann bei Bedarf wiederhergestellt werden

## Empfohlene Reihenfolge

1. **JETZT:** Test-Scan durchführen (alle Scanner)
2. **DANN:** Fallback-Logik im Code entfernen
3. **DANN:** Dockerfile anpassen
4. **ZU LETZT:** Bash-Script-Dateien löschen

## Checkliste

- [ ] Test-Scan erfolgreich (alle Scanner)
- [ ] Fallback-Logik im Orchestrator entfernt
- [ ] `script_path` aus Registry entfernt (optional)
- [ ] Dockerfile angepasst
- [ ] Alle `run_*.sh` Scripts gelöscht
- [ ] `security-check.sh` gelöscht
- [ ] Finale Tests erfolgreich
- [ ] Dokumentation aktualisiert

## Notizen

- Bash-Scripts können in Git History bleiben (für Notfälle)
- Dockerfile kann `scripts/` behalten falls andere Scripts noch benötigt werden
- `script_path` in Registry kann als Dokumentation bleiben (wird nicht verwendet)
