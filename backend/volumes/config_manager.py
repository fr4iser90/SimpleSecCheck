"""
Configuration Volume Management

This module manages the shared configuration volume for all services.
Includes scanner configurations, security policies, templates, and
environment-specific settings.
"""
import os
import json
import yaml
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
import logging

from config.settings import settings


logger = logging.getLogger("config_manager")


class ConfigManager:
    """
    Manages shared configuration files for all services.
    
    This class handles:
    - Scanner configuration management
    - Security policy management
    - Template management
    - Environment-specific configurations
    - Configuration validation and backup
    """
    
    def __init__(self, base_path: str = "/data"):
        """
        Initialize configuration manager.
        
        Args:
            base_path: Base data path for configuration
        """
        self.base_path = Path(base_path)
        self.config_path = self.base_path / "config"
        
        # Configuration structure
        self.config_structure = {
            "scanners": {
                "path": self.config_path / "scanners",
                "description": "Scanner-specific configurations",
                "backup_enabled": True,
            },
            "policies": {
                "path": self.config_path / "policies",
                "description": "Security policies and rules",
                "backup_enabled": True,
            },
            "templates": {
                "path": self.config_path / "templates",
                "description": "Scan templates and presets",
                "backup_enabled": True,
            },
            "environments": {
                "path": self.config_path / "environments",
                "description": "Environment-specific configurations",
                "backup_enabled": True,
            },
            "secrets": {
                "path": self.config_path / "secrets",
                "description": "Encrypted secrets and credentials",
                "backup_enabled": True,
                "strict_permissions": True,
            },
            "overrides": {
                "path": self.config_path / "overrides",
                "description": "Configuration overrides",
                "backup_enabled": True,
            },
        }
    
    def setup_config_directories(self) -> bool:
        """
        Set up configuration directory structure.
        
        Returns:
            True if setup successful, False otherwise
        """
        try:
            # Create base configuration directory
            self.config_path.mkdir(parents=True, exist_ok=True)
            os.chmod(self.config_path, 0o755)
            
            # Create subdirectories
            for config_type, config_info in self.config_structure.items():
                config_dir = config_info["path"]
                config_dir.mkdir(parents=True, exist_ok=True)
                
                # Set permissions based on configuration type
                if config_info.get("strict_permissions", False):
                    os.chmod(config_dir, 0o700)  # Strict permissions for secrets
                else:
                    os.chmod(config_dir, 0o755)
                
                logger.info(f"Created config directory: {config_type} at {config_dir}")
            
            # Create initial configuration files
            self._create_initial_configurations()
            
            logger.info("Configuration directories created successfully")
            return True
            
        except Exception as e:
            logger.error(f"Configuration directory setup failed: {e}")
            return False
    
    def _create_initial_configurations(self):
        """Create initial configuration files."""
        # Scanner configurations
        self._create_scanner_configs()
        
        # Security policies
        self._create_security_policies()
        
        # Templates
        self._create_templates()
        
        # Environment configurations
        self._create_environment_configs()
        
        # Configuration index
        self._create_config_index()
    
    def _create_scanner_configs(self):
        """Create default scanner configurations template."""
        # Create a template configuration that can be used for any scanner
        # Scanner-specific configurations will be discovered and created dynamically
        template_config = {
            "name": "Scanner Template",
            "description": "Template for scanner configurations",
            "enabled": True,
            "timeout": 300,
            "config_file": "scanner-config.yaml",
            "severity_threshold": "medium",
            "output_formats": ["json", "txt"],
            "config": {
                "exclude_dirs": ["tests", "venv", ".git"],
                "exclude_files": ["*.pyc", "__pycache__"],
                "tests": [],
                "skips": [],
            }
        }
        
        # Save template configuration
        scanners_dir = self.config_structure["scanners"]["path"]
        template_file = scanners_dir / "template.json"
        with open(template_file, "w") as f:
            json.dump(template_config, f, indent=2)
        
        logger.info("Scanner configuration template created")
    
    def _create_security_policies(self):
        """Create default security policies template."""
        # Create a template policy that can be used for any scanner configuration
        # Scanner-specific policies will be discovered and created dynamically
        template_policy = {
            "name": "Template Policy",
            "description": "Template for security policies",
            "version": "1.0",
            "rules": {
                "max_critical_vulnerabilities": 0,
                "max_high_vulnerabilities": 5,
                "max_medium_vulnerabilities": 20,
                "max_low_vulnerabilities": 100,
                "fail_on_critical": True,
                "fail_on_high": False,
                "fail_on_medium": False,
                "scan_timeout": 3600,
                "max_concurrent_scanners": 5,
                "severity_threshold": "medium",
            },
            "scanners": {
                "template": {"enabled": True, "severity_threshold": "medium"}
            }
        }
        
        # Save template policy
        policies_dir = self.config_structure["policies"]["path"]
        template_file = policies_dir / "template.json"
        with open(template_file, "w") as f:
            json.dump(template_policy, f, indent=2)
        
        logger.info("Security policy template created")
    
    def _create_templates(self):
        """Create default scan templates template."""
        # Create a template template that can be used for any scan configuration
        # Scanner-specific templates will be discovered and created dynamically
        template_template = {
            "name": "Template Template",
            "description": "Template for scan templates",
            "version": "1.0",
            "config": {
                "scan_mode": "template",
                "scan_depth": "medium",
                "timeout": 3600,
                "max_concurrent_scanners": 5,
                "enabled_scanners": ["template"],
                "severity_threshold": "medium",
                "output_formats": ["json", "txt"],
            }
        }
        
        # Save template template
        templates_dir = self.config_structure["templates"]["path"]
        template_file = templates_dir / "template.json"
        with open(template_file, "w") as f:
            json.dump(template_template, f, indent=2)
        
        logger.info("Scan template template created")
    
    def _create_environment_configs(self):
        """Create environment-specific configurations template."""
        # Create a template environment configuration that can be used for any environment
        # Environment-specific configurations will be discovered and created dynamically
        template_env = {
            "name": "Template Environment",
            "description": "Template for environment configurations",
            "version": "1.0",
            "config": {
                "debug": False,
                "log_level": "INFO",
                "scan_timeout": 3600,
                "max_concurrent_scanners": 5,
                "policy": "template",
                "template": "template",
                "redis_url": "redis://localhost:6379/0",
                "queue_timeout": 600,
                "result_retention_days": 30,
            }
        }
        
        # Save template environment
        env_dir = self.config_structure["environments"]["path"]
        template_file = env_dir / "template.json"
        with open(template_file, "w") as f:
            json.dump(template_env, f, indent=2)
        
        logger.info("Environment configuration template created")
    
    def _create_config_index(self):
        """Create configuration index file."""
        config_index = {
            "version": "1.0",
            "created_at": "2024-01-01T00:00:00Z",
            "configurations": {
                "scanners": {
                    "count": 1,
                    "enabled": ["template"],
                },
                "policies": {
                    "count": 1,
                    "available": ["template"],
                },
                "templates": {
                    "count": 1,
                    "available": ["template"],
                },
                "environments": {
                    "count": 1,
                    "available": ["template"],
                },
            },
            "metadata": {
                "last_updated": "2024-01-01T00:00:00Z",
                "version": "1.0",
                "description": "SimpleSecCheck Configuration Index",
            }
        }
        
        index_file = self.config_path / "config_index.json"
        with open(index_file, "w") as f:
            json.dump(config_index, f, indent=2)
        
        logger.info("Configuration index created")
    
    def get_scanner_config(self, scanner_name: str) -> Optional[Dict[str, Any]]:
        """
        Get configuration for a specific scanner.
        
        Args:
            scanner_name: Name of the scanner
            
        Returns:
            Scanner configuration or None if not found
        """
        try:
            config_file = self.config_structure["scanners"]["path"] / f"{scanner_name}.json"
            if config_file.exists():
                with open(config_file, "r") as f:
                    return json.load(f)
            return None
        except Exception as e:
            logger.error(f"Failed to get scanner config for {scanner_name}: {e}")
            return None
    
    def get_policy_config(self, policy_name: str) -> Optional[Dict[str, Any]]:
        """
        Get configuration for a specific policy.
        
        Args:
            policy_name: Name of the policy
            
        Returns:
            Policy configuration or None if not found
        """
        try:
            config_file = self.config_structure["policies"]["path"] / f"{policy_name}.json"
            if config_file.exists():
                with open(config_file, "r") as f:
                    return json.load(f)
            return None
        except Exception as e:
            logger.error(f"Failed to get policy config for {policy_name}: {e}")
            return None
    
    def get_template_config(self, template_name: str) -> Optional[Dict[str, Any]]:
        """
        Get configuration for a specific template.
        
        Args:
            template_name: Name of the template
            
        Returns:
            Template configuration or None if not found
        """
        try:
            config_file = self.config_structure["templates"]["path"] / f"{template_name}.json"
            if config_file.exists():
                with open(config_file, "r") as f:
                    return json.load(f)
            return None
        except Exception as e:
            logger.error(f"Failed to get template config for {template_name}: {e}")
            return None
    
    def get_environment_config(self, env_name: str) -> Optional[Dict[str, Any]]:
        """
        Get configuration for a specific environment.
        
        Args:
            env_name: Name of the environment
            
        Returns:
            Environment configuration or None if not found
        """
        try:
            config_file = self.config_structure["environments"]["path"] / f"{env_name}.json"
            if config_file.exists():
                with open(config_file, "r") as f:
                    return json.load(f)
            return None
        except Exception as e:
            logger.error(f"Failed to get environment config for {env_name}: {e}")
            return None
    
    def update_scanner_config(self, scanner_name: str, config: Dict[str, Any]) -> bool:
        """
        Update configuration for a specific scanner.
        
        Args:
            scanner_name: Name of the scanner
            config: New configuration
            
        Returns:
            True if update successful, False otherwise
        """
        try:
            config_file = self.config_structure["scanners"]["path"] / f"{scanner_name}.json"
            with open(config_file, "w") as f:
                json.dump(config, f, indent=2)
            logger.info(f"Updated scanner config: {scanner_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to update scanner config for {scanner_name}: {e}")
            return False
    
    def backup_configurations(self, backup_path: Optional[str] = None) -> bool:
        """
        Backup all configuration files.
        
        Args:
            backup_path: Optional backup path (uses default if not specified)
            
        Returns:
            True if backup successful, False otherwise
        """
        try:
            if not backup_path:
                backup_path = self.base_path / "backups" / "config"
            else:
                backup_path = Path(backup_path)
            
            backup_path.mkdir(parents=True, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"config_backup_{timestamp}"
            backup_dir = backup_path / backup_name
            
            # Copy configuration directory
            if self.config_path.exists():
                shutil.copytree(self.config_path, backup_dir, dirs_exist_ok=True)
            
            # Create backup metadata
            backup_metadata = {
                "backup_name": backup_name,
                "backup_path": str(backup_dir),
                "timestamp": datetime.now().isoformat(),
                "source_path": str(self.config_path),
                "backup_type": "full",
                "config_types": list(self.config_structure.keys()),
            }
            
            with open(backup_dir / "backup_metadata.json", "w") as f:
                json.dump(backup_metadata, f, indent=2)
            
            logger.info(f"Configuration backup created: {backup_dir}")
            return True
            
        except Exception as e:
            logger.error(f"Configuration backup failed: {e}")
            return False
    
    def restore_configurations(self, backup_path: str) -> bool:
        """
        Restore configurations from backup.
        
        Args:
            backup_path: Path to backup directory
            
        Returns:
            True if restore successful, False otherwise
        """
        try:
            backup_dir = Path(backup_path)
            if not backup_dir.exists():
                logger.error(f"Backup directory not found: {backup_path}")
                return False
            
            # Create backup of current configurations
            if self.config_path.exists():
                backup_current = self.config_path.with_suffix(f".backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
                shutil.move(self.config_path, backup_current)
                logger.info(f"Current configurations backed up to: {backup_current}")
            
            # Restore from backup
            shutil.copytree(backup_dir, self.config_path, dirs_exist_ok=True)
            
            logger.info(f"Configurations restored from: {backup_path}")
            return True
            
        except Exception as e:
            logger.error(f"Configuration restore failed: {e}")
            return False
    
    def validate_configurations(self) -> Dict[str, List[str]]:
        """
        Validate all configuration files.
        
        Returns:
            Dictionary of validation results
        """
        validation_results = {
            "valid": [],
            "invalid": [],
            "errors": [],
        }
        
        try:
            for config_type, config_info in self.config_structure.items():
                config_dir = config_info["path"]
                if not config_dir.exists():
                    validation_results["errors"].append(f"Missing directory: {config_type}")
                    continue
                
                for config_file in config_dir.glob("*.json"):
                    try:
                        with open(config_file, "r") as f:
                            json.load(f)
                        validation_results["valid"].append(f"{config_type}/{config_file.name}")
                    except json.JSONDecodeError as e:
                        validation_results["invalid"].append(f"{config_type}/{config_file.name}")
                        validation_results["errors"].append(f"JSON error in {config_file}: {e}")
                    except Exception as e:
                        validation_results["errors"].append(f"Error reading {config_file}: {e}")
            
            logger.info(f"Configuration validation completed: {len(validation_results['valid'])} valid, {len(validation_results['invalid'])} invalid")
            return validation_results
            
        except Exception as e:
            logger.error(f"Configuration validation failed: {e}")
            return {"valid": [], "invalid": [], "errors": [str(e)]}
    
    def get_config_status(self) -> Dict[str, Any]:
        """
        Get status information about all configurations.
        
        Returns:
            Dictionary with configuration status information
        """
        try:
            status = {
                "config_directory": str(self.config_path),
                "config_directory_exists": self.config_path.exists(),
                "config_types": {},
                "total_files": 0,
                "validation_results": self.validate_configurations(),
            }
            
            if self.config_path.exists():
                for config_type, config_info in self.config_structure.items():
                    config_dir = config_info["path"]
                    if config_dir.exists():
                        files = list(config_dir.glob("*.json"))
                        status["config_types"][config_type] = {
                            "path": str(config_dir),
                            "file_count": len(files),
                            "files": [f.name for f in files],
                            "description": config_info["description"],
                        }
                        status["total_files"] += len(files)
            
            return status
            
        except Exception as e:
            logger.error(f"Failed to get configuration status: {e}")
            return {"error": str(e)}


# Global configuration manager instance
config_manager = ConfigManager(settings.data_path)