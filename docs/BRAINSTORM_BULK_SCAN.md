# 🎨 Bulk Scan Feature - Visuelle Ideen

## Aktueller Stand (Single Repo)

```
┌─────────────────────────────────────────┐
│  Scan Type: ○ Code  ○ Website  ○ Network │
│                                         │
│  Target: [________________________]    │
│         https://github.com/user/repo    │
│                                         │
│  Git Branch: [main ▼]                   │
│                                         │
│  [ Start Scan ]                         │
└─────────────────────────────────────────┘
```

---

## 💡 Option 1: Multi-Repo Text Input (EINFACH)

```
┌─────────────────────────────────────────┐
│  Scan Type: ○ Code  ○ Website  ○ Network │
│                                         │
│  ⚙️ Scan Mode:                          │
│     ○ Single Repo                       │
│     ● Multiple Repos                     │
│                                         │
│  Repositories (one per line):           │
│  ┌───────────────────────────────────┐ │
│  │ https://github.com/user/repo1     │ │
│  │ https://github.com/user/repo2     │ │
│  │ https://github.com/user/repo3     │ │
│  │                                   │ │
│  └───────────────────────────────────┘ │
│                                         │
│  [ Start Batch Scan ]                   │
│                                         │
│  Progress:                              │
│  ████████░░░░░░░░ 3/10                 │
│  ✓ repo1                                │
│  ✓ repo2                                │
│  ⏳ Scanning repo3...                   │
└─────────────────────────────────────────┘
```

---

## 💡 Option 2: GitHub User/Org Browser (COOL)

```
┌─────────────────────────────────────────┐
│  Scan Type: ○ Code  ○ Website  ○ Network │
│                                         │
│  ⚙️ Scan Mode:                          │
│     ○ Single Repo                       │
│     ● GitHub User/Org                   │
│                                         │
│  GitHub Username/Org:                   │
│  [github________________] [🔍 Load]     │
│                                         │
│  ┌───────────────────────────────────┐ │
│  │ Found 15 repositories:            │ │
│  │                                   │ │
│  │ ☑ repo1 (Python, 2.3MB)          │ │
│  │ ☑ repo2 (JavaScript, 1.1MB)      │ │
│  │ ☐ repo3 (Go, 5.2MB) ⚠️ Large      │ │
│  │ ☑ repo4 (TypeScript, 0.8MB)      │ │
│  │ ☐ repo5 (Java, 12MB) ⚠️ Large     │ │
│  │ ...                               │ │
│  │                                   │ │
│  │ [Select All] [Deselect All]       │ │
│  │ Filter: [All ▼] [Size: <5MB]      │ │
│  └───────────────────────────────────┘ │
│                                         │
│  Selected: 12 repos                     │
│  [ Start Batch Scan ]                   │
└─────────────────────────────────────────┘
```

---

## 💡 Option 3: Hybrid (BESTE UX)

```
┌─────────────────────────────────────────┐
│  Scan Type: ○ Code  ○ Website  ○ Network │
│                                         │
│  ⚙️ Input Method:                        │
│     ○ Single URL                        │
│     ● GitHub User/Org                   │
│     ○ Multiple URLs (paste)              │
│                                         │
│  ┌─ Tab 1: GitHub User/Org ──────────┐ │
│  │ Username: [github______] [Load]    │ │
│  │                                    │ │
│  │ Repos:                             │ │
│  │ ☑ repo1  ☑ repo2  ☐ repo3         │ │
│  │ ☑ repo4  ☐ repo5  ☑ repo6         │ │
│  └────────────────────────────────────┘ │
│                                         │
│  ┌─ Tab 2: Paste URLs ───────────────┐ │
│  │ https://github.com/user/repo1     │ │
│  │ https://github.com/user/repo2     │ │
│  │ https://gitlab.com/user/repo3     │ │
│  └────────────────────────────────────┘ │
│                                         │
│  [ Start Batch Scan (12 repos) ]        │
└─────────────────────────────────────────┘
```

---

## 🔄 Scan Queue Flow

```
┌─────────────────────────────────────────┐
│  Batch Scan Progress                     │
│                                         │
│  ████████████░░░░░░░░ 60% (6/10)       │
│                                         │
│  Queue:                                 │
│  ┌───────────────────────────────────┐ │
│  │ ✓ repo1 - Completed               │ │
│  │ ✓ repo2 - Completed               │ │
│  │ ⏳ repo3 - Scanning...            │ │
│  │ ⏸ repo4 - Waiting                │ │
│  │ ⏸ repo5 - Waiting                │ │
│  │ ...                               │ │
│  └───────────────────────────────────┘ │
│                                         │
│  [ Pause ] [ Stop ]                     │
│                                         │
│  Results:                               │
│  • 6 completed                          │
│  • 0 failed                             │
│  • 4 pending                            │
└─────────────────────────────────────────┘
```

---

## 📊 Aggregated Report View

```
┌─────────────────────────────────────────┐
│  Batch Scan Results (12 repos)          │
│                                         │
│  Summary:                               │
│  • Total Findings: 45                   │
│  • Critical: 3                          │
│  • High: 12                             │
│  • Medium: 20                           │
│  • Low: 10                              │
│                                         │
│  Per Repository:                        │
│  ┌───────────────────────────────────┐ │
│  │ repo1: 5 findings [View Report]   │ │
│  │ repo2: 12 findings [View Report]  │ │
│  │ repo3: 0 findings ✓               │ │
│  │ repo4: 8 findings [View Report]   │ │
│  │ ...                               │ │
│  └───────────────────────────────────┘ │
│                                         │
│  [ Download All Reports (ZIP) ]         │
│  [ Generate Combined Report ]            │
└─────────────────────────────────────────┘
```

---

## 🎯 Empfehlung: Phase 1 (Multi-Repo Text)

**Warum?**
- ✅ Einfach zu implementieren
- ✅ Keine GitHub API nötig
- ✅ User hat volle Kontrolle
- ✅ Funktioniert mit GitHub, GitLab, etc.

**UI Mockup:**

```
┌─────────────────────────────────────────┐
│  Scan Type: ● Code  ○ Website  ○ Network │
│                                         │
│  Target Mode:                           │
│  ○ Single Repository                    │
│  ● Multiple Repositories                │
│                                         │
│  Repositories (one URL per line):       │
│  ┌───────────────────────────────────┐ │
│  │ https://github.com/user/repo1     │ │
│  │ https://github.com/user/repo2     │ │
│  │ https://gitlab.com/user/repo3     │ │
│  │                                   │ │
│  │                                   │ │
│  └───────────────────────────────────┘ │
│                                         │
│  ℹ️ Repos werden nacheinander gescannt  │
│                                         │
│  [ Start Batch Scan ]                   │
└─────────────────────────────────────────┘
```

---

## 🚀 Technische Architektur

```
Frontend (React)
    │
    ├─> POST /api/scan/batch/start
    │   {
    │     "repos": [
    │       "https://github.com/user/repo1",
    │       "https://github.com/user/repo2"
    │     ]
    │   }
    │
Backend (FastAPI)
    │
    ├─> Queue System
    │   ├─> repo1 → scan_service.start_scan()
    │   ├─> repo2 → scan_service.start_scan()
    │   └─> repo3 → scan_service.start_scan()
    │
    └─> Status Tracking
        ├─> GET /api/scan/batch/status
        └─> Returns: { queue: [...], current: 2, total: 10 }
```

---

## ⚠️ Wichtige Überlegungen

1. **Rate Limits**: GitHub API hat Limits
   - Ohne Token: 60 req/h
   - Mit Token: 5000 req/h

2. **Speicher**: Viele Clones = viel Platz
   - Lösung: Nach jedem Scan löschen

3. **Parallelisierung**: Aktuell nur 1 Scan gleichzeitig
   - Lösung: Queue System (nacheinander)

4. **UI Performance**: Bei 100+ Repos
   - Lösung: Pagination, Virtual Scrolling

---

## 🎨 Nächste Schritte

1. ✅ Phase 1: Multi-Repo Text Input
2. ⏳ Phase 2: GitHub User/Org Browser (wenn Bedarf)
3. ⏳ Phase 3: Advanced Features (Filter, Parallel, etc.)
