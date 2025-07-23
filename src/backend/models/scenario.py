"""
Pydantic models for scenario-related API data.

Defines the data structures for scenario information,
route details, and parameter specifications.
"""

from typing import Dict, List, Optional, Any, Tuple
from pydantic import BaseModel, Field


class ParameterInfo(BaseModel):
    """Information about a fuzzable parameter."""
    
    name: str = Field(description="Parameter name")
    value: float = Field(description="Current/default value")
    scenario: str = Field(description="Scenario that contains this parameter")
    scenario_instance: str = Field(description="Specific scenario instance name")
    min_range: Optional[float] = Field(description="Minimum allowed value")
    max_range: Optional[float] = Field(description="Maximum allowed value")
    description: Optional[str] = Field(description="Parameter description")
    unit: Optional[str] = Field(description="Parameter unit")


class ScenarioInfo(BaseModel):
    """Information about a scenario within a route."""
    
    name: str = Field(description="Scenario instance name")
    type: str = Field(description="Scenario type")
    parameters: Dict[str, Any] = Field(description="Scenario parameters")
    fuzzable_parameters: List[ParameterInfo] = Field(
        default=[], 
        description="Parameters available for fuzzing"
    )
    description: Optional[str] = Field(description="Scenario description")


class RouteInfo(BaseModel):
    """Information about a specific route."""
    
    route_id: str = Field(description="Route identifier")
    route_name: Optional[str] = Field(description="Human-readable route name")
    route_file: str = Field(description="Route file name")
    town: Optional[str] = Field(description="CARLA town name")
    scenarios: List[ScenarioInfo] = Field(description="Scenarios in this route")
    total_fuzzable_parameters: int = Field(description="Total number of fuzzable parameters")
    waypoints: Optional[List[Dict[str, float]]] = Field(
        description="Route waypoints (x, y, z coordinates)"
    )
    
    # Route metadata
    distance: Optional[float] = Field(description="Total route distance in meters")
    weather: Optional[Dict[str, Any]] = Field(description="Weather conditions")
    time_of_day: Optional[str] = Field(description="Time of day setting")


class RouteListItem(BaseModel):
    """Summary information for route list views."""
    
    route_id: str = Field(description="Route identifier")
    route_name: Optional[str] = Field(description="Human-readable route name")
    route_file: str = Field(description="Route file name")
    town: Optional[str] = Field(description="CARLA town name")
    scenario_count: int = Field(description="Number of scenarios")
    fuzzable_parameter_count: int = Field(description="Number of fuzzable parameters")
    primary_scenario_type: Optional[str] = Field(description="Main scenario type")


class RouteFileInfo(BaseModel):
    """Information about a route file."""
    
    filename: str = Field(description="Route file name")
    routes: List[RouteListItem] = Field(description="Routes in this file")
    total_routes: int = Field(description="Total number of routes")
    file_path: str = Field(description="Full file path")
    last_modified: Optional[str] = Field(description="Last modification time")


class ParameterValidation(BaseModel):
    """Validation result for parameter values."""
    
    parameter_name: str = Field(description="Parameter name")
    is_valid: bool = Field(description="Whether the value is valid")
    error_message: Optional[str] = Field(description="Error message if invalid")
    suggested_value: Optional[float] = Field(description="Suggested valid value")


class ScenarioValidation(BaseModel):
    """Validation result for scenario configuration."""
    
    is_valid: bool = Field(description="Whether the scenario is valid")
    parameter_validations: List[ParameterValidation] = Field(
        description="Individual parameter validations"
    )
    missing_parameters: List[str] = Field(
        default=[], 
        description="Required parameters that are missing"
    )
    warnings: List[str] = Field(
        default=[], 
        description="Non-critical warnings"
    )
    errors: List[str] = Field(
        default=[], 
        description="Critical errors"
    )


class ScenarioSearch(BaseModel):
    """Search criteria for finding scenarios."""
    
    scenario_type: Optional[str] = Field(description="Filter by scenario type")
    town: Optional[str] = Field(description="Filter by town")
    min_parameters: Optional[int] = Field(description="Minimum number of fuzzable parameters")
    parameter_names: Optional[List[str]] = Field(description="Required parameter names")
    route_file: Optional[str] = Field(description="Filter by route file")


class ParameterStatistics(BaseModel):
    """Statistics about parameter usage across scenarios."""
    
    parameter_name: str = Field(description="Parameter name")
    usage_count: int = Field(description="Number of scenarios using this parameter")
    min_value: float = Field(description="Minimum value across scenarios")
    max_value: float = Field(description="Maximum value across scenarios")
    mean_value: float = Field(description="Mean value across scenarios")
    scenarios: List[str] = Field(description="Scenarios that use this parameter")


class ScenarioStatistics(BaseModel):
    """Overall statistics about available scenarios."""
    
    total_routes: int = Field(description="Total number of routes")
    total_scenarios: int = Field(description="Total number of scenarios")
    scenario_types: Dict[str, int] = Field(description="Count by scenario type")
    parameter_statistics: List[ParameterStatistics] = Field(
        description="Statistics for each parameter"
    )
    towns: List[str] = Field(description="Available towns")
    route_files: List[str] = Field(description="Available route files") 