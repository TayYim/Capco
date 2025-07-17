#!/usr/bin/env python3
"""
Parameter Range Manager

Manages parameter ranges for scenario fuzzing by loading configuration from
YAML files and providing intelligent range resolution based on parameter types
and scenario-specific overrides.
"""

import yaml
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any, Union


class ParameterRangeManager:
    """
    Manages parameter ranges for scenario fuzzing.
    
    Provides hierarchical range resolution:
    1. User-provided ranges (highest priority)
    2. Scenario-specific overrides
    3. Parameter type defaults
    4. Intelligent defaults based on current values
    5. Fallback ranges (lowest priority)
    """
    
    def __init__(self, config_file: Optional[Union[str, Path]] = None, logger: Optional[logging.Logger] = None):
        """
        Initialize the Parameter Range Manager.
        
        Args:
            config_file: Path to the parameter ranges YAML file
            logger: Logger instance for output
        """
        self.logger = logger or logging.getLogger(__name__)
        
        # Set default config file path
        if config_file is None:
            # Look for config file relative to project root
            script_dir = Path(__file__).parent
            project_root = script_dir.parent.parent
            config_file = project_root / "config" / "parameter_ranges.yaml"
        
        self.config_file = Path(config_file)
        self.config_data = {}
        self.user_overrides = {}
        
        # Load configuration
        self._load_configuration()
        
    def _load_configuration(self):
        """Load parameter ranges from YAML configuration file."""
        try:
            if not self.config_file.exists():
                self.logger.warning(f"Parameter ranges config file not found: {self.config_file}")
                self.logger.warning("Using built-in default ranges")
                self._use_builtin_defaults()
                return
            
            with open(self.config_file, 'r') as f:
                self.config_data = yaml.safe_load(f)
            
            self.logger.info(f"Loaded parameter ranges from: {self.config_file}")
            
            # Validate configuration structure
            self._validate_configuration()
            
        except yaml.YAMLError as e:
            self.logger.error(f"Error parsing YAML configuration: {e}")
            self._use_builtin_defaults()
        except Exception as e:
            self.logger.error(f"Error loading parameter ranges configuration: {e}")
            self._use_builtin_defaults()
    
    def _validate_configuration(self):
        """Validate the loaded configuration structure."""
        required_sections = ['parameter_types', 'scenario_overrides', 'fallback']
        
        for section in required_sections:
            if section not in self.config_data:
                self.logger.warning(f"Missing required section '{section}' in configuration")
        
        # Validate parameter_types structure
        if 'parameter_types' in self.config_data:
            for category, params in self.config_data['parameter_types'].items():
                if not isinstance(params, dict):
                    self.logger.warning(f"Invalid parameter category '{category}': expected dict")
                    continue
                
                for param_name, param_range in params.items():
                    if not self._is_valid_range(param_range):
                        self.logger.warning(f"Invalid range for {category}.{param_name}: {param_range}")
    
    def _is_valid_range(self, param_range: Any) -> bool:
        """Check if a parameter range is valid (list/tuple of 2 numbers)."""
        return (isinstance(param_range, (list, tuple)) and 
                len(param_range) == 2 and
                all(isinstance(x, (int, float)) for x in param_range) and
                param_range[0] <= param_range[1])
    
    def _use_builtin_defaults(self):
        """Use built-in default ranges when configuration file is not available."""
        self.config_data = {
            'parameter_types': {
                'velocity': {
                    'absolute_v': [5.0, 25.0],
                    'relative_v': [-15.0, 15.0],
                    'v_ego': [0.1, 17.0],
                    'v_1': [0.0, 15.0],
                    'v_2': [0.0, 15.0],
                    'v_3': [0.0, 15.0],
                },
                'position': {
                    'relative_p': [5.0, 80.0],
                    'relative_p_1': [5.0, 80.0],
                    'relative_p_2': [5.0, 80.0],
                    'relative_p_3': [5.0, 80.0],
                    'r_ego': [10.0, 70.0],
                    'r_1': [10.0, 70.0],
                    'r_2': [10.0, 70.0],
                    'r_3': [10.0, 70.0],
                },
                'timing': {
                    'delay': [0.1, 3.0],
                    'duration': [1.0, 10.0],
                    'reaction_time': [0.2, 2.0],
                }
            },
            'scenario_overrides': {},
            'fallback': {
                'strategy': 'intelligent_defaults',
                'conservative_defaults': {
                    'velocity_range': [1.0, 15.0],
                    'position_range': [5.0, 50.0],
                    'timing_range': [0.1, 5.0],
                }
            }
        }
    
    def set_user_overrides(self, overrides: Dict[str, Tuple[float, float]]):
        """
        Set user-provided parameter range overrides.
        
        Args:
            overrides: Dictionary mapping parameter names to (min, max) tuples
        """
        self.user_overrides = {}
        for param_name, param_range in overrides.items():
            if self._is_valid_range(param_range):
                self.user_overrides[param_name] = param_range
            else:
                self.logger.warning(f"Invalid user override for {param_name}: {param_range}")
    
    def get_parameter_range(self, 
                           param_name: str, 
                           scenario_type: Optional[str] = None,
                           current_value: Optional[float] = None) -> Tuple[float, float]:
        """
        Get the parameter range for a specific parameter using hierarchical resolution.
        
        Args:
            param_name: Name of the parameter
            scenario_type: Type of scenario (for scenario-specific overrides)
            current_value: Current value from XML (for intelligent defaults)
            
        Returns:
            Tuple of (min_value, max_value)
        """
        # Priority 1: User-provided overrides
        if param_name in self.user_overrides:
            range_tuple = self.user_overrides[param_name]
            self.logger.debug(f"Using user override for {param_name}: {range_tuple}")
            return range_tuple
        
        # Priority 2: Scenario-specific overrides
        if scenario_type and scenario_type in self.config_data.get('scenario_overrides', {}):
            scenario_params = self.config_data['scenario_overrides'][scenario_type]
            if param_name in scenario_params:
                range_tuple = tuple(scenario_params[param_name])
                self.logger.debug(f"Using scenario override for {param_name} in {scenario_type}: {range_tuple}")
                return range_tuple
        
        # Priority 3: Parameter type defaults
        range_tuple = self._get_parameter_type_range(param_name)
        if range_tuple:
            self.logger.debug(f"Using parameter type default for {param_name}: {range_tuple}")
            return range_tuple
        
        # Priority 4: Intelligent defaults based on current value
        if current_value is not None:
            range_tuple = self._generate_intelligent_default(param_name, current_value)
            self.logger.debug(f"Using intelligent default for {param_name}: {range_tuple}")
            return range_tuple
        
        # Priority 5: Fallback ranges
        range_tuple = self._get_fallback_range(param_name)
        self.logger.warning(f"Using fallback range for unknown parameter {param_name}: {range_tuple}")
        return range_tuple
    
    def _get_parameter_type_range(self, param_name: str) -> Optional[Tuple[float, float]]:
        """Get range from parameter type defaults."""
        parameter_types = self.config_data.get('parameter_types', {})
        
        # Search through all parameter type categories
        for category, params in parameter_types.items():
            if param_name in params:
                param_range = params[param_name]
                if self._is_valid_range(param_range):
                    return tuple(param_range)
        
        return None
    
    def _generate_intelligent_default(self, param_name: str, current_value: float) -> Tuple[float, float]:
        """Generate intelligent default range based on current value and parameter semantics."""
        # Determine parameter category based on name patterns
        if any(keyword in param_name.lower() for keyword in ['v', 'velocity', 'speed']):
            # Velocity parameters: create range around current value (50% to 150%)
            min_val = max(0.0, current_value * 0.5)
            max_val = current_value * 1.5
            return (min_val, max_val)
        
        elif any(keyword in param_name.lower() for keyword in ['p', 'position', 'r', 'distance']):
            # Position parameters: create range around current value (70% to 130%)
            min_val = max(1.0, current_value * 0.7)
            max_val = current_value * 1.3
            return (min_val, max_val)
        
        elif any(keyword in param_name.lower() for keyword in ['time', 'delay', 'duration']):
            # Timing parameters: create range around current value (50% to 200%)
            min_val = max(0.1, current_value * 0.5)
            max_val = current_value * 2.0
            return (min_val, max_val)
        
        else:
            # Generic parameter: conservative range around current value
            min_val = current_value * 0.8
            max_val = current_value * 1.2
            return (min_val, max_val)
    
    def _get_fallback_range(self, param_name: str) -> Tuple[float, float]:
        """Get fallback range for unknown parameters."""
        fallback_config = self.config_data.get('fallback', {})
        strategy = fallback_config.get('strategy', 'conservative')
        
        # Determine parameter category and use appropriate fallback
        if any(keyword in param_name.lower() for keyword in ['v', 'velocity', 'speed']):
            if strategy == 'wide_range':
                return tuple(fallback_config.get('wide_defaults', {}).get('velocity_range', [0.1, 30.0]))
            else:
                return tuple(fallback_config.get('conservative_defaults', {}).get('velocity_range', [1.0, 15.0]))
        
        elif any(keyword in param_name.lower() for keyword in ['p', 'position', 'r', 'distance']):
            if strategy == 'wide_range':
                return tuple(fallback_config.get('wide_defaults', {}).get('position_range', [1.0, 100.0]))
            else:
                return tuple(fallback_config.get('conservative_defaults', {}).get('position_range', [5.0, 50.0]))
        
        elif any(keyword in param_name.lower() for keyword in ['time', 'delay', 'duration']):
            if strategy == 'wide_range':
                return tuple(fallback_config.get('wide_defaults', {}).get('timing_range', [0.05, 10.0]))
            else:
                return tuple(fallback_config.get('conservative_defaults', {}).get('timing_range', [0.1, 5.0]))
        
        else:
            # Generic fallback: conservative range
            return (1.0, 10.0)
    
    def get_ranges_for_parameters(self, 
                                 parameters: Dict[str, Any], 
                                 scenario_type: Optional[str] = None) -> Dict[str, Tuple[float, float]]:
        """
        Get ranges for multiple parameters at once.
        
        Args:
            parameters: Dictionary of parameter names to current values
            scenario_type: Type of scenario for scenario-specific overrides
            
        Returns:
            Dictionary mapping parameter names to (min, max) tuples
        """
        ranges = {}
        for param_name, param_info in parameters.items():
            current_value = param_info.get('value') if isinstance(param_info, dict) else param_info
            if isinstance(current_value, (int, float)):
                ranges[param_name] = self.get_parameter_range(param_name, scenario_type, current_value)
            else:
                ranges[param_name] = self.get_parameter_range(param_name, scenario_type)
        
        return ranges
    
    def list_available_parameters(self) -> Dict[str, List[str]]:
        """
        List all available parameters organized by category.
        
        Returns:
            Dictionary mapping categories to lists of parameter names
        """
        parameter_types = self.config_data.get('parameter_types', {})
        return {category: list(params.keys()) for category, params in parameter_types.items()}
    
    def list_scenario_overrides(self) -> List[str]:
        """
        List all scenario types that have specific overrides.
        
        Returns:
            List of scenario type names
        """
        return list(self.config_data.get('scenario_overrides', {}).keys())
    
    def get_configuration_info(self) -> Dict[str, Any]:
        """
        Get information about the current configuration.
        
        Returns:
            Dictionary with configuration metadata and statistics
        """
        parameter_types = self.config_data.get('parameter_types', {})
        scenario_overrides = self.config_data.get('scenario_overrides', {})
        
        total_params = sum(len(params) for params in parameter_types.values())
        total_overrides = sum(len(params) for params in scenario_overrides.values())
        
        return {
            'config_file': str(self.config_file),
            'total_parameter_types': len(parameter_types),
            'total_parameters': total_params,
            'scenario_types_with_overrides': len(scenario_overrides),
            'total_parameter_overrides': total_overrides,
            'fallback_strategy': self.config_data.get('fallback', {}).get('strategy', 'unknown'),
            'user_overrides_count': len(self.user_overrides),
            'metadata': self.config_data.get('metadata', {})
        } 