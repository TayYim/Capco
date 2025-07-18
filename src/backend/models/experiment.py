"""
Pydantic models for experiment-related API data.

Defines the data structures for experiment configuration,
status tracking, and result reporting.
"""

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Tuple, Any
from pydantic import BaseModel, Field, validator


class ExperimentStatusEnum(str, Enum):
    """Experiment status enumeration."""
    CREATED = "created"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    STOPPED = "stopped"


class SearchMethodEnum(str, Enum):
    """Search method enumeration."""
    RANDOM = "random"
    PSO = "pso"
    GA = "ga"


class RewardFunctionEnum(str, Enum):
    """Reward function enumeration."""
    COLLISION = "collision"
    DISTANCE = "distance"
    SAFETY_MARGIN = "safety_margin"
    TTC = "ttc"
    TTC_DIV_DIST = "ttc_div_dist"
    WEIGHTED_MULTI = "weighted_multi"


class ExperimentConfig(BaseModel):
    """Configuration for creating a new experiment."""
    
    route_id: str = Field(..., description="ID of the route to test")
    route_file: str = Field(default="routes_carlo", description="Route file name")
    search_method: SearchMethodEnum = Field(default=SearchMethodEnum.RANDOM, description="Search algorithm")
    num_iterations: int = Field(default=10, ge=1, le=1000, description="Number of iterations")
    timeout_seconds: int = Field(default=300, ge=30, le=3600, description="Timeout per simulation")
    headless: bool = Field(default=False, description="Run CARLA headless")
    random_seed: int = Field(default=42, description="Random seed for reproducibility")
    reward_function: RewardFunctionEnum = Field(default=RewardFunctionEnum.TTC, description="Reward function")
    parameter_overrides: Optional[Dict[str, Tuple[float, float]]] = Field(
        default=None, 
        description="Custom parameter ranges"
    )
    
    # Search method specific parameters
    pso_pop_size: Optional[int] = Field(default=20, ge=5, le=100, description="PSO population size")
    pso_w: Optional[float] = Field(default=0.8, ge=0.1, le=2.0, description="PSO inertia weight")
    pso_c1: Optional[float] = Field(default=0.5, ge=0.1, le=2.0, description="PSO cognitive parameter")
    pso_c2: Optional[float] = Field(default=0.5, ge=0.1, le=2.0, description="PSO social parameter")
    
    ga_pop_size: Optional[int] = Field(default=50, ge=10, le=200, description="GA population size")
    ga_prob_mut: Optional[float] = Field(default=0.1, ge=0.01, le=0.5, description="GA mutation probability")
    
    @validator('parameter_overrides')
    def validate_parameter_ranges(cls, v):
        """Validate parameter range tuples."""
        if v is not None:
            for param_name, (min_val, max_val) in v.items():
                if min_val >= max_val:
                    raise ValueError(f"Invalid range for {param_name}: min ({min_val}) >= max ({max_val})")
        return v


class ProgressInfo(BaseModel):
    """Progress information for running experiments."""
    
    current_iteration: int = Field(description="Current iteration number")
    total_iterations: int = Field(description="Total planned iterations")
    best_reward: Optional[float] = Field(description="Best reward found so far")
    collision_found: bool = Field(default=False, description="Whether collision was found")
    elapsed_time: Optional[float] = Field(description="Elapsed time in seconds")
    estimated_remaining: Optional[float] = Field(description="Estimated remaining time in seconds")
    recent_rewards: List[float] = Field(default=[], description="Recent reward values")


class ExperimentStatus(BaseModel):
    """Current status of an experiment."""
    
    id: str = Field(description="Experiment ID")
    status: ExperimentStatusEnum = Field(description="Current status")
    config: ExperimentConfig = Field(description="Experiment configuration")
    progress: Optional[ProgressInfo] = Field(description="Progress information")
    created_at: datetime = Field(description="Creation timestamp")
    started_at: Optional[datetime] = Field(description="Start timestamp")
    completed_at: Optional[datetime] = Field(description="Completion timestamp")
    error_message: Optional[str] = Field(description="Error message if failed")
    output_directory: Optional[str] = Field(description="Output directory path")


class CollisionInfo(BaseModel):
    """Information about collision details."""
    
    ego_x: float = Field(description="Ego vehicle X position")
    ego_y: float = Field(description="Ego vehicle Y position") 
    ego_velocity: float = Field(description="Ego vehicle velocity")
    ego_yaw: float = Field(description="Ego vehicle yaw angle")
    npc_x: float = Field(description="NPC vehicle X position")
    npc_y: float = Field(description="NPC vehicle Y position")
    npc_velocity: float = Field(description="NPC vehicle velocity")
    npc_yaw: float = Field(description="NPC vehicle yaw angle")


class ExperimentResult(BaseModel):
    """Detailed experiment results."""
    
    experiment_id: str = Field(description="Experiment ID")
    final_status: ExperimentStatusEnum = Field(description="Final experiment status")
    total_iterations: int = Field(description="Total iterations completed")
    best_reward: Optional[float] = Field(description="Best reward achieved")
    best_parameters: Optional[Dict[str, float]] = Field(description="Best parameter values")
    collision_found: bool = Field(description="Whether collision was found")
    collision_details: Optional[CollisionInfo] = Field(description="Collision details if found")
    
    # Timing information
    total_duration: Optional[float] = Field(description="Total experiment duration in seconds")
    average_iteration_time: Optional[float] = Field(description="Average time per iteration")
    
    # Statistical summary
    min_reward: Optional[float] = Field(description="Minimum reward found")
    max_reward: Optional[float] = Field(description="Maximum reward found")
    mean_reward: Optional[float] = Field(description="Mean reward across iterations")
    std_reward: Optional[float] = Field(description="Standard deviation of rewards")
    
    # File information
    result_files: List[str] = Field(default=[], description="Generated result file names")
    output_directory: Optional[str] = Field(description="Output directory path")


class ExperimentListItem(BaseModel):
    """Summary information for experiment list views."""
    
    id: str = Field(description="Experiment ID")
    route_id: str = Field(description="Route ID")
    route_file: str = Field(description="Route file")
    search_method: str = Field(description="Search method used")
    status: ExperimentStatusEnum = Field(description="Current status")
    created_at: datetime = Field(description="Creation timestamp")
    completed_at: Optional[datetime] = Field(description="Completion timestamp")
    collision_found: Optional[bool] = Field(description="Whether collision was found")
    best_reward: Optional[float] = Field(description="Best reward achieved")
    total_iterations: Optional[int] = Field(description="Total iterations")


class ExperimentCreate(BaseModel):
    """Request model for creating a new experiment."""
    
    config: ExperimentConfig = Field(description="Experiment configuration")
    start_immediately: bool = Field(default=False, description="Whether to start experiment immediately")


class ExperimentUpdate(BaseModel):
    """Request model for updating experiment metadata."""
    
    notes: Optional[str] = Field(description="User notes about the experiment")
    tags: Optional[List[str]] = Field(description="Tags for categorizing experiments") 