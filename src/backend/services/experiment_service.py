"""
Experiment service for managing fuzzing experiments.

This service acts as an adapter between the FastAPI web layer
and the existing fuzzing framework (sim_runner.py), providing
a clean interface for experiment management.
"""

import asyncio
import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
from pathlib import Path
import json
import logging

from models.experiment import (
    ExperimentConfig, ExperimentStatus, ExperimentResult,
    ExperimentListItem, ExperimentUpdate, ProgressInfo,
    ExperimentStatusEnum, CollisionInfo
)
from core.config import get_settings
from core.database import (
    save_experiment_record, update_experiment_status,
    get_experiment_record, list_experiment_records
)

# Import the existing fuzzing framework
import sys
sys.path.append(str(Path(__file__).parent.parent.parent / "simulation"))
from sim_runner import ScenarioFuzzer

settings = get_settings()
logger = logging.getLogger(__name__)


class ExperimentService:
    """Service for managing fuzzing experiments."""
    
    def __init__(self):
        self.active_experiments: Dict[str, asyncio.Task] = {}
        self.experiment_status: Dict[str, dict] = {}
    
    async def create_experiment(
        self, 
        config: ExperimentConfig
    ) -> ExperimentStatus:
        """
        Create a new fuzzing experiment.
        
        Args:
            config: Experiment configuration
            
        Returns:
            Created experiment status
        """
        experiment_id = str(uuid.uuid4())
        timestamp = datetime.utcnow()
        
        # Create output directory
        output_dir = Path(settings.output_dir) / f"experiment_{experiment_id}"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Save to database
        try:
            save_experiment_record(
                experiment_id=experiment_id,
                route_id=config.route_id,
                route_file=config.route_file,
                search_method=config.search_method.value,
                num_iterations=config.num_iterations,
                timeout_seconds=config.timeout_seconds,
                headless=config.headless,
                random_seed=config.random_seed,
                reward_function=config.reward_function.value,
                output_directory=str(output_dir)
            )
        except Exception as e:
            logger.error(f"Failed to save experiment record: {e}")
            # Continue without database record for now
        
        # Create experiment status
        experiment_status = ExperimentStatus(
            id=experiment_id,
            status=ExperimentStatusEnum.CREATED,
            config=config,
            created_at=timestamp,
            output_directory=str(output_dir)
        )
        
        # Store in memory
        self.experiment_status[experiment_id] = experiment_status.dict()
        
        logger.info(f"Created experiment {experiment_id}")
        return experiment_status
    
    async def start_experiment(self, experiment_id: str) -> None:
        """
        Start a fuzzing experiment in the background.
        
        Args:
            experiment_id: ID of the experiment to start
        """
        if experiment_id not in self.experiment_status:
            raise ValueError(f"Experiment {experiment_id} not found")
        
        if experiment_id in self.active_experiments:
            raise ValueError(f"Experiment {experiment_id} is already running")
        
        # Update status to running
        await self._update_experiment_status(experiment_id, ExperimentStatusEnum.RUNNING)
        
        # Start experiment task
        task = asyncio.create_task(self._run_experiment_task(experiment_id))
        self.active_experiments[experiment_id] = task
        
        logger.info(f"Started experiment {experiment_id}")
    
    async def stop_experiment(self, experiment_id: str) -> None:
        """
        Stop a running experiment.
        
        Args:
            experiment_id: ID of the experiment to stop
        """
        if experiment_id not in self.active_experiments:
            raise ValueError(f"Experiment {experiment_id} is not running")
        
        # Cancel the task
        task = self.active_experiments[experiment_id]
        task.cancel()
        
        try:
            await task
        except asyncio.CancelledError:
            pass
        
        # Clean up
        del self.active_experiments[experiment_id]
        
        # Update status
        await self._update_experiment_status(experiment_id, ExperimentStatusEnum.STOPPED)
        
        logger.info(f"Stopped experiment {experiment_id}")
    
    async def get_experiment(self, experiment_id: str) -> Optional[ExperimentStatus]:
        """
        Get experiment status by ID.
        
        Args:
            experiment_id: Experiment ID
            
        Returns:
            Experiment status if found, None otherwise
        """
        if experiment_id not in self.experiment_status:
            return None
        
        status_dict = self.experiment_status[experiment_id]
        return ExperimentStatus(**status_dict)
    
    async def list_experiments(
        self,
        limit: int = 50,
        offset: int = 0,
        status_filter: Optional[str] = None,
        search_method: Optional[str] = None
    ) -> List[ExperimentListItem]:
        """
        List experiments with optional filtering.
        
        Args:
            limit: Maximum number of results
            offset: Offset for pagination
            status_filter: Optional status filter
            search_method: Optional search method filter
            
        Returns:
            List of experiment summaries
        """
        # For now, return from memory store
        # In production, this would query the database
        experiments = []
        
        for exp_id, status_dict in self.experiment_status.items():
            if status_filter and status_dict.get("status") != status_filter:
                continue
            
            if search_method and status_dict.get("config", {}).get("search_method") != search_method:
                continue
            
            # Create list item
            experiments.append(ExperimentListItem(
                id=exp_id,
                route_id=status_dict["config"]["route_id"],
                route_file=status_dict["config"]["route_file"],
                search_method=status_dict["config"]["search_method"],
                status=ExperimentStatusEnum(status_dict["status"]),
                created_at=datetime.fromisoformat(status_dict["created_at"]),
                completed_at=datetime.fromisoformat(status_dict["completed_at"]) if status_dict.get("completed_at") else None,
                collision_found=status_dict.get("progress", {}).get("collision_found"),
                best_reward=status_dict.get("progress", {}).get("best_reward"),
                total_iterations=status_dict.get("progress", {}).get("current_iteration")
            ))
        
        # Apply pagination
        start_idx = offset
        end_idx = offset + limit
        return experiments[start_idx:end_idx]
    
    async def get_experiment_results(self, experiment_id: str) -> Optional[ExperimentResult]:
        """
        Get detailed results for a completed experiment.
        
        Args:
            experiment_id: Experiment ID
            
        Returns:
            Experiment results if available
        """
        experiment = await self.get_experiment(experiment_id)
        if not experiment:
            return None
        
        # Load results from output directory
        output_dir = Path(experiment.output_directory)
        
        # Try to load best solution
        best_solution_file = output_dir / "best_solution.json"
        if best_solution_file.exists():
            with open(best_solution_file, 'r') as f:
                best_solution_data = json.load(f)
        else:
            best_solution_data = {}
        
        # Create result object
        result = ExperimentResult(
            experiment_id=experiment_id,
            final_status=experiment.status,
            total_iterations=best_solution_data.get("total_iterations", 0),
            best_reward=best_solution_data.get("best_reward"),
            best_parameters=best_solution_data.get("best_parameters"),
            collision_found=best_solution_data.get("collision_found", False),
            result_files=self._list_result_files(output_dir),
            output_directory=str(output_dir)
        )
        
        return result
    
    async def update_experiment(
        self, 
        experiment_id: str, 
        update_data: ExperimentUpdate
    ) -> Optional[ExperimentStatus]:
        """
        Update experiment metadata.
        
        Args:
            experiment_id: Experiment ID
            update_data: Update data
            
        Returns:
            Updated experiment status
        """
        if experiment_id not in self.experiment_status:
            return None
        
        # Update notes and tags (metadata only)
        status_dict = self.experiment_status[experiment_id]
        if update_data.notes is not None:
            status_dict["notes"] = update_data.notes
        if update_data.tags is not None:
            status_dict["tags"] = update_data.tags
        
        return ExperimentStatus(**status_dict)
    
    async def delete_experiment(self, experiment_id: str) -> bool:
        """
        Delete an experiment and its files.
        
        Args:
            experiment_id: Experiment ID
            
        Returns:
            True if successful, False if not found
        """
        if experiment_id not in self.experiment_status:
            return False
        
        # Remove from active experiments if running
        if experiment_id in self.active_experiments:
            await self.stop_experiment(experiment_id)
        
        # Delete output directory
        status_dict = self.experiment_status[experiment_id]
        output_dir = Path(status_dict.get("output_directory", ""))
        if output_dir.exists():
            import shutil
            shutil.rmtree(output_dir)
        
        # Remove from memory
        del self.experiment_status[experiment_id]
        
        logger.info(f"Deleted experiment {experiment_id}")
        return True
    
    async def get_experiment_file_path(
        self, 
        experiment_id: str, 
        filename: str
    ) -> Optional[Path]:
        """
        Get path to an experiment file.
        
        Args:
            experiment_id: Experiment ID
            filename: File name
            
        Returns:
            File path if valid, None otherwise
        """
        experiment = await self.get_experiment(experiment_id)
        if not experiment:
            return None
        
        output_dir = Path(experiment.output_directory)
        file_path = output_dir / filename
        
        # Security check: ensure file is within output directory
        try:
            file_path.resolve().relative_to(output_dir.resolve())
            return file_path if file_path.exists() else None
        except ValueError:
            # Path is outside output directory
            return None
    
    async def _run_experiment_task(self, experiment_id: str) -> None:
        """
        Run the actual fuzzing experiment.
        
        Args:
            experiment_id: Experiment ID
        """
        try:
            status_dict = self.experiment_status[experiment_id]
            config_dict = status_dict["config"]
            
            # Create ScenarioFuzzer instance
            fuzzer = ScenarioFuzzer(
                route_id=config_dict["route_id"],
                search_method=config_dict["search_method"],
                num_iterations=config_dict["num_iterations"],
                route_file=config_dict["route_file"],
                timeout_seconds=config_dict["timeout_seconds"],
                headless=config_dict["headless"],
                random_seed=config_dict["random_seed"],
                reward_function=config_dict["reward_function"]
            )
            
            # Update output directory to match our experiment
            fuzzer.output_dir = Path(status_dict["output_directory"])
            
            # Run the search
            best_params, best_reward = fuzzer.run_search()
            
            # Update final status
            await self._update_experiment_status(
                experiment_id, 
                ExperimentStatusEnum.COMPLETED,
                final_reward=best_reward,
                collision_found=(best_reward == 0.0)
            )
            
            logger.info(f"Experiment {experiment_id} completed successfully")
            
        except asyncio.CancelledError:
            logger.info(f"Experiment {experiment_id} was cancelled")
            raise
        except Exception as e:
            logger.error(f"Experiment {experiment_id} failed: {e}")
            await self._update_experiment_status(
                experiment_id, 
                ExperimentStatusEnum.FAILED,
                error_message=str(e)
            )
        finally:
            # Clean up active experiment
            if experiment_id in self.active_experiments:
                del self.active_experiments[experiment_id]
    
    async def _update_experiment_status(
        self, 
        experiment_id: str, 
        status: ExperimentStatusEnum,
        **kwargs
    ) -> None:
        """
        Update experiment status.
        
        Args:
            experiment_id: Experiment ID
            status: New status
            **kwargs: Additional status fields
        """
        if experiment_id not in self.experiment_status:
            return
        
        status_dict = self.experiment_status[experiment_id]
        status_dict["status"] = status.value
        
        # Update timestamps
        if status == ExperimentStatusEnum.RUNNING:
            status_dict["started_at"] = datetime.utcnow().isoformat()
        elif status in [ExperimentStatusEnum.COMPLETED, ExperimentStatusEnum.FAILED, ExperimentStatusEnum.STOPPED]:
            status_dict["completed_at"] = datetime.utcnow().isoformat()
        
        # Update additional fields
        for key, value in kwargs.items():
            if key == "error_message":
                status_dict["error_message"] = value
            elif key == "final_reward":
                if "progress" not in status_dict:
                    status_dict["progress"] = {}
                status_dict["progress"]["best_reward"] = value
            elif key == "collision_found":
                if "progress" not in status_dict:
                    status_dict["progress"] = {}
                status_dict["progress"]["collision_found"] = value
        
        # Update database
        try:
            update_experiment_status(experiment_id, status.value, **kwargs)
        except Exception as e:
            logger.warning(f"Failed to update database for experiment {experiment_id}: {e}")
    
    def _list_result_files(self, output_dir: Path) -> List[str]:
        """
        List result files in output directory.
        
        Args:
            output_dir: Output directory path
            
        Returns:
            List of file names
        """
        if not output_dir.exists():
            return []
        
        files = []
        for file_path in output_dir.iterdir():
            if file_path.is_file():
                files.append(file_path.name)
        
        return sorted(files)


# Dependency injection
_experiment_service = None

def get_experiment_service() -> ExperimentService:
    """Get experiment service instance."""
    global _experiment_service
    if _experiment_service is None:
        _experiment_service = ExperimentService()
    return _experiment_service 