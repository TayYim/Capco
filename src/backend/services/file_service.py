"""
File service for handling experiment file operations.

This service manages file operations including downloads, previews,
archives, and data analysis for experiment results.
"""

import zipfile
import tarfile
import csv
import json
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple, Generator, AsyncGenerator
import logging
from datetime import datetime, timedelta
import asyncio
import shutil
import mimetypes
import pandas as pd
import numpy as np

from models.api import FileInfo, FilePreview, ExperimentAnalysis
from core.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


class FileService:
    """Service for managing experiment files and data analysis."""
    
    def __init__(self):
        self.output_base_dir = Path(settings.output_dir)
        self.max_preview_lines = 1000
        self.max_file_size_for_preview = 10 * 1024 * 1024  # 10MB
    
    async def list_experiment_files(self, experiment_id: str) -> Optional[List[FileInfo]]:
        """
        List all files for an experiment.
        
        Args:
            experiment_id: Experiment ID
            
        Returns:
            List of file information or None if experiment not found
        """
        try:
            experiment_dir = self._get_experiment_directory(experiment_id)
            if not experiment_dir or not experiment_dir.exists():
                return None
            
            files = []
            for file_path in experiment_dir.rglob("*"):
                if file_path.is_file():
                    try:
                        stat = file_path.stat()
                        file_type = mimetypes.guess_type(str(file_path))[0] or "application/octet-stream"
                        
                        files.append(FileInfo(
                            name=file_path.name,
                            size=stat.st_size,
                            modified=datetime.fromtimestamp(stat.st_mtime).isoformat(),
                            type=file_type
                        ))
                    except Exception as e:
                        logger.warning(f"Error getting file info for {file_path}: {e}")
                        continue
            
            # Sort by modification time (newest first)
            files.sort(key=lambda f: f.modified, reverse=True)
            return files
            
        except Exception as e:
            logger.error(f"Error listing files for experiment {experiment_id}: {e}")
            return None
    
    async def get_file_path(self, experiment_id: str, filename: str) -> Optional[Path]:
        """
        Get the file path for a specific experiment file.
        
        Args:
            experiment_id: Experiment ID
            filename: File name
            
        Returns:
            File path if valid and exists, None otherwise
        """
        try:
            experiment_dir = self._get_experiment_directory(experiment_id)
            if not experiment_dir or not experiment_dir.exists():
                return None
            
            # Security check: ensure filename doesn't contain path traversal
            if ".." in filename or "/" in filename or "\\" in filename:
                logger.warning(f"Potentially unsafe filename: {filename}")
                return None
            
            file_path = experiment_dir / filename
            
            # Ensure the file is within the experiment directory
            try:
                file_path.resolve().relative_to(experiment_dir.resolve())
            except ValueError:
                logger.warning(f"File path outside experiment directory: {file_path}")
                return None
            
            return file_path if file_path.exists() else None
            
        except Exception as e:
            logger.error(f"Error getting file path for {experiment_id}/{filename}: {e}")
            return None
    
    async def create_experiment_archive(
        self, 
        experiment_id: str, 
        format: str = "zip"
    ) -> Tuple[Optional[AsyncGenerator[bytes, None]], Optional[str]]:
        """
        Create an archive of all experiment files.
        
        Args:
            experiment_id: Experiment ID
            format: Archive format ("zip" or "tar")
            
        Returns:
            Tuple of (stream_generator, filename) or (None, None) if error
        """
        try:
            experiment_dir = self._get_experiment_directory(experiment_id)
            if not experiment_dir or not experiment_dir.exists():
                return None, None
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"experiment_{experiment_id}_{timestamp}.{format}"
            
            if format == "zip":
                stream = self._create_zip_stream(experiment_dir)
            elif format == "tar":
                stream = self._create_tar_stream(experiment_dir)
            else:
                raise ValueError(f"Unsupported archive format: {format}")
            
            return stream, filename
            
        except Exception as e:
            logger.error(f"Error creating archive for experiment {experiment_id}: {e}")
            return None, None
    
    async def preview_file(
        self, 
        experiment_id: str, 
        filename: str, 
        max_lines: int = 100
    ) -> Optional[FilePreview]:
        """
        Preview file contents.
        
        Args:
            experiment_id: Experiment ID
            filename: File name
            max_lines: Maximum lines to preview
            
        Returns:
            File preview data or None if error
        """
        try:
            file_path = await self.get_file_path(experiment_id, filename)
            if not file_path:
                return None
            
            # Check file size
            file_size = file_path.stat().st_size
            if file_size > self.max_file_size_for_preview:
                return FilePreview(
                    filename=filename,
                    content=f"File too large for preview ({file_size:,} bytes). Maximum size is {self.max_file_size_for_preview:,} bytes.",
                    is_truncated=True,
                    total_lines=0,
                    displayed_lines=0
                )
            
            # Determine if file is text
            if not self._is_text_file(file_path):
                return FilePreview(
                    filename=filename,
                    content="Binary file - cannot preview",
                    is_truncated=False,
                    total_lines=0,
                    displayed_lines=0
                )
            
            # Read and preview file
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                lines = []
                total_lines = 0
                
                for line in f:
                    total_lines += 1
                    if len(lines) < max_lines:
                        lines.append(line.rstrip('\n\r'))
                    elif len(lines) >= max_lines:
                        # Count remaining lines without storing them
                        for _ in f:
                            total_lines += 1
                        break
                
                is_truncated = total_lines > max_lines
                content = '\n'.join(lines)
                
                return FilePreview(
                    filename=filename,
                    content=content,
                    is_truncated=is_truncated,
                    total_lines=total_lines,
                    displayed_lines=len(lines)
                )
            
        except Exception as e:
            logger.error(f"Error previewing file {experiment_id}/{filename}: {e}")
            return None
    
    async def analyze_experiment_data(self, experiment_id: str) -> Optional[ExperimentAnalysis]:
        """
        Analyze experiment data and generate insights.
        
        Args:
            experiment_id: Experiment ID
            
        Returns:
            Experiment analysis or None if error
        """
        try:
            experiment_dir = self._get_experiment_directory(experiment_id)
            if not experiment_dir or not experiment_dir.exists():
                return None
            
            # Load experiment results
            search_history_file = experiment_dir / "search_history.csv"
            best_solution_file = experiment_dir / "best_solution.json"
            
            if not search_history_file.exists():
                logger.warning(f"No search history found for experiment {experiment_id}")
                return None
            
            # Load best solution data
            best_solution_data = {}
            if best_solution_file.exists():
                with open(best_solution_file, 'r') as f:
                    best_solution_data = json.load(f)
            
            # Load and analyze search history
            try:
                df = pd.read_csv(search_history_file)
            except Exception as e:
                logger.error(f"Error reading search history CSV: {e}")
                return None
            
            if df.empty:
                return None
            
            # Calculate summary statistics
            total_iterations = len(df)
            collision_rate = (df['collision_flag'] == True).sum() / total_iterations if total_iterations > 0 else 0
            average_reward = df['reward'].mean() if 'reward' in df.columns else 0
            best_reward = df['reward'].min() if 'reward' in df.columns else 0  # Lower is better
            
            # Calculate total duration
            total_duration = 0.0
            if 'iteration' in df.columns and len(df) > 1:
                # Estimate duration based on iterations (placeholder)
                total_duration = len(df) * 30.0  # Assume 30 seconds per iteration
            
            # Generate trends
            reward_over_time = []
            if 'iteration' in df.columns and 'reward' in df.columns:
                for _, row in df.iterrows():
                    reward_over_time.append({
                        "iteration": int(row['iteration']),
                        "reward": float(row['reward']) if pd.notna(row['reward']) else 0.0
                    })
            
            collision_distribution = {}
            if 'collision_flag' in df.columns:
                collision_counts = df['collision_flag'].value_counts()
                for value, count in collision_counts.items():
                    collision_distribution[str(value)] = int(count)
            
            # Analyze parameters
            best_parameters = best_solution_data.get("best_parameters", {})
            
            # Calculate parameter correlations (simplified)
            parameter_correlations = {}
            parameter_columns = [col for col in df.columns if col not in [
                'iteration', 'method', 'reward', 'collision_flag', 'min_ttc', 'distance'
            ]]
            
            if 'reward' in df.columns and parameter_columns:
                for param_col in parameter_columns:
                    try:
                        correlation = df[param_col].corr(df['reward'])
                        if pd.notna(correlation):
                            parameter_correlations[param_col] = float(correlation)
                    except Exception:
                        continue
            
            return ExperimentAnalysis(
                experiment_id=experiment_id,
                summary={
                    "total_iterations": total_iterations,
                    "collision_rate": collision_rate,
                    "average_reward": average_reward,
                    "best_reward": best_reward,
                    "total_duration": total_duration
                },
                trends={
                    "reward_over_time": reward_over_time,
                    "collision_distribution": collision_distribution
                },
                parameters={
                    "best_parameters": best_parameters,
                    "parameter_correlations": parameter_correlations
                }
            )
            
        except Exception as e:
            logger.error(f"Error analyzing experiment data for {experiment_id}: {e}")
            return None
    
    async def delete_experiment_files(self, experiment_id: str) -> bool:
        """
        Delete all files for an experiment.
        
        Args:
            experiment_id: Experiment ID
            
        Returns:
            True if successful, False otherwise
        """
        try:
            experiment_dir = self._get_experiment_directory(experiment_id)
            if not experiment_dir or not experiment_dir.exists():
                return False
            
            shutil.rmtree(experiment_dir)
            logger.info(f"Deleted experiment files for {experiment_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting files for experiment {experiment_id}: {e}")
            return False
    
    async def cleanup_old_files(self, days_old: int, dry_run: bool = False) -> Dict[str, Any]:
        """
        Clean up old experiment files.
        
        Args:
            days_old: Delete files older than this many days
            dry_run: If True, only report what would be deleted
            
        Returns:
            Cleanup report
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=days_old)
            deleted_experiments = []
            total_size_freed = 0
            
            if not self.output_base_dir.exists():
                return {
                    "deleted_experiments": [],
                    "total_size_freed": 0,
                    "dry_run": dry_run,
                    "message": "Output directory does not exist"
                }
            
            for experiment_dir in self.output_base_dir.iterdir():
                if not experiment_dir.is_dir():
                    continue
                
                try:
                    # Check if directory is old enough
                    dir_modified = datetime.fromtimestamp(experiment_dir.stat().st_mtime)
                    if dir_modified > cutoff_date:
                        continue
                    
                    # Calculate directory size
                    dir_size = sum(f.stat().st_size for f in experiment_dir.rglob('*') if f.is_file())
                    
                    deleted_experiments.append({
                        "experiment_id": experiment_dir.name,
                        "modified_date": dir_modified.isoformat(),
                        "size_bytes": dir_size
                    })
                    
                    total_size_freed += dir_size
                    
                    # Delete if not dry run
                    if not dry_run:
                        shutil.rmtree(experiment_dir)
                        logger.info(f"Deleted old experiment directory: {experiment_dir}")
                
                except Exception as e:
                    logger.warning(f"Error processing directory {experiment_dir}: {e}")
                    continue
            
            return {
                "deleted_experiments": deleted_experiments,
                "total_size_freed": total_size_freed,
                "dry_run": dry_run,
                "message": f"{'Would delete' if dry_run else 'Deleted'} {len(deleted_experiments)} experiments ({total_size_freed:,} bytes)"
            }
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
            return {
                "deleted_experiments": [],
                "total_size_freed": 0,
                "dry_run": dry_run,
                "error": str(e)
            }
    
    def _get_experiment_directory(self, experiment_id: str) -> Optional[Path]:
        """Get the directory path for an experiment."""
        try:
            # Handle different possible naming patterns
            possible_patterns = [
                f"experiment_{experiment_id}",
                f"fuzzing_*_{experiment_id}_*",
                experiment_id
            ]
            
            for pattern in possible_patterns:
                if "*" in pattern:
                    # Use glob for patterns with wildcards
                    matches = list(self.output_base_dir.glob(pattern))
                    if matches:
                        return matches[0]  # Return first match
                else:
                    # Direct path check
                    dir_path = self.output_base_dir / pattern
                    if dir_path.exists():
                        return dir_path
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting experiment directory for {experiment_id}: {e}")
            return None
    
    def _is_text_file(self, file_path: Path) -> bool:
        """Check if a file is a text file."""
        try:
            # Check by extension first
            text_extensions = {'.txt', '.csv', '.json', '.log', '.yaml', '.yml', '.py', '.md'}
            if file_path.suffix.lower() in text_extensions:
                return True
            
            # Check MIME type
            mime_type, _ = mimetypes.guess_type(str(file_path))
            if mime_type and mime_type.startswith('text/'):
                return True
            
            # Check first few bytes for binary content
            with open(file_path, 'rb') as f:
                chunk = f.read(1024)
                if b'\x00' in chunk:  # Null bytes indicate binary
                    return False
            
            return True
            
        except Exception:
            return False
    
    async def _create_zip_stream(self, directory: Path) -> AsyncGenerator[bytes, None]:
        """Create a streaming ZIP archive."""
        import io
        import asyncio
        
        def create_zip():
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
                for file_path in directory.rglob('*'):
                    if file_path.is_file():
                        arcname = file_path.relative_to(directory)
                        zf.write(file_path, arcname)
            return zip_buffer.getvalue()
        
        # Create ZIP in thread pool to avoid blocking
        zip_data = await asyncio.get_event_loop().run_in_executor(None, create_zip)
        
        # Yield data in chunks
        chunk_size = 8192
        for i in range(0, len(zip_data), chunk_size):
            yield zip_data[i:i + chunk_size]
    
    async def _create_tar_stream(self, directory: Path) -> AsyncGenerator[bytes, None]:
        """Create a streaming TAR archive."""
        import io
        import asyncio
        
        def create_tar():
            tar_buffer = io.BytesIO()
            with tarfile.open(fileobj=tar_buffer, mode='w') as tf:
                for file_path in directory.rglob('*'):
                    if file_path.is_file():
                        arcname = file_path.relative_to(directory)
                        tf.add(file_path, arcname)
            return tar_buffer.getvalue()
        
        # Create TAR in thread pool to avoid blocking
        tar_data = await asyncio.get_event_loop().run_in_executor(None, create_tar)
        
        # Yield data in chunks
        chunk_size = 8192
        for i in range(0, len(tar_data), chunk_size):
            yield tar_data[i:i + chunk_size]


# Dependency injection
_file_service = None

def get_file_service() -> FileService:
    """Get file service instance."""
    global _file_service
    if _file_service is None:
        _file_service = FileService()
    return _file_service 