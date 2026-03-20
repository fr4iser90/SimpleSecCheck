"""
E2E: Gleiches Git-Target, 3 Scans — Zeit, echte Parallelität (API-Status), Docker-Stats.

- Misst max. gleichzeitig ``running`` (schnelles Polling nach Scan-Start).
- Assert: bei concurrency 1 nie >1 running; bei 2 mindestens 2; bei 3 mindestens 3.
- Docker: CPU/RAM von worker/backend/scanner-Containern bei Peak-Parallelität + am Rundenende.

  export SSC_BENCHMARK_EMAIL='...'
  export SSC_BENCHMARK_PASSWORD='...'
  pytest tests/e2e/test_worker_parallelism_benchmark.py -v -s

  SSC_BENCHMARK_AUTO_RESTART=0 — kein ``docker compose restart worker`` (nur wenn du Slots selbst stimmst)
  SSC_COMPOSE_DIR — Repo-Root mit docker-compose.yml (Default: aktuelles Arbeitsverzeichnis)

Ohne Neustart greift ein neues max_concurrent_jobs nicht (Worker liest DB nur beim Start;
MAX_CONCURRENT_JOBS in Compose überschreibt die DB dauerhaft).

Wenn Scans zu schnell durch sind (nur trivy): mehr Scanner setzen, z.B.
  SSC_BENCHMARK_SCANNERS='trivy semgrep'

Parallelitäts-Assert abschalten (nur messen):
  SSC_BENCHMARK_SKIP_PARALLEL_ASSERT=1
"""
from __future__ import annotations

import os
import re
import subprocess
import time

import httpx
import pytest

from tests.e2e.manifest_timeouts import max_scan_profile_timeout_seconds_all_plugins

BASE = os.environ.get("SSC_BENCHMARK_BASE", "http://localhost:8080").rstrip("/")
TARGET = os.environ.get("SSC_BENCHMARK_TARGET", "https://github.com/fr4iser90/SimpleSecCheck")
BRANCH = os.environ.get("SSC_BENCHMARK_BRANCH", "main")
SCANNERS = os.environ.get("SSC_BENCHMARK_SCANNERS", "trivy").strip().split()
PARALLEL_ROUNDS = [int(x) for x in os.environ.get("SSC_BENCHMARK_ROUNDS", "1,2,3").split(",")]
POLL = float(os.environ.get("SSC_BENCHMARK_POLL", "10"))
_mw = os.environ.get("SSC_BENCHMARK_MAX_WAIT", "").strip()
MAX_WAIT = int(_mw) if _mw else max_scan_profile_timeout_seconds_all_plugins()
FAST_POLL = float(os.environ.get("SSC_BENCHMARK_FAST_POLL", "0.4"))
FAST_PHASE_SEC = float(os.environ.get("SSC_BENCHMARK_FAST_PHASE_SEC", "180"))
SKIP_PARALLEL_ASSERT = os.environ.get("SSC_BENCHMARK_SKIP_PARALLEL_ASSERT", "").strip() == "1"
AUTO_RESTART_WORKER = os.environ.get("SSC_BENCHMARK_AUTO_RESTART", "1").strip() != "0"


def _need_creds():
    return bool(os.environ.get("SSC_BENCHMARK_EMAIL") and os.environ.get("SSC_BENCHMARK_PASSWORD"))


pytestmark = pytest.mark.skipif(
    not _need_creds(),
    reason="SSC_BENCHMARK_EMAIL + SSC_BENCHMARK_PASSWORD setzen",
)


def _login(client: httpx.Client) -> str:
    r = client.post(
        f"{BASE}/api/v1/auth/login",
        json={
            "email": os.environ["SSC_BENCHMARK_EMAIL"],
            "password": os.environ["SSC_BENCHMARK_PASSWORD"],
        },
        timeout=60,
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data.get("role") == "admin", "Admin nötig für worker-jobs"
    return data["access_token"]


def _put_jobs(client: httpx.Client, token: str, n: int) -> None:
    r = client.put(
        f"{BASE}/api/admin/config/worker-jobs",
        headers={"Authorization": f"Bearer {token}"},
        json={"max_concurrent_jobs": n},
        timeout=30,
    )
    assert r.status_code == 200, r.text


def _try_restart_worker() -> tuple[bool, str]:
    d = os.environ.get("SSC_COMPOSE_DIR", ".")
    p = subprocess.run(
        ["docker", "compose", "restart", "worker"],
        cwd=d,
        capture_output=True,
        text=True,
    )
    if p.returncode != 0:
        return False, (p.stderr or p.stdout or "unknown error")[:800]
    time.sleep(15)
    return True, ""


def _worker_max_concurrent_jobs_env() -> int | None:
    """Wenn gesetzt, überschreibt MAX_CONCURRENT_JOBS die DB — dann kein Parallel-Benchmark."""
    name = os.environ.get("SSC_WORKER_CONTAINER", "SimpleSecCheck_worker")
    try:
        p = subprocess.run(
            ["docker", "inspect", name, "--format", "{{range .Config.Env}}{{println .}}{{end}}"],
            capture_output=True,
            text=True,
            timeout=20,
        )
        if p.returncode != 0:
            return None
        for line in p.stdout.splitlines():
            if line.startswith("MAX_CONCURRENT_JOBS="):
                v = line.split("=", 1)[1].strip()
                if not v:
                    continue
                try:
                    return max(1, int(v))
                except ValueError:
                    continue
    except (subprocess.TimeoutExpired, FileNotFoundError, ValueError):
        pass
    return None


def _verify_db_worker_jobs(client: httpx.Client, token: str, expected: int) -> None:
    r = client.get(
        f"{BASE}/api/admin/config",
        headers={"Authorization": f"Bearer {token}"},
        timeout=30,
    )
    assert r.status_code == 200, r.text
    n = r.json().get("max_concurrent_jobs")
    assert int(n) == expected, f"DB max_concurrent_jobs ist {n}, erwartet {expected}"


def _create_scan(client: httpx.Client, token: str, label: str) -> str:
    r = client.post(
        f"{BASE}/api/v1/scans/",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "name": f"e2e-bench {label}",
            "scan_type": "code",
            "target_url": TARGET,
            "scanners": SCANNERS,
            "config": {"git_branch": BRANCH},
        },
        timeout=120,
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _status(client: httpx.Client, token: str, scan_id: str) -> str:
    r = client.get(
        f"{BASE}/api/v1/scans/{scan_id}/status",
        headers={"Authorization": f"Bearer {token}"},
        timeout=30,
    )
    if r.status_code != 200:
        return "unknown"
    return (r.json().get("status") or "unknown").lower()


def _docker_stats_all() -> list[tuple[str, str, str, float]]:
    """Alle Container, sortiert nach CPU absteigend (Scanner-Jobs haben oft Random-Namen)."""
    try:
        p = subprocess.run(
            [
                "docker",
                "stats",
                "--no-stream",
                "--format",
                "{{.Name}}|{{.CPUPerc}}|{{.MemUsage}}",
            ],
            capture_output=True,
            text=True,
            timeout=45,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return []
    rows: list[tuple[str, str, str, float]] = []
    for line in p.stdout.strip().splitlines():
        parts = line.split("|", 2)
        if len(parts) != 3:
            continue
        name, cpu, mem = parts
        rows.append((name, cpu, mem, _parse_cpu_pct(cpu)))
    rows.sort(key=lambda x: -x[3])
    return rows


def _docker_stats_relevant() -> list[tuple[str, str, str]]:
    all_rows = _docker_stats_all()
    out: list[tuple[str, str, str]] = []
    for name, cpu, mem, _ in all_rows:
        nl = name.lower()
        if any(x in nl for x in ("worker", "backend", "scanner", "simpleseccheck")):
            out.append((name, cpu, mem))
    # Top-6 nach CPU (erfasst auch frische Scan-Container ohne festen Namen)
    top = [(n, c, m) for n, c, m, _ in all_rows[:6]]
    seen = {n for n, _, _ in out}
    for n, c, m in top:
        if n not in seen:
            out.append((n, c, m))
            seen.add(n)
    return out[:12]


def _parse_cpu_pct(s: str) -> float:
    m = re.search(r"([\d.]+)", s)
    return float(m.group(1)) if m else 0.0


def test_parallelism_wall_time_three_scans():
    terminal = {"completed", "failed", "cancelled", "interrupted"}
    results: list[tuple[int, float, list[str], int, list[tuple[str, str, str]]]] = []

    with httpx.Client(timeout=httpx.Timeout(120.0)) as client:
        token = _login(client)

        for conc in PARALLEL_ROUNDS:
            print(f"\n>>> max_concurrent_jobs = {conc}")
            _put_jobs(client, token, conc)
            if AUTO_RESTART_WORKER:
                print("    docker compose restart worker (Slots aus DB wirksam)…")
                ok, err = _try_restart_worker()
                if not ok:
                    pytest.fail(
                        "Worker-Neustart fehlgeschlagen — ohne den greift das neue max_concurrent_jobs nicht.\n"
                        f"  {err}\n"
                        "Von Repo-Root ausführen oder SSC_COMPOSE_DIR setzen.\n"
                        "Wenn der Worker MAX_CONCURRENT_JOBS per Env hat: Wert anpassen oder Env entfernen.\n"
                        "Nur messen ohne Neustart: SSC_BENCHMARK_AUTO_RESTART=0 + SSC_BENCHMARK_SKIP_PARALLEL_ASSERT=1"
                    )
                _verify_db_worker_jobs(client, token, conc)
                env_cap = _worker_max_concurrent_jobs_env()
                if env_cap is not None and env_cap < conc:
                    pytest.fail(
                        f"Worker-Container: MAX_CONCURRENT_JOBS={env_cap} (überschreibt DB). "
                        f"Runde braucht {conc} Slots.\n"
                        "→ Zeile MAX_CONCURRENT_JOBS aus .env löschen oder auf >= diese Runde setzen; "
                        "`docker compose up -d worker`."
                    )
                if env_cap is not None:
                    print(f"    Hinweis: MAX_CONCURRENT_JOBS={env_cap} im Container (nicht DB).")
            else:
                print(
                    "    WARN: SSC_BENCHMARK_AUTO_RESTART=0 — parallel-Assert kann scheitern, "
                    "wenn der Worker noch alte Slot-Zahl nutzt."
                )

            ids: list[str] = []
            t0 = time.time()
            for i in range(3):
                sid = _create_scan(client, token, f"p{conc}-{i + 1}")
                ids.append(sid)
                print(f"    scan {i + 1}: {sid}")

            max_running = 0
            peak_stats: list[tuple[str, str, str]] = []
            fast_until = time.time() + FAST_PHASE_SEC
            deadline = t0 + MAX_WAIT
            last_log = 0.0
            total_cpu_peak = 0.0

            while time.time() < deadline:
                states = [_status(client, token, s) for s in ids]
                running = sum(1 for st in states if st == "running")
                max_running = max(max_running, running)

                now = time.time()
                use_fast = now < fast_until
                interval = FAST_POLL if use_fast else POLL

                if running >= conc and conc >= 1:
                    stats = _docker_stats_relevant()
                    if stats:
                        peak_stats = stats
                        sm = sum(_parse_cpu_pct(c) for _, c, _ in stats)
                        total_cpu_peak = max(total_cpu_peak, sm)

                if all(st in terminal for st in states):
                    elapsed = now - t0
                    print(f"    fertig nach {elapsed:.1f}s  {states}")
                    print(f"    Parallelität: max. gleichzeitig 'running' = {max_running}")
                    if peak_stats:
                        print("    Docker (letzter Snapshot bei hoher Last / relevante Container):")
                        for n, c, m in peak_stats:
                            print(f"      {n}: CPU {c}  MEM {m}")
                        print(f"    Summe CPU% (genähert, über obige Zeilen): max {total_cpu_peak:.1f}%")
                    end_stats = _docker_stats_relevant()
                    if end_stats:
                        print("    Docker Ende Runde:")
                        for n, c, m in end_stats:
                            print(f"      {n}: CPU {c}  MEM {m}")

                    if not SKIP_PARALLEL_ASSERT:
                        if conc == 1:
                            assert max_running <= 1, (
                                f"Bei 1 Job-Slot sollten nie 2 Scans parallel laufen, "
                                f"max_running={max_running}"
                            )
                        elif conc == 2:
                            assert max_running >= 2, (
                                f"Erwartet mindestens 2 Scans gleichzeitig running (Worker-Slots=2). "
                                f"Max beobachtet: {max_running}. "
                                f"Scans evtl. zu kurz — SSC_BENCHMARK_SCANNERS erweitern oder "
                                f"SSC_BENCHMARK_SKIP_PARALLEL_ASSERT=1."
                            )
                        elif conc >= 3:
                            assert max_running >= 3, (
                                f"Erwartet 3 parallel running. Max: {max_running}. "
                                f"Mehr Scanner oder SKIP_PARALLEL_ASSERT."
                            )

                    results.append((conc, elapsed, states, max_running, peak_stats or end_stats))
                    break

                if now - last_log >= (2.0 if use_fast else POLL):
                    print(
                        f"    … {now - t0:.0f}s  running={running} max_seen={max_running}  "
                        f"{list(zip([i[:8] for i in ids], states))}"
                    )
                    last_log = now

                time.sleep(interval)
            else:
                pytest.fail(f"Timeout scans {ids}")

        assert len(results) == len(PARALLEL_ROUNDS)
        print("\n=== Zusammenfassung ===")
        for conc, elapsed, states, max_run, _ in results:
            print(
                f"  concurrency {conc}: {elapsed:.1f}s  max_parallel_running={max_run}  end={states}"
            )
