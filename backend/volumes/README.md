# SimpleSecCheck Volume Management

This directory contains the volume management system for SimpleSecCheck, providing persistent storage, configuration management, and backup/restore capabilities for all services.

## 📁 Directory Structure

```
volumes/
├── README.md                    # This file
├── redis_config.py             # Redis configuration and persistence
├── results_manager.py          # Results storage and organization
├── config_manager.py           # Configuration management
├── scripts/                    # Management scripts
│   └── setup_volumes.sh        # Complete volume setup script
└── templates/                  # Configuration templates (created by setup)
```

## 🚀 Quick Start

### Automated Setup

Run the setup script to configure all volume management components:

```bash
# Run the setup script
./volumes/scripts/setup_volumes.sh

# Or with custom data path
DATA_PATH=/custom/path ./volumes/scripts/setup_volumes.sh
```

### Manual Setup

1. **Create volume directories:**
   ```bash
   mkdir -p /data/volumes/{backend,worker,redis,database,results,config}
   mkdir -p /data/backups/{backend,worker,redis,database,results,config}
   ```

2. **Set permissions:**
   ```bash
   chmod 755 /data/volumes
   chmod 700 /data/volumes/redis
   chmod 700 /data/volumes/database
   ```

3. **Setup Redis configuration:**
   ```bash
   python3 -c "from volumes.redis_config import redis_config_manager; redis_config_manager.setup_redis_directories()"
   ```

## 🔧 Components

### Redis Configuration (`redis_config.py`)

Manages Redis persistence and configuration for optimal performance:

**Features:**
- AOF (Append Only File) and RDB persistence
- Performance tuning for scan operations
- Backup and restore capabilities
- Health monitoring and maintenance

**Configuration:**
- **AOF**: Every second fsync for balance between performance and durability
- **RDB**: Multiple save conditions (900s/1, 300s/10, 60s/10000)
- **Memory**: 2GB max with LRU eviction policy
- **Security**: Password protection and command renaming

**Usage:**
```python
from volumes.redis_config import redis_config_manager

# Setup Redis directories
redis_config_manager.setup_redis_directories()

# Generate configuration
redis_config_manager.generate_redis_config()

# Get health status
status = redis_config_manager.get_redis_health_status()
```

### Results Manager (`results_manager.py`)

Organizes and manages scan results with proper retention policies:

**Features:**
- Structured directory organization (logs, outputs, reports, metadata)
- Compression and archiving for storage optimization
- Retention policies and cleanup automation
- Backup and restore capabilities

**Directory Structure:**
```
results/
├── [scan_name]_[timestamp]_[id]/
│   ├── logs/           # Scan execution logs
│   ├── outputs/        # Scanner outputs (JSON, TXT, SARIF)
│   ├── reports/        # Generated reports (HTML, PDF, MD)
│   ├── metadata/       # Scan metadata and configuration
│   └── archives/       # Compressed archives
└── tmp/               # Temporary project copies
```

**Usage:**
```python
from volumes.results_manager import results_manager

# Organize scan results
directories = results_manager.organize_scan_results(scan_id, scan_name)

# Store scanner output
results_manager.store_scan_output(directories["outputs"], "bandit", output_data)

# Compress results
results_manager.compress_scan_results(scan_dir)

# Cleanup old results
results_manager.cleanup_old_results(retention_days=180)
```

### Configuration Manager (`config_manager.py`)

Manages shared configuration files for all services:

**Features:**
- Scanner configuration templates
- Security policy management
- Environment-specific configurations
- Configuration validation and backup

**Configuration Structure:**
```
config/
├── scanners/         # Scanner-specific configurations
├── policies/         # Security policies and rules
├── templates/        # Scan templates and presets
├── environments/     # Environment-specific configurations
├── secrets/          # Encrypted secrets and credentials
└── overrides/        # Configuration overrides
```

**Usage:**
```python
from volumes.config_manager import config_manager

# Setup configuration directories
config_manager.setup_config_directories()

# Get scanner configuration
scanner_config = config_manager.get_scanner_config("bandit")

# Update configuration
config_manager.update_scanner_config("bandit", new_config)

# Validate all configurations
validation_results = config_manager.validate_configurations()
```

## 🛠️ Management Scripts

### Setup Script (`scripts/setup_volumes.sh`)

Comprehensive setup script that configures all volume management components:

**Features:**
- Automated directory creation and permission setup
- Redis configuration generation
- Results management setup
- Configuration management setup
- Backup and restore procedures
- Health monitoring scripts
- Systemd service creation (optional)

**Usage:**
```bash
# Basic setup
./scripts/setup_volumes.sh

# With custom data path
DATA_PATH=/custom/path ./scripts/setup_volumes.sh

# With verbose output
./scripts/setup_volumes.sh -v
```

### Health Check Script

Monitor the health of all volume components:

```bash
# Run health check
/data/config/scripts/health_check.sh

# Check status
cat /tmp/simpleseccheck_health.json
```

### Backup and Restore Scripts

Complete backup and restore procedures:

```bash
# Full backup
/data/config/scripts/backup_all.sh

# Restore from backup
/data/config/scripts/restore_all.sh /path/to/backup

# Redis-specific backup
/data/config/redis/redis_backup.sh
```

## 📊 Monitoring and Maintenance

### Health Monitoring

The system provides comprehensive health monitoring:

- **Volume Status**: Check if all required directories exist
- **Configuration Status**: Validate configuration files
- **Redis Health**: Monitor Redis connectivity and performance
- **Storage Usage**: Track disk space and file counts

### Backup Strategies

**Automated Backups:**
- Daily Redis backups via systemd timer
- Weekly full system backups
- Configuration-only backups

**Backup Locations:**
- Local backups: `/data/backups/`
- Remote backups: Configurable via environment variables
- Cloud backups: Integration points available

### Retention Policies

**Results Retention:**
- Default: 180 days
- Configurable per environment
- Automatic cleanup with size reporting

**Backup Retention:**
- Redis backups: Last 10 backups
- Full backups: Last 5 backups
- Configuration backups: Last 20 backups

## 🔒 Security Considerations

### File Permissions

- **Configuration directories**: 755 (readable by services)
- **Redis data**: 700 (restricted access)
- **Database data**: 700 (restricted access)
- **Secrets**: 700 (highly restricted)

### Data Protection

- **Encryption**: Secrets are encrypted at rest
- **Access Control**: Service-specific user accounts
- **Audit Logging**: All configuration changes logged
- **Backup Security**: Encrypted backup files

## 🐳 Docker Integration

### Volume Mounts

```yaml
volumes:
  - simpleseccheck-backend:/data/volumes/backend
  - simpleseccheck-worker:/data/volumes/worker
  - simpleseccheck-redis:/data/volumes/redis
  - simpleseccheck-database:/data/volumes/database
  - simpleseccheck-results:/data/volumes/results
  - simpleseccheck-config:/data/config
```

### Environment Variables

```bash
DATA_PATH=/data
REDIS_PASSWORD=your_redis_password
BACKUP_PATH=/backups
```

## 🔧 Troubleshooting

### Common Issues

**Redis Not Starting:**
```bash
# Check Redis configuration
cat /data/config/redis/redis.conf

# Check permissions
ls -la /data/volumes/redis

# Check logs
tail -f /var/log/redis/redis-server.log
```

**Results Not Found:**
```bash
# Check results directory
ls -la /data/volumes/results

# Check permissions
ls -la /data/volumes/results

# Check configuration
cat /data/config/results/organize_results.sh
```

**Configuration Errors:**
```bash
# Validate configurations
python3 -c "from volumes.config_manager import config_manager; print(config_manager.validate_configurations())"

# Check configuration files
find /data/config -name "*.json" -exec jsonlint {} \;
```

### Performance Optimization

**Redis Optimization:**
- Adjust memory limits based on available RAM
- Tune AOF fsync frequency for your requirements
- Monitor slow queries and optimize

**Storage Optimization:**
- Use SSD storage for better I/O performance
- Implement compression for large result files
- Regular cleanup of old data

**Backup Optimization:**
- Use incremental backups for large datasets
- Compress backup files
- Store backups on separate storage

## 📈 Scaling Considerations

### Horizontal Scaling

- **Redis**: Use Redis Cluster for high availability
- **Database**: Implement read replicas
- **Results**: Use distributed storage (S3, etc.)
- **Configuration**: Use configuration management tools

### Vertical Scaling

- **Memory**: Increase Redis and application memory
- **Storage**: Use faster storage solutions
- **Network**: Optimize network bandwidth

## 🤝 Contributing

When contributing to the volume management system:

1. **Follow DDD principles**: Keep domain boundaries clear
2. **Maintain backward compatibility**: Don't break existing configurations
3. **Add tests**: Include unit and integration tests
4. **Update documentation**: Keep this README current
5. **Test thoroughly**: Test on different environments

## 📞 Support

For issues and questions:

1. **Check logs**: Review service logs for error details
2. **Run health checks**: Use the health check script
3. **Validate configurations**: Use the validation tools
4. **Check permissions**: Ensure proper file permissions
5. **Review documentation**: Check this README and related docs

## 📄 License

This volume management system is part of SimpleSecCheck and follows the same licensing terms.