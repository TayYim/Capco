"""
Pydantic models for configuration-related API data.

Defines the data structures for parameter ranges, 
system configuration, and settings management.
"""

from typing import Dict, List, Optional, Tuple, Any
from pydantic import BaseModel, Field, validator


class ParameterRange(BaseModel):
    """Parameter range configuration."""
    
    parameter_name: str = Field(description="Parameter name")
    min_value: float = Field(description="Minimum allowed value")
    max_value: float = Field(description="Maximum allowed value")
    default_value: Optional[float] = Field(description="Default value")
    description: Optional[str] = Field(description="Parameter description")
    unit: Optional[str] = Field(description="Parameter unit")
    scenario_type: Optional[str] = Field(description="Applicable scenario type")
    
    @validator('min_value', 'max_value')
    def validate_range(cls, v, values):
        """Validate that min_value < max_value."""
        if 'min_value' in values and v is not None:
            min_val = values['min_value']
            if hasattr(cls, 'max_value') and v <= min_val:
                raise ValueError("max_value must be greater than min_value")
        return v


class ScenarioParameterConfig(BaseModel):
    """Parameter configuration for a specific scenario type."""
    
    scenario_type: str = Field(description="Scenario type name")
    parameters: Dict[str, ParameterRange] = Field(description="Parameter configurations")
    description: Optional[str] = Field(description="Scenario type description")
    is_active: bool = Field(default=True, description="Whether this configuration is active")


class SystemConfiguration(BaseModel):
    """Overall system configuration."""
    
    # CARLA settings
    carla_path: str = Field(description="Path to CARLA installation")
    default_timeout: int = Field(description="Default simulation timeout")
    restart_gap: int = Field(description="Runs before CARLA restart")
    
    # Experiment settings
    max_concurrent_experiments: int = Field(description="Maximum concurrent experiments")
    default_iterations: int = Field(description="Default number of iterations")
    default_search_method: str = Field(description="Default search method")
    default_reward_function: str = Field(description="Default reward function")
    
    # File settings
    output_directory: str = Field(description="Base output directory")
    max_file_size: int = Field(description="Maximum file upload size")
    cleanup_after_days: int = Field(default=30, description="Days to keep experiment files")
    
    # Performance settings
    enable_headless: bool = Field(default=True, description="Enable headless mode by default")
    log_level: str = Field(default="INFO", description="Logging level")
    
    # Security settings (for future use)
    # No authentication configuration needed for prototype
    session_timeout: int = Field(default=3600, description="Session timeout in seconds")


class ParameterRangeUpdate(BaseModel):
    """Update request for parameter ranges."""
    
    ranges: Dict[str, Tuple[float, float]] = Field(
        description="Parameter name to (min, max) mapping"
    )
    scenario_type: Optional[str] = Field(
        description="Scenario type to apply ranges to"
    )
    apply_globally: bool = Field(
        default=False, 
        description="Apply to all scenario types"
    )
    
    @validator('ranges')
    def validate_ranges(cls, v):
        """Validate that all ranges have min < max."""
        for param_name, (min_val, max_val) in v.items():
            if min_val >= max_val:
                raise ValueError(f"Invalid range for {param_name}: {min_val} >= {max_val}")
        return v


class ConfigurationUpdate(BaseModel):
    """General configuration update request."""
    
    carla_path: Optional[str] = Field(description="CARLA installation path")
    default_timeout: Optional[int] = Field(ge=30, le=3600, description="Default timeout")
    max_concurrent_experiments: Optional[int] = Field(ge=1, le=10, description="Max concurrent experiments")
    default_iterations: Optional[int] = Field(ge=1, le=1000, description="Default iterations")
    default_search_method: Optional[str] = Field(description="Default search method")
    default_reward_function: Optional[str] = Field(description="Default reward function")
    log_level: Optional[str] = Field(description="Logging level")
    cleanup_after_days: Optional[int] = Field(ge=1, le=365, description="File cleanup days")


class ConfigurationStatus(BaseModel):
    """Current configuration status."""
    
    is_valid: bool = Field(description="Whether configuration is valid")
    carla_available: bool = Field(description="Whether CARLA is accessible")
    apollo_available: bool = Field(description="Whether Apollo container is available")
    parameter_ranges_loaded: bool = Field(description="Whether parameter ranges are loaded")
    output_directory_writable: bool = Field(description="Whether output directory is writable")
    errors: List[str] = Field(default=[], description="Configuration errors")
    warnings: List[str] = Field(default=[], description="Configuration warnings")


class ParameterRangeImport(BaseModel):
    """Import parameter ranges from file."""
    
    file_content: str = Field(description="YAML file content")
    override_existing: bool = Field(default=False, description="Override existing ranges")
    validate_only: bool = Field(default=False, description="Only validate, don't import")


class ParameterRangeExport(BaseModel):
    """Export parameter ranges configuration."""
    
    scenario_types: Optional[List[str]] = Field(description="Scenario types to export")
    include_defaults: bool = Field(default=True, description="Include default parameters")
    format: str = Field(default="yaml", description="Export format (yaml/json)")


class RewardFunctionConfig(BaseModel):
    """Configuration for reward functions."""
    
    name: str = Field(description="Reward function name")
    description: str = Field(description="Function description")
    parameters: Dict[str, Any] = Field(default={}, description="Function parameters")
    is_default: bool = Field(default=False, description="Whether this is the default function")
    is_active: bool = Field(default=True, description="Whether this function is available")


class SearchMethodConfig(BaseModel):
    """Configuration for search methods."""
    
    name: str = Field(description="Search method name")
    description: str = Field(description="Method description")
    default_parameters: Dict[str, Any] = Field(description="Default method parameters")
    parameter_ranges: Dict[str, Tuple[float, float]] = Field(
        description="Valid ranges for method parameters"
    )
    is_available: bool = Field(description="Whether method is available")
    requires_library: Optional[str] = Field(description="Required library if any")


class SystemInfo(BaseModel):
    """System information and status."""
    
    version: str = Field(description="Framework version")
    carla_version: Optional[str] = Field(description="CARLA version if available")
    python_version: str = Field(description="Python version")
    available_search_methods: List[SearchMethodConfig] = Field(description="Available search methods")
    available_reward_functions: List[RewardFunctionConfig] = Field(description="Available reward functions")
    system_status: ConfigurationStatus = Field(description="System status")
    uptime: float = Field(description="Server uptime in seconds")
    active_experiments: int = Field(description="Number of active experiments") 