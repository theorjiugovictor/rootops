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
        # Patterns to search for
        self.log_patterns = [
            "*.log",
            "**/*.log", 
            "**/*error*.log",
            "**/*access*.log",
            "pm2/*.log"
        ]
        # Priority keywords for file ranking
        self.priority_keywords = ["error", "err", "exception", "fatal", "app", "service"]
    
    async def fetch_logs(
        self,
        since_minutes: int = 15,
        service: Optional[str] = None,
        level: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Read recent logs from files"""
        
        # Look for files modified in last 24 hours (relaxed from since_minutes)
        # We process the content to filter by time, but we shouldn't ignore files 
        # just because they weren't touched in the exact window we're querying.
        file_cutoff = datetime.utcnow() - timedelta(hours=24)
        logs = []
        
        # Find and rank log files
        log_files = self._find_log_files(file_cutoff)
        
        # Read recent lines from prioritized files
        files_processed = 0
        max_files = 50  # Increased limit
        
        for log_file in log_files:
            if files_processed >= max_files:
                break
                
            try:
                service_name = self._get_service_name(log_file)
                
                # Filter by service if requested
                if service and service not in service_name:
                    continue
                
                # Read last N lines
                file_logs = self._read_file_tail(log_file, 500)
                
                for line in file_logs:
                    if not line.strip():
                        continue
                    
                    # Parse log level
                    log_level = self._extract_level(line)
                    
                    # Filter by level
                    if level and log_level != level:
                        continue
                    
                    logs.append({
                        "timestamp": datetime.utcnow().isoformat() + "Z", # TODO: Extract real timestamp if possible
                        "level": log_level,
                        "message": line,
                        "service": service_name,
                        "source": log_file
                    })
                    
                files_processed += 1
            
            except Exception as e:
                logger.debug(f"Skipping log file {log_file}: {e}")
                continue
        
        logger.info(f"Scanned {files_processed} files, found {len(logs)} matching logs")
        return logs[-1000:]  # Return last 1000
    
    def _find_log_files(self, cutoff_time: datetime) -> List[str]:
        """Find log files, filter by time, and rank by relevance"""
        found_files = set()
        
        for pattern in self.log_patterns:
            path_pattern = os.path.join(self.log_path, pattern)
            # Use recursive=True for relevant patterns
            matches = glob.glob(path_pattern, recursive=("**" in pattern))
            found_files.update(matches)
            
        valid_files = []
        for f in found_files:
            if not os.path.isfile(f):
                continue
                
            try:
                mtime = datetime.fromtimestamp(os.path.getmtime(f))
                if mtime >= cutoff_time:
                    valid_files.append((f, mtime))
            except OSError:
                continue
                
        # Sort files: Priority keywords first, then by Modification Time (newest first)
        def score_file(item):
            path, mtime = item
            filename = os.path.basename(path).lower()
            
            # Score 100 for priority keywords
            priority_score = 100 if any(k in filename for k in self.priority_keywords) else 0
            
            # Add timestamp score (newer is better)
            return (priority_score, mtime.timestamp())
            
        valid_files.sort(key=score_file, reverse=True)
        return [f for f, _ in valid_files]

    def _get_service_name(self, filepath: str) -> str:
        """Extract service name from filepath"""
        basename = os.path.basename(filepath)
        name = basename.replace(".log", "")
        # Remove common suffixes/prefixes
        name = re.sub(r'[-_](error|access|out|prod|dev|staging)', '', name)
        return name

    def _read_file_tail(self, filepath: str, n_lines: int) -> List[str]:
        """Efficiently read last N lines of a file"""
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                # If file is small, just read it
                f.seek(0, os.SEEK_END)
                size = f.tell()
                
                if size < 50000: # 50KB
                    f.seek(0)
                    return f.readlines()
                
                # For larger files, seek back appropriately
                # Avg line length ~100 bytes, read N*150 bytes to be safe
                block_size = n_lines * 150
                f.seek(max(size - block_size, 0))
                
                lines = f.readlines()
                # Discard first incomplete line if we sought to middle
                if size > block_size and lines:
                    lines.pop(0)
                    
                return lines
        except Exception:
            return []

    def _extract_level(self, line: str) -> str:
        """Extract log level from line, supporting PM2/JSON formats"""
        line_lower = line.lower()
        
        # Check standard keywords
        if re.search(r'\b(error|err|fatal|critical|exception)\b', line_lower):
            return "error"
        elif re.search(r'\bwarn(ing)?\b', line_lower):
            return "warning"
        elif re.search(r'\b(info|notice)\b', line_lower):
            return "info"
        elif re.search(r'\bdebug\b', line_lower):
            return "debug"
        
        # Check PM2/JSON patterns "type":"error" or "level":30
        if '"level":' in line_lower or '"type":' in line_lower:
             if '"error"' in line_lower or '"err"' in line_lower or '"fatal"' in line_lower:
                 return "error"
             if '"warn"' in line_lower:
                 return "warning"
                 
        return "info"
    
    async def health_check(self) -> bool:
        """Check if log path exists"""
        return os.path.exists(self.log_path)
