"""
Redis Configuration and Persistence Setup

This module configures Redis for optimal persistence and performance
in the SimpleSecCheck environment. Includes AOF and RDB configuration.
"""
import os
import json
from pathlib import Path
from typing import Dict, Any
import logging

from config.settings import settings


logger = logging.getLogger("redis_config")


class RedisConfigManager:
    """
    Manages Redis configuration for persistence and performance.
    
    This class handles:
    - Redis AOF (Append Only File) configuration
    - Redis RDB (Redis Database) configuration
    - Performance tuning for scan operations
    - Backup and recovery configuration
    """
    
    def __init__(self, data_path: str = "/data"):
        """
        Initialize Redis configuration manager.
        
        Args:
            data_path: Base data path for Redis files
        """
        self.data_path = Path(data_path)
        self.redis_data_path = self.data_path / "volumes" / "redis"
        self.config_path = self.data_path / "config" / "redis"
        
        # Redis configuration template
        self.redis_config = {
            # Persistence Configuration
            "appendonly": "yes",
            "appendfsync": "everysec",  # Balance between performance and durability
            "no-appendfsync-on-rewrite": "no",
            "auto-aof-rewrite-percentage": 100,
            "auto-aof-rewrite-min-size": "64mb",
            "aof-load-truncated": "yes",
            "aof-use-rdb-preamble": "yes",
            
            # RDB Configuration
            "save": "900 1\n300 10\n60 10000",  # Save conditions
            "stop-writes-on-bgsave-error": "yes",
            "rdbcompression": "yes",
            "rdbchecksum": "yes",
            
            # Memory and Performance
            "maxmemory": "2gb",
            "maxmemory-policy": "allkeys-lru",
            "tcp-keepalive": 300,
            "timeout": 0,
            
            # Security
            "requirepass": "",  # Will be set from environment
            "rename-command": "FLUSHDB \"\"",
            "rename-command": "FLUSHALL \"\"",
            "rename-command": "DEBUG \"\"",
            "rename-command": "CONFIG \"\"",
            
            # Logging
            "loglevel": "notice",
            "logfile": "/var/log/redis/redis-server.log",
            
            # Network
            "bind": "0.0.0.0",
            "port": 6379,
            "protected-mode": "yes",
            
            # Client Configuration
            "maxclients": 10000,
            "client-output-buffer-limit": "normal 0 0 0 slave 256mb 64mb 60 pubsub 32mb 8mb 60",
            
            # Slow Log
            "slowlog-log-slower-than": 10000,  # Log queries slower than 10ms
            "slowlog-max-len": 128,
        }
    
    def setup_redis_directories(self) -> bool:
        """
        Set up Redis directories with proper permissions.
        
        Returns:
            True if setup successful, False otherwise
        """
        try:
            # Create directories
            self.redis_data_path.mkdir(parents=True, exist_ok=True)
            self.config_path.mkdir(parents=True, exist_ok=True)
            
            # Set proper permissions
            os.chmod(self.redis_data_path, 0o700)  # Strict permissions for data
            os.chmod(self.config_path, 0o755)
            
            # Create log directory
            log_dir = Path("/var/log/redis")
            log_dir.mkdir(parents=True, exist_ok=True)
            os.chmod(log_dir, 0o755)
            
            logger.info("Redis directories created successfully")
            return True
            
        except Exception as e:
            logger.error(f"Redis directory setup failed: {e}")
            return False
    
    def generate_redis_config(self, output_file: Optional[str] = None) -> str:
        """
        Generate Redis configuration file.
        
        Args:
            output_file: Optional output file path
            
        Returns:
            Generated configuration content
        """
        config_content = []
        
        # Add header
        config_content.append("# SimpleSecCheck Redis Configuration")
        config_content.append(f"# Generated on {__import__('datetime').datetime.now().isoformat()}")
        config_content.append("")
        
        # Add persistence configuration
        config_content.append("# Persistence Configuration")
        config_content.append("appendonly yes")
        config_content.append("appendfsync everysec")
        config_content.append("no-appendfsync-on-rewrite no")
        config_content.append("auto-aof-rewrite-percentage 100")
        config_content.append("auto-aof-rewrite-min-size 64mb")
        config_content.append("aof-load-truncated yes")
        config_content.append("aof-use-rdb-preamble yes")
        config_content.append("")
        
        # Add RDB configuration
        config_content.append("# RDB Configuration")
        config_content.append("save 900 1")
        config_content.append("save 300 10")
        config_content.append("save 60 10000")
        config_content.append("stop-writes-on-bgsave-error yes")
        config_content.append("rdbcompression yes")
        config_content.append("rdbchecksum yes")
        config_content.append("")
        
        # Add memory and performance
        config_content.append("# Memory and Performance")
        config_content.append("maxmemory 2gb")
        config_content.append("maxmemory-policy allkeys-lru")
        config_content.append("tcp-keepalive 300")
        config_content.append("timeout 0")
        config_content.append("")
        
        # Add security (password from environment)
        config_content.append("# Security")
        config_content.append("requirepass ${REDIS_PASSWORD:-defaultpassword}")
        config_content.append("rename-command FLUSHDB \"\"")
        config_content.append("rename-command FLUSHALL \"\"")
        config_content.append("rename-command DEBUG \"\"")
        config_content.append("rename-command CONFIG \"\"")
        config_content.append("")
        
        # Add logging
        config_content.append("# Logging")
        config_content.append("loglevel notice")
        config_content.append("logfile /var/log/redis/redis-server.log")
        config_content.append("")
        
        # Add network configuration
        config_content.append("# Network")
        config_content.append("bind 0.0.0.0")
        config_content.append("port 6379")
        config_content.append("protected-mode yes")
        config_content.append("")
        
        # Add client configuration
        config_content.append("# Client Configuration")
        config_content.append("maxclients 10000")
        config_content.append("client-output-buffer-limit normal 0 0 0")
        config_content.append("client-output-buffer-limit replica 256mb 64mb 60")
        config_content.append("client-output-buffer-limit pubsub 32mb 8mb 60")
        config_content.append("")
        
        # Add slow log
        config_content.append("# Slow Log")
        config_content.append("slowlog-log-slower-than 10000")
        config_content.append("slowlog-max-len 128")
        config_content.append("")
        
        # Add custom SimpleSecCheck settings
        config_content.append("# SimpleSecCheck Custom Settings")
        config_content.append("# Queue database (database 0)")
        config_content.append("# Session database (database 1)")
        config_content.append("# Cache database (database 2)")
        config_content.append("# Job database (database 3)")
        config_content.append("")
        
        config_content = "\n".join(config_content)
        
        # Write to file if specified
        if output_file:
            with open(output_file, "w") as f:
                f.write(config_content)
            logger.info(f"Redis configuration written to: {output_file}")
        
        return config_content
    
    def create_redis_backup_script(self) -> str:
        """
        Create Redis backup script for automated backups.
        
        Returns:
            Backup script content
        """
        backup_script = f"""#!/bin/bash
# SimpleSecCheck Redis Backup Script
# This script creates backups of Redis data

set -e

# Configuration
REDIS_DATA_DIR="{self.redis_data_path}"
BACKUP_DIR="{self.data_path}/backups/redis"
DATE=$(date +"%Y%m%d_%H%M%S")
BACKUP_NAME="redis_backup_$DATE"
BACKUP_PATH="$BACKUP_DIR/$BACKUP_NAME"

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Create backup
echo "Creating Redis backup: $BACKUP_NAME"

# Use redis-cli to create backup
redis-cli BGSAVE
sleep 2

# Wait for background save to complete
while [ $(redis-cli LASTSAVE) -eq $(redis-cli LASTSAVE) ]; do
    sleep 1
    echo "Waiting for Redis background save to complete..."
done

# Copy RDB file
if [ -f "$REDIS_DATA_DIR/dump.rdb" ]; then
    mkdir -p "$BACKUP_PATH"
    cp "$REDIS_DATA_DIR/dump.rdb" "$BACKUP_PATH/"
    echo "RDB file copied to $BACKUP_PATH"
fi

# Copy AOF file if exists
if [ -f "$REDIS_DATA_DIR/appendonly.aof" ]; then
    cp "$REDIS_DATA_DIR/appendonly.aof" "$BACKUP_PATH/"
    echo "AOF file copied to $BACKUP_PATH"
fi

# Create metadata
cat > "$BACKUP_PATH/metadata.json" << EOF
{{
    "backup_name": "$BACKUP_NAME",
    "timestamp": "$(date -Iseconds)",
    "redis_version": "$(redis-cli INFO server | grep redis_version | cut -d: -f2 | tr -d '\r')",
    "rdb_file": "dump.rdb",
    "aof_file": "appendonly.aof",
    "backup_type": "full"
}}
EOF

echo "Redis backup completed: $BACKUP_PATH"

# Cleanup old backups (keep last 10)
cd "$BACKUP_DIR"
ls -t | tail -n +11 | xargs -r rm -rf

echo "Old backups cleaned up"
"""
        
        backup_script_path = self.config_path / "redis_backup.sh"
        with open(backup_script_path, "w") as f:
            f.write(backup_script)
        
        # Make script executable
        os.chmod(backup_script_path, 0o755)
        
        logger.info(f"Redis backup script created: {backup_script_path}")
        return backup_script
    
    def create_redis_restore_script(self) -> str:
        """
        Create Redis restore script for automated restoration.
        
        Returns:
            Restore script content
        """
        restore_script = f"""#!/bin/bash
# SimpleSecCheck Redis Restore Script
# This script restores Redis data from backup

set -e

# Configuration
REDIS_DATA_DIR="{self.redis_data_path}"
BACKUP_DIR="{self.data_path}/backups/redis"
BACKUP_NAME="$1"

if [ -z "$BACKUP_NAME" ]; then
    echo "Usage: $0 <backup_name>"
    echo "Available backups:"
    ls -la "$BACKUP_DIR"
    exit 1
fi

BACKUP_PATH="$BACKUP_DIR/$BACKUP_NAME"

if [ ! -d "$BACKUP_PATH" ]; then
    echo "Backup not found: $BACKUP_PATH"
    exit 1
fi

echo "Restoring Redis from backup: $BACKUP_NAME"

# Stop Redis (orchestrator manages lifecycle in deploy)
echo "Stopping Redis service..."
# systemctl stop redis || true

# Backup current data
if [ -f "$REDIS_DATA_DIR/dump.rdb" ]; then
    CURRENT_BACKUP="$REDIS_DATA_DIR/dump.rdb.backup.$(date +%Y%m%d_%H%M%S)"
    cp "$REDIS_DATA_DIR/dump.rdb" "$CURRENT_BACKUP"
    echo "Current data backed up to: $CURRENT_BACKUP"
fi

# Restore RDB file
if [ -f "$BACKUP_PATH/dump.rdb" ]; then
    cp "$BACKUP_PATH/dump.rdb" "$REDIS_DATA_DIR/"
    echo "RDB file restored"
fi

# Restore AOF file
if [ -f "$BACKUP_PATH/appendonly.aof" ]; then
    cp "$BACKUP_PATH/appendonly.aof" "$REDIS_DATA_DIR/"
    echo "AOF file restored"
fi

# Set proper permissions
chown -R redis:redis "$REDIS_DATA_DIR" 2>/dev/null || true
chmod 644 "$REDIS_DATA_DIR/dump.rdb" 2>/dev/null || true
chmod 644 "$REDIS_DATA_DIR/appendonly.aof" 2>/dev/null || true

echo "Redis data restored from: $BACKUP_PATH"

# Start Redis (orchestrator manages lifecycle in deploy)
echo "Starting Redis service..."
# systemctl start redis || true

echo "Redis restore completed"
"""
        
        restore_script_path = self.config_path / "redis_restore.sh"
        with open(restore_script_path, "w") as f:
            f.write(restore_script)
        
        # Make script executable
        os.chmod(restore_script_path, 0o755)
        
        logger.info(f"Redis restore script created: {restore_script_path}")
        return restore_script
    
    def create_redis_monitoring_script(self) -> str:
        """
        Create Redis monitoring script for health checks.
        
        Returns:
            Monitoring script content
        """
        monitoring_script = f"""#!/bin/bash
# SimpleSecCheck Redis Monitoring Script
# This script monitors Redis health and performance

set -e

# Configuration
REDIS_HOST="localhost"
REDIS_PORT="6379"
REDIS_PASSWORD="${{REDIS_PASSWORD:-}}"

# Function to check Redis connectivity
check_redis_connectivity() {{
    if [ -n "$REDIS_PASSWORD" ]; then
        redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" -a "$REDIS_PASSWORD" ping > /dev/null 2>&1
    else
        redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" ping > /dev/null 2>&1
    fi
}}

# Function to get Redis info
get_redis_info() {{
    if [ -n "$REDIS_PASSWORD" ]; then
        redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" -a "$REDIS_PASSWORD" INFO
    else
        redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" INFO
    fi
}}

# Function to check memory usage
check_memory_usage() {{
    local info=$(get_redis_info)
    local used_memory=$(echo "$info" | grep "used_memory:" | cut -d: -f2 | tr -d '\r')
    local max_memory=$(echo "$info" | grep "maxmemory:" | cut -d: -f2 | tr -d '\r')
    
    if [ "$max_memory" -gt 0 ]; then
        local usage_percent=$((used_memory * 100 / max_memory))
        echo "Memory usage: $usage_percent%"
        
        if [ "$usage_percent" -gt 90 ]; then
            echo "WARNING: Redis memory usage is high ($usage_percent%)"
            return 1
        fi
    fi
}}

# Function to check persistence status
check_persistence() {{
    local info=$(get_redis_info)
    local aof_enabled=$(echo "$info" | grep "appendonly:" | cut -d: -f2 | tr -d '\r')
    local rdb_enabled=$(echo "$info" | grep "rdb_enabled:" | cut -d: -f2 | tr -d '\r')
    
    if [ "$aof_enabled" = "yes" ]; then
        echo "AOF persistence: Enabled"
    else
        echo "AOF persistence: Disabled"
    fi
    
    if [ "$rdb_enabled" = "1" ]; then
        echo "RDB persistence: Enabled"
    else
        echo "RDB persistence: Disabled"
    fi
}}

# Main monitoring
echo "=== Redis Health Check ==="
echo "Timestamp: $(date)"

if check_redis_connectivity; then
    echo "✓ Redis connectivity: OK"
else
    echo "✗ Redis connectivity: FAILED"
    exit 1
fi

echo ""
echo "=== Redis Info ==="
get_redis_info | grep -E "(redis_version|used_memory_human|maxmemory_human|connected_clients|keyspace_hits|keyspace_misses)"

echo ""
echo "=== Memory Check ==="
check_memory_usage

echo ""
echo "=== Persistence Check ==="
check_persistence

echo ""
echo "=== Queue Status ==="
if [ -n "$REDIS_PASSWORD" ]; then
    redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" -a "$REDIS_PASSWORD" LLEN scan_queue
    redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" -a "$REDIS_PASSWORD" LLEN result_queue
else
    redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" LLEN scan_queue
    redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" LLEN result_queue
fi

echo ""
echo "Redis monitoring completed successfully"
"""
        
        monitoring_script_path = self.config_path / "redis_monitor.sh"
        with open(monitoring_script_path, "w") as f:
            f.write(monitoring_script)
        
        # Make script executable
        os.chmod(monitoring_script_path, 0o755)
        
        logger.info(f"Redis monitoring script created: {monitoring_script_path}")
        return monitoring_script
    
    def setup_redis_cron_jobs(self) -> bool:
        """
        Set up cron jobs for Redis maintenance.
        
        Returns:
            True if setup successful, False otherwise
        """
        try:
            # Create cron job for backups (daily at 2 AM)
            backup_cron = f"0 2 * * * {self.config_path}/redis_backup.sh >> /var/log/redis/backup.log 2>&1"
            
            # Create cron job for monitoring (every 5 minutes)
            monitor_cron = f"*/5 * * * * {self.config_path}/redis_monitor.sh >> /var/log/redis/monitor.log 2>&1"
            
            # Write cron jobs to file
            cron_file = self.config_path / "redis_cron.txt"
            with open(cron_file, "w") as f:
                f.write("# SimpleSecCheck Redis Cron Jobs\n")
                f.write(f"{backup_cron}\n")
                f.write(f"{monitor_cron}\n")
            
            logger.info(f"Redis cron jobs configured in: {cron_file}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to setup Redis cron jobs: {e}")
            return False
    
    def get_redis_health_status(self) -> Dict[str, Any]:
        """
        Get Redis health and status information.
        
        Returns:
            Dictionary with Redis health information
        """
        try:
            import subprocess
            
            # Check if Redis is running
            try:
                result = subprocess.run(
                    ["redis-cli", "ping"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                is_running = result.returncode == 0 and result.stdout.strip() == "PONG"
            except:
                is_running = False
            
            status = {
                "redis_running": is_running,
                "data_directory": str(self.redis_data_path),
                "data_directory_exists": self.redis_data_path.exists(),
                "data_directory_size": self._get_directory_size(self.redis_data_path),
                "config_directory": str(self.config_path),
                "config_directory_exists": self.config_path.exists(),
                "backup_directory": str(self.data_path / "backups" / "redis"),
                "backup_directory_exists": (self.data_path / "backups" / "redis").exists(),
            }
            
            # Add file information if Redis is running
            if is_running:
                try:
                    info = subprocess.run(
                        ["redis-cli", "INFO"],
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    
                    if info.returncode == 0:
                        info_lines = info.stdout.split('\n')
                        redis_info = {}
                        
                        for line in info_lines:
                            if ':' in line and not line.startswith('#'):
                                key, value = line.split(':', 1)
                                redis_info[key] = value.strip()
                        
                        status.update({
                            "redis_version": redis_info.get("redis_version", "unknown"),
                            "used_memory_human": redis_info.get("used_memory_human", "unknown"),
                            "connected_clients": redis_info.get("connected_clients", "unknown"),
                            "keyspace_hits": redis_info.get("keyspace_hits", "unknown"),
                            "keyspace_misses": redis_info.get("keyspace_misses", "unknown"),
                            "aof_enabled": redis_info.get("appendonly", "unknown"),
                            "rdb_enabled": redis_info.get("rdb_enabled", "unknown"),
                        })
                except:
                    pass
            
            return status
            
        except Exception as e:
            logger.error(f"Failed to get Redis health status: {e}")
            return {"error": str(e)}
    
    def _get_directory_size(self, directory: Path) -> str:
        """Get directory size in human readable format."""
        try:
            import subprocess
            result = subprocess.run(
                ["du", "-sh", str(directory)],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                return result.stdout.split()[0]
            else:
                return "unknown"
        except:
            return "unknown"


# Global Redis configuration manager instance
redis_config_manager = RedisConfigManager(settings.data_path)