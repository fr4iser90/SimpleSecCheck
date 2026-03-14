# SimpleSecCheck Backend - Refactored DDD Architecture

## Overview

This is the refactored backend implementation of SimpleSecCheck following Domain-Driven Design (DDD) principles with clear layer separation.

## Architecture

### Layer Structure

```
backend-refactored/
├── api/                        # REST API Layer (FastAPI)
│   ├── auth/                   # Authentication endpoints
│   ├── scans/                  # Scan management endpoints
│   ├── results/                # Results endpoints
│   ├── health.py               # Health check endpoint
│   └── __init__.py
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
│   ├── auth/                   # Authentication entities
│   ├── job/                    # Job entities and value objects
│   ├── scanner/                # Scanner entities
│   └── targets/                # Target entities
│
├── infrastructure/             # Infrastructure Layer
│   ├── database/               # Database adapters
│   ├── redis/                  # Redis client
│   ├── docker_runner.py        # Docker execution
│   ├── logging_config.py       # Logging setup
│   └── scanner_execution/      # Scanner execution logic
│
├── worker/                     # Scanner Worker Container
│   ├── main.py                 # Worker entrypoint
│   └── jobs/                   # Job definitions
│
├── config/                     # Configuration
│   ├── scanner_config.yaml
│   └── settings.py
│
├── scripts/                    # Utility scripts
├── Dockerfile                  # Backend container
├── docker-entrypoint.sh        # Container startup
├── requirements.txt            # Dependencies
└── README.md                   # This file
```

### Layer Responsibilities

#### API Layer
- **Purpose**: HTTP endpoints only
- **Responsibilities**: Request validation, response formatting
- **Dependencies**: Application layer services only

#### Application Layer
- **Purpose**: Orchestration and coordination
- **Responsibilities**: Business process orchestration, use case execution
- **Dependencies**: Domain layer entities, infrastructure adapters

#### Domain Layer
- **Purpose**: Pure business logic
- **Responsibilities**: Entities, value objects, domain services
- **Dependencies**: No external dependencies

#### Infrastructure Layer
- **Purpose**: External system integration
- **Responsibilities**: Database, Redis, Docker, logging
- **Dependencies**: External libraries only

#### Worker Layer
- **Purpose**: Scan job execution
- **Responsibilities**: Job processing, scanner execution
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

## Development

### Running the Backend

```bash
# Install dependencies
pip install -r requirements.txt

# Start database and Redis
docker compose up postgres redis

# Run backend
python -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

### Testing

```bash
# Run tests
python -m pytest

# Run with coverage
python -m pytest --cov=backend_refactored
```

### Code Quality

```bash
# Format code
black backend_refactored/

# Type checking
mypy backend_refactored/

# Linting
ruff check backend_refactored/
```

## Migration from Original Backend

### Current Status
- [ ] Domain layer refactoring
- [ ] Application layer implementation
- [ ] Infrastructure layer cleanup
- [ ] API layer simplification
- [ ] Worker separation
- [ ] Configuration management

### Migration Steps

1. **Phase A**: Analyze current structure and identify components
2. **Phase B**: Refactor domain layer (entities, value objects)
3. **Phase C**: Implement application layer (services, use cases)
4. **Phase D**: Clean up infrastructure layer
5. **Phase E**: Simplify API layer
6. **Phase F**: Separate worker container
7. **Phase G**: Update configuration and deployment

## Configuration

### Environment Variables

```bash
# Database
DATABASE_URL=postgresql://user:password@host:port/database

# Redis
REDIS_URL=redis://localhost:6379

# Application
SECRET_KEY=your-secret-key
DEBUG=false
```

### Docker Configuration

```bash
# Build backend
docker build -t simpleseccheck-backend .

# Run with compose
docker compose up backend-refactored
```

## Monitoring

### Health Checks
- Database connectivity
- Redis connectivity
- API responsiveness

### Metrics
- Request/response times
- Queue depth
- Job processing rates

### Logging
- Structured logging
- Request tracing
- Error tracking

## Security

### Authentication
- JWT tokens
- Session management
- Role-based access

### Authorization
- Permission checking
- Resource access control

### Data Protection
- Input validation
- SQL injection prevention
- XSS protection

## Future Enhancements

- [ ] Event sourcing for audit trails
- [ ] CQRS pattern implementation
- [ ] Microservice extraction
- [ ] Advanced caching strategies
- [ ] Performance optimization