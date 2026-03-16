# Plugin-Workflow: Analyse & Neues Plugin hinzufügen

## 1. Analyse: Ist alles generisch?

### ✅ Generisch (keine Tool-Namen in zentralem Code)

| Bereich | Verhalten |
|--------|-----------|
| **Registry** | Scanner werden über `scanner.plugins.<paket>.scanner` entdeckt; `tools_key` und Name kommen aus Modulpfad bzw. Klasse (SCANNER_NAME, NAME, manifest.name). Kein Hardcoding von Plugin-Namen. |
| **Orchestrator** | Verwendet nur `ScannerRegistry.get_scanners_for_target(...)` und `scanner.name` / `scanner.tools_key`. Führt alle so ermittelten Scanner aus. |
| **Report (generate-html-report)** | Verwendet `ScannerRegistry.get_all_scanners()` und `_get_processor_for_scanner(scanner)` (Processor aus `scanner.plugins.<tools_key>.processor`). Findings-Struktur über `_findings_as_list()` / `_findings_count()` (dict mit `alerts`/`summary` oder Liste). `html_func`-Signatur per `inspect.signature` – kein Tool-Check. |
| **html_utils** | Nur `_findings_as_list()` / `_findings_count()` (strukturbasiert). Domain-Scores aus `ScanType` + Registry. Keine Tool-Namen. |
| **Finding Policy** | Wird pro Tool über `processor.policy_key` und `scanner.name` zugeordnet; Keys kommen aus dem Plugin. |

### ✅ Keine Tool-Namen in zentralem Code

- **Orchestrator:** Beschreibung, Kategorien und Icon kommen ausschließlich aus der **`manifest.yaml`** jedes Plugins (Felder `description`, `categories`, `icon`). Kein Scanner-Name im Core.
- **Pfade:** Plugin-Datenpfade über **`path_setup.get_plugin_data_path_host(plugin_name)`** bzw. **`get_plugin_data_dir(plugin_name)`**; der Plugin-Name wird nur vom jeweiligen Plugin übergeben (z. B. aus `PLUGIN_NAME` in `scanner/plugins/<name>/scanner.py`).

### ✅ Pro-Plugin „eigener Name“ ist gewollt

- Jedes Plugin **darf** in seinem Modul den eigenen Namen nutzen (z. B. CLI `"bandit"`, `name="Bandit"` im Processor, `policy_key="bandit"`). Das ist keine Verletzung der Generik: Die **zentrale** Logik (Registry, Orchestrator, Report) kennt keine Tool-Namen und leitet alles über Modulpfad / Registry ab.

---

## 2. Workflow: Neues Plugin hinzufügen (Plug & Play)

Wenn du ein neues Plugin hinzufügst, läuft alles von Registry über Scan bis Report automatisch – **ohne** Änderung an Orchestrator, Report-Generator oder html_utils.

### Schritt 1: Plugin-Ordner anlegen

```
scanner/plugins/<plugin_name>/
├── scanner.py          # Pflicht: Scanner-Klasse, CAPABILITIES, run()
├── processor.py        # Pflicht: REPORT_PROCESSOR (summary_func, html_func, json_file, …)
├── manifest.yaml       # name, install, assets; optional: display_name, version, languages, severity_*, timeout, category, description, categories, icon, homepage, documentation
└── config/             # Optional: Tool-Config
```

`<plugin_name>` = Verzeichnisname (z. B. `my_scanner`). Wird aus dem Modulpfad abgeleitet (`PLUGIN_NAME = __name__.split(".")[2]`) – **eine Schreibweise**, nirgends doppelt pflegen.

### Schritt 2: Scanner-Klasse (scanner.py)

- Von **BaseScanner** erben.
- **Plugin-Name einmal ableiten:** `PLUGIN_NAME = __name__.split(".")[2]` (kommt vom Ordner `plugins/<name>/`).
- **CAPABILITIES** setzen; **PRIORITY**, **REQUIRES_CONDITION** (optional).
- **Anzeigename nur im Manifest:** In `manifest.yaml` `display_name: …` setzen. Im Scanner: `display_name = get_plugin_display_name(PLUGIN_NAME)` und `super().__init__(display_name, target_path, …)`. Registry und UI lesen den Namen ebenfalls aus dem Manifest – **kein SCANNER_NAME/NAME** nötig.
- **run()** implementieren: Tool ausführen, Ausgabe nach `self.results_dir` (z. B. `report.json`), bei „keine relevanten Dateien“ optional `status.json` mit `{"status": "skipped", "message": "…"}` schreiben.

Die Klasse muss auf `*Scanner` enden (z. B. `MyScanner`), damit sie von `scanner.plugins.__init__` erkannt wird.

### Schritt 3: Processor (processor.py)

- **REPORT_PROCESSOR** = `ReportProcessor(...)` mit mindestens:
  - **name**: Anzeigename (z. B. wie im Scanner).
  - **summary_func**: `(json_path)` oder `(html_path, json_path)` → Liste von Finding-Dicts (oder Dict mit `alerts`/`summary`).
  - **html_func**: `(findings)` oder `(findings, html_path, Path, os)` → HTML-String. Bei mehr als einem Parameter erkennt der Report-Generator das per `inspect.signature` und übergibt die Zusatzargumente.
  - **json_file**: z. B. `"report.json"`.
  - **html_file**: optional.
- Optional: **policy_key** (z. B. `"my_scanner"`), **apply_policy**, **policy_example_snippet**, **ai_normalizer**.

Findings-Dicts sollten mindestens **Severity**/severity, **path**/file/filename, **line**/line_number, **message**/description, **rule_id**/id enthalten, damit Executive Summary, Domain-Scores und All-Findings-Tabelle funktionieren.

### Schritt 4: Registrierung (automatisch)

- Beim Start wird **`import scanner.plugins`** ausgeführt.
- **`scanner/plugins/__init__.py`** durchsucht alle Unterpakete, lädt `scanner.plugins.<plugin_name>.scanner` und ruft **`ScannerRegistry.register_from_class(scanner_class)`** auf.
- Kein manuelles Eintragen in einer zentralen Liste nötig.

### Schritt 5: Scan (automatisch)

- Orchestrator holt Scanner mit **`ScannerRegistry.get_scanners_for_target(target_type, scan_types, conditions)`**.
- Dein Plugin erscheint, wenn seine **CAPABILITIES** zu target_type und scan_types passen.
- Für jeden Scanner: Instanziierung der Klasse aus **scanner.python_class**, Aufruf **run()**, Ergebnisse unter **`results/tools/<tools_key>/`**.

### Schritt 6: Report (automatisch)

- **generate-html-report** lädt **ScannerRegistry.get_all_scanners()**.
- Pro Scanner: **Processor** = `scanner.plugins.<tools_key>.processor.REPORT_PROCESSOR` (über **scanner.python_class** → `_get_processor_for_scanner`).
- Wenn unter `results/tools/<tools_key>/` die erwarteten Dateien (z. B. `processor.json_file`) existieren: **summary_func** aufrufen → **findings_by_tool[scanner.name]**.
- Findings-Struktur: Liste oder Dict mit `alerts`/`summary` → wird über **`_findings_as_list()`** / **`_findings_count()`** einheitlich verarbeitet.
- Executive Summary, Domain-Scores (nach **ScanType** aus den Capabilities), Tool-Status, All-Findings-Tabelle, Filter/Sort, pro-Tool-HTML-Sektion und Finding Policy nutzen nur Registry, Processor-Attribute und diese Strukturen – **keine Tool-Namen** in der Report-Logik.

### Optional: UI-Metadaten (manifest.yaml)

**Ein Ort für Namen und Metadaten:** Im **`manifest.yaml`** des Plugins:
- **`name`**: Plugin-ID (Ordnername, z. B. `owasp`).
- **`display_name`**: Anzeigename in UI/Registry (z. B. `OWASP Dependency Check`). Wenn gesetzt, wird er überall verwendet; sonst Fallback auf `name` bzw. Klassenname.
- **`description`**, **`categories`**, **`icon`**: für die Weboberfläche. Alles aus dem Manifest – keine Doppelpflege im Code.
- **`homepage`**, **`documentation`**: optionale Links für die UI.

### Optional: Capabilities & Execution (manifest.yaml)

Empfohlen für Orchestrierung, Scoring und Filtering (alle optional, schrittweise ergänzbar):
- **`version`**: z. B. `"1.0"` – für Updates, Migrationen, Debugging.
- **`languages`**: z. B. `["python"]` – Project Detector kann den Scanner skippen, wenn das Repo keine dieser Sprachen hat.
- **`severity_supported`**: `true`/`false` – manche Tools (z. B. Gitleaks) liefern keine Severity.
- **`severity_map`**: z. B. `{"ERROR": "HIGH", "WARNING": "MEDIUM"}` – für einheitliches Scoring/UI.
- **`category`**: einer von `code` | `dependency` | `secrets` | `container` | `iac` | `web` – für Domain-Scores (Code Security, Dependency Security, …).
- **`timeout`**: Laufzeit-Limit in Sekunden; Orchestrator kann es durchsetzen.

Execution (wie der Scanner läuft) bleibt im **Scanner-Code**; das Manifest beschreibt nur Capabilities und Hints – Single Source of Truth ohne Doppelung.

---

## 3. Kurzüberblick: Datenfluss

```
scanner/plugins/<name>/
    scanner.py  (CAPABILITIES, run())
         ↓
scanner/plugins/__init__.py  (pkgutil → register_from_class)
         ↓
ScannerRegistry  (name, tools_key, capabilities, python_class)
         ↓
Orchestrator  (get_scanners_for_target → _run_scanner → results/tools/<tools_key>/)
         ↓
generate-html-report
    get_all_scanners()
    _get_processor_for_scanner(scanner)  →  scanner.plugins.<tools_key>.processor.REPORT_PROCESSOR
    results/tools/<tools_key>/<processor.json_file>  →  summary_func  →  all_findings[scanner.name]
    _findings_as_list / _findings_count  (strukturbasiert, kein Tool-Name)
    Domain-Scores aus ScanType + Registry
    HTML aus html_func(findings) oder html_func(findings, html_path, Path, os)  (Signatur automatisch)
```

**Fazit:** Ein neues Plugin braucht nur den Ordner unter `scanner/plugins/<plugin_name>/` mit `scanner.py` und `processor.py` (plus optional manifest.yaml inkl. description/categories/icon für die UI). Registry, Scan und Report laufen danach automatisch; keine Anpassung in zentralem Code nötig.
