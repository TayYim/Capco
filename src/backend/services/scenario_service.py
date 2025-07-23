"""
Scenario service for handling scenario discovery and validation.

This service provides methods for discovering scenarios from XML files,
parsing route information, and validating experiment configurations.
"""

import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Optional, Dict, Any
import logging
from datetime import datetime

from models.scenario import (
    ScenarioInfo, RouteInfo, RouteListItem, RouteFileInfo,
    ScenarioValidation, ScenarioSearch, ScenarioStatistics,
    ParameterInfo, ParameterValidation
)
from models.experiment import ExperimentConfig
from core.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


class ScenarioService:
    """Service for managing scenarios and route information."""
    
    def __init__(self):
        # Path to leaderboard data directory
        self.data_dir = Path(settings.project_root) / "dependencies" / "leaderboard" / "data"
        self._cached_routes: Dict[str, Any] = {}
        self._cache_timestamp: Optional[datetime] = None
        
    async def list_route_files(self) -> List[RouteFileInfo]:
        """
        List all available route XML files.
        
        Returns:
            List of route file information
        """
        try:
            route_files = []
            
            if not self.data_dir.exists():
                logger.warning(f"Data directory not found: {self.data_dir}")
                return []
            
            # Find all XML files
            for xml_file in self.data_dir.glob("*.xml"):
                try:
                    routes = await self._parse_route_file(xml_file.name)
                    
                    route_file_info = RouteFileInfo(
                        filename=xml_file.stem,
                        routes=[
                            RouteListItem(
                                route_id=route["route_id"],
                                route_name=route.get("route_name"),
                                route_file=xml_file.stem,
                                town=route.get("town"),
                                scenario_count=len(route.get("scenarios", [])),
                                fuzzable_parameter_count=route.get("fuzzable_parameter_count", 0),
                                primary_scenario_type=route.get("primary_scenario_type")
                            )
                            for route in routes
                        ],
                        total_routes=len(routes),
                        file_path=str(xml_file),
                        last_modified=datetime.fromtimestamp(xml_file.stat().st_mtime).isoformat()
                    )
                    
                    route_files.append(route_file_info)
                    
                except Exception as e:
                    logger.error(f"Error parsing route file {xml_file}: {e}")
                    continue
            
            return route_files
            
        except Exception as e:
            logger.error(f"Error listing route files: {e}")
            return []
    
    async def list_routes(self, route_file: str) -> List[RouteListItem]:
        """
        List all routes in a specific route file.
        
        Args:
            route_file: Name of the route file
            
        Returns:
            List of route summaries
        """
        try:
            routes = await self._parse_route_file(route_file + ".xml")
            
            return [
                RouteListItem(
                    route_id=route["route_id"],
                    route_name=route.get("route_name"),
                    route_file=route_file,
                    town=route.get("town"),
                    scenario_count=len(route.get("scenarios", [])),
                    fuzzable_parameter_count=route.get("fuzzable_parameter_count", 0),
                    primary_scenario_type=route.get("primary_scenario_type")
                )
                for route in routes
            ]
            
        except Exception as e:
            logger.error(f"Error listing routes for {route_file}: {e}")
            return []
    
    async def get_route_info(self, route_file: str, route_id: str) -> Optional[RouteInfo]:
        """
        Get detailed information about a specific route.
        
        Args:
            route_file: Name of the route file
            route_id: ID of the route
            
        Returns:
            Detailed route information if found
        """
        try:
            file_path = self.data_dir / f"{route_file}.xml"
            if not file_path.exists():
                return None
            
            tree = ET.parse(file_path)
            root = tree.getroot()
            
            # Find the specific route
            route_element = None
            for route in root.findall(".//route"):
                if route.get("id") == str(route_id):
                    route_element = route
                    break
            
            if route_element is None:
                return None
            
            # Parse scenarios
            scenarios = []
            total_fuzzable_params = 0
            
            for scenario_element in route_element.findall(".//scenario"):
                scenario_info = self._parse_scenario_element(scenario_element)
                scenarios.append(scenario_info)
                total_fuzzable_params += len(scenario_info.fuzzable_parameters)
            
            # Extract waypoints if available
            waypoints = []
            for waypoint in route_element.findall(".//waypoint"):
                try:
                    waypoints.append({
                        "x": float(waypoint.get("x", 0)),
                        "y": float(waypoint.get("y", 0)),
                        "z": float(waypoint.get("z", 0))
                    })
                except (ValueError, TypeError):
                    continue
            
            # Extract weather information
            weather = {}
            weather_element = route_element.find(".//weather")
            if weather_element is not None:
                weather = {attr: weather_element.get(attr) for attr in weather_element.attrib}
            
            return RouteInfo(
                route_id=route_id,
                route_name=route_element.get("name"),
                route_file=route_file,
                town=route_element.get("town"),
                scenarios=scenarios,
                total_fuzzable_parameters=total_fuzzable_params,
                waypoints=waypoints if waypoints else None,
                distance=None,  # Distance calculation would be implemented here
                weather=weather if weather else None,
                time_of_day=route_element.get("time_of_day")
            )
            
        except Exception as e:
            logger.error(f"Error getting route info for {route_file}/{route_id}: {e}")
            return None
    
    async def validate_experiment_config(
        self, 
        route_file: str, 
        route_id: str, 
        config: ExperimentConfig
    ) -> ScenarioValidation:
        """
        Validate experiment configuration for a specific scenario.
        
        Args:
            route_file: Route file name
            route_id: Route ID
            config: Experiment configuration
            
        Returns:
            Validation result
        """
        try:
            route_info = await self.get_route_info(route_file, route_id)
            
            if not route_info:
                return ScenarioValidation(
                    is_valid=False,
                    parameter_validations=[],
                    missing_parameters=[],
                    warnings=[],
                    errors=[f"Route {route_id} not found in {route_file}"]
                )
            
            parameter_validations = []
            warnings = []
            errors = []
            
            # Validate parameter overrides if provided
            if config.parameter_overrides:
                available_params = {
                    param.name for scenario in route_info.scenarios 
                    for param in scenario.fuzzable_parameters
                }
                
                for param_name, (min_val, max_val) in config.parameter_overrides.items():
                    if param_name not in available_params:
                        parameter_validations.append(ParameterValidation(
                            parameter_name=param_name,
                            is_valid=False,
                            error_message=f"Parameter {param_name} not found in route",
                            suggested_value=None
                        ))
                    elif min_val >= max_val:
                        parameter_validations.append(ParameterValidation(
                            parameter_name=param_name,
                            is_valid=False,
                            error_message=f"Invalid range: min ({min_val}) >= max ({max_val})",
                            suggested_value=None
                        ))
                    else:
                        parameter_validations.append(ParameterValidation(
                            parameter_name=param_name,
                            is_valid=True,
                            error_message=None,
                            suggested_value=None
                        ))
            
            # Validate search method parameters
            if config.search_method == "pso":
                if not config.pso_pop_size or config.pso_pop_size < 1:
                    warnings.append("PSO population size should be at least 1")
                if not config.pso_w or config.pso_w <= 0:
                    errors.append("PSO inertia weight must be positive")
            
            elif config.search_method == "ga":
                if not config.ga_pop_size or config.ga_pop_size < 1:
                    warnings.append("GA population size should be at least 1")
                if not config.ga_prob_mut or config.ga_prob_mut <= 0:
                    errors.append("GA mutation probability must be positive")
            
            # Check if route has fuzzable parameters
            if route_info.total_fuzzable_parameters == 0:
                warnings.append("Route has no fuzzable parameters")
            
            # Validate timeout
            if config.timeout_seconds < 60:
                warnings.append("Timeout less than 60 seconds may cause premature termination")
            
            is_valid = len(errors) == 0 and all(pv.is_valid for pv in parameter_validations)
            
            return ScenarioValidation(
                is_valid=is_valid,
                parameter_validations=parameter_validations,
                missing_parameters=[],
                warnings=warnings,
                errors=errors
            )
            
        except Exception as e:
            logger.error(f"Error validating config: {e}")
            return ScenarioValidation(
                is_valid=False,
                parameter_validations=[],
                missing_parameters=[],
                warnings=[],
                errors=[f"Validation error: {str(e)}"]
            )
    
    async def search_scenarios(
        self, 
        search_criteria: ScenarioSearch, 
        limit: int = 50, 
        offset: int = 0
    ) -> List[RouteListItem]:
        """
        Search for scenarios based on criteria.
        
        Args:
            search_criteria: Search criteria
            limit: Maximum results
            offset: Offset for pagination
            
        Returns:
            List of matching routes
        """
        try:
            all_routes = []
            
            # Get routes from specific file or all files
            if search_criteria.route_file:
                routes = await self.list_routes(search_criteria.route_file)
                all_routes.extend(routes)
            else:
                route_files = await self.list_route_files()
                for route_file_info in route_files:
                    all_routes.extend(route_file_info.routes)
            
            # Apply filters
            filtered_routes = []
            for route in all_routes:
                # Get detailed info for filtering
                route_info = await self.get_route_info(route.route_file, route.route_id)
                if not route_info:
                    continue
                
                # Apply scenario type filter
                if search_criteria.scenario_type:
                    scenario_types = {s.type for s in route_info.scenarios}
                    if search_criteria.scenario_type not in scenario_types:
                        continue
                
                # Apply town filter
                if search_criteria.town and route_info.town != search_criteria.town:
                    continue
                
                # Apply minimum parameters filter
                if search_criteria.min_parameters:
                    if route_info.total_fuzzable_parameters < search_criteria.min_parameters:
                        continue
                
                # Apply parameter names filter
                if search_criteria.parameter_names:
                    available_params = {
                        param.name for scenario in route_info.scenarios 
                        for param in scenario.fuzzable_parameters
                    }
                    if not all(name in available_params for name in search_criteria.parameter_names):
                        continue
                
                filtered_routes.append(route)
            
            # Apply pagination
            start_idx = offset
            end_idx = offset + limit
            return filtered_routes[start_idx:end_idx]
            
        except Exception as e:
            logger.error(f"Error searching scenarios: {e}")
            return []
    
    async def get_scenario_statistics(self, route_file: Optional[str] = None) -> ScenarioStatistics:
        """
        Get statistics about available scenarios.
        
        Args:
            route_file: Optional specific route file
            
        Returns:
            Scenario statistics
        """
        try:
            route_files_to_process = []
            
            if route_file:
                route_files_to_process = [route_file]
            else:
                route_file_infos = await self.list_route_files()
                route_files_to_process = [rf.filename for rf in route_file_infos]
            
            total_routes = 0
            total_scenarios = 0
            scenario_types = {}
            parameter_stats = {}
            towns = set()
            
            for rf in route_files_to_process:
                routes = await self.list_routes(rf)
                total_routes += len(routes)
                
                for route in routes:
                    route_info = await self.get_route_info(rf, route.route_id)
                    if not route_info:
                        continue
                    
                    total_scenarios += len(route_info.scenarios)
                    
                    if route_info.town:
                        towns.add(route_info.town)
                    
                    for scenario in route_info.scenarios:
                        # Count scenario types
                        scenario_types[scenario.type] = scenario_types.get(scenario.type, 0) + 1
                        
                        # Collect parameter statistics
                        for param in scenario.fuzzable_parameters:
                            if param.name not in parameter_stats:
                                parameter_stats[param.name] = {
                                    "usage_count": 0,
                                    "values": [],
                                    "scenarios": set()
                                }
                            
                            parameter_stats[param.name]["usage_count"] += 1
                            parameter_stats[param.name]["values"].append(param.value)
                            parameter_stats[param.name]["scenarios"].add(scenario.name)
            
            # Convert parameter stats to proper format
            from models.scenario import ParameterStatistics
            parameter_statistics = []
            for param_name, stats in parameter_stats.items():
                values = stats["values"]
                parameter_statistics.append(ParameterStatistics(
                    parameter_name=param_name,
                    usage_count=stats["usage_count"],
                    min_value=min(values) if values else 0,
                    max_value=max(values) if values else 0,
                    mean_value=sum(values) / len(values) if values else 0,
                    scenarios=list(stats["scenarios"])
                ))
            
            return ScenarioStatistics(
                total_routes=total_routes,
                total_scenarios=total_scenarios,
                scenario_types=scenario_types,
                parameter_statistics=parameter_statistics,
                towns=list(towns),
                route_files=route_files_to_process
            )
            
        except Exception as e:
            logger.error(f"Error getting scenario statistics: {e}")
            # Return basic statistics anyway
            try:
                route_file_infos = await self.list_route_files()
                return ScenarioStatistics(
                    total_routes=sum(rf.total_routes for rf in route_file_infos),
                    total_scenarios=0,
                    scenario_types={},
                    parameter_statistics=[],
                    towns=[],
                    route_files=[rf.filename for rf in route_file_infos]
                )
            except:
                return ScenarioStatistics(
                    total_routes=0,
                    total_scenarios=0,
                    scenario_types={},
                    parameter_statistics=[],
                    towns=[],
                    route_files=[]
                )
    
    async def get_fuzzable_parameters(self, route_file: str, route_id: str) -> Optional[List[ParameterInfo]]:
        """
        Get fuzzable parameters for a specific route.
        
        Args:
            route_file: Route file name
            route_id: Route ID
            
        Returns:
            List of fuzzable parameters
        """
        route_info = await self.get_route_info(route_file, route_id)
        if not route_info:
            return None
        
        parameters = []
        for scenario in route_info.scenarios:
            parameters.extend(scenario.fuzzable_parameters)
        
        return parameters
    
    async def get_scenario_xml_preview(self, route_file: str, route_id: str) -> Optional[str]:
        """
        Get XML preview for a specific route.
        
        Args:
            route_file: Route file name
            route_id: Route ID
            
        Returns:
            XML content as string
        """
        try:
            file_path = self.data_dir / f"{route_file}.xml"
            if not file_path.exists():
                return None
            
            tree = ET.parse(file_path)
            root = tree.getroot()
            
            # Find the specific route
            for route in root.findall(".//route"):
                if route.get("id") == str(route_id):
                    return ET.tostring(route, encoding='unicode')
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting XML preview: {e}")
            return None
    
    async def get_scenario_types(self) -> List[str]:
        """Get list of all available scenario types."""
        try:
            scenario_types = set()
            route_files = await self.list_route_files()
            
            for route_file_info in route_files:
                for route in route_file_info.routes:
                    route_info = await self.get_route_info(route_file_info.filename, route.route_id)
                    if route_info:
                        for scenario in route_info.scenarios:
                            scenario_types.add(scenario.type)
            
            return sorted(list(scenario_types))
            
        except Exception as e:
            logger.error(f"Error getting scenario types: {e}")
            return []
    
    async def get_available_towns(self) -> List[str]:
        """Get list of all available CARLA towns."""
        try:
            towns = set()
            route_files = await self.list_route_files()
            
            for route_file_info in route_files:
                for route in route_file_info.routes:
                    if route.town:
                        towns.add(route.town)
            
            return sorted(list(towns))
            
        except Exception as e:
            logger.error(f"Error getting available towns: {e}")
            return []
    
    async def _parse_route_file(self, filename: str) -> List[Dict[str, Any]]:
        """Parse a route XML file and extract route information."""
        file_path = self.data_dir / filename
        if not file_path.exists():
            return []
        
        try:
            tree = ET.parse(file_path)
            root = tree.getroot()
            
            routes = []
            for route_element in root.findall(".//route"):
                route_id = route_element.get("id")
                if not route_id:
                    continue
                
                # Extract route name from XML (new feature)
                route_name = route_element.get("name")
                
                scenarios = []
                fuzzable_param_count = 0
                primary_scenario_type = None
                
                for scenario_element in route_element.findall(".//scenario"):
                    scenario_info = self._parse_scenario_element(scenario_element)
                    scenarios.append(scenario_info)
                    fuzzable_param_count += len(scenario_info.fuzzable_parameters)
                    
                    # Set primary scenario type (first non-data-collection scenario)
                    if not primary_scenario_type and "Data_Collect" not in scenario_info.type:
                        primary_scenario_type = scenario_info.type
                
                routes.append({
                    "route_id": route_id,
                    "route_name": route_name,  # Include route name
                    "town": route_element.get("town"),
                    "scenarios": scenarios,
                    "fuzzable_parameter_count": fuzzable_param_count,
                    "primary_scenario_type": primary_scenario_type
                })
            
            return routes
            
        except Exception as e:
            logger.error(f"Error parsing route file {filename}: {e}")
            return []
    
    def _parse_scenario_element(self, scenario_element) -> ScenarioInfo:
        """Parse a scenario XML element."""
        scenario_name = scenario_element.get("name", "Unknown")
        scenario_type = scenario_element.get("type", "Unknown")
        
        # Extract all parameters
        parameters = {}
        for attr, value in scenario_element.attrib.items():
            if attr not in ["name", "type"]:
                parameters[attr] = value
        
        # Find fuzzable parameters (numeric parameters that can be varied)
        fuzzable_parameters = []
        parameter_elements = ['absolute_v', 'relative_p', 'relative_v', 
                            'relative_p_1', 'relative_v_1', 'relative_p_2', 'relative_v_2',
                            'r_ego', 'v_ego', 'r_1', 'v_1', 'r_2', 'v_2']
        
        for param_name in parameter_elements:
            param_element = scenario_element.find(param_name)
            if param_element is not None:
                param_value = param_element.get("value")
                if param_value:
                    try:
                        numeric_value = float(param_value)
                        fuzzable_parameters.append(ParameterInfo(
                            name=param_name,
                            value=numeric_value,
                            scenario=scenario_type,
                            scenario_instance=scenario_name,
                            min_range=None,
                            max_range=None,
                            description=f"Parameter {param_name} from {scenario_type}",
                            unit=None
                        ))
                    except ValueError:
                        continue
        
        return ScenarioInfo(
            name=scenario_name,
            type=scenario_type,
            parameters=parameters,
            fuzzable_parameters=fuzzable_parameters,
            description=f"Scenario of type {scenario_type}"
        )


# Dependency injection
_scenario_service = None

def get_scenario_service() -> ScenarioService:
    """Get scenario service instance."""
    global _scenario_service
    if _scenario_service is None:
        _scenario_service = ScenarioService()
    return _scenario_service 