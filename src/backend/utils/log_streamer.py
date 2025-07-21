"""
Log streamer for real-time log monitoring and WebSocket streaming.

This module provides functionality to monitor log files and stream
their content in real-time to WebSocket clients.
"""

import asyncio
import re
from pathlib import Path
from typing import AsyncGenerator, Tuple, Optional, Set, Dict
import logging
from datetime import datetime
import aiofiles

from core.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


class LogStreamer:
    """Service for streaming log files to WebSocket clients."""
    
    def __init__(self):
        self.active_streams: Dict[str, asyncio.Task] = {}
        self.log_level_patterns = {
            'DEBUG': re.compile(r'\bDEBUG\b', re.IGNORECASE),
            'INFO': re.compile(r'\bINFO\b', re.IGNORECASE),
            'WARNING': re.compile(r'\b(WARNING|WARN)\b', re.IGNORECASE),
            'ERROR': re.compile(r'\bERROR\b', re.IGNORECASE),
            'CRITICAL': re.compile(r'\b(CRITICAL|FATAL)\b', re.IGNORECASE),
        }
    
    async def stream_experiment_logs(self, experiment_id: str) -> AsyncGenerator[Tuple[str, str], None]:
        """
        Stream logs for a specific experiment.
        
        Args:
            experiment_id: ID of the experiment to stream logs for
            
        Yields:
            Tuples of (log_line, log_level)
        """
        try:
            log_file_path = self._get_experiment_log_path(experiment_id)
            
            if not log_file_path:
                logger.warning(f"No log file found for experiment {experiment_id}")
                yield f"No log file found for experiment {experiment_id}", "WARNING"
                return
            
            # Stream existing content first
            if log_file_path.exists():
                async for line, level in self._read_existing_log(log_file_path):
                    yield line, level
            
            # Then monitor for new content
            async for line, level in self._monitor_log_file(log_file_path):
                yield line, level
                
        except Exception as e:
            logger.error(f"Error streaming logs for experiment {experiment_id}: {e}")
            yield f"Error streaming logs: {str(e)}", "ERROR"
    
    async def get_recent_logs(
        self, 
        experiment_id: str, 
        lines: int = 100
    ) -> list[Tuple[str, str]]:
        """
        Get recent log lines for an experiment.
        
        Args:
            experiment_id: Experiment ID
            lines: Number of recent lines to retrieve
            
        Returns:
            List of (log_line, log_level) tuples
        """
        try:
            log_file_path = self._get_experiment_log_path(experiment_id)
            
            if not log_file_path or not log_file_path.exists():
                return []
            
            recent_lines = []
            async with aiofiles.open(log_file_path, 'r', encoding='utf-8', errors='replace') as f:
                # Read all lines into memory (for small files) or use a more efficient approach for large files
                all_lines = await f.readlines()
                
                # Get the last N lines
                start_index = max(0, len(all_lines) - lines)
                for line in all_lines[start_index:]:
                    line = line.strip()
                    if line:
                        level = self._detect_log_level(line)
                        recent_lines.append((line, level))
            
            return recent_lines
            
        except Exception as e:
            logger.error(f"Error getting recent logs for experiment {experiment_id}: {e}")
            return [("Error reading logs: " + str(e), "ERROR")]
    
    def stop_stream(self, experiment_id: str):
        """
        Stop streaming logs for an experiment.
        
        Args:
            experiment_id: Experiment ID
        """
        if experiment_id in self.active_streams:
            task = self.active_streams[experiment_id]
            task.cancel()
            del self.active_streams[experiment_id]
            logger.info(f"Stopped log streaming for experiment {experiment_id}")
    
    def _get_experiment_log_path(self, experiment_id: str) -> Optional[Path]:
        """
        Get the log file path for an experiment.
        
        Args:
            experiment_id: Experiment ID
            
        Returns:
            Path to log file or None if not found
        """
        try:
            # Try different possible log file locations and names
            base_output_dir = Path(settings.output_dir)
            
            possible_patterns = [
                # Direct experiment directory with log file
                base_output_dir / f"experiment_{experiment_id}" / "fuzzing.log",
                base_output_dir / f"experiment_{experiment_id}" / "experiment.log",
                base_output_dir / f"experiment_{experiment_id}" / "output.log",
                
                # Fuzzing output directory pattern
                base_output_dir / f"fuzzing_*_{experiment_id}_*" / "fuzzing.log",
                
                # Generic experiment ID directory
                base_output_dir / experiment_id / "fuzzing.log",
                base_output_dir / experiment_id / "experiment.log",
            ]
            
            for pattern in possible_patterns:
                if "*" in str(pattern):
                    # Use glob for wildcard patterns
                    matches = list(base_output_dir.glob(str(pattern.relative_to(base_output_dir))))
                    if matches:
                        return matches[0]
                else:
                    # Direct file check
                    if pattern.exists():
                        return pattern
            
            # If no specific log file found, look for any log files in experiment directories
            experiment_dirs = [
                base_output_dir / f"experiment_{experiment_id}",
                base_output_dir / experiment_id
            ]
            
            # Also check wildcard patterns
            for pattern in [f"fuzzing_*_{experiment_id}_*"]:
                experiment_dirs.extend(base_output_dir.glob(pattern))
            
            for exp_dir in experiment_dirs:
                if exp_dir.exists() and exp_dir.is_dir():
                    # Look for any .log files
                    log_files = list(exp_dir.glob("*.log"))
                    if log_files:
                        return log_files[0]  # Return first log file found
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting log path for experiment {experiment_id}: {e}")
            return None
    
    async def _read_existing_log(self, log_file_path: Path) -> AsyncGenerator[Tuple[str, str], None]:
        """
        Read existing content from a log file.
        
        Args:
            log_file_path: Path to the log file
            
        Yields:
            Tuples of (log_line, log_level)
        """
        try:
            async with aiofiles.open(log_file_path, 'r', encoding='utf-8', errors='replace') as f:
                async for line in f:
                    line = line.strip()
                    if line:
                        level = self._detect_log_level(line)
                        yield line, level
        except Exception as e:
            logger.error(f"Error reading existing log {log_file_path}: {e}")
            yield f"Error reading log file: {str(e)}", "ERROR"
    
    async def _monitor_log_file(self, log_file_path: Path) -> AsyncGenerator[Tuple[str, str], None]:
        """
        Monitor a log file for new content.
        
        Args:
            log_file_path: Path to the log file
            
        Yields:
            Tuples of (log_line, log_level) for new content
        """
        try:
            # Start monitoring from the end of the file
            last_position = log_file_path.stat().st_size if log_file_path.exists() else 0
            
            while True:
                try:
                    if not log_file_path.exists():
                        # Wait for file to be created
                        await asyncio.sleep(1)
                        continue
                    
                    current_size = log_file_path.stat().st_size
                    
                    if current_size > last_position:
                        # File has grown, read new content
                        async with aiofiles.open(log_file_path, 'r', encoding='utf-8', errors='replace') as f:
                            await f.seek(last_position)
                            new_content = await f.read()
                            
                            if new_content:
                                # Process new lines
                                lines = new_content.split('\n')
                                for line in lines:
                                    line = line.strip()
                                    if line:
                                        level = self._detect_log_level(line)
                                        yield line, level
                                
                                last_position = current_size
                    
                    elif current_size < last_position:
                        # File was truncated or rotated, start from beginning
                        last_position = 0
                        yield "Log file was rotated or truncated", "INFO"
                    
                    # Wait before checking again
                    await asyncio.sleep(0.5)
                    
                except asyncio.CancelledError:
                    # Stream was cancelled
                    break
                except Exception as e:
                    logger.warning(f"Error monitoring log file {log_file_path}: {e}")
                    yield f"Error monitoring log: {str(e)}", "ERROR"
                    await asyncio.sleep(2)  # Wait longer on error
                    
        except Exception as e:
            logger.error(f"Fatal error monitoring log file {log_file_path}: {e}")
            yield f"Fatal error monitoring log: {str(e)}", "ERROR"
    
    def _detect_log_level(self, log_line: str) -> str:
        """
        Detect the log level of a log line.
        
        Args:
            log_line: The log line to analyze
            
        Returns:
            Detected log level
        """
        # Check for [Progress] logs first - these get special treatment
        if log_line.strip().startswith('[Progress]'):
            return 'PROGRESS'
        
        # Check for explicit log level patterns
        for level, pattern in self.log_level_patterns.items():
            if pattern.search(log_line):
                return level
        
        # Check for specific keywords that indicate severity
        line_lower = log_line.lower()
        
        if any(word in line_lower for word in ['error', 'exception', 'failed', 'failure']):
            return 'ERROR'
        elif any(word in line_lower for word in ['warning', 'warn', 'deprecated']):
            return 'WARNING'
        elif any(word in line_lower for word in ['collision', 'found', 'success', 'completed']):
            return 'INFO'
        elif any(word in line_lower for word in ['debug', 'trace']):
            return 'DEBUG'
        
        # Default to INFO for unrecognized patterns
        return 'INFO'
    
    def _format_log_line(self, line: str, level: str) -> str:
        """
        Format a log line with timestamp if not already present.
        
        Args:
            line: Original log line
            level: Log level
            
        Returns:
            Formatted log line
        """
        # Check if line already has a timestamp
        timestamp_patterns = [
            r'^\d{4}-\d{2}-\d{2}',  # YYYY-MM-DD
            r'^\d{2}:\d{2}:\d{2}',  # HH:MM:SS
            r'^\[\d{4}-\d{2}-\d{2}',  # [YYYY-MM-DD
        ]
        
        has_timestamp = any(re.match(pattern, line) for pattern in timestamp_patterns)
        
        if not has_timestamp:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            return f"[{timestamp}] {level}: {line}"
        
        return line


# Dependency injection
_log_streamer = None

def get_log_streamer() -> LogStreamer:
    """Get log streamer instance."""
    global _log_streamer
    if _log_streamer is None:
        _log_streamer = LogStreamer()
    return _log_streamer 