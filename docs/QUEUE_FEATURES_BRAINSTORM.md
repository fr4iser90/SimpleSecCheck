# Queue Features - Brainstorming & Design

## Aktueller Stand

### Bereits implementiert:
- ✅ Queue anzeigen (Admin sieht alle, User nur eigene)
- ✅ Scan cancel (läuft, aber entfernt nicht aus Redis Queue)
- ✅ Position-Berechnung basierend auf `created_at`

### Fehlend:
- ❌ Scan aus Queue löschen (nur eigene für User, alle für Admin)
- ❌ Scan aus Redis Queue entfernen (wenn pending)
- ❌ Position in Queue ändern (nur Admin)
- ❌ Cancel entfernt Scan nicht aus Redis Queue

---

## Feature-Design

### 1. Queue View Unterschiede

#### Normal User sieht:
- Nur eigene Scans (gefiltert nach `user_id` oder `session_id`)
- Position in Queue
- Status (pending, running, completed, failed)
- Kann eigene Scans:
  - ✅ Anzeigen
  - ✅ Canceln (wenn running/pending)
  - ✅ Aus Queue löschen (wenn pending)
  - ❌ Position ändern

#### Admin sieht:
- **ALLE Scans** (keine Filterung)
- Zusätzliche Infos:
  - `user_id` / `username` des Erstellers
  - `session_id` für Guest-Scans
  - Erweiterte Statistiken
- Kann alle Scans:
  - ✅ Anzeigen
  - ✅ Canceln (jeder Scan)
  - ✅ Aus Queue löschen (jeder Scan)
  - ✅ Position ändern (reorder)
  - ✅ Queue-Management (clear, pause, resume)

---

## API Endpoints Design

### 1. Delete Scan from Queue
```
DELETE /api/queue/{scan_id}
```
- **User**: Kann nur eigene Scans löschen (wenn pending)
- **Admin**: Kann alle Scans löschen
- Entfernt Scan aus:
  - PostgreSQL (Status → "cancelled" oder soft delete)
  - Redis Queue (wenn pending)
  - Worker (wenn running → cancel first)

### 2. Remove from Redis Queue
```
POST /api/queue/{scan_id}/remove
```
- Entfernt Scan nur aus Redis Queue (nicht aus DB)
- Nützlich wenn Scan in Queue "hängen geblieben" ist
- **Admin only**

### 3. Change Position in Queue
```
PATCH /api/queue/{scan_id}/position
Body: { "position": 2 }
```
- Ändert Position in Queue
- Implementierung:
  - Option A: `priority` Feld in Scan-Modell
  - Option B: Redis Sorted Set mit Score
  - Option C: `queue_position` Feld in DB
- **Admin only**

### 4. Cancel Scan (verbessert)
```
POST /api/scans/{scan_id}/cancel
```
- Bereits vorhanden, aber erweitern:
  - Entfernt aus Redis Queue wenn pending
  - Stoppt Worker wenn running
  - Setzt Status auf "cancelled"

---

## Implementierungs-Optionen für Position Change

### Option A: Priority Field
```python
class Scan(Base):
    priority: int = 0  # Höher = früher in Queue
```
- **Pro**: Einfach, direkt in DB
- **Contra**: Muss alle Scans neu sortieren bei Änderung

### Option B: Redis Sorted Set
```python
# Queue als Sorted Set mit Score = Position
ZADD scan_queue:priority {position} {scan_id}
```
- **Pro**: Sehr schnell, native Sortierung
- **Contra**: Zusätzliche Redis-Struktur, Sync mit DB nötig

### Option C: Queue Position Field
```python
class Scan(Base):
    queue_position: Optional[int] = None  # NULL = nicht in Queue
```
- **Pro**: Klar, einfach zu verstehen
- **Contra**: Muss bei jedem Dequeue alle Positionen updaten

### **Empfehlung: Option A (Priority)**
- Einfachste Implementierung
- Gute Performance bei normaler Queue-Größe
- Kann später zu Sorted Set migriert werden

---

## Queue Management (Admin)

### Clear Queue
```
DELETE /api/queue
```
- Löscht alle pending Scans aus Queue
- Setzt Status auf "cancelled"
- **Admin only**

### Pause/Resume Queue
```
POST /api/queue/pause
POST /api/queue/resume
```
- Pausiert/Resumed Worker-Processing
- Setzt Flag in Redis/DB
- Worker prüft Flag vor Dequeue

---

## UI/UX Überlegungen

### Queue View für User:
```
┌─────────────────────────────────────┐
│ My Scans in Queue                    │
├─────────────────────────────────────┤
│ [1] repo-name (pending)  [Cancel]   │
│ [2] other-repo (pending)  [Cancel]  │
│ [3] test-repo (running)   [Cancel]  │
└─────────────────────────────────────┘
```

### Queue View für Admin:
```
┌─────────────────────────────────────────────────────┐
│ All Scans in Queue (Admin View)                      │
├─────────────────────────────────────────────────────┤
│ [1] repo-name (pending)  user:john  [↑][↓][Cancel]  │
│ [2] other-repo (pending) user:jane  [↑][↓][Cancel]  │
│ [3] test-repo (running)  guest:abc  [Cancel]        │
│ [4] old-repo (pending)   user:admin [↑][↓][Cancel]  │
└─────────────────────────────────────────────────────┘
[Clear Queue] [Pause Queue]
```

---

## Datenbank Schema Änderungen

```python
class Scan(Base):
    # ... existing fields ...
    priority: int = Column(Integer, default=0, index=True)  # Für Position
    cancelled_at: Optional[datetime] = Column(DateTime, nullable=True)
    cancelled_by: Optional[UUID] = Column(UUID, ForeignKey("users.id"), nullable=True)
    cancellation_reason: Optional[str] = Column(String, nullable=True)
```

---

## Redis Queue Management

### Aktuell:
- `scan_queue`: Liste (FIFO)
- Worker: `BRPOP` zum Dequeue

### Erweitert:
- `scan_queue:priority`: Sorted Set (optional, für Position Change)
- `scan_queue:paused`: Flag (für Pause/Resume)
- `scan:{scan_id}:status`: Hash (für Status-Tracking)

---

## Security & Permissions

### User Permissions:
- ✅ View: Nur eigene Scans
- ✅ Cancel: Nur eigene Scans (wenn pending/running)
- ✅ Delete: Nur eigene Scans (wenn pending)
- ❌ Position Change: Nicht erlaubt
- ❌ Admin Actions: Nicht erlaubt

### Admin Permissions:
- ✅ View: Alle Scans
- ✅ Cancel: Alle Scans
- ✅ Delete: Alle Scans
- ✅ Position Change: Alle Scans
- ✅ Clear Queue: Erlaubt
- ✅ Pause/Resume: Erlaubt

---

## Implementierungs-Reihenfolge

1. **Delete Scan from Queue** (höchste Priorität)
   - User kann eigene Scans löschen
   - Admin kann alle löschen
   - Entfernt aus Redis + DB

2. **Remove from Redis Queue** (wenn Scan "hängt")
   - Admin-only
   - Nur Redis, nicht DB

3. **Position Change** (nur Admin)
   - Priority-Feld implementieren
   - API Endpoint
   - Queue-Sortierung anpassen

4. **Cancel Scan verbessern**
   - Entfernt aus Redis Queue
   - Stoppt Worker

5. **Queue Management** (optional)
   - Clear Queue
   - Pause/Resume
