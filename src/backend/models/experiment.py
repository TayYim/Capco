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


class RewardDataPoint(BaseModel):
    """Individual reward data point for charting."""
    
    scenario_number: int = Field(description="Sequential scenario number (1, 2, 3, ...)")
    reward: float = Field(description="Reward value for this scenario")
    iteration: int = Field(description="Optimization iteration this scenario belongs to")
    timestamp: Optional[datetime] = Field(default=None, description="When this scenario was executed")


class ExperimentConfig(BaseModel):
    """Configuration for a fuzzing experiment."""
    
    name: str = Field(description="Human-readable experiment name")
    route_id: str = Field(description="Route identifier") 
    route_name: Optional[str] = Field(description="Human-readable route name")
    route_file: str = Field(description="Route file name")
    search_method: SearchMethodEnum = Field(description="Search algorithm to use")
    num_iterations: int = Field(description="Number of iterations to run", gt=0, le=10000)
    timeout_seconds: int = Field(description="Timeout per scenario in seconds", gt=0, le=3600)
    headless: bool = Field(description="Run in headless mode", default=False)
    random_seed: int = Field(description="Random seed for reproducibility", ge=0)
    reward_function: RewardFunctionEnum = Field(description="Reward function to use")
    agent: str = Field(description="Agent type (ba or apollo)", default="ba")
    
    # Parameter overrides for specific parameters (optional)
    parameter_overrides: Optional[Dict[str, List[float]]] = Field(
        description="Parameter range overrides",
        default=None
    )
    
    # PSO-specific parameters
    pso_pop_size: Optional[int] = Field(description="PSO population size", default=20, gt=0, le=1000)
    pso_w: Optional[float] = Field(description="PSO inertia weight", default=0.9, ge=0, le=2)
    pso_c1: Optional[float] = Field(description="PSO cognitive coefficient", default=0.5, ge=0, le=4)
    pso_c2: Optional[float] = Field(description="PSO social coefficient", default=0.3, ge=0, le=4)
    
    # GA-specific parameters  
    ga_pop_size: Optional[int] = Field(description="GA population size", default=30, gt=0, le=1000)
    ga_prob_mut: Optional[float] = Field(description="GA mutation probability", default=0.1, ge=0, le=1)
    
    @validator('agent')
    def validate_agent(cls, v):
        """Validate agent type."""
        valid_agents = ['ba', 'apollo']
        if v not in valid_agents:
            raise ValueError(f"Invalid agent '{v}'. Must be one of: {valid_agents}")
        return v
    
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
    
    # Optimization-level tracking (PSO/GA iterations)
    current_iteration: int = Field(description="Current optimization iteration number")
    total_iterations: int = Field(description="Total planned optimization iterations")
    
    # Scenario-level tracking (actual CARLA simulations)
    scenarios_executed: int = Field(default=0, description="Total scenarios executed so far")
    total_scenarios: int = Field(description="Total scenarios to execute")
    scenarios_this_iteration: int = Field(default=0, description="Scenarios executed in current iteration")
    
    # Results tracking
    best_reward: Optional[float] = Field(default=None, description="Best reward found so far")
    collision_found: bool = Field(default=False, description="Whether collision was found")
    elapsed_time: Optional[float] = Field(default=None, description="Elapsed time in seconds")
    estimated_remaining: Optional[float] = Field(default=None, description="Estimated remaining time in seconds")
    recent_rewards: List[float] = Field(default=[], description="Recent reward values")
    
    # Real-time charting data
    reward_history: List[RewardDataPoint] = Field(default=[], description="Complete reward history for charting")
    
    # Method-specific information
    search_method: str = Field(description="Search method being used")
    population_size: Optional[int] = Field(default=None, description="Population size for PSO/GA methods")
    
    # Computed progress percentages
    @property
    def iteration_progress_percentage(self) -> float:
        """Calculate iteration progress percentage."""
        if self.total_iterations == 0:
            return 0.0
        return (self.current_iteration / self.total_iterations) * 100
    
    @property
    def scenario_progress_percentage(self) -> float:
        """Calculate scenario progress percentage."""
        if self.total_scenarios == 0:
            return 0.0
        return (self.scenarios_executed / self.total_scenarios) * 100


class ExperimentStatus(BaseModel):
    """Current status of an experiment."""
    
    id: str = Field(description="Experiment ID")
    name: str = Field(description="Human-readable experiment name")
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
    name: str = Field(description="Human-readable experiment name")
    route_id: str = Field(description="Route ID")
    route_name: Optional[str] = Field(description="Human-readable route name")
    route_file: str = Field(description="Route file")
    search_method: str = Field(description="Search method used")
    agent: str = Field(default="ba", description="Agent type (ba or apollo)")
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