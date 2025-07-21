"""
Experiment service for managing fuzzing experiments.

This service acts as an adapter between the FastAPI web layer
and the existing fuzzing framework (sim_runner.py), providing
a clean interface for experiment management.
"""

import asyncio
import uuid
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from pathlib import Path
import json
import logging
import subprocess
import sys
import time
import math

# Add path for utilities  
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from utils.carla_cleanup import full_carla_cleanup

# Name generator functions (inline to avoid import issues)
import random

def generate_experiment_name(style: str = "animal") -> str:
    """Generate a random experiment name."""
    adjectives = [
        "Agile", "Bold", "Clever", "Dynamic", "Elegant", "Fast", "Graceful", "Heavy",
        "Intelligent", "Jolly", "Keen", "Lightning", "Mighty", "Noble", "Optimized",
        "Precise", "Quick", "Robust", "Swift", "Turbulent", "Ultra", "Vibrant",
        "Wild", "Youthful", "Zealous", "Active", "Brave", "Careful", "Daring", "Epic"
    ]
    animals = [
        "Falcon", "Tiger", "Eagle", "Wolf", "Lion", "Shark", "Panther", "Cheetah",
        "Hawk", "Bear", "Fox", "Lynx", "Jaguar", "Leopard", "Raven", "Phoenix",
        "Dragon", "Griffin", "Viper", "Cobra", "Stallion", "Mustang", "Bronco"
    ]
    tech_adjectives = [
        "Quantum", "Neural", "Binary", "Digital", "Cyber", "Virtual", "Matrix",
        "Nano", "Micro", "Mega", "Turbo", "Hyper", "Ultra", "Meta", "Proto"
    ]
    objects = [
        "Quest", "Mission", "Trial", "Test", "Probe", "Scan", "Search", "Hunt",
        "Explorer", "Finder", "Seeker", "Scout", "Tracker", "Analyzer", "Monitor"
    ]
    
    if style == "tech":
        return f"{random.choice(tech_adjectives)} {random.choice(objects)}"
    elif style == "mixed":
        if random.random() < 0.7:
            return f"{random.choice(adjectives)} {random.choice(animals)}"
        else:
            return f"{random.choice(tech_adjectives)} {random.choice(objects)}"
    else:
        return f"{random.choice(adjectives)} {random.choice(animals)}"

def generate_unique_name(existing_names: set[str] | None = None, style: str = "animal", max_attempts: int = 100) -> str:
    """Generate a unique experiment name not in the existing set."""
    if existing_names is None:
        existing_names = set()
    
    for _ in range(max_attempts):
        name = generate_experiment_name(style)
        if name not in existing_names:
            return name
    
    # If we can't find a unique name, add a number suffix
    base_name = generate_experiment_name(style)
    counter = 1
    while f"{base_name} #{counter}" in existing_names:
        counter += 1
    
    return f"{base_name} #{counter}"

def validate_experiment_name(name: str) -> tuple[bool, str]:
    """Validate an experiment name."""
    if not name or not name.strip():
        return False, "Name cannot be empty"
    
    if len(name.strip()) < 2:
        return False, "Name must be at least 2 characters long"
    
    if len(name.strip()) > 100:
        return False, "Name must be less than 100 characters"
    
    # Check for invalid characters (basic validation)
    invalid_chars = set('<>:"/\\|?*')
    if any(char in name for char in invalid_chars):
        return False, f"Name cannot contain these characters: {' '.join(invalid_chars)}"
    
    return True, ""

# Import WebSocket broadcasting for real-time logs
try:
    from api.websockets.console_logs import broadcast_log_message
except ImportError:
    # Fallback if WebSocket module not available
    async def broadcast_log_message(experiment_id: str, message: str, level: str = "INFO"):
        pass

from models.experiment import (
    ExperimentConfig, ExperimentStatus, ExperimentResult,
    ExperimentListItem, ExperimentUpdate, ProgressInfo,
    ExperimentStatusEnum, CollisionInfo
)
from core.config import get_settings
from core.database import (
    save_experiment_record, update_experiment_status,
    get_experiment_record, list_experiment_records, delete_experiment_record
)

settings = get_settings()
logger = logging.getLogger(__name__)


def sanitize_float_value(value: Any) -> Optional[float]:
    """
    Sanitize float values to be JSON-compliant.
    
    Args:
        value: The value to sanitize
        
    Returns:
        Sanitized float value or None if invalid
    """
    if value is None:
        return None
    
    try:
        float_val = float(value)
        # Check for infinity or NaN values
        if math.isinf(float_val) or math.isnan(float_val):
            return None
        return float_val
    except (ValueError, TypeError):
        return None


class ExperimentService:
    """Service for managing fuzzing experiments."""
    
    def __init__(self):
        self.active_experiments: Dict[str, asyncio.Task] = {}
        self.experiment_status: Dict[str, dict] = {}
        self._status_locks: Dict[str, asyncio.Lock] = {}
        self._actual_output_dirs: Dict[str, str] = {}
        # Load existing experiments from database on startup
        self._load_experiments_from_database()
    
    def _calculate_total_scenarios(self, search_method: str, iterations: int, population_size: int = None) -> int:
        """Calculate total number of scenarios to be executed."""
        if search_method == 'random':
            return iterations
        elif search_method in ['pso', 'ga']:
            if population_size is None:
                # Default population sizes
                population_size = 20 if search_method == 'pso' else 30
            return iterations * population_size
        return iterations
    
    def _get_population_size_from_config(self, config: dict) -> int:
        """Extract population size from experiment configuration."""
        search_method = config.get('search_method', 'random')
        if search_method == 'pso':
            return config.get('pso_pop_size', 20)
        elif search_method == 'ga':
            return config.get('ga_pop_size', 30)
        return 1  # For random method
    
    def _create_progress_from_database_record(self, record) -> Optional[dict]:
        """Create progress dictionary from database record."""
        if not record:
            return None
            
        search_method = getattr(record, 'search_method', 'random')
        num_iterations = getattr(record, 'num_iterations', 10)
        
        # Get population size from record or defaults
        population_size = None
        if search_method == 'pso':
            population_size = getattr(record, 'pso_pop_size', 20)
        elif search_method == 'ga':
            population_size = getattr(record, 'ga_pop_size', 30)
        
        # Calculate total scenarios
        total_scenarios = self._calculate_total_scenarios(search_method, num_iterations, population_size)
        
        return {
            "current_iteration": getattr(record, 'current_iteration', 0),
            "total_iterations": num_iterations,
            "scenarios_executed": getattr(record, 'scenarios_executed', 0),
            "total_scenarios": total_scenarios,
            "scenarios_this_iteration": getattr(record, 'scenarios_this_iteration', 0),
            "best_reward": sanitize_float_value(getattr(record, 'best_reward', None)),
            "collision_found": getattr(record, 'collision_found', False) or False,
            "elapsed_time": None,  # Runtime-only data
            "estimated_remaining": None,  # Runtime-only data
            "recent_rewards": [],  # Runtime-only data
            "reward_history": [],  # Runtime-only data for charting
            "search_method": search_method,
            "population_size": population_size if search_method != 'random' else None
        }
    
    def _load_experiments_from_database(self):
        """Load existing experiments from database to preserve history across restarts."""
        try:
            # Load experiments from database
            experiment_records = list_experiment_records(limit=1000)  # Load recent experiments
            
            for record in experiment_records:
                # Safely extract values from database record
                record_id = getattr(record, 'id', None)
                if not record_id:
                    continue
                    
                created_at = getattr(record, 'created_at', None)
                started_at = getattr(record, 'started_at', None)
                completed_at = getattr(record, 'completed_at', None)
                
                # Get experiment name (with fallback for legacy experiments)
                experiment_name = getattr(record, 'name', None)
                if not experiment_name:
                    # Generate a name for legacy experiments without names
                    experiment_name = f"Legacy Experiment {record_id[:8]}"
                
                # Convert database record to experiment status dictionary
                experiment_status = {
                    "id": record_id,
                    "name": experiment_name,
                    "status": getattr(record, 'status', 'created'),
                    "config": {
                        "name": experiment_name,
                        "route_id": getattr(record, 'route_id', ''),
                        "route_file": getattr(record, 'route_file', ''),
                        "search_method": getattr(record, 'search_method', 'random'),
                        "num_iterations": getattr(record, 'num_iterations', 10),
                        "timeout_seconds": getattr(record, 'timeout_seconds', 300),
                        "headless": getattr(record, 'headless', False),
                        "random_seed": getattr(record, 'random_seed', 42),
                        "reward_function": getattr(record, 'reward_function', 'ttc')
                    },
                    "created_at": created_at.isoformat() if created_at else None,
                    "started_at": started_at.isoformat() if started_at else None,
                    "completed_at": completed_at.isoformat() if completed_at else None,
                    "error_message": getattr(record, 'error_message', None),
                    "output_directory": getattr(record, 'output_directory', None),
                    "progress": self._create_progress_from_database_record(record)
                }
                
                self.experiment_status[record_id] = experiment_status
                
            logger.info(f"Loaded {len(experiment_records)} experiments from database")
            
        except Exception as e:
            logger.warning(f"Failed to load experiments from database: {e}")
            # Continue with empty status - new experiments can still be created
    
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
        timestamp = datetime.now()
        
        # Validate and ensure unique experiment name
        is_valid, error_message = validate_experiment_name(config.name)
        if not is_valid:
            raise ValueError(f"Invalid experiment name: {error_message}")
        
        # Get existing names to ensure uniqueness
        existing_names = set()
        for exp_data in self.experiment_status.values():
            if exp_data and exp_data.get("config") and exp_data["config"].get("name"):
                existing_names.add(exp_data["config"]["name"])
        
        # Generate unique name if the provided name already exists
        final_name = config.name
        if final_name in existing_names:
            final_name = generate_unique_name(existing_names, style="mixed")
            logger.info(f"Name '{config.name}' already exists, using '{final_name}' instead")
        
        # Update config with final name
        config.name = final_name
        
        # Create output directory
        output_dir = Path(settings.output_dir) / f"experiment_{experiment_id}"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Save to database
        try:
            # Prepare method-specific parameters for database
            db_params = {}
            if config.search_method.value == 'pso':
                db_params.update({
                    'pso_pop_size': getattr(config, 'pso_pop_size', 20),
                    'pso_w': getattr(config, 'pso_w', 0.8),
                    'pso_c1': getattr(config, 'pso_c1', 0.5),
                    'pso_c2': getattr(config, 'pso_c2', 0.5)
                })
            elif config.search_method.value == 'ga':
                db_params.update({
                    'ga_pop_size': getattr(config, 'ga_pop_size', 30),
                    'ga_prob_mut': getattr(config, 'ga_prob_mut', 0.1)
                })
            
            save_experiment_record(
                experiment_id=experiment_id,
                name=final_name,
                route_id=config.route_id,
                route_file=config.route_file,
                search_method=config.search_method.value,
                num_iterations=config.num_iterations,
                timeout_seconds=config.timeout_seconds,
                headless=config.headless,
                random_seed=config.random_seed,
                reward_function=config.reward_function.value,
                output_directory=str(output_dir),
                **db_params
            )
        except Exception as e:
            logger.error(f"Failed to save experiment record: {e}")
            # Continue without database record for now
        
        # Calculate enhanced progress tracking
        population_size = self._get_population_size_from_config(config.dict())
        total_scenarios = self._calculate_total_scenarios(
            config.search_method.value, 
            config.num_iterations, 
            population_size
        )
        
        # Create enhanced progress tracking
        progress_info = ProgressInfo(
            current_iteration=0,
            total_iterations=config.num_iterations,
            scenarios_executed=0,
            total_scenarios=total_scenarios,
            scenarios_this_iteration=0,
            best_reward=None,
            collision_found=False,
            elapsed_time=None,
            estimated_remaining=None,
            recent_rewards=[],
            reward_history=[],
            search_method=config.search_method.value,
            population_size=population_size if config.search_method.value != 'random' else None
        )

        # Create experiment status
        experiment_status = ExperimentStatus(
            id=experiment_id,
            name=final_name,
            status=ExperimentStatusEnum.CREATED,
            config=config,
            progress=progress_info,
            created_at=timestamp,
            started_at=None,
            completed_at=None,
            error_message=None,
            output_directory=str(output_dir)
        )
        
        # Store in memory with lock
        self.experiment_status[experiment_id] = experiment_status.dict()
        self._status_locks[experiment_id] = asyncio.Lock()
        
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
        
        # Check for "zombie" experiments - marked as running but no active task
        if (status_dict.get("status") == "running" and 
            experiment_id not in self.active_experiments):
            logger.warning(f"Detected zombie experiment {experiment_id} - marking as failed")
            await self._update_experiment_status(
                experiment_id, 
                ExperimentStatusEnum.FAILED,
                error_message="Experiment process died unexpectedly"
            )
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
            # Skip if status_dict is None
            if status_dict is None:
                continue
                
            # Apply filters
            if status_filter and status_dict.get("status") != status_filter:
                continue
            if search_method and status_dict.get("config", {}).get("search_method") != search_method:
                continue
            
            # Safely get nested values
            config = status_dict.get("config") or {}
            progress = status_dict.get("progress") or {}
            
            # Convert status string to enum
            try:
                status_enum = ExperimentStatusEnum(status_dict.get("status", "created"))
            except ValueError:
                status_enum = ExperimentStatusEnum.CREATED
            
            # Parse timestamps safely
            created_at = datetime.utcnow()
            if status_dict.get("created_at"):
                try:
                    if isinstance(status_dict["created_at"], str):
                        created_at = datetime.fromisoformat(status_dict["created_at"])
                    else:
                        created_at = status_dict["created_at"]
                except (ValueError, TypeError):
                    pass
            
            completed_at = None
            if status_dict.get("completed_at"):
                try:
                    if isinstance(status_dict["completed_at"], str):
                        completed_at = datetime.fromisoformat(status_dict["completed_at"])
                    else:
                        completed_at = status_dict["completed_at"]
                except (ValueError, TypeError):
                    pass
            
            experiments.append(ExperimentListItem(
                id=exp_id,
                name=status_dict.get("name", config.get("name", f"Experiment {exp_id[:8]}")),
                status=status_enum,
                route_id=config.get("route_id", "unknown"),
                route_file=config.get("route_file", "unknown"),
                search_method=config.get("search_method", "unknown"),
                created_at=created_at,
                completed_at=completed_at,
                collision_found=progress.get("collision_found", False),
                best_reward=sanitize_float_value(progress.get("best_reward", None)),
                total_iterations=progress.get("current_iteration", 0)
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
        output_dir = Path(experiment.output_directory or "")
        
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
            collision_details=None,
            total_duration=best_solution_data.get("total_duration"),
            average_iteration_time=best_solution_data.get("average_iteration_time"),
            min_reward=best_solution_data.get("min_reward"),
            max_reward=best_solution_data.get("max_reward"),
            mean_reward=best_solution_data.get("mean_reward"),
            std_reward=best_solution_data.get("std_reward"),
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
    
    async def duplicate_experiment(self, experiment_id: str) -> Optional[ExperimentStatus]:
        """
        Duplicate an existing experiment with a new ID.
        
        Args:
            experiment_id: ID of the experiment to duplicate
            
        Returns:
            New experiment with same configuration but different ID
        """
        if experiment_id not in self.experiment_status:
            return None
        
        # Get the original experiment
        original_status_dict = self.experiment_status[experiment_id]
        original_config = original_status_dict.get("config", {})
        
        # Create new experiment with same config
        from models.experiment import ExperimentConfig, SearchMethodEnum, RewardFunctionEnum
        
        # Generate new name for the duplicated experiment
        original_name = original_config.get("name", "Unnamed Experiment")
        existing_names = set()
        for exp_data in self.experiment_status.values():
            if exp_data and exp_data.get("config") and exp_data["config"].get("name"):
                existing_names.add(exp_data["config"]["name"])
        
        # Generate unique name based on original
        new_name = generate_unique_name(existing_names, style="mixed")
        
        # Convert config dict back to ExperimentConfig object
        config = ExperimentConfig(
            name=new_name,
            route_id=original_config.get("route_id", ""),
            route_file=original_config.get("route_file", ""),
            search_method=SearchMethodEnum(original_config.get("search_method", "random")),
            num_iterations=original_config.get("num_iterations", 10),
            timeout_seconds=original_config.get("timeout_seconds", 300),
            headless=original_config.get("headless", False),
            random_seed=original_config.get("random_seed", 42),
            reward_function=RewardFunctionEnum(original_config.get("reward_function", "ttc"))
        )
        
        # Create the duplicated experiment
        duplicated_experiment = await self.create_experiment(config)
        
        logger.info(f"Duplicated experiment {experiment_id} as {duplicated_experiment.id}")
        return duplicated_experiment
    
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
        
        # Delete from database
        try:
            delete_experiment_record(experiment_id)
        except Exception as e:
            logger.warning(f"Failed to delete experiment record from database: {e}")
        
        # Remove from memory and cleanup tracking
        del self.experiment_status[experiment_id]
        if experiment_id in self._status_locks:
            del self._status_locks[experiment_id]
        if experiment_id in self._actual_output_dirs:
            del self._actual_output_dirs[experiment_id]
        
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
        
        output_dir = Path(experiment.output_directory or "")
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
        Run the actual fuzzing experiment using subprocess to avoid import issues.
        
        Args:
            experiment_id: Experiment ID
        """
        process = None
        try:
            status_dict = self.experiment_status[experiment_id]
            config_dict = status_dict["config"]
            output_dir = Path(status_dict["output_directory"])
            
            # Clean up any existing CARLA processes before starting
            logger.info(f"Cleaning up CARLA environment for experiment {experiment_id}...")
            cleanup_success = full_carla_cleanup(logger)
            if not cleanup_success:
                logger.warning("CARLA cleanup had some issues, but continuing...")
            
            # Wait a moment after cleanup
            time.sleep(2)
            
            # Create a configuration file for the subprocess
            config_file = output_dir / "experiment_config.json"
            with open(config_file, 'w') as f:
                json.dump({
                    "experiment_id": experiment_id,
                    "route_id": config_dict["route_id"],
                    "route_file": config_dict["route_file"],
                    "search_method": config_dict["search_method"],
                    "num_iterations": config_dict["num_iterations"],
                    "timeout_seconds": config_dict["timeout_seconds"],
                    "headless": config_dict["headless"],
                    "random_seed": config_dict["random_seed"],
                    "reward_function": config_dict["reward_function"],
                    "output_directory": str(output_dir)
                }, f, indent=2)
            
            # Build command to run the experiment
            python_exe = sys.executable
            script_path = Path(settings.project_root) / "src" / "simulation" / "sim_runner.py"
            
            # Validate script exists
            if not script_path.exists():
                raise FileNotFoundError(f"Simulation script not found: {script_path}")
            
            # Clean and validate route_id (remove any formatting like "(Town04)")
            route_id = config_dict["route_id"]
            if route_id.startswith("(") and route_id.endswith(")"):
                # Extract town name and try to find corresponding route ID
                town_name = route_id.strip("()")
                # For now, default to "1" but this should be handled by frontend
                route_id = "1"
                logger.warning(f"Route ID was formatted as '{config_dict['route_id']}', using '{route_id}' instead")
            
            cmd = [
                python_exe,
                "sim_runner.py",  # Use relative path since we're running from simulation directory
                route_id,  # cleaned positional argument
                "--method", config_dict["search_method"],
                "--iterations", str(config_dict["num_iterations"]),
                "--route-file", config_dict["route_file"],
                "--timeout", str(config_dict["timeout_seconds"]),
                "--seed", str(config_dict["random_seed"]),
                "--reward-function", config_dict["reward_function"],
                "--agent", config_dict.get("agent", "ba")  # Add agent parameter with default
            ]
            
            # Add PSO parameters if using PSO method
            if config_dict["search_method"] == "pso":
                if "pso_pop_size" in config_dict:
                    cmd.extend(["--pso-pop-size", str(config_dict["pso_pop_size"])])
                if "pso_w" in config_dict:
                    cmd.extend(["--pso-w", str(config_dict["pso_w"])])
                if "pso_c1" in config_dict:
                    cmd.extend(["--pso-c1", str(config_dict["pso_c1"])])
                if "pso_c2" in config_dict:
                    cmd.extend(["--pso-c2", str(config_dict["pso_c2"])])
            
            # Add GA parameters if using GA method
            elif config_dict["search_method"] == "ga":
                if "ga_pop_size" in config_dict:
                    cmd.extend(["--ga-pop-size", str(config_dict["ga_pop_size"])])
                if "ga_prob_mut" in config_dict:
                    cmd.extend(["--ga-prob-mut", str(config_dict["ga_prob_mut"])])
            
            if config_dict["headless"]:
                cmd.append("--headless")
            
            logger.info(f"Starting experiment {experiment_id}")
            logger.info(f"Working directory: {Path(settings.project_root) / 'src' / 'simulation'}")
            logger.info(f"Command: {' '.join(cmd)}")
            
            # Start the subprocess with separate stdout and stderr
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=Path(settings.project_root) / "src" / "simulation"
            )
            
            logger.info(f"Subprocess started for experiment {experiment_id} with PID {process.pid}")
            
            # Update progress periodically by reading output
            best_reward = None
            collision_found = False
            current_iteration = 0
            start_time = time.time()
            last_output_time = start_time
            
            # Set up overall timeout (max 2 hours)
            max_runtime = 7200  # 2 hours in seconds
            
            # Read output and error streams concurrently
            stdout_task = None
            stderr_task = None
            
            if process.stdout:
                stdout_task = asyncio.create_task(self._read_stream(process.stdout, experiment_id, "stdout"))
            if process.stderr:
                stderr_task = asyncio.create_task(self._read_stream(process.stderr, experiment_id, "stderr"))
            
            # Monitor subprocess progress with timeout
            while True:
                try:
                    # Wait for process completion with timeout
                    return_code = await asyncio.wait_for(process.wait(), timeout=30.0)
                    break
                except asyncio.TimeoutError:
                    # Check if process is still alive
                    if process.returncode is not None:
                        break
                    
                    # Check overall timeout
                    current_time = time.time()
                    if current_time - start_time > max_runtime:
                        logger.error(f"Experiment {experiment_id} timed out after {max_runtime} seconds")
                        process.terminate()
                        await asyncio.sleep(5)
                        if process.returncode is None:
                            process.kill()
                        raise Exception(f"Experiment timed out after {max_runtime} seconds")
                    
                    # Check for inactivity (no output for 10 minutes)
                    if current_time - last_output_time > 600:
                        logger.warning(f"Experiment {experiment_id} appears inactive (no output for 10 minutes)")
                        # Don't terminate yet, just warn
                    
                    # Update progress if we have monitoring info
                    if experiment_id in self.experiment_status and self.experiment_status[experiment_id] is not None:
                        if ("progress" not in self.experiment_status[experiment_id] or 
                            self.experiment_status[experiment_id]["progress"] is None):
                            self.experiment_status[experiment_id]["progress"] = {}
                        
                        elapsed_time = current_time - start_time
                        total_iterations = self.experiment_status[experiment_id]["config"].get("num_iterations", 10)
                        
                        self.experiment_status[experiment_id]["progress"].update({
                            "current_iteration": current_iteration,
                            "total_iterations": total_iterations,
                            "best_reward": best_reward,
                            "collision_found": collision_found,
                            "elapsed_time": elapsed_time,
                            "estimated_remaining": None,
                            "recent_rewards": []
                        })
            
            # Wait for output tasks to complete
            if stdout_task:
                await stdout_task
            if stderr_task:
                await stderr_task
            
            # Check return code and completion
            logger.info(f"Experiment {experiment_id} subprocess finished with return code: {return_code}")
            
            # Try to find the actual output directory that sim_runner.py used
            actual_output_dir = None
            status_dict = self.experiment_status.get(experiment_id, {})
            
            # Check if we have the actual output directory from console output
            if experiment_id in self._actual_output_dirs:
                actual_output_dir = Path(self._actual_output_dirs[experiment_id])
                logger.info(f"Using actual output directory: {actual_output_dir}")
                # Update the experiment status with the correct output directory
                async with self._status_locks.get(experiment_id, asyncio.Lock()):
                    status_dict["output_directory"] = str(actual_output_dir)
                
                # Also update the database with the actual output directory
                try:
                    from core.database import update_experiment_status
                    update_experiment_status(experiment_id, status_dict["status"], output_directory=str(actual_output_dir))
                    logger.info(f"Updated database with actual output directory: {actual_output_dir}")
                except Exception as e:
                    logger.warning(f"Failed to update database with actual output directory: {e}")
            
            # Check for results in both expected and actual directories
            dirs_to_check = [output_dir]
            if actual_output_dir and actual_output_dir != output_dir:
                dirs_to_check.append(actual_output_dir)
            
            results_data = {}
            has_results = False
            best_reward = None
            collision_found = False
            
            for check_dir in dirs_to_check:
                results_file = check_dir / "best_solution.json"
                search_history_file = check_dir / "search_history.csv"
                
                if results_file.exists():
                    try:
                        with open(results_file, 'r') as f:
                            results_data = json.load(f)
                            file_best_reward = results_data.get("best_reward", best_reward)
                            # Sanitize the reward value from file
                            sanitized_reward = sanitize_float_value(file_best_reward)
                            if sanitized_reward is not None:
                                best_reward = sanitized_reward
                            collision_found = results_data.get("collision_found", collision_found)
                            has_results = True
                            logger.info(f"Loaded results from {results_file}: best_reward={best_reward}, collision_found={collision_found}")
                            break
                    except Exception as e:
                        logger.warning(f"Failed to load results file {results_file}: {e}")
                
                if search_history_file.exists():
                    has_results = True
                    logger.info(f"Found search history file: {search_history_file}")
                    break
            
            if return_code == 0 or has_results:
                logger.info(f"Experiment {experiment_id} completed successfully (return_code={return_code}, has_results={has_results})")
                
                await self._update_experiment_status(
                    experiment_id, 
                    ExperimentStatusEnum.COMPLETED,
                    final_reward=best_reward,
                    collision_found=collision_found
                )
                
                logger.info(f"Experiment {experiment_id} completed with final reward {best_reward}")
            else:
                error_msg = f"Experiment subprocess failed with return code {return_code} and no results generated"
                logger.error(error_msg)
                
                await self._update_experiment_status(
                    experiment_id, 
                    ExperimentStatusEnum.FAILED,
                    error_message=error_msg
                )
            
        except asyncio.CancelledError:
            logger.info(f"Experiment {experiment_id} was cancelled")
            if process and process.returncode is None:
                process.terminate()
                await asyncio.sleep(2)
                if process.returncode is None:
                    process.kill()
            raise
        except Exception as e:
            logger.error(f"Experiment {experiment_id} failed: {e}")
            if process and process.returncode is None:
                logger.info(f"Terminating subprocess for failed experiment {experiment_id}")
                process.terminate()
                await asyncio.sleep(2)
                if process.returncode is None:
                    process.kill()
            
            await self._update_experiment_status(
                experiment_id, 
                ExperimentStatusEnum.FAILED,
                error_message=str(e)
            )
        finally:
            # Always clean up active experiment tracking
            if experiment_id in self.active_experiments:
                del self.active_experiments[experiment_id]
            # Clean up output directory tracking for completed experiments
            if experiment_id in self._actual_output_dirs:
                del self._actual_output_dirs[experiment_id]
            logger.info(f"Cleaned up active experiment tracking for {experiment_id}")
    
    async def _read_stream(self, stream, experiment_id: str, stream_name: str):
        """Read from a subprocess stream and log output."""
        try:
            while True:
                line = await stream.readline()
                if not line:
                    break
                
                line_str = line.decode().strip()
                if line_str:  # Only log non-empty lines
                    # Determine log level based on content, not stream
                    log_level = "INFO"  # Default to INFO for all streams
                    
                    # Check for [Progress] logs first
                    if '[Progress]' in line_str:
                        log_level = "PROGRESS"
                    # Check for specific patterns to set appropriate log level
                    elif any(word in line_str.lower() for word in ["collision", "found"]):
                        log_level = "SUCCESS" 
                    elif any(word in line_str.lower() for word in ["error", "failed", "exception"]):
                        log_level = "ERROR"
                    elif any(word in line_str.lower() for word in ["warning", "warn"]):
                        log_level = "WARNING"
                    
                    # Log to console with appropriate level
                    if log_level == "ERROR":
                        logger.error(f"Experiment {experiment_id} [{stream_name}]: {line_str}")
                    elif log_level == "WARNING":
                        logger.warning(f"Experiment {experiment_id} [{stream_name}]: {line_str}")
                    else:
                        logger.info(f"Experiment {experiment_id} [{stream_name}]: {line_str}")
                    
                    # Broadcast to WebSocket clients in real-time
                    try:
                        await broadcast_log_message(experiment_id, line_str, log_level)
                    except Exception as ws_error:
                        logger.warning(f"Failed to broadcast log message: {ws_error}")
                    
                    # Parse progress information from output
                    await self._parse_progress_info(experiment_id, line_str)
                        
        except Exception as e:
            logger.error(f"Error reading {stream_name} for experiment {experiment_id}: {e}")
            # Also broadcast the error
            try:
                await broadcast_log_message(experiment_id, f"Error reading {stream_name}: {e}", "ERROR")
            except Exception:
                pass
    
    async def _parse_progress_info(self, experiment_id: str, line_str: str):
        """Parse progress information from [Progress] prefixed logs."""
        try:
            # Look for [Progress] anywhere in the line, not just at the start
            if '[Progress]' not in line_str:
                # Still handle non-progress log patterns for backward compatibility
                await self._parse_legacy_patterns(experiment_id, line_str)
                return
            
            # Extract the progress message by finding [Progress] and taking everything after it
            progress_start = line_str.find('[Progress]')
            if progress_start == -1:
                return
                
            # Extract everything after "[Progress] "
            progress_message = line_str[progress_start + 10:].strip()  # +10 for len('[Progress]')
            
            if not progress_message:
                return
            
            if experiment_id not in self.experiment_status:
                return
                
            config = self.experiment_status[experiment_id].get("config", {})
            search_method = config.get("search_method", "random")
            
            # Get population size for PSO/GA methods
            population_size = None
            if search_method == "pso":
                population_size = config.get("pso_pop_size", 20)
            elif search_method == "ga":
                population_size = config.get("ga_pop_size", 30)
            else:
                population_size = 1  # Random method
            
            # Use async lock to prevent concurrent modification
            if experiment_id not in self._status_locks:
                self._status_locks[experiment_id] = asyncio.Lock()
            
            async with self._status_locks[experiment_id]:
                # Initialize progress structure if needed
                if ("progress" not in self.experiment_status[experiment_id] or 
                    self.experiment_status[experiment_id]["progress"] is None):
                    num_iterations = config.get("num_iterations", 10)
                    total_scenarios = self._calculate_total_scenarios(search_method, num_iterations, population_size)
                    
                    self.experiment_status[experiment_id]["progress"] = {
                        "current_iteration": 0,
                        "total_iterations": num_iterations,
                        "scenarios_executed": 0,
                        "total_scenarios": total_scenarios,
                        "scenarios_this_iteration": 0,
                        "best_reward": None,
                        "collision_found": False,
                        "elapsed_time": None,
                        "estimated_remaining": None,
                        "recent_rewards": [],
                        "reward_history": [],
                        "search_method": search_method,
                        "population_size": population_size if search_method != 'random' else None
                    }
                
                progress = self.experiment_status[experiment_id]["progress"]
                updated = False
                
                # Parse different types of progress messages
                message_lower = progress_message.lower()
                
                # Pattern 1: "Total iterations: X"
                if message_lower.startswith("total iterations:"):
                    try:
                        total_iterations = int(progress_message.split(":")[1].strip())
                        progress["total_iterations"] = total_iterations
                        # Recalculate total scenarios with the confirmed iteration count
                        total_scenarios = self._calculate_total_scenarios(search_method, total_iterations, population_size)
                        progress["total_scenarios"] = total_scenarios
                        logger.info(f"Updated total iterations for {experiment_id}: {total_iterations}, total scenarios: {total_scenarios}")
                        updated = True
                    except (ValueError, IndexError) as e:
                        logger.warning(f"Failed to parse total iterations from: {progress_message} - {e}")
                
                # Pattern 2: "Start iteration X"
                elif message_lower.startswith("start iteration"):
                    try:
                        iteration_num = int(progress_message.split()[-1])
                        progress["current_iteration"] = iteration_num
                        
                        # Reset scenarios count for this iteration
                        if search_method != "random":
                            progress["scenarios_this_iteration"] = 0
                        
                        logger.info(f"Started iteration {iteration_num} for {experiment_id}")
                        updated = True
                    except (ValueError, IndexError) as e:
                        logger.warning(f"Failed to parse start iteration from: {progress_message} - {e}")
                
                # Pattern 3: "Start scenario execution X, iteration Y/Z"
                elif message_lower.startswith("start scenario execution"):
                    try:
                        # Parse: "Start scenario execution 5, iteration 2/10"
                        parts = progress_message.split(",")
                        scenario_part = parts[0].strip()
                        iteration_part = parts[1].strip() if len(parts) > 1 else ""
                        
                        # Extract scenario number
                        scenario_num = int(scenario_part.split()[-1])
                        
                        # Extract iteration info if available
                        if "iteration" in iteration_part:
                            iter_info = iteration_part.split()[-1]  # "2/10"
                            if "/" in iter_info:
                                current_iter, total_iter = iter_info.split("/")
                                progress["current_iteration"] = int(current_iter)
                        
                        logger.debug(f"Started scenario {scenario_num} for {experiment_id}")
                        # Note: We don't increment counters here, wait for completion
                        
                    except (ValueError, IndexError) as e:
                        logger.warning(f"Failed to parse start scenario from: {progress_message} - {e}")
                
                # Pattern 4: "End scenario execution X, iteration Y/Z"
                elif message_lower.startswith("end scenario execution"):
                    try:
                        # One scenario completed - increment counters
                        progress["scenarios_executed"] += 1
                        
                        if search_method != "random":
                            progress["scenarios_this_iteration"] += 1
                            # Ensure we don't exceed population size for current iteration
                            if progress["scenarios_this_iteration"] > population_size:
                                progress["scenarios_this_iteration"] = population_size
                        else:
                            # For random search, scenarios_this_iteration is always 1
                            progress["scenarios_this_iteration"] = 1
                        
                        logger.info(f"Completed scenario for {experiment_id}: total {progress['scenarios_executed']}/{progress['total_scenarios']}")
                        updated = True
                        
                    except Exception as e:
                        logger.warning(f"Failed to parse end scenario from: {progress_message} - {e}")
                
                # Pattern 5: "Reward: X.XXXXXX"
                elif message_lower.startswith("reward:"):
                    try:
                        reward_value = float(progress_message.split(":")[1].strip())
                        sanitized_reward = sanitize_float_value(reward_value)
                        
                        if sanitized_reward is not None:
                            # Update best reward if this is better (lower is better)
                            if (progress["best_reward"] is None or 
                                sanitized_reward < progress["best_reward"]):
                                progress["best_reward"] = sanitized_reward
                                logger.info(f"New best reward for {experiment_id}: {sanitized_reward}")
                            
                            # Add to recent rewards (keep last 10)
                            recent_rewards = progress.get("recent_rewards", [])
                            recent_rewards.append(sanitized_reward)
                            progress["recent_rewards"] = recent_rewards[-10:]  # Keep last 10
                            
                            # Add to reward history for charting
                            if "reward_history" not in progress:
                                progress["reward_history"] = []
                            
                            # Create reward data point
                            scenario_number = progress.get("scenarios_executed", 0) + 1  # Next scenario number
                            current_iteration = progress.get("current_iteration", 1)
                            
                            reward_data_point = {
                                "scenario_number": scenario_number,
                                "reward": sanitized_reward,
                                "iteration": current_iteration,
                                "timestamp": datetime.now().isoformat()
                            }
                            
                            progress["reward_history"].append(reward_data_point)
                            
                            # Keep reward history reasonable (last 1000 points for performance)
                            if len(progress["reward_history"]) > 1000:
                                progress["reward_history"] = progress["reward_history"][-1000:]
                            
                            logger.info(f"Added reward data point for {experiment_id}: scenario {scenario_number}, reward {sanitized_reward}")
                            
                            # Check for collision (reward of 0.0 typically indicates collision)
                            if sanitized_reward == 0.0:
                                progress["collision_found"] = True
                                logger.info(f"Collision detected from reward for {experiment_id}")
                            
                            updated = True
                            
                    except (ValueError, IndexError) as e:
                        logger.warning(f"Failed to parse reward from: {progress_message} - {e}")
                
                # Pattern 6: "Scenario executed: X"
                elif message_lower.startswith("scenario executed:"):
                    try:
                        scenarios_count = int(progress_message.split(":")[1].strip())
                        
                        # This tells us how many scenarios were executed in the current iteration
                        if search_method != "random":
                            progress["scenarios_this_iteration"] = scenarios_count
                        
                        logger.info(f"Scenarios executed in current iteration for {experiment_id}: {scenarios_count}")
                        updated = True
                        
                    except (ValueError, IndexError) as e:
                        logger.warning(f"Failed to parse scenario executed from: {progress_message} - {e}")
                
                # Pattern 7: "End iteration X"
                elif message_lower.startswith("end iteration"):
                    try:
                        iteration_num = int(progress_message.split()[-1])
                        
                        # For PSO/GA, when an iteration ends, reset the scenarios count for next iteration
                        if search_method != "random":
                            progress["scenarios_this_iteration"] = 0
                        
                        logger.info(f"Ended iteration {iteration_num} for {experiment_id}")
                        updated = True
                        
                    except (ValueError, IndexError) as e:
                        logger.warning(f"Failed to parse end iteration from: {progress_message} - {e}")
                
                # Pattern 8: "Scenario execution time: Xs" or "Iteration execution time: Xs"
                elif "execution time:" in message_lower and "s" in progress_message:
                    try:
                        import re
                        # Extract time value
                        match = re.search(r'(\d+(?:\.\d+)?)s', progress_message)
                        if match:
                            execution_time = float(match.group(1))
                            
                            # For now, we'll use this as the elapsed time
                            # In the future, we could distinguish between scenario and iteration times
                            progress["elapsed_time"] = execution_time
                            logger.debug(f"Updated execution time for {experiment_id}: {execution_time}s")
                            updated = True
                            
                    except (ValueError, AttributeError) as e:
                        logger.warning(f"Failed to parse execution time from: {progress_message} - {e}")
                
                # Pattern 9: "Total running time: Xs"
                elif message_lower.startswith("total running time:"):
                    try:
                        import re
                        match = re.search(r'(\d+(?:\.\d+)?)s', progress_message)
                        if match:
                            total_time = float(match.group(1))
                            progress["elapsed_time"] = total_time
                            logger.info(f"Final execution time for {experiment_id}: {total_time}s")
                            updated = True
                            
                    except (ValueError, AttributeError) as e:
                        logger.warning(f"Failed to parse total running time from: {progress_message} - {e}")
                
                # Update database if we have meaningful changes
                if updated:
                    try:
                        update_experiment_status(
                            experiment_id, 
                            self.experiment_status[experiment_id]["status"],
                            best_reward=progress.get("best_reward"),
                            collision_found=progress.get("collision_found", False),
                            current_iteration=progress.get("current_iteration", 0),
                            scenarios_executed=progress.get("scenarios_executed", 0),
                            scenarios_this_iteration=progress.get("scenarios_this_iteration", 0)
                        )
                        
                        logger.info(f"Progress updated for {experiment_id}: "
                                   f"iteration {progress['current_iteration']}/{progress['total_iterations']}, "
                                   f"scenarios {progress['scenarios_executed']}/{progress['total_scenarios']}, "
                                   f"best_reward {progress.get('best_reward')}")
                    except Exception as e:
                        logger.warning(f"Failed to update database for progress: {e}")
                    
        except Exception as e:
            logger.debug(f"Could not parse progress from line: {line_str} - {e}")
            
    async def _parse_legacy_patterns(self, experiment_id: str, line_str: str):
        """Parse legacy patterns for backward compatibility (collision detection, etc.)."""
        try:
            line_lower = line_str.lower()
            
            # Legacy collision detection patterns
            collision_patterns = [
                "collision found", "collision detected", "crash detected", 
                "collision occurred: true", "🎯 collision found"
            ]
            
            if any(pattern in line_lower for pattern in collision_patterns):
                if experiment_id in self.experiment_status:
                    async with self._status_locks.get(experiment_id, asyncio.Lock()):
                        if "progress" in self.experiment_status[experiment_id]:
                            self.experiment_status[experiment_id]["progress"]["collision_found"] = True
                            logger.info(f"Legacy collision detected in experiment {experiment_id}: {line_str}")
            
            # Legacy "Results saved to:" pattern for output directory detection
            elif "results saved to:" in line_lower:
                try:
                    actual_path = line_str.split(":")[-1].strip()
                    self._actual_output_dirs[experiment_id] = actual_path
                    logger.info(f"Captured actual output directory for {experiment_id}: {actual_path}")
                except Exception:
                    pass
                    
        except Exception as e:
            logger.debug(f"Could not parse legacy patterns from line: {line_str} - {e}")
    
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
        
        # Use async lock to prevent concurrent modification
        if experiment_id not in self._status_locks:
            self._status_locks[experiment_id] = asyncio.Lock()
        
        async with self._status_locks[experiment_id]:
            status_dict = self.experiment_status[experiment_id]
            status_dict["status"] = status.value
            
            # Update timestamps
            if status == ExperimentStatusEnum.RUNNING:
                status_dict["started_at"] = datetime.now().isoformat()
            elif status in [ExperimentStatusEnum.COMPLETED, ExperimentStatusEnum.FAILED, ExperimentStatusEnum.STOPPED]:
                status_dict["completed_at"] = datetime.now().isoformat()
            
            # Prepare database update kwargs first (before modifying anything)
            db_kwargs = {}
            for key, value in kwargs.items():
                if key == "final_reward":
                    sanitized_reward = sanitize_float_value(value)
                    if sanitized_reward is not None:
                        db_kwargs["best_reward"] = sanitized_reward
                else:
                    db_kwargs[key] = value
            
            # Update additional fields (safe to do after preparing db_kwargs)
            for key, value in kwargs.items():
                if key == "error_message":
                    status_dict["error_message"] = value
                elif key == "final_reward":
                    if "progress" not in status_dict:
                        status_dict["progress"] = {}
                    sanitized_reward = sanitize_float_value(value)
                    if sanitized_reward is not None:
                        status_dict["progress"]["best_reward"] = sanitized_reward
                elif key == "collision_found":
                    if "progress" not in status_dict:
                        status_dict["progress"] = {}
                    status_dict["progress"]["collision_found"] = value
        
        # Update database
        try:
            update_experiment_status(experiment_id, status.value, **db_kwargs)
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