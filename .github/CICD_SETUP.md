#  CI/CD Setup für SimpleSecCheck

## Übersicht

Dieses Projekt nutzt **GitHub Actions** für Continuous Integration und Continuous Delivery (CI/CD).

### Was passiert automatisch?

1. **Bei jedem Push auf `main`**: 
   - Docker Image wird gebaut
   - Image wird auf Docker Hub gepusht
   - Tags werden automatisch erstellt

2. **Bei Pull Requests**:
   - Docker Image wird gebaut und getestet
   - Image wird NICHT gepusht (nur Validierung)

## 🔐 GitHub Secrets einrichten

Damit die Pipeline funktioniert, musst du diese **GitHub Secrets** einrichten:

### Schritt 1: Gehe zu deinem GitHub Repository
- Navigiere zu: **Settings** → **Secrets and variables** → **Actions**

### Schritt 2: Erstelle die folgenden Secrets

#### `DOCKERHUB_USERNAME`
- **Name**: `DOCKERHUB_USERNAME`
- **Value**: `fr4iser` (dein Docker Hub Username)

#### `DOCKERHUB_TOKEN`
- **Name**: `DOCKERHUB_TOKEN`
- **Wert**: Dein Docker Hub Personal Access Token
- **Wie erstellt man einen Token?**:
  1. Gehe zu https://hub.docker.com/settings/security
  2. Klicke auf "New Access Token"
  3. Gib ihm einen Namen (z.B. "github-actions")
  4. Kopiere den Token (wird nur einmal angezeigt!)
  5. Füge ihn als Secret `DOCKERHUB_TOKEN` in GitHub ein

## 📋 Workflow-Details

### Trigger
Die Pipeline wird ausgelöst bei:
- ✅ Pushes auf `main` branch
- ✅ Pull Requests auf `main` 
- ✅ Manuelle Auslösung via GitHub UI

### Tags
Das Image wird mit folgenden Tags erstellt:
- `latest` (nur bei main branch)
- `main-<sha>` (z.B. `main-abc1234`)
- `1.1.0` (Version aus build-args)

### Cache-Optimierung
- Docker Layer Caching wird verwendet für schnellere Builds
- Verwendet: `fr4iser/simpleseccheck:buildcache`

## 🎯 Manuelle Ausführung

Du kannst die Pipeline auch manuell starten:
1. Gehe zu **Actions** Tab
2. Wähle "Build and Push Docker Image"
3. Klicke "Run workflow"

## 📊 Build-Status anzeigen

Nach jedem Push siehst du den Build-Status:
- 🟢 Grüner Checkmark = Erfolgreich
- 🔴 Rotes X = Fehler
- 🟡 Gelber Kreis = Läuft gerade

## 🔧 Fehlerbehebung

### "Authentication failed" Fehler
- Überprüfe, ob die Docker Hub Secrets korrekt gesetzt sind
- Stelle sicher, dass `DOCKERHUB_TOKEN` ein **Access Token** ist, nicht dein Passwort

### "Permission denied" Fehler
- Überprüfe, ob der Docker Hub Username korrekt ist
- Stelle sicher, dass das Repository existiert auf Docker Hub

##  Version hochsetzen

Um die Version zu ändern:
1. Bearbeite die Datei `VERSION`
2. Bearbeite `build-args` in `.github/workflows/docker-build-push.yml`
3. Committe und pushe die Änderungen

```bash
# Beispiel
echo "1.2.0" > VERSION
git add VERSION .github/workflows/docker-build-push.yml
git commit -m "Bump version to 1.2.0"
git push
```

## 📚 Weitere Ressourcen

- [GitHub Actions Dokumentation](https://docs.github.com/en/actions)
- [Docker Buildx](https://docs.docker.com/build/buildx/)
- [Docker Metadata Action](https://github.com/docker/metadata-action)

