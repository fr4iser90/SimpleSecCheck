# SimpleSecCheck WebUI - UI/UX Design Plan (Single-Shot MVP)

## 🎯 Core Principle: Single-Shot First!

**WICHTIG**: Dieses WebUI ist ein **optionaler Wrapper** für die CLI. Es:
- ✅ Ruft einfach `bin/run-docker.sh` auf (keine Logik-Duplikation)
- ✅ Zeigt Live-Progress während Scan läuft
- ✅ Zeigt Report nach Scan (embedded)
- ❌ **KEIN** Dashboard/History (widerspricht Single-Shot)
- ❌ **KEINE** persistente Infrastruktur
- ❌ **KEINE** Datenbank/State

**Philosophie**: "WebUI = CLI mit Browser-Interface, sonst nichts!"

---

## 🎨 Design-Philosophie

### Design-Prinzipien
- **Minimalistisch & Fokussiert**: Nur Scan starten & Report anzeigen
- **Single-Shot**: Keine History, kein State, kein Dashboard
- **Dark-First**: Dark Mode als Standard (Security-Tools Standard)
- **Glassmorphism**: Konsistent mit bestehenden HTML-Reports
- **Responsive**: Mobile & Desktop optimiert
- **Performance**: Schnelle Ladezeiten, effiziente Datenübertragung

### Design-System

#### Farben
```css
/* Severity Colors (konsistent mit Reports) */
--color-critical: #dc3545;  /* Rot */
--color-high: #fd7e14;       /* Orange */
--color-medium: #ffc107;      /* Gelb */
--color-low: #0dcaf0;        /* Cyan */
--color-info: #6c757d;       /* Grau */
--color-pass: #28a745;       /* Grün */

/* Background (Dark Mode Standard) */
--bg-dark: linear-gradient(135deg, #0c0c0c 0%, #1a1a2e 50%, #16213e 100%);
--bg-light: linear-gradient(135deg, #667eea 0%, #764ba2 50%, #f093fb 100%);

/* Glassmorphism */
--glass-bg-dark: rgba(0,0,0,0.25);
--glass-border-dark: rgba(255,255,255,0.1);
```

#### Typografie
- **Font**: System Font Stack (`-apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto'`)
- **Headings**: Bold, klare Hierarchie
- **Body**: 14-16px, gute Lesbarkeit

#### Spacing
- **Container Padding**: 2rem
- **Card Gap**: 1.5rem
- **Element Spacing**: 0.5rem - 1rem

---

## 📐 Seiten-Struktur (MINIMAL - Single-Shot MVP)

### 1. **Homepage (Scan Start)** - `/`

**Zweck**: Scan starten - das war's!

**Layout**:
```
┌─────────────────────────────────────────────────────────┐
│  🛡️ SimpleSecCheck          [🌙 Dark Mode]             │
├─────────────────────────────────────────────────────────┤
│                                                           │
│  ┌─────────────────────────────────────────────────┐    │
│  │  Start New Scan                                   │    │
│  │  ┌──────────────────────────────────────────┐  │    │
│  │  │ Scan Type:                                  │  │    │
│  │  │ ○ Code  ○ Website  ○ Network              │  │    │
│  │  │                                             │  │    │
│  │  │ Target:                                     │  │    │
│  │  │ [_________________________________]         │  │    │
│  │  │                                             │  │    │
│  │  │ Options:                                    │  │    │
│  │  │ ☑ CI Mode                                   │  │    │
│  │  │ Finding Policy: [________________]          │  │    │
│  │  │                                             │  │    │
│  │  │ [🚀 Start Scan]                            │  │    │
│  │  └──────────────────────────────────────────┘  │    │
│  └─────────────────────────────────────────────────┘    │
│                                                           │
│  ℹ️  This is a single-shot scanner. Each scan is         │
│      independent. No history is stored.                  │
│                                                           │
└─────────────────────────────────────────────────────────┘
```

**Komponenten**:
- `ScanForm`: Scan-Konfiguration (einzige Komponente auf Homepage)

---

### 2. **Scan View** - `/scan` (kein ID, nur aktueller Scan)

**Zweck**: Live-Progress während Scan, Results danach

**WICHTIG**: Kein `/scan/:id` - nur der **aktuelle laufende Scan** wird angezeigt!

**Layout (Während Scan)**:
```
┌─────────────────────────────────────────────────────────┐
│  ← Back to Dashboard                                      │
├─────────────────────────────────────────────────────────┤
│                                                           │
│  ┌─────────────────────────────────────────────────┐    │
│  │  Scan Info Card                                   │    │
│  │  Project: EventPromoter                           │    │
│  │  Type: Code Scan                                   │    │
│  │  Started: 15:37:11                                 │    │
│  │  Status: 🔄 Running...                            │    │
│  └─────────────────────────────────────────────────┘    │
│                                                           │
│  ┌─────────────────────────────────────────────────┐    │
│  │  Tool Progress (Accordion)                        │    │
│  │  ┌──────────────────────────────────────────┐  │    │
│  │  │ ✅ Semgrep        [████████░░] 80%        │  │    │
│  │  │ 🔄 Trivy          [██████░░░░] 60%        │  │    │
│  │  │ ⏳ CodeQL         [░░░░░░░░░░] Waiting    │  │    │
│  │  │ ⏳ OWASP DC       [░░░░░░░░░░] Waiting    │  │    │
│  │  └──────────────────────────────────────────┘  │    │
│  └─────────────────────────────────────────────────┘    │
│                                                           │
│  ┌─────────────────────────────────────────────────┐    │
│  │  Live Logs (Terminal-Style)                       │    │
│  │  ┌──────────────────────────────────────────┐  │    │
│  │  │ [2025-02-15 15:37:12] Starting Semgrep...│  │    │
│  │  │ [2025-02-15 15:37:45] Semgrep completed  │  │    │
│  │  │ [2025-02-15 15:37:46] Starting Trivy...  │  │    │
│  │  │ [2025-02-15 15:38:12] Trivy completed    │  │    │
│  │  │ ... (auto-scroll)                         │  │    │
│  │  └──────────────────────────────────────────┘  │    │
│  └─────────────────────────────────────────────────┘    │
│                                                           │
└─────────────────────────────────────────────────────────┘
```

**Layout (Nach Scan)**:
```
┌─────────────────────────────────────────────────────────┐
│  ← Back to Dashboard                                      │
├─────────────────────────────────────────────────────────┤
│                                                           │
│  ┌─────────────────────────────────────────────────┐    │
│  │  Scan Summary Card                               │    │
│  │  ✅ Completed | Duration: 12m 34s                │    │
│  │  📊 15 Critical | 8 High | 23 Medium            │    │
│  │  [📥 Download Report] [📥 Download Logs]        │    │
│  └─────────────────────────────────────────────────┘    │
│                                                           │
│  ┌─────────────────────────────────────────────────┐    │
│  │  Embedded HTML Report (iframe oder parsed)       │    │
│  │  ┌──────────────────────────────────────────┐  │    │
│  │  │ [Security Summary Report - wie bisher]   │  │    │
│  │  │                                          │  │    │
│  │  │ Executive Summary                        │  │    │
│  │  │ Visual Summary                           │  │    │
│  │  │ Detailed Findings...                     │  │    │
│  │  │                                          │  │    │
│  │  └──────────────────────────────────────────┘  │    │
│  └─────────────────────────────────────────────────┘    │
│                                                           │
└─────────────────────────────────────────────────────────┘
```

**Komponenten**:
- `ScanHeader`: Scan-Info & Status
- `ToolProgress`: Live-Progress pro Tool
- `LiveLogs`: Terminal-Style Log-Viewer
- `ReportViewer`: Embedded HTML Report

---

### 3. **Results Browser** - `/results` (Optional - nur File Browser)

**Zweck**: Manuelle Navigation zu alten Reports (falls User sie lokal gespeichert hat)

**Layout**:
```
┌─────────────────────────────────────────────────────────┐
│  Browse Results (Local Files)                            │
├─────────────────────────────────────────────────────────┤
│                                                           │
│  ℹ️  These are local files from results/ directory.      │
│      No database, no tracking - just file browser.      │
│                                                           │
│  ┌─────────────────────────────────────────────────┐    │
│  │  results/                                         │    │
│  │  ┌──────────────────────────────────────────┐  │    │
│  │  │ 📁 Project_20250215_153711/              │  │    │
│  │  │    📄 security-summary.html               │  │    │
│  │  │    📄 security-check.log                  │  │    │
│  │  ├──────────────────────────────────────────┤  │    │
│  │  │ 📁 example.com_20250215_120000/          │  │    │
│  │  │    📄 security-summary.html               │  │    │
│  │  └──────────────────────────────────────────┘  │    │
│  └─────────────────────────────────────────────────┘    │
│                                                           │
└─────────────────────────────────────────────────────────┘
```

**Komponenten**:
- `FileBrowser`: Einfacher File-Browser (keine DB!)

---

## 🧩 Komponenten-Details

### 1. QuickScanForm

**Props**:
```typescript
interface ScanConfig {
  type: 'code' | 'website' | 'network';
  target: string;
  ciMode?: boolean;
  findingPolicy?: string;
  excludePaths?: string;
}
```

**Features**:
- Dropdown für Scan-Type
- Input für Target (mit Validation)
- Checkbox für CI Mode
- Optional: Finding Policy File Picker
- Submit Button mit Loading State

**Validation**:
- Code: Muss existierender Pfad sein
- Website: Muss gültige URL sein
- Network: Kein Target nötig

---

### 2. ToolProgress

**Props**:
```typescript
interface ToolStatus {
  name: string;
  status: 'waiting' | 'running' | 'success' | 'failed';
  progress?: number; // 0-100
  findings?: number;
}
```

**Visual**:
- Icon pro Tool (✅/🔄/❌/⏳)
- Progress Bar
- Findings Count (wenn verfügbar)

---

### 3. LiveLogs

**Features**:
- Auto-scroll zum Ende
- Terminal-Style (Monospace Font)
- Syntax Highlighting (optional)
- Copy Button
- Pause/Resume Auto-scroll

**Implementation**:
- Server-Sent Events (SSE) oder WebSocket
- Streamt `results/*/logs/security-check.log`

---

### 4. ReportViewer

**Options**:
1. **Iframe** (einfach): Zeigt HTML direkt
2. **Parsed** (komplexer): Parst HTML, zeigt in React Components

**Empfehlung**: Iframe für MVP, später parsed für bessere Integration

---

### 5. FileBrowser (Optional)

**Features**:
- Listet `results/` Verzeichnis auf
- Zeigt HTML Reports zum Öffnen
- Keine Datenbank - nur File System

---

## 🎯 User Flows (Single-Shot)

### Flow 1: Scan starten & ansehen (EINZIGER Flow!)
```
Homepage → ScanForm ausfüllen 
→ "Start Scan" klicken 
→ Auto-Redirect zu /scan 
→ Live Progress anzeigen 
→ Nach Completion: Report anzeigen
→ [Start New Scan] Button → zurück zu Homepage
```

**Das war's!** Keine History, kein Dashboard, kein State.

---

## 📱 Responsive Design

### Mobile (< 768px)
- **Dashboard**: Cards untereinander
- **Scan Form**: Vollbreite Inputs
- **Table**: Cards statt Table
- **Report**: Scrollbar, kein Iframe (zu klein)

### Tablet (768px - 1024px)
- **Dashboard**: 2 Spalten
- **Table**: Kompakt, scrollbar

### Desktop (> 1024px)
- **Dashboard**: 3 Spalten
- **Table**: Vollständig sichtbar
- **Report**: Side-by-side möglich

---

## 🚀 Technische Umsetzung

### Frontend Stack
- **Framework**: React + TypeScript
- **Styling**: Tailwind CSS (oder CSS Modules)
- **State**: React Context / Zustand
- **Routing**: React Router
- **HTTP**: Fetch API / Axios
- **Real-time**: Server-Sent Events (SSE)

### Backend Stack
- **Framework**: FastAPI (Python)
- **Endpoints**: REST API
- **File Serving**: Static Files für Reports
- **Log Streaming**: SSE für Live Logs

### API Endpoints (MINIMAL)

```
POST /api/scan/start         # Scan starten (ruft bin/run-docker.sh auf)
GET  /api/scan/status        # Aktueller Scan Status (running/done/error)
GET  /api/scan/logs           # Logs (SSE Stream) - nur während Scan
GET  /api/scan/report         # HTML Report - nur nach Scan
GET  /api/results/*           # File Browser für results/ (optional)
```

---

## 🎨 Design-Mockups (Text-basiert)

### Header (alle Seiten)
```
┌────────────────────────────────────────────────────┐
│  🛡️ SimpleSecCheck          [🌙 Dark Mode]        │
└────────────────────────────────────────────────────┘
```

### Scan Form (Homepage)
```
┌────────────────────────────────────────────────────┐
│  Start New Scan                                     │
│  ────────────────────────────────────────────────  │
│  Scan Type: ○ Code  ○ Website  ○ Network           │
│  Target: [_________________________________]        │
│  ☑ CI Mode                                          │
│  Finding Policy: [________________]                 │
│                                                     │
│  [🚀 Start Scan]                                    │
└────────────────────────────────────────────────────┘
```

### Tool Progress Item
```
┌────────────────────────────────────────────────────┐
│  ✅ Semgrep                                         │
│  ████████████████░░░░  80%                         │
│  142 findings detected                              │
└────────────────────────────────────────────────────┘
```

---

## ✅ MVP Features (Single-Shot MVP - Phase 1)

**NUR das Nötigste:**

1. ✅ **Homepage**: Scan Form (Code/Website/Network)
2. ✅ **Scan View**: Live Progress während Scan
3. ✅ **Live Logs**: Terminal-Style Log Stream (SSE)
4. ✅ **Report Viewer**: Embedded HTML Report nach Scan
5. ✅ **"Start New Scan" Button**: Zurück zur Homepage

**Das war's!** Keine History, kein Dashboard, keine Statistics.

---

## ❌ Was NICHT im MVP (Single-Shot Prinzip)

- ❌ Dashboard/Statistics (widerspricht Single-Shot)
- ❌ Scan History (keine DB, kein State)
- ❌ Multi-Scan Management
- ❌ Scheduling
- ❌ Notifications
- ❌ User Accounts

**Philosophie**: "Ein Scan, ein Report, fertig. Nächster Scan = neuer Start."

---

## 🔮 Future Features (NUR wenn gewünscht - optional)

- [ ] File Browser für `results/` (manuelle Navigation)
- [ ] Download Button (Report als ZIP)
- [ ] Export als JSON/PDF (optional)

**Aber**: Keine persistente Infrastruktur, keine DB, kein State!

---

## 🎯 Next Steps

1. ✅ UI/UX Plan (dieses Dokument)
2. ⏭️ Frontend Setup (React + TypeScript)
3. ⏭️ Backend Setup (FastAPI)
4. ⏭️ Komponenten implementieren
5. ⏭️ API Integration
6. ⏭️ Testing & Polish

---

**Erstellt**: 2025-02-15
**Version**: 1.0
**Status**: Planung abgeschlossen, bereit für Implementation
