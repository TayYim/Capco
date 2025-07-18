"""
Parameter service for handling system configuration and parameter ranges.

This service manages system-wide settings, parameter ranges for fuzzing,
and configuration validation.
"""

import yaml
import json
import sys
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple
import logging
from datetime import datetime

from models.configuration import (
    SystemConfiguration, ConfigurationUpdate, ConfigurationStatus,
    ParameterRange, ParameterRangeUpdate, ParameterRangeImport,
    ParameterRangeExport, SystemInfo, RewardFunctionConfig,
    SearchMethodConfig
)
from core.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


class ParameterService:
    """Service for managing system configuration and parameter ranges."""
    
    def __init__(self):
        self.config_dir = Path(settings.project_root) / "config"
        self.parameter_ranges_file = self.config_dir / "parameter_ranges.yaml"
        self._cached_ranges: Optional[Dict[str, Any]] = None
        self._cache_timestamp: Optional[datetime] = None
        
        # Initialize parameter ranges if not exists
        self._ensure_parameter_ranges_file()
    
    async def get_system_configuration(self) -> SystemConfiguration:
        """
        Get current system configuration.
        
        Returns:
            System configuration
        """
        try:
            return SystemConfiguration(
                carla_path=settings.carla_path,
                default_timeout=settings.default_timeout,
                restart_gap=5,  # Default restart gap
                max_concurrent_experiments=settings.max_concurrent_experiments,
                default_iterations=10,  # Default iterations
                default_search_method="random",
                default_reward_function="ttc",
                output_directory=settings.output_dir,
                max_file_size=settings.max_file_size,
                cleanup_after_days=30,
                enable_headless=True,
                log_level=settings.log_level,
                session_timeout=3600
            )
        except Exception as e:
            logger.error(f"Error getting system configuration: {e}")
            # Return default configuration
            return SystemConfiguration(
                carla_path="/path/to/carla",
                default_timeout=300,
                restart_gap=5,
                max_concurrent_experiments=1,
                default_iterations=10,
                default_search_method="random",
                default_reward_function="ttc",
                output_directory="output",
                max_file_size=100 * 1024 * 1024,
                cleanup_after_days=30,
                enable_headless=True,
                log_level="INFO",
                session_timeout=3600
            )
    
    async def update_system_configuration(self, update: ConfigurationUpdate) -> SystemConfiguration:
        """
        Update system configuration.
        
        Args:
            update: Configuration updates
            
        Returns:
            Updated system configuration
        """
        try:
            # Here you would typically update a configuration file
            # For now, we'll return the current configuration with updates applied
            current_config = await self.get_system_configuration()
            
            # Apply updates
            if update.carla_path is not None:
                current_config.carla_path = update.carla_path
            if update.default_timeout is not None:
                current_config.default_timeout = update.default_timeout
            if update.max_concurrent_experiments is not None:
                current_config.max_concurrent_experiments = update.max_concurrent_experiments
            if update.default_iterations is not None:
                current_config.default_iterations = update.default_iterations
            if update.default_search_method is not None:
                current_config.default_search_method = update.default_search_method
            if update.default_reward_function is not None:
                current_config.default_reward_function = update.default_reward_function
            if update.log_level is not None:
                current_config.log_level = update.log_level
            if update.cleanup_after_days is not None:
                current_config.cleanup_after_days = update.cleanup_after_days
            
            logger.info("System configuration updated")
            return current_config
            
        except Exception as e:
            logger.error(f"Error updating system configuration: {e}")
            raise
    
    async def get_configuration_status(self) -> ConfigurationStatus:
        """
        Get configuration validation status.
        
        Returns:
            Configuration status with validation results
        """
        try:
            errors = []
            warnings = []
            
            # Check CARLA availability
            carla_available = False
            carla_path = Path(settings.carla_path)
            if carla_path.exists():
                carla_executable = carla_path / "CarlaUE4.sh"
                if carla_executable.exists():
                    carla_available = True
                else:
                    errors.append(f"CARLA executable not found at {carla_executable}")
            else:
                errors.append(f"CARLA path does not exist: {carla_path}")
            
            # Check parameter ranges
            parameter_ranges_loaded = False
            try:
                await self.get_parameter_ranges()
                parameter_ranges_loaded = True
            except Exception as e:
                errors.append(f"Error loading parameter ranges: {e}")
            
            # Check output directory
            output_directory_writable = False
            output_dir = Path(settings.output_dir)
            try:
                output_dir.mkdir(parents=True, exist_ok=True)
                test_file = output_dir / "test_write"
                test_file.touch()
                test_file.unlink()
                output_directory_writable = True
            except Exception as e:
                errors.append(f"Output directory not writable: {e}")
            
            # Check for optional dependencies (avoid multiprocessing context issues)
            try:
                import importlib.util
                spec = importlib.util.find_spec("sko")
                if spec is None:
                    warnings.append("scikit-opt not available - PSO and GA search methods disabled")
            except Exception:
                warnings.append("Could not check scikit-opt availability")
            
            is_valid = len(errors) == 0
            
            return ConfigurationStatus(
                is_valid=is_valid,
                carla_available=carla_available,
                parameter_ranges_loaded=parameter_ranges_loaded,
                output_directory_writable=output_directory_writable,
                errors=errors,
                warnings=warnings
            )
            
        except Exception as e:
            logger.error(f"Error getting configuration status: {e}")
            return ConfigurationStatus(
                is_valid=False,
                carla_available=False,
                parameter_ranges_loaded=False,
                output_directory_writable=False,
                errors=[f"Configuration check failed: {e}"],
                warnings=[]
            )
    
    async def get_parameter_ranges(self, scenario_type: Optional[str] = None) -> List[ParameterRange]:
        """
        Get parameter ranges configuration.
        
        Args:
            scenario_type: Optional filter by scenario type
            
        Returns:
            List of parameter ranges
        """
        try:
            ranges_data = self._load_parameter_ranges()
            parameter_ranges = []
            
            # Handle the current YAML format with parameter_types
            if "parameter_types" in ranges_data:
                # Process parameter_types structure
                for category, params in ranges_data["parameter_types"].items():
                    for param_name, range_values in params.items():
                        if isinstance(range_values, list) and len(range_values) >= 2:
                            parameter_ranges.append(ParameterRange(
                                parameter_name=param_name,
                                min_value=float(range_values[0]),
                                max_value=float(range_values[1]),
                                default_value=(float(range_values[0]) + float(range_values[1])) / 2,
                                description=f"{category.title()} parameter {param_name}",
                                unit="m/s" if category == "velocity" else "m" if category == "position" else "s",
                                scenario_type=None
                            ))
            
            # Handle legacy default format
            default_ranges = ranges_data.get("default", {})
            for param_name, range_config in default_ranges.items():
                if isinstance(range_config, dict):
                    parameter_ranges.append(ParameterRange(
                        parameter_name=param_name,
                        min_value=range_config["min"],
                        max_value=range_config["max"],
                        default_value=range_config.get("default"),
                        description=range_config.get("description"),
                        unit=range_config.get("unit"),
                        scenario_type=None
                    ))
            
            # Get scenario-specific ranges
            scenario_overrides = ranges_data.get("scenario_overrides", {})
            if scenario_type and scenario_type in scenario_overrides:
                for param_name, range_values in scenario_overrides[scenario_type].items():
                    if isinstance(range_values, list) and len(range_values) >= 2:
                        parameter_ranges.append(ParameterRange(
                            parameter_name=param_name,
                            min_value=float(range_values[0]),
                            max_value=float(range_values[1]),
                            default_value=(float(range_values[0]) + float(range_values[1])) / 2,
                            description=f"Override for {scenario_type} scenario",
                            unit=None,
                            scenario_type=scenario_type
                        ))
                    elif isinstance(range_values, dict):
                        parameter_ranges.append(ParameterRange(
                            parameter_name=param_name,
                            min_value=range_values["min"],
                            max_value=range_values["max"],
                            default_value=range_values.get("default"),
                            description=range_values.get("description"),
                            unit=range_values.get("unit"),
                            scenario_type=scenario_type
                        ))
            elif not scenario_type:
                # Include all scenario-specific ranges
                for st, params in scenario_overrides.items():
                    for param_name, range_values in params.items():
                        if isinstance(range_values, list) and len(range_values) >= 2:
                            parameter_ranges.append(ParameterRange(
                                parameter_name=param_name,
                                min_value=float(range_values[0]),
                                max_value=float(range_values[1]),
                                default_value=(float(range_values[0]) + float(range_values[1])) / 2,
                                description=f"Override for {st} scenario",
                                unit=None,
                                scenario_type=st
                            ))
                        elif isinstance(range_values, dict):
                            parameter_ranges.append(ParameterRange(
                                parameter_name=param_name,
                                min_value=range_values["min"],
                                max_value=range_values["max"],
                                default_value=range_values.get("default"),
                                description=range_values.get("description"),
                                unit=range_values.get("unit"),
                                scenario_type=st
                            ))
            
            return parameter_ranges
            
        except Exception as e:
            logger.error(f"Error getting parameter ranges: {e}")
            return []
    
    async def update_parameter_ranges(self, update: ParameterRangeUpdate) -> List[ParameterRange]:
        """
        Update parameter ranges.
        
        Args:
            update: Parameter range updates
            
        Returns:
            Updated parameter ranges
        """
        try:
            ranges_data = self._load_parameter_ranges()
            
            for param_name, (min_val, max_val) in update.ranges.items():
                range_config = {
                    "min": min_val,
                    "max": max_val,
                    "description": f"Range for {param_name}"
                }
                
                if update.apply_globally or not update.scenario_type:
                    # Update default ranges
                    if "default" not in ranges_data:
                        ranges_data["default"] = {}
                    ranges_data["default"][param_name] = range_config
                else:
                    # Update scenario-specific ranges
                    if "scenario_overrides" not in ranges_data:
                        ranges_data["scenario_overrides"] = {}
                    if update.scenario_type not in ranges_data["scenario_overrides"]:
                        ranges_data["scenario_overrides"][update.scenario_type] = {}
                    ranges_data["scenario_overrides"][update.scenario_type][param_name] = range_config
            
            # Save updated ranges
            self._save_parameter_ranges(ranges_data)
            
            # Return updated ranges
            return await self.get_parameter_ranges(update.scenario_type)
            
        except Exception as e:
            logger.error(f"Error updating parameter ranges: {e}")
            raise
    
    async def import_parameter_ranges(self, import_data: ParameterRangeImport) -> Dict[str, Any]:
        """
        Import parameter ranges from YAML content.
        
        Args:
            import_data: Import configuration and content
            
        Returns:
            Import result
        """
        try:
            # Parse YAML content
            imported_ranges = yaml.safe_load(import_data.file_content)
            
            if import_data.validate_only:
                # Just validate without importing
                self._validate_parameter_ranges_format(imported_ranges)
                return {
                    "status": "valid",
                    "message": "Parameter ranges format is valid",
                    "imported_count": 0
                }
            
            if import_data.override_existing:
                # Replace existing ranges
                self._save_parameter_ranges(imported_ranges)
            else:
                # Merge with existing ranges
                existing_ranges = self._load_parameter_ranges()
                merged_ranges = self._merge_parameter_ranges(existing_ranges, imported_ranges)
                self._save_parameter_ranges(merged_ranges)
            
            # Count imported parameters
            imported_count = 0
            if "default" in imported_ranges:
                imported_count += len(imported_ranges["default"])
            if "scenario_overrides" in imported_ranges:
                for scenario_params in imported_ranges["scenario_overrides"].values():
                    imported_count += len(scenario_params)
            
            return {
                "status": "success",
                "message": f"Successfully imported {imported_count} parameter ranges",
                "imported_count": imported_count
            }
            
        except Exception as e:
            logger.error(f"Error importing parameter ranges: {e}")
            return {
                "status": "error",
                "message": f"Import failed: {str(e)}",
                "imported_count": 0
            }
    
    async def export_parameter_ranges(self, export_data: ParameterRangeExport) -> Tuple[str, str]:
        """
        Export parameter ranges to file content.
        
        Args:
            export_data: Export configuration
            
        Returns:
            Tuple of (content, filename)
        """
        try:
            ranges_data = self._load_parameter_ranges()
            
            # Filter by scenario types if specified
            if export_data.scenario_types:
                filtered_data = {}
                if export_data.include_defaults and "default" in ranges_data:
                    filtered_data["default"] = ranges_data["default"]
                
                if "scenario_overrides" in ranges_data:
                    filtered_overrides = {}
                    for scenario_type in export_data.scenario_types:
                        if scenario_type in ranges_data["scenario_overrides"]:
                            filtered_overrides[scenario_type] = ranges_data["scenario_overrides"][scenario_type]
                    if filtered_overrides:
                        filtered_data["scenario_overrides"] = filtered_overrides
                
                ranges_data = filtered_data
            
            # Generate content
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            if export_data.format == "json":
                content = json.dumps(ranges_data, indent=2)
                filename = f"parameter_ranges_{timestamp}.json"
            else:  # yaml
                content = yaml.dump(ranges_data, default_flow_style=False, indent=2)
                filename = f"parameter_ranges_{timestamp}.yaml"
            
            return content, filename
            
        except Exception as e:
            logger.error(f"Error exporting parameter ranges: {e}")
            raise
    
    async def get_system_info(self) -> SystemInfo:
        """
        Get comprehensive system information.
        
        Returns:
            System information including available methods and status
        """
        try:
            # Get search methods
            search_methods = []
            
            # Random search (always available)
            search_methods.append(SearchMethodConfig(
                name="random",
                description="Random search baseline",
                default_parameters={"iterations": 10},
                parameter_ranges={"iterations": (1, 1000)},
                is_available=True,
                requires_library=None
            ))
            
            # Check for scikit-opt (handle multiprocessing context issues)
            sko_available = False
            try:
                import importlib.util
                spec = importlib.util.find_spec("sko")
                sko_available = spec is not None
            except Exception:
                sko_available = False
            
            if sko_available:
                search_methods.extend([
                    SearchMethodConfig(
                        name="pso",
                        description="Particle Swarm Optimization",
                        default_parameters={
                            "pop_size": 20,
                            "w": 0.8,
                            "c1": 0.5,
                            "c2": 0.5
                        },
                        parameter_ranges={
                            "pop_size": (5, 100),
                            "w": (0.1, 2.0),
                            "c1": (0.1, 2.0),
                            "c2": (0.1, 2.0)
                        },
                        is_available=True,
                        requires_library=None
                    ),
                    SearchMethodConfig(
                        name="ga",
                        description="Genetic Algorithm",
                        default_parameters={
                            "pop_size": 50,
                            "prob_mut": 0.1
                        },
                        parameter_ranges={
                            "pop_size": (10, 200),
                            "prob_mut": (0.01, 0.5)
                        },
                        is_available=True,
                        requires_library=None
                    )
                ])
            else:
                search_methods.extend([
                    SearchMethodConfig(
                        name="pso",
                        description="Particle Swarm Optimization",
                        default_parameters={},
                        parameter_ranges={},
                        is_available=False,
                        requires_library="scikit-opt"
                    ),
                    SearchMethodConfig(
                        name="ga",
                        description="Genetic Algorithm",
                        default_parameters={},
                        parameter_ranges={},
                        is_available=False,
                        requires_library="scikit-opt"
                    )
                ])
            
            # Get reward functions
            reward_functions = [
                RewardFunctionConfig(
                    name="collision",
                    description="Binary collision detection (0 if collision, 1 if no collision)",
                    parameters={},
                    is_default=False,
                    is_active=True
                ),
                RewardFunctionConfig(
                    name="distance",
                    description="Minimum distance between vehicles",
                    parameters={},
                    is_default=False,
                    is_active=True
                ),
                RewardFunctionConfig(
                    name="safety_margin",
                    description="Safety margin based on distance and velocity",
                    parameters={},
                    is_default=False,
                    is_active=True
                ),
                RewardFunctionConfig(
                    name="ttc",
                    description="Time to collision (TTC) based reward",
                    parameters={},
                    is_default=True,
                    is_active=True
                ),
                RewardFunctionConfig(
                    name="ttc_div_dist",
                    description="TTC divided by distance metric",
                    parameters={},
                    is_default=False,
                    is_active=True
                ),
                RewardFunctionConfig(
                    name="weighted_multi",
                    description="Weighted combination of multiple metrics",
                    parameters={
                        "collision_weight": 1.0,
                        "ttc_weight": 0.5,
                        "distance_weight": 0.3
                    },
                    is_default=False,
                    is_active=True
                )
            ]
            
            # Get system status
            system_status = await self.get_configuration_status()
            
            # Calculate uptime (placeholder)
            uptime = 0.0  # This would be calculated from server start time
            
            # Count active experiments (placeholder)
            active_experiments = 0  # This would come from experiment service
            
            return SystemInfo(
                version="1.0.0",
                carla_version=None,  # Would be detected from CARLA installation
                python_version=f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
                available_search_methods=search_methods,
                available_reward_functions=reward_functions,
                system_status=system_status,
                uptime=uptime,
                active_experiments=active_experiments
            )
            
        except Exception as e:
            logger.error(f"Error getting system info: {e}")
            raise
    
    async def reset_configuration(self) -> None:
        """Reset configuration to defaults."""
        try:
            # Reset parameter ranges to defaults
            default_ranges = self._get_default_parameter_ranges()
            self._save_parameter_ranges(default_ranges)
            
            logger.info("Configuration reset to defaults")
            
        except Exception as e:
            logger.error(f"Error resetting configuration: {e}")
            raise
    
    def _ensure_parameter_ranges_file(self):
        """Ensure parameter ranges file exists with defaults."""
        if not self.parameter_ranges_file.exists():
            self.config_dir.mkdir(parents=True, exist_ok=True)
            default_ranges = self._get_default_parameter_ranges()
            self._save_parameter_ranges(default_ranges)
    
    def _load_parameter_ranges(self) -> Dict[str, Any]:
        """Load parameter ranges from file."""
        if not self.parameter_ranges_file.exists():
            return self._get_default_parameter_ranges()
        
        try:
            with open(self.parameter_ranges_file, 'r') as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            logger.error(f"Error loading parameter ranges: {e}")
            return self._get_default_parameter_ranges()
    
    def _save_parameter_ranges(self, ranges_data: Dict[str, Any]):
        """Save parameter ranges to file."""
        try:
            self.config_dir.mkdir(parents=True, exist_ok=True)
            with open(self.parameter_ranges_file, 'w') as f:
                yaml.dump(ranges_data, f, default_flow_style=False, indent=2)
            
            # Invalidate cache
            self._cached_ranges = None
            self._cache_timestamp = None
            
        except Exception as e:
            logger.error(f"Error saving parameter ranges: {e}")
            raise
    
    def _get_default_parameter_ranges(self) -> Dict[str, Any]:
        """Get default parameter ranges configuration."""
        return {
            "default": {
                "absolute_v": {
                    "min": 0.0,
                    "max": 30.0,
                    "default": 10.0,
                    "description": "Absolute velocity in m/s",
                    "unit": "m/s"
                },
                "relative_p": {
                    "min": -100.0,
                    "max": 100.0,
                    "default": 0.0,
                    "description": "Relative position in meters",
                    "unit": "m"
                },
                "relative_v": {
                    "min": -20.0,
                    "max": 20.0,
                    "default": 0.0,
                    "description": "Relative velocity in m/s",
                    "unit": "m/s"
                },
                "r_ego": {
                    "min": 0.0,
                    "max": 200.0,
                    "default": 50.0,
                    "description": "Ego vehicle range parameter",
                    "unit": "m"
                },
                "v_ego": {
                    "min": 0.0,
                    "max": 30.0,
                    "default": 15.0,
                    "description": "Ego vehicle velocity",
                    "unit": "m/s"
                }
            },
            "scenario_overrides": {
                "CutIn": {
                    "absolute_v": {
                        "min": 5.0,
                        "max": 25.0,
                        "default": 15.0,
                        "description": "Cut-in velocity for CutIn scenario",
                        "unit": "m/s"
                    }
                },
                "FollowLeadingVehicle": {
                    "relative_p": {
                        "min": 10.0,
                        "max": 50.0,
                        "default": 30.0,
                        "description": "Following distance",
                        "unit": "m"
                    }
                }
            }
        }
    
    def _validate_parameter_ranges_format(self, ranges_data: Dict[str, Any]):
        """Validate parameter ranges format."""
        if not isinstance(ranges_data, dict):
            raise ValueError("Parameter ranges must be a dictionary")
        
        for section_name, section_data in ranges_data.items():
            if section_name not in ["default", "scenario_overrides"]:
                raise ValueError(f"Unknown section: {section_name}")
            
            if section_name == "default":
                self._validate_parameter_section(section_data)
            elif section_name == "scenario_overrides":
                if not isinstance(section_data, dict):
                    raise ValueError("scenario_overrides must be a dictionary")
                for scenario_type, params in section_data.items():
                    self._validate_parameter_section(params)
    
    def _validate_parameter_section(self, params: Dict[str, Any]):
        """Validate a parameter section."""
        if not isinstance(params, dict):
            raise ValueError("Parameter section must be a dictionary")
        
        for param_name, param_config in params.items():
            if not isinstance(param_config, dict):
                raise ValueError(f"Parameter config for {param_name} must be a dictionary")
            
            if "min" not in param_config or "max" not in param_config:
                raise ValueError(f"Parameter {param_name} must have min and max values")
            
            try:
                min_val = float(param_config["min"])
                max_val = float(param_config["max"])
                if min_val >= max_val:
                    raise ValueError(f"Parameter {param_name}: min >= max")
            except (ValueError, TypeError):
                raise ValueError(f"Parameter {param_name}: min and max must be numeric")
    
    def _merge_parameter_ranges(self, existing: Dict[str, Any], imported: Dict[str, Any]) -> Dict[str, Any]:
        """Merge imported parameter ranges with existing ones."""
        merged = existing.copy()
        
        for section_name, section_data in imported.items():
            if section_name not in merged:
                merged[section_name] = {}
            
            if section_name == "default":
                merged[section_name].update(section_data)
            elif section_name == "scenario_overrides":
                for scenario_type, params in section_data.items():
                    if scenario_type not in merged[section_name]:
                        merged[section_name][scenario_type] = {}
                    merged[section_name][scenario_type].update(params)
        
        return merged


# Dependency injection
_parameter_service = None

def get_parameter_service() -> ParameterService:
    """Get parameter service instance."""
    global _parameter_service
    if _parameter_service is None:
        _parameter_service = ParameterService()
    return _parameter_service 