"""
File-based log backend (fallback for systems without centralized logging).
"""
import logging
import os
import glob
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import re

from ..base import LogBackend

logger = logging.getLogger(__name__)


class FileBackend(LogBackend):
    """Read logs from local files"""
    
    def __init__(self, log_path: str = "/var/log"):
        self.log_path = log_path
        self.log_patterns = [
            "*.log",
            "**/*.log",
            "app.log",
            "application.log"
        ]
    
    async def fetch_logs(
        self,
        since_minutes: int = 15,
        service: Optional[str] = None,
        level: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Read recent logs from files"""
        
        cutoff_time = datetime.utcnow() - timedelta(minutes=since_minutes)
        logs = []
        
        # Find log files
        log_files = []
        for pattern in self.log_patterns:
            path_pattern = os.path.join(self.log_path, pattern)
            log_files.extend(glob.glob(path_pattern, recursive=True))
        
        # Read recent lines from each file
        for log_file in log_files[:10]:  # Limit to 10 files
            try:
                # Get file modification time
                mtime = datetime.fromtimestamp(os.path.getmtime(log_file))
                if mtime < cutoff_time:
                    continue  # Skip old files
                
                service_name = os.path.basename(log_file).replace(".log", "")
                
                # Read last N lines
                with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                    lines = f.readlines()[-1000:]  # Last 1000 lines
                    
                    for line in lines:
                        line = line.strip()
                        if not line:
                            continue
                        
                        # Parse log level
                        log_level = self._extract_level(line)
                        
                        # Filter by level
                        if level and log_level != level:
                            continue
                        
                        logs.append({
                            "timestamp": datetime.utcnow().isoformat() + "Z",
                            "level": log_level,
                            "message": line,
                            "service": service_name
                        })
            
            except Exception as e:
                logger.warning(f"Failed to read log file {log_file}: {e}")
                continue
        
        logger.info(f"Fetched {len(logs)} logs from files")
        return logs[-1000:]  # Return last 1000
    
    def _extract_level(self, line: str) -> str:
        """Extract log level from line"""
        line_lower = line.lower()
        
        if re.search(r'\b(error|fatal|critical)\b', line_lower):
            return "error"
        elif re.search(r'\bwarn(ing)?\b', line_lower):
            return "warning"
        elif re.search(r'\binfo\b', line_lower):
            return "info"
        elif re.search(r'\bdebug\b', line_lower):
            return "debug"
        else:
            return "info"
    
    async def health_check(self) -> bool:
        """Check if log path exists"""
        return os.path.exists(self.log_path)
