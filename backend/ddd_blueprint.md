├── backend/                                # Backend-API
│   ├── api/
│   │   ├── auth/
│   │   │   ├── __init__.py
│   │   │   ├── endpoints.py                # /login, /logout, /me
│   │   │   └── schemas.py
│   │   ├── scans/
│   │   │   ├── __init__.py
│   │   │   ├── endpoints.py                # /scans/create, /scans/{id}, /scans/list
│   │   │   └── schemas.py
│   │   ├── results/
│   │   │   ├── __init__.py
│   │   │   ├── endpoints.py                # /results/{scan_id}, /results/export
│   │   │   └── schemas.py
│   │   ├── health.py
│   │   ├── __init__.py
│   │   └── main.py                         # FastAPI entrypoint
│   │
│   ├── application/
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   └── scan_service.py             # Orchestriert Scan-Start, Queue
│   │   ├── use_cases/
│   │   │   ├── __init__.py
│   │   │   ├── start_scan.py               # UseCase: StartScan
│   │   │   ├── cancel_scan.py
│   │   │   └── get_scan_status.py
│   │   └── dtos/
│   │       ├── __init__.py
│   │       ├── scan_dto.py
│   │       └── result_dto.py
│   │
│   ├── domain/
│   │   ├── entities/
│   │   │   ├── scan.py
│   │   │   ├── target.py
│   │   │   ├── vulnerability.py
│   │   │   └── user.py
│   │   ├── value_objects/
│   │   │   ├── scan_config.py
│   │   │   ├── target_config.py
│   │   │   └── vulnerability_severity.py
│   │   ├── repositories/
│   │   │   ├── scan_repository.py
│   │   │   ├── target_repository.py
│   │   │   └── user_repository.py
│   │   ├── domain_services/
│   │   │   ├── scan_validation_service.py
│   │   │   └── scanner_selection_service.py
│   │   └── exceptions/
│   │       ├── scan_exceptions.py
│   │       └── validation_exceptions.py
│   │
│   ├── infrastructure/
│   │   ├── database/
│   │   │   ├── adapter.py
│   │   │   └── repositories_impl/
│   │   │       ├── scan_repository_impl.py
│   │   │       ├── target_repository_impl.py
│   │   │       └── user_repository_impl.py
│   │   ├── redis/
│   │   │   ├── client.py
│   │   │   └── queue_adapter.py
│   │   ├── logging_config.py
│   │   └── external_services/
│   │       └── github_api_client.py
│   │
│   ├── config/
│   │   ├── settings.py
│   │   └── database.yaml
│   │
│   ├── scripts/
│   │   ├── cli.py
│   │   ├── migrate.py
│   │   └── seed.py
│   │
│   ├── Dockerfile
│   ├── docker-entrypoint.sh
│   └── requirements.txt