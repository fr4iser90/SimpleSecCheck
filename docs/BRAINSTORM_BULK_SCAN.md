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
