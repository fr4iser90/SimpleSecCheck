"""
Results Volume Management

This module manages the results volume for scan outputs, reports, and
metadata. Includes organization, compression, and retention policies.
"""
import os
import json
import shutil
import gzip
import tarfile
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import logging
from enum import Enum

from config.settings import settings


logger = logging.getLogger("results_manager")


class ResultType(Enum):
    """Types of scan results."""
    SCAN_OUTPUT = "scan_output"
    REPORT = "report"
    METADATA = "metadata"
    LOG = "log"
    ARCHIVE = "archive"


class ResultsManager:
    """
    Manages scan results storage and organization.
    
    This class handles:
    - Results directory structure
    - File organization by scan and type
    - Compression and archiving
    - Retention policies and cleanup
    - Results backup and restore
    """
    
    def __init__(self, base_path: str = "/data"):
        """
        Initialize results manager.
        
        Args:
            base_path: Base data path for results
        """
        self.base_path = Path(base_path)
        self.results_path = self.base_path / "volumes" / "results"
        self.tmp_path = self.base_path / "volumes" / "tmp"
        
        # Results organization structure
        self.result_types = {
            ResultType.SCAN_OUTPUT: ["json", "txt", "sarif"],
            ResultType.REPORT: ["html", "pdf", "md"],
            ResultType.METADATA: ["json"],
            ResultType.LOG: ["log"],
            ResultType.ARCHIVE: ["tar.gz", "zip"],
        }
    
    def setup_results_directories(self) -> bool:
        """
        Set up results directory structure.
        
        Returns:
            True if setup successful, False otherwise
        """
        try:
            # Create base directories
            self.results_path.mkdir(parents=True, exist_ok=True)
            self.tmp_path.mkdir(parents=True, exist_ok=True)
            
            # Set permissions
            os.chmod(self.results_path, 0o755)
            os.chmod(self.tmp_path, 0o755)
            
            logger.info("Results directories created successfully")
            return True
            
        except Exception as e:
            logger.error(f"Results directory setup failed: {e}")
            return False
    
    def organize_scan_results(self, scan_id: str, scan_name: str) -> Dict[str, Path]:
        """
        Create organized directory structure for a scan.
        
        Args:
            scan_id: Unique scan identifier
            scan_name: Human-readable scan name
            
        Returns:
            Dictionary of created directory paths
        """
        try:
            # Create scan directory with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            scan_dir_name = f"{scan_name.replace(' ', '_')}_{timestamp}_{scan_id[:8]}"
            scan_dir = self.results_path / scan_dir_name
            
            # Create subdirectories
            directories = {
                "logs": scan_dir / "logs",
                "outputs": scan_dir / "outputs",
                "reports": scan_dir / "reports",
                "metadata": scan_dir / "metadata",
                "archives": scan_dir / "archives",
            }
            
            for dir_name, dir_path in directories.items():
                dir_path.mkdir(parents=True, exist_ok=True)
                os.chmod(dir_path, 0o755)
            
            # Create scan metadata
            scan_metadata = {
                "scan_id": scan_id,
                "scan_name": scan_name,
                "timestamp": timestamp,
                "scan_directory": str(scan_dir),
                "directories": {k: str(v) for k, v in directories.items()},
                "created_at": datetime.now().isoformat(),
            }
            
            metadata_file = directories["metadata"] / "scan-metadata.json"
            with open(metadata_file, "w") as f:
                json.dump(scan_metadata, f, indent=2)
            
            logger.info(f"Scan results organized for: {scan_dir_name}")
            return directories
            
        except Exception as e:
            logger.error(f"Failed to organize scan results for {scan_name}: {e}")
            return {}
    
    def store_scan_output(self, scan_dir: Path, scanner_name: str, output_data: Any, 
                         output_format: str = "json") -> Path:
        """
        Store scanner output in the appropriate location.
        
        Args:
            scan_dir: Scan directory path
            scanner_name: Name of the scanner
            output_data: Scanner output data
            output_format: Output format (json, txt, sarif, etc.)
            
        Returns:
            Path where the output was stored
        """
        try:
            outputs_dir = scan_dir / "outputs"
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Determine file extension and path
            if output_format == "json":
                filename = f"{scanner_name}_{timestamp}.json"
                file_path = outputs_dir / filename
                
                # Pretty print JSON
                with open(file_path, "w") as f:
                    json.dump(output_data, f, indent=2)
                    
            elif output_format == "txt":
                filename = f"{scanner_name}_{timestamp}.txt"
                file_path = outputs_dir / filename
                
                # Handle string or list data
                if isinstance(output_data, list):
                    content = "\n".join(str(item) for item in output_data)
                else:
                    content = str(output_data)
                
                with open(file_path, "w") as f:
                    f.write(content)
                    
            elif output_format == "sarif":
                filename = f"{scanner_name}_{timestamp}.sarif"
                file_path = outputs_dir / filename
                
                # SARIF format
                with open(file_path, "w") as f:
                    json.dump(output_data, f, indent=2)
                    
            else:
                # Generic handling
                filename = f"{scanner_name}_{timestamp}.{output_format}"
                file_path = outputs_dir / filename
                
                with open(file_path, "w") as f:
                    if isinstance(output_data, (dict, list)):
                        json.dump(output_data, f, indent=2)
                    else:
                        f.write(str(output_data))
            
            os.chmod(file_path, 0o644)
            logger.info(f"Stored {scanner_name} output: {file_path}")
            return file_path
            
        except Exception as e:
            logger.error(f"Failed to store {scanner_name} output: {e}")
            return Path()
    
    def store_report(self, scan_dir: Path, report_name: str, report_data: Any, 
                    report_format: str = "html") -> Path:
        """
        Store scan report in the appropriate location.
        
        Args:
            scan_dir: Scan directory path
            report_name: Name of the report
            report_data: Report data
            report_format: Report format (html, pdf, md, etc.)
            
        Returns:
            Path where the report was stored
        """
        try:
            reports_dir = scan_dir / "reports"
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            filename = f"{report_name.replace(' ', '_')}_{timestamp}.{report_format}"
            file_path = reports_dir / filename
            
            if report_format == "html":
                with open(file_path, "w") as f:
                    f.write(str(report_data))
            elif report_format == "pdf":
                # PDF handling would require additional libraries
                with open(file_path, "wb") as f:
                    f.write(report_data)
            elif report_format == "md":
                with open(file_path, "w") as f:
                    f.write(str(report_data))
            else:
                with open(file_path, "w") as f:
                    f.write(str(report_data))
            
            os.chmod(file_path, 0o644)
            logger.info(f"Stored report {report_name}: {file_path}")
            return file_path
            
        except Exception as e:
            logger.error(f"Failed to store report {report_name}: {e}")
            return Path()
    
    def store_log(self, scan_dir: Path, log_name: str, log_data: str) -> Path:
        """
        Store log file in the appropriate location.
        
        Args:
            scan_dir: Scan directory path
            log_name: Name of the log
            log_data: Log content
            
        Returns:
            Path where the log was stored
        """
        try:
            logs_dir = scan_dir / "logs"
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            filename = f"{log_name.replace(' ', '_')}_{timestamp}.log"
            file_path = logs_dir / filename
            
            with open(file_path, "w") as f:
                f.write(log_data)
            
            os.chmod(file_path, 0o644)
            logger.info(f"Stored log {log_name}: {file_path}")
            return file_path
            
        except Exception as e:
            logger.error(f"Failed to store log {log_name}: {e}")
            return Path()
    
    def compress_scan_results(self, scan_dir: Path) -> Path:
        """
        Compress scan results for storage.
        
        Args:
            scan_dir: Scan directory to compress
            
        Returns:
            Path to the compressed archive
        """
        try:
            archives_dir = scan_dir / "archives"
            archives_dir.mkdir(exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            archive_name = f"{scan_dir.name}_{timestamp}.tar.gz"
            archive_path = archives_dir / archive_name
            
            # Create compressed archive
            with tarfile.open(archive_path, "w:gz") as tar:
                # Add all directories except archives
                for item in scan_dir.iterdir():
                    if item.name != "archives":
                        tar.add(item, arcname=item.name)
            
            # Calculate compression ratio
            original_size = sum(f.stat().st_size for f in scan_dir.rglob("*") if f.is_file())
            compressed_size = archive_path.stat().st_size
            compression_ratio = (1 - compressed_size / original_size) * 100 if original_size > 0 else 0
            
            logger.info(f"Compressed {scan_dir.name}: {compression_ratio:.1f}% reduction")
            return archive_path
            
        except Exception as e:
            logger.error(f"Failed to compress scan results for {scan_dir.name}: {e}")
            return Path()
    
    def cleanup_old_results(self, retention_days: int = 180) -> Dict[str, int]:
        """
        Clean up old scan results based on retention policy.
        
        Args:
            retention_days: Number of days to keep results
            
        Returns:
            Dictionary with cleanup statistics
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=retention_days)
            stats = {
                "directories_removed": 0,
                "files_removed": 0,
                "space_freed_mb": 0,
            }
            
            for scan_dir in self.results_path.iterdir():
                if scan_dir.is_dir():
                    try:
                        # Check directory modification time
                        dir_time = datetime.fromtimestamp(scan_dir.stat().st_mtime)
                        
                        if dir_time < cutoff_date:
                            # Calculate size before removal
                            dir_size = sum(f.stat().st_size for f in scan_dir.rglob("*") if f.is_file())
                            stats["space_freed_mb"] += dir_size / (1024 * 1024)
                            
                            # Count files
                            file_count = sum(1 for f in scan_dir.rglob("*") if f.is_file())
                            stats["files_removed"] += file_count
                            
                            # Remove directory
                            shutil.rmtree(scan_dir)
                            stats["directories_removed"] += 1
                            
                            logger.info(f"Removed old scan results: {scan_dir.name}")
                            
                    except Exception as e:
                        logger.warning(f"Failed to cleanup {scan_dir.name}: {e}")
            
            logger.info(f"Cleanup completed: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"Cleanup failed: {e}")
            return {}
    
    def get_results_status(self) -> Dict[str, Any]:
        """
        Get status information about stored results.
        
        Returns:
            Dictionary with results status information
        """
        try:
            status = {
                "results_directory": str(self.results_path),
                "results_directory_exists": self.results_path.exists(),
                "total_scans": 0,
                "total_size_mb": 0,
                "scan_directories": [],
            }
            
            if self.results_path.exists():
                scan_dirs = [d for d in self.results_path.iterdir() if d.is_dir()]
                status["total_scans"] = len(scan_dirs)
                
                total_size = 0
                for scan_dir in scan_dirs:
                    try:
                        size = sum(f.stat().st_size for f in scan_dir.rglob("*") if f.is_file())
                        total_size += size
                        
                        scan_info = {
                            "name": scan_dir.name,
                            "path": str(scan_dir),
                            "size_mb": size / (1024 * 1024),
                            "created_at": datetime.fromtimestamp(scan_dir.stat().st_ctime).isoformat(),
                            "modified_at": datetime.fromtimestamp(scan_dir.stat().st_mtime).isoformat(),
                        }
                        status["scan_directories"].append(scan_info)
                        
                    except Exception as e:
                        logger.debug(f"Failed to get info for {scan_dir.name}: {e}")
                
                status["total_size_mb"] = total_size / (1024 * 1024)
                status["scan_directories"].sort(key=lambda x: x["modified_at"], reverse=True)
            
            return status
            
        except Exception as e:
            logger.error(f"Failed to get results status: {e}")
            return {"error": str(e)}
    
    def backup_results(self, backup_path: Optional[str] = None) -> bool:
        """
        Create backup of all results.
        
        Args:
            backup_path: Optional backup path (uses default if not specified)
            
        Returns:
            True if backup successful, False otherwise
        """
        try:
            if not backup_path:
                backup_path = self.base_path / "backups" / "results"
            else:
                backup_path = Path(backup_path)
            
            backup_path.mkdir(parents=True, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"results_backup_{timestamp}.tar.gz"
            backup_file = backup_path / backup_name
            
            # Create backup archive
            with tarfile.open(backup_file, "w:gz") as tar:
                tar.add(self.results_path, arcname="results")
            
            # Create backup metadata
            backup_metadata = {
                "backup_name": backup_name,
                "backup_path": str(backup_file),
                "timestamp": datetime.now().isoformat(),
                "source_path": str(self.results_path),
                "backup_type": "full",
            }
            
            with open(backup_path / f"{backup_name}.metadata.json", "w") as f:
                json.dump(backup_metadata, f, indent=2)
            
            logger.info(f"Results backup created: {backup_file}")
            return True
            
        except Exception as e:
            logger.error(f"Results backup failed: {e}")
            return False
    
    def restore_results(self, backup_file: str) -> bool:
        """
        Restore results from backup.
        
        Args:
            backup_file: Path to backup file
            
        Returns:
            True if restore successful, False otherwise
        """
        try:
            backup_path = Path(backup_file)
            if not backup_path.exists():
                logger.error(f"Backup file not found: {backup_file}")
                return False
            
            # Create backup of current results
            if self.results_path.exists():
                backup_current = self.results_path.with_suffix(f".backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
                shutil.move(self.results_path, backup_current)
                logger.info(f"Current results backed up to: {backup_current}")
            
            # Extract backup
            with tarfile.open(backup_path, "r:gz") as tar:
                tar.extractall(path=self.base_path)
            
            logger.info(f"Results restored from: {backup_file}")
            return True
            
        except Exception as e:
            logger.error(f"Results restore failed: {e}")
            return False
    
    def get_scan_results(self, scan_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get information about scan results.
        
        Args:
            scan_id: Optional scan ID to filter results
            
        Returns:
            List of scan result information
        """
        try:
            results = []
            
            for scan_dir in self.results_path.iterdir():
                if scan_dir.is_dir():
                    try:
                        # Check if this matches the requested scan_id
                        if scan_id and scan_id not in scan_dir.name:
                            continue
                        
                        scan_info = {
                            "scan_directory": str(scan_dir),
                            "scan_name": scan_dir.name,
                            "created_at": datetime.fromtimestamp(scan_dir.stat().st_ctime).isoformat(),
                            "modified_at": datetime.fromtimestamp(scan_dir.stat().st_mtime).isoformat(),
                            "size_mb": sum(f.stat().st_size for f in scan_dir.rglob("*") if f.is_file()) / (1024 * 1024),
                            "files": [],
                            "directories": {},
                        }
                        
                        # Get file information
                        for file_path in scan_dir.rglob("*"):
                            if file_path.is_file():
                                file_info = {
                                    "path": str(file_path.relative_to(scan_dir)),
                                    "size": file_path.stat().st_size,
                                    "modified_at": datetime.fromtimestamp(file_path.stat().st_mtime).isoformat(),
                                }
                                scan_info["files"].append(file_info)
                        
                        # Get directory structure
                        for subdir in scan_dir.iterdir():
                            if subdir.is_dir():
                                scan_info["directories"][subdir.name] = {
                                    "path": str(subdir.relative_to(scan_dir)),
                                    "file_count": len(list(subdir.rglob("*"))),
                                }
                        
                        results.append(scan_info)
                        
                    except Exception as e:
                        logger.debug(f"Failed to get info for {scan_dir.name}: {e}")
            
            # Sort by modification time
            results.sort(key=lambda x: x["modified_at"], reverse=True)
            return results
            
        except Exception as e:
            logger.error(f"Failed to get scan results: {e}")
            return []


# Global results manager instance
results_manager = ResultsManager(settings.data_path)