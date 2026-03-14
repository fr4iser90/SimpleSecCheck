#!/bin/bash
# SimpleSecCheck Volume Setup Script
# This script sets up all volume management components

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
DATA_PATH="${DATA_PATH:-/data}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING:${NC} $1"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR:${NC} $1"
}

info() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] INFO:${NC} $1"
}

# Check if running as root
check_permissions() {
    if [[ $EUID -eq 0 ]]; then
        warn "Running as root. This is not recommended for production."
        read -p "Continue anyway? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            error "Setup cancelled."
            exit 1
        fi
    fi
}

# Install Python dependencies if needed
install_dependencies() {
    log "Installing volume management dependencies..."
    
    # Check if Python is available
    if ! command -v python3 &> /dev/null; then
        error "Python3 is required but not installed."
        exit 1
    fi
    
    # Install required Python packages
    python3 -m pip install --user --upgrade pip
    python3 -m pip install --user pyyaml
}

# Setup volume directories
setup_directories() {
    log "Setting up volume directories..."
    
    # Create base directories
    mkdir -p "$DATA_PATH/volumes"/{backend,worker,redis,database,results,config}
    mkdir -p "$DATA_PATH/backups"/{backend,worker,redis,database,results,config}
    mkdir -p "$DATA_PATH/config"/{scanners,policies,templates,environments,secrets,overrides}
    
    # Set permissions
    chmod 755 "$DATA_PATH/volumes"
    chmod 755 "$DATA_PATH/backups"
    chmod 755 "$DATA_PATH/config"
    
    # Set strict permissions for sensitive directories
    chmod 700 "$DATA_PATH/volumes/redis"
    chmod 700 "$DATA_PATH/volumes/database"
    chmod 700 "$DATA_PATH/config/secrets"
    
    log "Volume directories created successfully"
}

# Setup Redis configuration
setup_redis() {
    log "Setting up Redis configuration..."
    
    # Create Redis configuration directory
    mkdir -p "$DATA_PATH/config/redis"
    
    # Generate Redis configuration
    cat > "$DATA_PATH/config/redis/redis.conf" << 'EOF'
# SimpleSecCheck Redis Configuration
# Generated on $(date)

# Persistence Configuration
appendonly yes
appendfsync everysec
no-appendfsync-on-rewrite no
auto-aof-rewrite-percentage 100
auto-aof-rewrite-min-size 64mb
aof-load-truncated yes
aof-use-rdb-preamble yes

# RDB Configuration
save 900 1
save 300 10
save 60 10000
stop-writes-on-bgsave-error yes
rdbcompression yes
rdbchecksum yes

# Memory and Performance
maxmemory 2gb
maxmemory-policy allkeys-lru
tcp-keepalive 300
timeout 0

# Security
requirepass ${REDIS_PASSWORD:-defaultpassword}
rename-command FLUSHDB ""
rename-command FLUSHALL ""
rename-command DEBUG ""
rename-command CONFIG ""

# Logging
loglevel notice
logfile /var/log/redis/redis-server.log

# Network
bind 0.0.0.0
port 6379
protected-mode yes

# Client Configuration
maxclients 10000
client-output-buffer-limit normal 0 0 0
client-output-buffer-limit replica 256mb 64mb 60
client-output-buffer-limit pubsub 32mb 8mb 60

# Slow Log
slowlog-log-slower-than 10000
slowlog-max-len 128

# SimpleSecCheck Custom Settings
# Queue database (database 0)
# Session database (database 1)
# Cache database (database 2)
# Job database (database 3)
EOF

    # Create Redis backup script
    cat > "$DATA_PATH/config/redis/redis_backup.sh" << 'EOF'
#!/bin/bash
# SimpleSecCheck Redis Backup Script

set -e

REDIS_DATA_DIR="/data/volumes/redis"
BACKUP_DIR="/data/backups/redis"
DATE=$(date +"%Y%m%d_%H%M%S")
BACKUP_NAME="redis_backup_$DATE"
BACKUP_PATH="$BACKUP_DIR/$BACKUP_NAME"

mkdir -p "$BACKUP_DIR"
echo "Creating Redis backup: $BACKUP_NAME"

redis-cli BGSAVE
sleep 2

while [ $(redis-cli LASTSAVE) -eq $(redis-cli LASTSAVE) ]; do
    sleep 1
    echo "Waiting for Redis background save to complete..."
done

if [ -f "$REDIS_DATA_DIR/dump.rdb" ]; then
    mkdir -p "$BACKUP_PATH"
    cp "$REDIS_DATA_DIR/dump.rdb" "$BACKUP_PATH/"
    echo "RDB file copied to $BACKUP_PATH"
fi

if [ -f "$REDIS_DATA_DIR/appendonly.aof" ]; then
    cp "$REDIS_DATA_DIR/appendonly.aof" "$BACKUP_PATH/"
    echo "AOF file copied to $BACKUP_PATH"
fi

cat > "$BACKUP_PATH/metadata.json" << METADATA_EOF
{
    "backup_name": "$BACKUP_NAME",
    "timestamp": "$(date -Iseconds)",
    "redis_version": "$(redis-cli INFO server | grep redis_version | cut -d: -f2 | tr -d '\r')",
    "rdb_file": "dump.rdb",
    "aof_file": "appendonly.aof",
    "backup_type": "full"
}
METADATA_EOF

echo "Redis backup completed: $BACKUP_PATH"

cd "$BACKUP_DIR"
ls -t | tail -n +11 | xargs -r rm -rf
echo "Old backups cleaned up"
EOF

    chmod +x "$DATA_PATH/config/redis/redis_backup.sh"
    
    log "Redis configuration setup completed"
}

# Setup results management
setup_results() {
    log "Setting up results management..."
    
    # Create results organization script
    cat > "$DATA_PATH/config/results/organize_results.sh" << 'EOF'
#!/bin/bash
# SimpleSecCheck Results Organization Script

SCAN_ID="$1"
SCAN_NAME="$2"

if [ -z "$SCAN_ID" ] || [ -z "$SCAN_NAME" ]; then
    echo "Usage: $0 <scan_id> <scan_name>"
    exit 1
fi

RESULTS_PATH="/data/volumes/results"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
SCAN_DIR_NAME="${SCAN_NAME// /_}_${TIMESTAMP}_${SCAN_ID:0:8}"
SCAN_DIR="$RESULTS_PATH/$SCAN_DIR_NAME"

mkdir -p "$SCAN_DIR"/{logs,outputs,reports,metadata,archives}

# Create scan metadata
cat > "$SCAN_DIR/metadata/scan-metadata.json" << METADATA_EOF
{
    "scan_id": "$SCAN_ID",
    "scan_name": "$SCAN_NAME",
    "timestamp": "$TIMESTAMP",
    "scan_directory": "$SCAN_DIR",
    "created_at": "$(date -Iseconds)"
}
METADATA_EOF

echo "Results directory created: $SCAN_DIR"
EOF

    chmod +x "$DATA_PATH/config/results/organize_results.sh"
    
    log "Results management setup completed"
}

# Setup configuration management
setup_config() {
    log "Setting up configuration management..."
    
    # Create configuration templates
    mkdir -p "$DATA_PATH/config/scanners"
    mkdir -p "$DATA_PATH/config/policies"
    mkdir -p "$DATA_PATH/config/templates"
    mkdir -p "$DATA_PATH/config/environments"
    
    # Scanner configuration template
    cat > "$DATA_PATH/config/scanners/template.json" << 'EOF'
{
    "name": "Scanner Template",
    "description": "Template for scanner configurations",
    "enabled": true,
    "timeout": 300,
    "config_file": "scanner-config.yaml",
    "severity_threshold": "medium",
    "output_formats": ["json", "txt"],
    "config": {
        "exclude_dirs": ["tests", "venv", ".git"],
        "exclude_files": ["*.pyc", "__pycache__"],
        "tests": [],
        "skips": []
    }
}
EOF

    # Security policy template
    cat > "$DATA_PATH/config/policies/template.json" << 'EOF'
{
    "name": "Template Policy",
    "description": "Template for security policies",
    "version": "1.0",
    "rules": {
        "max_critical_vulnerabilities": 0,
        "max_high_vulnerabilities": 5,
        "max_medium_vulnerabilities": 20,
        "max_low_vulnerabilities": 100,
        "fail_on_critical": true,
        "fail_on_high": false,
        "fail_on_medium": false,
        "scan_timeout": 3600,
        "max_concurrent_scanners": 5,
        "severity_threshold": "medium"
    },
    "scanners": {
        "template": {
            "enabled": true,
            "severity_threshold": "medium"
        }
    }
}
EOF

    # Environment configuration template
    cat > "$DATA_PATH/config/environments/template.json" << 'EOF'
{
    "name": "Template Environment",
    "description": "Template for environment configurations",
    "version": "1.0",
    "config": {
        "debug": false,
        "log_level": "INFO",
        "scan_timeout": 3600,
        "max_concurrent_scanners": 5,
        "policy": "template",
        "template": "template",
        "redis_url": "redis://localhost:6379/0",
        "queue_timeout": 600,
        "result_retention_days": 30
    }
}
EOF

    log "Configuration management setup completed"
}

# Setup backup and restore
setup_backup_restore() {
    log "Setting up backup and restore procedures..."
    
    # Create backup script
    cat > "$DATA_PATH/config/scripts/backup_all.sh" << 'EOF'
#!/bin/bash
# SimpleSecCheck Complete Backup Script

set -e

DATA_PATH="/data"
BACKUP_PATH="/data/backups"
DATE=$(date +"%Y%m%d_%H%M%S")
BACKUP_NAME="full_backup_$DATE"
BACKUP_DIR="$BACKUP_PATH/$BACKUP_NAME"

mkdir -p "$BACKUP_DIR"

echo "Creating full backup: $BACKUP_NAME"

# Backup volumes
if [ -d "$DATA_PATH/volumes" ]; then
    tar -czf "$BACKUP_DIR/volumes.tar.gz" -C "$DATA_PATH" volumes/
    echo "Volumes backed up"
fi

# Backup configurations
if [ -d "$DATA_PATH/config" ]; then
    tar -czf "$BACKUP_DIR/config.tar.gz" -C "$DATA_PATH" config/
    echo "Configurations backed up"
fi

# Create backup metadata
cat > "$BACKUP_DIR/metadata.json" << METADATA_EOF
{
    "backup_name": "$BACKUP_NAME",
    "timestamp": "$(date -Iseconds)",
    "backup_type": "full",
    "components": ["volumes", "configurations"],
    "source_path": "$DATA_PATH"
}
METADATA_EOF

echo "Full backup completed: $BACKUP_DIR"

# Cleanup old backups (keep last 5)
cd "$BACKUP_PATH"
ls -t | grep "^full_backup_" | tail -n +6 | xargs -r rm -rf
echo "Old backups cleaned up"
EOF

    # Create restore script
    cat > "$DATA_PATH/config/scripts/restore_all.sh" << 'EOF'
#!/bin/bash
# SimpleSecCheck Complete Restore Script

set -e

BACKUP_PATH="$1"

if [ -z "$BACKUP_PATH" ]; then
    echo "Usage: $0 <backup_path>"
    exit 1
fi

if [ ! -d "$BACKUP_PATH" ]; then
    echo "Backup directory not found: $BACKUP_PATH"
    exit 1
fi

DATA_PATH="/data"

echo "Restoring from: $BACKUP_PATH"

# Create backup of current data
if [ -d "$DATA_PATH" ]; then
    CURRENT_BACKUP="$DATA_PATH.backup.$(date +%Y%m%d_%H%M%S)"
    mv "$DATA_PATH" "$CURRENT_BACKUP"
    echo "Current data backed up to: $CURRENT_BACKUP"
fi

# Restore volumes
if [ -f "$BACKUP_PATH/volumes.tar.gz" ]; then
    tar -xzf "$BACKUP_PATH/volumes.tar.gz" -C "$DATA_PATH"
    echo "Volumes restored"
fi

# Restore configurations
if [ -f "$BACKUP_PATH/config.tar.gz" ]; then
    tar -xzf "$BACKUP_PATH/config.tar.gz" -C "$DATA_PATH"
    echo "Configurations restored"
fi

echo "Restore completed successfully"
EOF

    chmod +x "$DATA_PATH/config/scripts/backup_all.sh"
    chmod +x "$DATA_PATH/config/scripts/restore_all.sh"
    
    log "Backup and restore setup completed"
}

# Setup monitoring
setup_monitoring() {
    log "Setting up monitoring scripts..."
    
    # Create health check script
    cat > "$DATA_PATH/config/scripts/health_check.sh" << 'EOF'
#!/bin/bash
# SimpleSecCheck Health Check Script

set -e

DATA_PATH="/data"
STATUS_FILE="/tmp/simpleseccheck_health.json"

echo "Running health checks..."

# Check volumes
VOLUMES_STATUS="ok"
for volume in backend worker redis database results config; do
    if [ ! -d "$DATA_PATH/volumes/$volume" ]; then
        VOLUMES_STATUS="error"
        echo "ERROR: Volume $volume not found"
    fi
done

# Check configurations
CONFIG_STATUS="ok"
for config_type in scanners policies templates environments; do
    if [ ! -d "$DATA_PATH/config/$config_type" ]; then
        CONFIG_STATUS="error"
        echo "ERROR: Config directory $config_type not found"
    fi
done

# Check Redis (if running)
REDIS_STATUS="unknown"
if command -v redis-cli &> /dev/null; then
    if redis-cli ping &> /dev/null; then
        REDIS_STATUS="ok"
    else
        REDIS_STATUS="error"
        echo "ERROR: Redis not responding"
    fi
fi

# Create status report
cat > "$STATUS_FILE" << STATUS_EOF
{
    "timestamp": "$(date -Iseconds)",
    "volumes": "$VOLUMES_STATUS",
    "configurations": "$CONFIG_STATUS",
    "redis": "$REDIS_STATUS",
    "overall_status": "$([ "$VOLUMES_STATUS" = "ok" ] && [ "$CONFIG_STATUS" = "ok" ] && [ "$REDIS_STATUS" != "error" ] && echo "healthy" || echo "unhealthy")"
}
STATUS_EOF

echo "Health check completed. Status saved to: $STATUS_FILE"

# Print summary
echo "=== Health Check Summary ==="
echo "Volumes: $VOLUMES_STATUS"
echo "Configurations: $CONFIG_STATUS"
echo "Redis: $REDIS_STATUS"
echo "Overall: $(cat $STATUS_FILE | grep overall_status | cut -d'"' -f4)"
EOF

    chmod +x "$DATA_PATH/config/scripts/health_check.sh"
    
    log "Monitoring setup completed"
}

# Create systemd services (optional)
create_systemd_services() {
    if [ "$EUID" -eq 0 ]; then
        log "Creating systemd services..."
        
        # Redis backup service
        cat > /etc/systemd/system/simpleseccheck-redis-backup.service << 'EOF'
[Unit]
Description=SimpleSecCheck Redis Backup
After=redis.service

[Service]
Type=oneshot
ExecStart=/data/config/redis/redis_backup.sh
User=redis
Group=redis

[Install]
WantedBy=multi-user.target
EOF

        # Redis backup timer
        cat > /etc/systemd/system/simpleseccheck-redis-backup.timer << 'EOF'
[Unit]
Description=Run SimpleSecCheck Redis Backup Daily
Requires=simpleseccheck-redis-backup.service

[Timer]
OnCalendar=daily
Persistent=true

[Install]
WantedBy=timers.target
EOF

        systemctl daemon-reload
        systemctl enable simpleseccheck-redis-backup.timer
        systemctl start simpleseccheck-redis-backup.timer
        
        log "Systemd services created and enabled"
    else
        warn "Skipping systemd service creation (requires root)"
    fi
}

# Main setup function
main() {
    log "Starting SimpleSecCheck Volume Setup..."
    
    check_permissions
    install_dependencies
    setup_directories
    setup_redis
    setup_results
    setup_config
    setup_backup_restore
    setup_monitoring
    
    if [ "$EUID" -eq 0 ]; then
        create_systemd_services
    fi
    
    log "Volume setup completed successfully!"
    log "You can now run the following commands:"
    echo "  - Health check: $DATA_PATH/config/scripts/health_check.sh"
    echo "  - Full backup: $DATA_PATH/config/scripts/backup_all.sh"
    echo "  - Redis backup: $DATA_PATH/config/redis/redis_backup.sh"
}

# Run main function
main "$@"