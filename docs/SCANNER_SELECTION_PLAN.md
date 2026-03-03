# Scanner-Auswahl Feature - Implementierungsplan

## Übersicht
Benutzer sollen vor dem Scan-Start auswählen können, welche Scanner ausgeführt werden sollen. Dies ermöglicht:
- Schnellere Scans (weniger Scanner = weniger Zeit)
- Fokussierte Scans (nur relevante Scanner)
- Ressourcen-Schonung (keine unnötigen Scanner)

---

## 1. Backend-Änderungen

### 1.1 API-Endpoint erweitern
**Datei:** `webui/backend/app/routers/scan.py`

**Änderung:** `/api/scan/start` Endpoint erweitern

```python
# Aktuell:
class ScanRequest:
    type: str
    target: str
    git_branch: Optional[str]
    ci_mode: bool
    finding_policy: Optional[str]
    collect_metadata: bool

# Neu:
class ScanRequest:
    type: str
    target: str
    git_branch: Optional[str]
    ci_mode: bool
    finding_policy: Optional[str]
    collect_metadata: bool
    enabled_scanners: Optional[List[str]] = None  # Liste von Scanner-Namen
```

**Logik:**
- Wenn `enabled_scanners` nicht gesetzt → alle Scanner aktivieren (Backward Compatibility)
- Wenn `enabled_scanners` leer → Fehler werfen
- Wenn `enabled_scanners` gesetzt → nur diese Scanner ausführen

### 1.2 Scanner Registry API-Endpoint (NEU)
**Datei:** `webui/backend/app/routers/scan.py`

**Neuer Endpoint:** `GET /api/scan/available-scanners`

```python
@router.get("/api/scan/available-scanners")
async def get_available_scanners(scan_type: str):
    """
    Gibt alle verfügbaren Scanner für einen Scan-Typ zurück
    
    Returns:
    {
        "scan_type": "code",
        "scanners": [
            {
                "name": "Semgrep",
                "description": "Static analysis tool",
                "priority": 1,
                "category": "Static Analysis"
            },
            ...
        ]
    }
    """
```

**Implementierung:**
- Nutzt `ScannerRegistry.get_scanners_for_type(ScanType.CODE/WEBSITE/NETWORK)`
- Gibt Scanner-Info zurück (Name, Priority, Kategorie)

### 1.3 Orchestrator anpassen
**Datei:** `scanner/core/orchestrator.py`

**Änderung:** `run_scan()` Methode erweitern

```python
def run_scan(
    self,
    enabled_scanners: Optional[List[str]] = None  # NEU
):
    """
    Args:
        enabled_scanners: Liste von Scanner-Namen, die ausgeführt werden sollen
                         Wenn None → alle Scanner ausführen
    """
    scanners = ScannerRegistry.get_scanners_for_type(self.scan_type)
    
    # Filter nach enabled_scanners
    if enabled_scanners:
        scanners = [s for s in scanners if s.name in enabled_scanners]
    
    # Rest der Logik...
```

### 1.4 Docker Runner anpassen
**Datei:** `webui/backend/app/services/docker_runner.py`

**Änderung:** `enabled_scanners` als Environment Variable übergeben

```python
env_vars = [
    ("SCAN_ID", scan_id),
    ("SCAN_TYPE", scan_type),
    ("ENABLED_SCANNERS", ",".join(enabled_scanners) if enabled_scanners else ""),  # NEU
    # ... rest
]
```

---

## 2. Frontend-Änderungen

### 2.1 Neue Komponente: ScannerSelector
**Datei:** `webui/frontend/src/components/ScannerSelector.tsx` (NEU)

**Features:**
- Collapsible Card/Accordion für Scanner-Auswahl
- Checkboxen für jeden Scanner
- Gruppierung nach Kategorien (Static Analysis, Dependency Check, Secret Scanning, etc.)
- "Select All" / "Deselect All" Buttons
- "Recommended" Preset (nur wichtige Scanner)
- "Full Scan" Preset (alle Scanner)
- "Custom" Preset (benutzerdefinierte Auswahl)

**UI-Struktur:**
```
┌─────────────────────────────────────────┐
│ Scanner Selection (Click to expand) ▼  │
├─────────────────────────────────────────┤
│ [ ] Select All                          │
│ [ ] Deselect All                        │
│                                         │
│ Presets:                                │
│ [Recommended] [Full Scan] [Custom]      │
│                                         │
│ Static Analysis:                        │
│ ☑ Semgrep (Priority 1)                 │
│ ☑ CodeQL (Priority 3)                  │
│ ☐ SonarQube (Priority 7)                │
│                                         │
│ Dependency Scanning:                    │
│ ☑ Trivy (Priority 2)                    │
│ ☑ OWASP Dependency Check (Priority 4)  │
│ ☑ Safety (Priority 5)                   │
│                                         │
│ Secret Scanning:                        │
│ ☑ TruffleHog (Priority 16)              │
│ ☑ GitLeaks (Priority 17)               │
│ ☐ Detect-secrets (Priority 18)         │
│                                         │
│ ... (weitere Kategorien)                │
└─────────────────────────────────────────┘
```

**State Management:**
```typescript
interface Scanner {
  name: string
  description?: string
  priority: number
  category: string
  enabled: boolean
}

const [scanners, setScanners] = useState<Scanner[]>([])
const [selectedScanners, setSelectedScanners] = useState<Set<string>>(new Set())
const [isExpanded, setIsExpanded] = useState(false)
```

**API-Integration:**
```typescript
// Beim Scan-Type-Wechsel: Scanner laden
useEffect(() => {
  fetch(`/api/scan/available-scanners?scan_type=${scanType}`)
    .then(res => res.json())
    .then(data => {
      setScanners(data.scanners)
      // Default: Alle aktivieren
      setSelectedScanners(new Set(data.scanners.map(s => s.name)))
    })
}, [scanType])
```

### 2.2 ScanForm erweitern
**Datei:** `webui/frontend/src/components/ScanForm.tsx`

**Änderungen:**
1. ScannerSelector-Komponente einbinden
2. State für ausgewählte Scanner hinzufügen
3. Scanner-Liste beim Submit mitsenden

```typescript
const [selectedScanners, setSelectedScanners] = useState<string[]>([])

// In handleSubmit:
body: JSON.stringify({
  type: scanType,
  target: scanType === 'network' ? 'network' : cleanTarget,
  git_branch: cleanGitBranch,
  ci_mode: ciMode,
  finding_policy: cleanFindingPolicy,
  collect_metadata: collectMetadata,
  enabled_scanners: selectedScanners.length > 0 ? selectedScanners : undefined,  // NEU
}),
```

**UI-Integration:**
```tsx
{/* Nach "Collect Metadata" Checkbox, vor Submit-Button */}
<ScannerSelector
  scanType={scanType}
  selectedScanners={selectedScanners}
  onSelectionChange={setSelectedScanners}
/>
```

### 2.3 BulkScanForm erweitern
**Datei:** `webui/frontend/src/components/BulkScanForm.tsx`

**Änderungen:**
- Gleiche ScannerSelector-Komponente verwenden
- Scanner-Auswahl für alle Repos in Batch übernehmen

---

## 3. Datenfluss

```
1. User wählt Scan-Type (code/website/network)
   ↓
2. Frontend lädt verfügbare Scanner via GET /api/scan/available-scanners
   ↓
3. ScannerSelector zeigt Scanner mit Checkboxen
   ↓
4. User wählt Scanner aus (oder nutzt Preset)
   ↓
5. User klickt "Start Scan"
   ↓
6. Frontend sendet POST /api/scan/start mit enabled_scanners: ["Semgrep", "Trivy", ...]
   ↓
7. Backend erstellt Queue-Job mit enabled_scanners
   ↓
8. Scanner Worker liest enabled_scanners aus Environment
   ↓
9. Orchestrator filtert Scanner-Liste basierend auf enabled_scanners
   ↓
10. Nur ausgewählte Scanner werden ausgeführt
```

---

## 4. UI/UX Design-Vorschläge

### 4.1 Collapsible Card
- Standardmäßig **eingeklappt** (um Form nicht zu überladen)
- Zeigt Anzahl ausgewählter Scanner: "3 of 16 scanners selected"
- Icon: Chevron down/up für Expand/Collapse

### 4.2 Scanner-Gruppierung
**Kategorien:**
- **Static Analysis:** Semgrep, CodeQL, SonarQube, ESLint, Brakeman, Bandit
- **Dependency Scanning:** Trivy, OWASP DC, Safety, Snyk, npm audit
- **Infrastructure:** Terraform Security, Checkov
- **Secret Scanning:** TruffleHog, GitLeaks, Detect-secrets
- **Container:** Clair, Anchore
- **Mobile:** Android, iOS
- **Web Application:** ZAP, Nuclei, Wapiti, Nikto, Burp
- **Network:** Kube-hunter, Kube-bench, Docker Bench

### 4.3 Presets
**Recommended (Standard):**
- Semgrep, Trivy, OWASP DC, Safety, TruffleHog, GitLeaks
- Schnell, deckt die meisten Fälle ab

**Full Scan:**
- Alle Scanner aktivieren

**Custom:**
- Benutzer wählt manuell

### 4.4 Visual Feedback
- **Aktivierte Scanner:** Grüner Checkmark
- **Deaktivierte Scanner:** Grauer Checkmark
- **Anzahl:** "X of Y scanners selected" Badge
- **Warnung:** Wenn 0 Scanner ausgewählt → "Please select at least one scanner"

### 4.5 Responsive Design
- Mobile: Accordion bleibt funktional
- Desktop: Kann auch immer sichtbar sein (Option)

---

## 5. Validierung

### 5.1 Frontend-Validierung
```typescript
if (selectedScanners.length === 0) {
  setError('Please select at least one scanner')
  return
}
```

### 5.2 Backend-Validierung
```python
if enabled_scanners and len(enabled_scanners) == 0:
    raise HTTPException(
        status_code=400,
        detail="At least one scanner must be enabled"
    )

# Prüfen ob alle Scanner-Namen gültig sind
valid_scanners = [s.name for s in ScannerRegistry.get_scanners_for_type(scan_type)]
invalid = set(enabled_scanners) - set(valid_scanners)
if invalid:
    raise HTTPException(
        status_code=400,
        detail=f"Invalid scanner names: {', '.join(invalid)}"
    )
```

---

## 6. Backward Compatibility

### 6.1 Alte Clients
- Wenn `enabled_scanners` nicht gesendet wird → alle Scanner aktivieren
- Wenn `enabled_scanners` leer ist → Fehler (explizite Auswahl erforderlich)

### 6.2 Migration
- Keine Breaking Changes
- Bestehende API-Calls funktionieren weiterhin

---

## 7. Persistierung (Optional - Future Enhancement)

### 7.1 User Preferences
- Scanner-Auswahl in LocalStorage speichern
- Beim nächsten Scan automatisch laden
- Pro Scan-Type separate Preferences

### 7.2 Presets speichern
- Benutzer kann eigene Presets erstellen
- "Save as Preset" Button
- Presets in LocalStorage oder Backend speichern

---

## 8. Implementierungsreihenfolge

### Phase 1: Backend Foundation
1. ✅ Scanner Registry API-Endpoint (`/api/scan/available-scanners`)
2. ✅ ScanRequest erweitern (`enabled_scanners`)
3. ✅ Orchestrator anpassen (Filter-Logik)
4. ✅ Docker Runner anpassen (Environment Variable)

### Phase 2: Frontend Basic
5. ✅ ScannerSelector Komponente erstellen
6. ✅ Scanner-Liste von API laden
7. ✅ Checkboxen für Scanner-Auswahl
8. ✅ State Management

### Phase 3: UI/UX Enhancement
9. ✅ Collapsible Card
10. ✅ Scanner-Gruppierung nach Kategorien
11. ✅ Presets (Recommended, Full Scan, Custom)
12. ✅ Visual Feedback & Validierung

### Phase 4: Integration
13. ✅ ScanForm erweitern
14. ✅ BulkScanForm erweitern
15. ✅ Testing & Bugfixes

### Phase 5: Optional Features
16. ⏳ LocalStorage Persistierung
17. ⏳ Custom Presets
18. ⏳ Scanner-Beschreibungen/Tooltips

---

## 9. Beispiel-Implementierung (Code-Snippets)

### 9.1 ScannerSelector.tsx (Grundgerüst)
```typescript
interface ScannerSelectorProps {
  scanType: 'code' | 'website' | 'network'
  selectedScanners: string[]
  onSelectionChange: (scanners: string[]) => void
}

export default function ScannerSelector({
  scanType,
  selectedScanners,
  onSelectionChange
}: ScannerSelectorProps) {
  const [scanners, setScanners] = useState<Scanner[]>([])
  const [isExpanded, setIsExpanded] = useState(false)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    setLoading(true)
    fetch(`/api/scan/available-scanners?scan_type=${scanType}`)
      .then(res => res.json())
      .then(data => {
        setScanners(data.scanners)
        // Default: Alle aktivieren
        if (selectedScanners.length === 0) {
          onSelectionChange(data.scanners.map(s => s.name))
        }
      })
      .finally(() => setLoading(false))
  }, [scanType])

  const handleToggle = (scannerName: string) => {
    if (selectedScanners.includes(scannerName)) {
      onSelectionChange(selectedScanners.filter(s => s !== scannerName))
    } else {
      onSelectionChange([...selectedScanners, scannerName])
    }
  }

  const handleSelectAll = () => {
    onSelectionChange(scanners.map(s => s.name))
  }

  const handleDeselectAll = () => {
    onSelectionChange([])
  }

  return (
    <div className="scanner-selector-card">
      <div 
        className="scanner-selector-header"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <h3>Scanner Selection</h3>
        <span>{selectedScanners.length} of {scanners.length} selected</span>
        <ChevronIcon direction={isExpanded ? 'up' : 'down'} />
      </div>
      
      {isExpanded && (
        <div className="scanner-selector-content">
          {/* Presets */}
          <div className="presets">
            <button onClick={handleSelectAll}>Select All</button>
            <button onClick={handleDeselectAll}>Deselect All</button>
            <button onClick={() => applyPreset('recommended')}>Recommended</button>
            <button onClick={() => applyPreset('full')}>Full Scan</button>
          </div>

          {/* Scanner-Gruppen */}
          {groupScannersByCategory(scanners).map(category => (
            <div key={category.name} className="scanner-category">
              <h4>{category.name}</h4>
              {category.scanners.map(scanner => (
                <label key={scanner.name}>
                  <input
                    type="checkbox"
                    checked={selectedScanners.includes(scanner.name)}
                    onChange={() => handleToggle(scanner.name)}
                  />
                  {scanner.name}
                  <small>(Priority {scanner.priority})</small>
                </label>
              ))}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
```

---

## 10. Testing Checkliste

- [ ] Scanner-Liste wird korrekt geladen
- [ ] Scanner-Auswahl funktioniert
- [ ] Presets funktionieren
- [ ] Validierung (mindestens 1 Scanner)
- [ ] Backend filtert korrekt
- [ ] Nur ausgewählte Scanner werden ausgeführt
- [ ] Backward Compatibility (ohne enabled_scanners)
- [ ] Mobile Responsive
- [ ] Error Handling (API-Fehler, etc.)

---

## 11. Offene Fragen / Entscheidungen

1. **Standard-Verhalten:**
   - Alle Scanner aktiviert? ✅ (Empfohlen)
   - Oder nur "Recommended" Preset?

2. **Persistierung:**
   - LocalStorage? (Einfach)
   - Backend User Preferences? (Komplexer)

3. **Scanner-Beschreibungen:**
   - Tooltips?
   - Separate Info-Seite?
   - In API-Response?

4. **Performance:**
   - Scanner-Liste cachen?
   - Oder immer neu laden?

---

## Zusammenfassung

Dieser Plan ermöglicht es Benutzern, Scanner vor dem Scan-Start auszuwählen. Die Implementierung ist in Phasen aufgeteilt und kann schrittweise umgesetzt werden. Die Lösung ist rückwärtskompatibel und erweitert die bestehende Funktionalität ohne Breaking Changes.
