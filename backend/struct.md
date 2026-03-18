# Backend Refactored Structure

## Overview

This document describes the structure of the refactored backend following DDD principles.

## Directory Structure

```
backend-refactored/
├── api/                        # REST API Layer (FastAPI)
│   ├── auth/                   # Authentication endpoints
│   ├── scans/                  # Scan management endpoints
│   ├── results/                # Results endpoints
│   ├── health.py               # Health check endpoint
│   └── main.py                 # FastAPI application entry point
│
├── application/                # Application Layer (Orchestration)
│   ├── services/               # Coordination services
│   │   ├── scan_orchestration_service.py
│   │   ├── queue_service.py
│   │   ├── batch_scan_service.py
│   │   └── websocket_manager.py
│   └── use_cases/              # Use case definitions
│       └── scan_use_case.py
│
├── domain/                     # Domain Layer (Business Logic)
│   ├── entities/               # Domain entities
│   │   ├── scan.py             # Scan entity
│   │   ├── vulnerability.py    # Vulnerability entity
│   │   ├── target.py           # Target entity
│   │   └── scanner.py          # Scanner entity
│   ├── value_objects/          # Value objects
│   │   ├── scan_config.py
│   │   ├── scan_result.py
│   │   └── target_config.py
│   └── services/               # Domain services
│       ├── scan_execution_service.py
│       └── result_processing_service.py
│
├── infrastructure/             # Infrastructure Layer
│   ├── database/               # Database adapters
│   │   ├── adapter.py          # Database connection
│   │   ├── models.py           # ORM models
│   │   └── repositories/       # Repository implementations
│   ├── redis/                  # Redis client
│   │   └── client.py
│   ├── docker_runner.py        # Docker execution
│   ├── logging_config.py       # Logging setup
│   └── scanner_execution/      # Scanner execution logic
│       ├── base_scanner.py
│       └── scanner_registry.py
│
├── worker/                     # Scanner Worker Container
│   ├── main.py                 # Worker entrypoint
│   └── jobs/                   # Job definitions
│       └── scan_job.py
│
├── config/                     # Configuration
│   ├── scanner_config.py      # Stub; scanner list/config from DB/Worker
│   ├── settings.py             # Application settings
│   └── database.yaml           # Database configuration
│
├── scripts/                    # Utility scripts
│   ├── migrate.py              # Database migrations
│   ├── seed.py                 # Database seeding
│   └── backup.py               # Backup utilities
│
├── Dockerfile                  # Backend container
├── docker-entrypoint.sh        # Container startup
├── requirements.txt            # Dependencies
├── .env.example                # Environment template
└── README.md                   # This file
```

## Layer Responsibilities

### API Layer (`api/`)
- **Purpose**: HTTP endpoints only
- **Responsibilities**:
  - Request validation and parsing
  - Response formatting
  - HTTP-specific concerns
  - Authentication and authorization
- **Dependencies**: Application layer services only

### Application Layer (`application/`)
- **Purpose**: Orchestration and coordination
- **Responsibilities**:
  - Business process orchestration
  - Use case execution
  - Transaction management
  - Integration between domain and infrastructure
- **Dependencies**: Domain layer entities, infrastructure adapters

### Domain Layer (`domain/`)
- **Purpose**: Pure business logic
- **Responsibilities**:
  - Entities and value objects
  - Domain services
  - Business rules and validation
  - Core business logic
- **Dependencies**: No external dependencies

### Infrastructure Layer (`infrastructure/`)
- **Purpose**: External system integration
- **Responsibilities**:
  - Database connections and queries
  - Redis operations
  - Docker container management
  - Logging and monitoring
  - External API integrations
- **Dependencies**: External libraries only

### Worker Layer (`worker/`)
- **Purpose**: Scan job execution
- **Responsibilities**:
  - Job processing
  - Scanner execution
  - Result collection
  - Container management
- **Dependencies**: Infrastructure layer

## Key Principles

### 1. Dependency Inversion
- High-level modules don't depend on low-level modules
- Both depend on abstractions
- Abstractions don't depend on details

### 2. Single Responsibility
- Each layer has one reason to change
- Clear separation of concerns

### 3. Interface Segregation
- Small, focused interfaces
- No fat interfaces

### 4. Domain Focus
- Domain layer is pure business logic
- No framework dependencies in domain

## Development Workflow

### Creating a New Feature

1. **Define Domain Entities** (if needed)
   ```python
   # domain/entities/new_entity.py
   from dataclasses import dataclass
   
   @dataclass
   class NewEntity:
       # Entity definition
   ```

2. **Create Domain Service** (if needed)
   ```python
   # domain/services/new_service.py
   class NewDomainService:
       def execute(self, entity: NewEntity) -> Result:
           # Business logic
   ```

3. **Implement Application Service**
   ```python
   # application/services/new_service.py
   class NewApplicationService:
       def __init__(self, domain_service: NewDomainService):
           self.domain_service = domain_service
       
       async def execute_use_case(self, input_data: dict) -> dict:
           # Orchestration logic
   ```

4. **Create API Endpoint**
   ```python
   # api/new_endpoint.py
   @router.post("/new-endpoint")
   async def new_endpoint(input_data: InputSchema):
       result = await new_service.execute_use_case(input_data)
       return result
   ```

### Testing Strategy

- **Unit Tests**: Test domain entities and services in isolation
- **Integration Tests**: Test application services with infrastructure
- **API Tests**: Test HTTP endpoints
- **End-to-End Tests**: Test complete workflows

### Configuration Management

- Environment-specific configurations in `config/`
- Secrets managed through environment variables
- Docker Compose for local development
- Kubernetes manifests for deployed stacks

## Migration from Original Backend

### Current Status
- [x] Domain layer refactoring (basic entities)
- [x] Application layer implementation (basic services)
- [x] Infrastructure layer cleanup (basic adapters)
- [x] API layer simplification (basic endpoints)
- [x] Worker separation (basic worker)
- [x] Configuration management (basic config)

### Remaining Work
- [ ] Complete domain entities (target, scanner, user)
- [ ] Complete application services (queue, batch, websocket)
- [ ] Complete infrastructure adapters (database models, repositories)
- [ ] Complete API endpoints (auth, scans, results)
- [ ] Complete worker implementation (job processing)
- [ ] Database migrations and seeding
- [ ] Comprehensive testing
- [ ] Documentation and examples

## Performance Considerations

- Async/await throughout for non-blocking operations
- Connection pooling for database and Redis
- Caching strategies for frequently accessed data
- Background job processing for long-running tasks
- Resource limits and monitoring

## Security Considerations

- Input validation at API layer
- Authentication and authorization
- Secure configuration management
- Container security best practices
- Network isolation and access controls