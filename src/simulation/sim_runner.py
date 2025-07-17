#!/usr/bin/env python3
"""
Scenario Fuzzing Framework

A modular, extensible fuzzing framework for finding critical scenarios in CARLA
autonomous vehicle simulations. Supports multiple search algorithms including
random search, PSO, and genetic algorithms.
"""

import random
import numpy as np
import copy
import xml.etree.ElementTree as ET
import functools
import signal
import time
import threading
import argparse
import subprocess
import sys
import os
import select
import termios
import tty
from pathlib import Path
from datetime import datetime
import shutil
import logging
import json
import csv
from typing import Optional, List, Tuple, Dict, Union, Any

# Import optimization libraries
try:
    from sko.PSO import PSO
    from sko.GA import GA
    SKO_AVAILABLE = True
except ImportError:
    PSO = None
    GA = None
    SKO_AVAILABLE = False

# Add src directory to Python path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.xml_utils import display_route_info, parse_route_scenarios, validate_route_exists
from utils.parameter_range_manager import ParameterRangeManager
from rewards import RewardRegistry


class SearchMethodRegistry:
    """Registry for managing different search methods."""
    
    _methods = {}
    
    @classmethod
    def register(cls, name: str):
        """Decorator to register a search method."""
        def decorator(func):
            cls._methods[name] = func
            return func
        return decorator
    
    @classmethod
    def get_method(cls, name: str):
        """Get a registered search method."""
        if name not in cls._methods:
            raise ValueError(f"Unknown search method: {name}. Available: {list(cls._methods.keys())}")
        return cls._methods[name]
    
    @classmethod
    def list_methods(cls) -> List[str]:
        """List all available search methods."""
        return list(cls._methods.keys())


def search_method_decorator(method_name: str):
    """
    Decorator for search methods to provide consistent setup and teardown.
    
    This decorator:
    - Sets up timing and logging
    - Handles cleanup on completion/interruption
    - Saves results consistently
    - Provides graceful error handling
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            # Setup
            self.current_search_method = method_name
            self._reset_search_state()
            start_time = time.perf_counter()
            
            self.logger.info(f"Starting search with method: {method_name}")
            self.logger.info(f"Parameters: {dict(zip(func.__code__.co_varnames[1:], args))}")
            
            # Reset random seed for reproducibility
            self._set_random_seed(self.random_seed)
            
            def terminate_search(start_time):
                """Clean termination of search."""
                end_time = time.perf_counter()
                time_usage = end_time - start_time
                
                # Save timing information
                if 'time' not in self.search_history_data:
                    self.search_history_data['time'] = []
                self.search_history_data['time'].append(time_usage)
                
                # Save all results
                self._save_search_results()
                
                self.logger.info(f"Search completed. Method: {method_name}, Time: {time_usage:.2f}s")
                self.logger.info(f"Results saved to: {self.output_dir}")
                
                # Cleanup CARLA if needed
                if hasattr(self, 'carla_running') and self.carla_running:
                    self.cleanup()
            
            def signal_handler(sig, frame):
                """Handle user interruption gracefully."""
                self.logger.info("Search interrupted by user")
                terminate_search(start_time)
                sys.exit(0)
            
            # Set up signal handler
            signal.signal(signal.SIGINT, signal_handler)
            
            try:
                # Execute the actual search method
                result = func(self, *args, **kwargs)
                
                # Normal termination
                terminate_search(start_time)
                return result
                
            except Exception as e:
                self.logger.error(f"Error in search method {method_name}: {e}")
                terminate_search(start_time)
                raise
        
        return wrapper
    return decorator


class ScenarioFuzzer:
    """
    Comprehensive scenario fuzzing framework with multiple search algorithms.
    
    This class provides a modular, extensible framework for scenario-based
    testing of autonomous vehicles. It supports multiple optimization algorithms
    and is designed for easy maintenance and extension.
    
    Features:
    - Multiple search algorithms (Random, PSO, GA)
    - Modular architecture for easy extension
    - Comprehensive result tracking and analysis
    - Robust error handling and cleanup
    - Easy-to-use interface for method selection
    """
    
    # Class-level configuration
    SUPPORTED_SEARCH_METHODS = ['random', 'pso', 'ga'] if SKO_AVAILABLE else ['random']
    
    def __init__(self, 
                 route_id: str,
                 search_method: str = "random",
                 num_iterations: int = 10,
                 route_file: str = "routes_carlo",
                 timeout_seconds: int = 300,
                 headless: bool = False,
                 parameter_ranges: Optional[Dict[str, Tuple[float, float]]] = None,
                 random_seed: int = 42,
                 restart_gap: int = 5,
                 reward_function: str = "ttc"):
        """
        Initialize the scenario fuzzer.
        
        Args:
            route_id: ID of the route to fuzz
            search_method: Search algorithm to use ('random', 'pso', 'ga')
            num_iterations: Number of search iterations
            route_file: Name of the route file
            timeout_seconds: Timeout for each simulation
            headless: Whether to run CARLA headless
            parameter_ranges: Custom parameter ranges for fuzzing
            random_seed: Random seed for reproducibility
            reward_function: Name of the reward function to use
            restart_gap: Number of runs before restarting CARLA
        """
        # Validate search method
        if search_method not in self.SUPPORTED_SEARCH_METHODS:
            available_methods = self.SUPPORTED_SEARCH_METHODS
            if not SKO_AVAILABLE and search_method in ['pso', 'ga']:
                raise ValueError(f"Search method {search_method} requires scikit-opt library. "
                               f"Please install it with: pip install scikit-opt")
            raise ValueError(f"Unsupported search method: {search_method}. "
                           f"Available: {available_methods}")
        
        # Basic configuration
        self.route_id = route_id
        self.route_file = route_file
        self.restart_gap = restart_gap
        self.timeout_seconds = timeout_seconds
        self.headless = headless
        
        # Paths
        self.carla_path = Path("/home/tay/Applications/CARLA_LB")  # TODO: get it from config file
        self.script_dir = Path(__file__).parent.absolute()
        self.project_root = self.script_dir.parent.parent
        
        # State variables
        self.should_exit = False
        self.carla_running = False
        self.runs_since_restart = 0
        self.carla_process: Optional[subprocess.Popen] = None
        
        # Fuzzing configuration
        self.search_method = search_method
        self.num_iterations = num_iterations
        self.random_seed = random_seed
        self.parameter_ranges = parameter_ranges or {}
        
        # Reward function configuration
        self.reward_function_name = reward_function
        try:
            self.reward_function = RewardRegistry.get_function(reward_function)
        except ValueError as e:
            available_functions = RewardRegistry.list_functions()
            raise ValueError(f"Invalid reward function '{reward_function}'. Available: {available_functions}") from e
        
        # Search state management
        self.current_search_method = None
        self.search_history_data = {}
        self.best_solution = None
        self.best_reward = float('inf')
        self.current_iteration = 0
        
        # Parameter management
        self._detected_parameters = {}
        self._search_bounds = None
        
        # Setup output directory
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.output_dir = (self.project_root / "output" / 
                          f"fuzzing_{route_file}_{route_id}_{search_method}_{timestamp}")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Data collection for experiment results
        self.experiment_results = []
        
        # Scenario parameters for this experiment
        self.scenario_parameters = {}
        
        # Setup logging
        self.setup_logging()
        
        # Log reward function after logger is set up
        self.logger.info(f"Using reward function: {reward_function}")
        
        # Initialize parameter range manager
        self.parameter_range_manager = ParameterRangeManager(logger=self.logger)
        if self.parameter_ranges:
            self.parameter_range_manager.set_user_overrides(self.parameter_ranges)
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        # Thread for monitoring user input
        self.input_thread = None
        self.old_settings = None
        
        # Initialize search infrastructure
        self._initialize_search_infrastructure()

    def setup_logging(self):
        """Setup comprehensive logging for the fuzzing framework."""
        log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        
        # Console handler with clean formatting
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter('%(levelname)s - %(message)s')
        console_handler.setFormatter(console_formatter)
        
        # File handler with detailed formatting
        log_file = self.output_dir / "fuzzing.log"
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(log_format)
        file_handler.setFormatter(file_formatter)
        
        # Configure logger
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)
        self.logger.addHandler(console_handler)
        self.logger.addHandler(file_handler)
        
    def _signal_handler(self, signum, frame):
        """Handle interrupt signals gracefully."""
        self.logger.info("Received interrupt signal. Will exit after current run completes.")
        self.should_exit = True
        
    def _setup_terminal(self):
        """Setup terminal for non-blocking input."""
        try:
            self.old_settings = termios.tcgetattr(sys.stdin)
            tty.setraw(sys.stdin.fileno())
        except (termios.error, AttributeError):
            # Fallback for environments without termios
            self.old_settings = None
            
    def _restore_terminal(self):
        """Restore terminal settings."""
        if self.old_settings:
            try:
                termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self.old_settings)
            except termios.error:
                pass
                
    def _monitor_user_input(self):
        """Monitor for 'q' key press in a separate thread."""
        self._setup_terminal()
        try:
            while not self.should_exit:
                if sys.stdin in select.select([sys.stdin], [], [], 0.1)[0]:
                    key = sys.stdin.read(1)
                    if key.lower() == 'q':
                        self.logger.info("User requested exit. Will terminate after current run completes.")
                        self.should_exit = True
                        break
                time.sleep(0.1)
        except Exception as e:
            self.logger.debug(f"Error in input monitoring: {e}")
        finally:
            self._restore_terminal()

    def _initialize_search_infrastructure(self):
        """Initialize the search infrastructure."""
        self.logger.info("Initializing fuzzing infrastructure...")
        
        # Detect scenario parameters
        self._detect_scenario_parameters()
        
        # Setup search bounds
        self._setup_search_bounds()
        
        # Initialize search history
        self._reset_search_state()
        
        self.logger.info(f"Found {len(self._detected_parameters)} fuzzable parameters")
        self.logger.info(f"Parameter ranges: {self._search_bounds}")

    def _detect_scenario_parameters(self) -> Dict[str, Any]:
        """Detect parameters available for fuzzing from the route XML."""
        route_file_path = self.project_root / "dependencies" / "leaderboard" / "data" / f"{self.route_file}.xml"
        
        if not route_file_path.exists():
            self.logger.error(f"Route file not found: {route_file_path}")
            return {}
        
        try:
            tree = ET.parse(route_file_path)
            root = tree.getroot()
            
            # Find the specific route
            route = None
            for r in root.findall(".//route"):
                if r.get("id") == str(self.route_id):
                    route = r
                    break
            
            if route is None:
                self.logger.error(f"Route {self.route_id} not found in {self.route_file}.xml")
                return {}
            
            # Extract parameters from scenarios
            parameters = {}
            for scenario in route.findall(".//scenario"):
                scenario_name = scenario.get("type", "Unknown")
                scenario_instance_name = scenario.get("name", "Unknown")
                
                # Skip data collection scenarios as they don't have fuzzable parameters
                if "Data_Collect" in scenario_name:
                    continue
                
                # Look for parameter elements (like <absolute_v value="..."/>)
                parameter_elements = ['absolute_v', 'relative_p', 'relative_v', 
                                    'relative_p_1', 'relative_v_1', 'relative_p_2', 'relative_v_2',
                                    'r_ego', 'v_ego', 'r_1', 'v_1', 'r_2', 'v_2']
                
                for param_name in parameter_elements:
                    param_element = scenario.find(param_name)
                    if param_element is not None:
                        param_value = param_element.get("value")
                        if param_value:
                            try:
                                # Try to convert to float for numeric parameters
                                numeric_value = float(param_value)
                                parameters[param_name] = {
                                    'value': numeric_value,
                                    'scenario': scenario_name,
                                    'scenario_instance': scenario_instance_name,
                                    'element': param_element
                                }
                                self.logger.debug(f"Found parameter: {param_name} = {numeric_value} (from {scenario_name})")
                            except ValueError:
                                # Non-numeric parameters are not suitable for fuzzing
                                self.logger.debug(f"Skipping non-numeric parameter: {param_name} = {param_value}")
            
            self._detected_parameters = parameters
            return parameters
            
        except Exception as e:
            self.logger.error(f"Error detecting parameters: {e}")
            return {}

    def _setup_search_bounds(self):
        """Setup search bounds using the ParameterRangeManager."""
        bounds = []
        param_names = []
        
        # Detect scenario type for the current route
        scenario_type = self._detect_primary_scenario_type()
        
        # Get ranges for all detected parameters
        parameter_ranges = self.parameter_range_manager.get_ranges_for_parameters(
            self._detected_parameters, scenario_type
        )
        
        for param_name, param_info in self._detected_parameters.items():
            param_range = parameter_ranges.get(param_name)
            
            if param_range:
                bounds.append(param_range)
                param_names.append(param_name)
                self.logger.debug(f"Parameter {param_name}: range {param_range}")
            else:
                self.logger.warning(f"No range found for parameter {param_name}, skipping")
        
        self._search_bounds = bounds
        self._param_names = param_names
        
        self.logger.info(f"Search bounds set for {len(param_names)} parameters: {param_names}")
        
        # Log configuration info
        config_info = self.parameter_range_manager.get_configuration_info()
        self.logger.info(f"Using parameter ranges from: {config_info['config_file']}")
        if scenario_type:
            self.logger.info(f"Scenario type detected: {scenario_type}")
            if scenario_type in self.parameter_range_manager.list_scenario_overrides():
                self.logger.info(f"Using scenario-specific overrides for {scenario_type}")
        
    def _detect_primary_scenario_type(self) -> Optional[str]:
        """Detect the primary scenario type for parameter range resolution."""
        # Find the first non-data-collection scenario as the primary type
        for param_name, param_info in self._detected_parameters.items():
            scenario_type = param_info.get('scenario')
            if scenario_type and 'Data_Collect' not in scenario_type:
                return scenario_type
        return None

    def _set_random_seed(self, seed: int):
        """Set random seed for reproducibility."""
        random.seed(seed)
        np.random.seed(seed)

    def _reset_search_state(self):
        """Reset search state for a new search run."""
        self.search_history_data = {
            'parameters': [],
            'rewards': [],
            'collision_flags': [],
            'min_ttcs': [],
            'distances': [],
            'iterations': [],
            'methods': []
        }
        self.best_solution = None
        self.best_reward = float('inf')
        self.current_iteration = 0

    def _evaluate_scenario(self, parameters: List[float]) -> float:
        """
        Evaluate a scenario with given parameters.
        
        Args:
            parameters: List of parameter values to test
            
        Returns:
            Reward value (lower is better, collision = 0, no collision = min_ttc)
        """
        self.current_iteration += 1
        
        # Update XML with new parameters
        self._update_scenario_xml(parameters)
        
        # Log current parameters
        param_dict = dict(zip(self._param_names, parameters))
        self.logger.info(f"Iteration {self.current_iteration}: Testing parameters {param_dict}")
        
        # Run simulation
        run_status = self.run_simulation_with_timeout(self.current_iteration)
        
        # Process results
        result = self.process_epoch_result(self.current_iteration)
        self.experiment_results.append(result)
        
        # Calculate reward using selected reward function (lower is better)
        reward = self.reward_function(result)
        
        # Log reward information
        collision_flag = result.get('collision_flag', False)
        min_ttc = result.get('min_ttc', None)
        
        if collision_flag:
            self.logger.info(f"🎯 COLLISION FOUND! Reward ({self.reward_function_name}): {reward:.3f}")
        elif min_ttc is not None:
            self.logger.info(f"No collision, min TTC: {min_ttc:.3f}, reward ({self.reward_function_name}): {reward:.3f}")
        else:
            self.logger.info(f"Invalid result, reward ({self.reward_function_name}): {reward:.3f}")
        
        # Update best solution
        if reward < self.best_reward:
            self.best_reward = reward
            self.best_solution = parameters.copy()
            self.logger.info(f"🌟 NEW BEST SOLUTION! Reward: {reward:.3f}, Parameters: {param_dict}")
        
        # Store in history
        self.search_history_data['parameters'].append(parameters.copy())
        self.search_history_data['rewards'].append(reward)
        self.search_history_data['collision_flags'].append(collision_flag)
        self.search_history_data['min_ttcs'].append(min_ttc)
        self.search_history_data['distances'].append(result.get('distance', None))
        self.search_history_data['iterations'].append(self.current_iteration)
        self.search_history_data['methods'].append(self.current_search_method)
        
        return reward

    def _update_scenario_xml(self, parameters: List[float]):
        """Update the scenario XML file with new parameter values."""
        route_file_path = self.project_root / "dependencies" / "leaderboard" / "data" / f"{self.route_file}.xml"
        
        try:
            tree = ET.parse(route_file_path)
            root = tree.getroot()
            
            # Find the specific route
            route = None
            for r in root.findall(".//route"):
                if r.get("id") == str(self.route_id):
                    route = r
                    break
            
            if route is None:
                raise ValueError(f"Route {self.route_id} not found")
            
            # Update parameters using the parameter names we detected
            param_idx = 0
            for param_name in self._param_names:
                if param_idx < len(parameters):
                    # Find the parameter info
                    param_info = self._detected_parameters[param_name]
                    scenario_instance = param_info['scenario_instance']
                    
                    # Find the specific scenario instance
                    for scenario in route.findall(".//scenario"):
                        if scenario.get("name") == scenario_instance:
                            # Find the parameter element
                            param_element = scenario.find(param_name)
                            if param_element is not None:
                                param_element.set("value", str(parameters[param_idx]))
                                self.logger.debug(f"Updated {param_name} = {parameters[param_idx]} in {scenario_instance}")
                                break
                    param_idx += 1
            
            # Save the updated XML
            tree.write(route_file_path, encoding='unicode', xml_declaration=True)
            
        except Exception as e:
            self.logger.error(f"Error updating scenario XML: {e}")
            raise

    def _save_search_results(self):
        """Save comprehensive search results to multiple formats."""
        try:
            # Save detailed search history to CSV
            history_file = self.output_dir / "search_history.csv"
            
            if self.search_history_data['parameters']:
                with open(history_file, 'w', newline='') as f:
                    # Create header
                    header = ['iteration', 'method', 'reward', 'collision_flag', 'min_ttc', 'distance']
                    header.extend(self._param_names)
                    
                    writer = csv.writer(f)
                    writer.writerow(header)
                    
                    # Write data
                    for i in range(len(self.search_history_data['iterations'])):
                        row = [
                            self.search_history_data['iterations'][i],
                            self.search_history_data['methods'][i],
                            self.search_history_data['rewards'][i],
                            self.search_history_data['collision_flags'][i],
                            self.search_history_data['min_ttcs'][i],
                            self.search_history_data['distances'][i]
                        ]
                        row.extend(self.search_history_data['parameters'][i])
                        writer.writerow(row)
                
                self.logger.info(f"Search history saved to: {history_file}")
            
            # Save best solution to JSON
            best_solution_file = self.output_dir / "best_solution.json"
            best_solution_data = {
                'best_reward': self.best_reward,
                'best_parameters': dict(zip(self._param_names, self.best_solution)) if self.best_solution else None,
                'search_method': self.current_search_method,
                'total_iterations': self.current_iteration,
                'collision_found': self.best_reward == 0.0,
                'search_bounds': dict(zip(self._param_names, self._search_bounds)) if self._search_bounds else {},
                'timestamp': datetime.now().isoformat()
            }
            
            with open(best_solution_file, 'w') as f:
                json.dump(best_solution_data, f, indent=2)
            
            self.logger.info(f"Best solution saved to: {best_solution_file}")
            
            # Save experiment results (similar to original sim_runner)
            self.save_results_to_csv()
            
        except Exception as e:
            self.logger.error(f"Error saving search results: {e}")

    # Search method implementations
    @SearchMethodRegistry.register('random')
    @search_method_decorator('random')
    def search_random(self, iterations: Optional[int] = None) -> Tuple[List[float], float]:
        """
        Random search method - baseline approach.
        
        Args:
            iterations: Number of random samples to evaluate
            
        Returns:
            Tuple of (best_parameters, best_reward)
        """
        if iterations is None:
            iterations = self.num_iterations
            
        if not self._search_bounds:
            raise ValueError("No search bounds available for optimization")
            
        self.logger.info(f"Starting random search with {iterations} iterations")
        
        for i in range(iterations):
            if self.should_exit:
                self.logger.info("Random search terminated by user")
                break
                
            # Generate random parameters within bounds
            parameters = []
            for lower, upper in self._search_bounds:
                param_value = random.uniform(lower, upper)
                parameters.append(param_value)
            
            # Evaluate this parameter set
            reward = self._evaluate_scenario(parameters)
            
            # Early termination if collision found
            if reward == 0.0:
                self.logger.info("Collision found! Terminating search early.")
                break
        
        if self.best_solution is None:
            raise ValueError("No valid solution found during search")
        return self.best_solution, self.best_reward

    @SearchMethodRegistry.register('pso')
    @search_method_decorator('pso')
    def search_pso(self, 
                   iterations: Optional[int] = None,
                   pop_size: int = 20,
                   w: float = 0.8,
                   c1: float = 0.5,
                   c2: float = 0.5) -> Tuple[List[float], float]:
        """
        Particle Swarm Optimization search method.
        
        Args:
            iterations: Maximum number of iterations
            pop_size: Size of particle swarm
            w: Inertia weight
            c1: Cognitive parameter
            c2: Social parameter
            
        Returns:
            Tuple of (best_parameters, best_reward)
        """
        if not SKO_AVAILABLE:
            raise ImportError("PSO requires scikit-opt library. Install with: pip install scikit-opt")
            
        if iterations is None:
            iterations = self.num_iterations
            
        if not self._search_bounds:
            raise ValueError("No search bounds available for optimization")
            
        self.logger.info(f"Starting PSO search with {iterations} iterations, population size {pop_size}")
        
        # Setup PSO
        n_dim = len(self._search_bounds)
        lb = [bound[0] for bound in self._search_bounds]
        ub = [bound[1] for bound in self._search_bounds]
        
        pso = PSO(func=self._evaluate_scenario, n_dim=n_dim, pop=pop_size, max_iter=iterations,
                  lb=lb, ub=ub, w=w, c1=c1, c2=c2)
        
        # Run PSO
        best_x, best_y = pso.run()
        
        return best_x.tolist(), best_y

    @SearchMethodRegistry.register('ga')
    @search_method_decorator('ga')
    def search_ga(self,
                  iterations: Optional[int] = None,
                  pop_size: int = 50,
                  prob_mut: float = 0.1) -> Tuple[List[float], float]:
        """
        Genetic Algorithm search method.
        
        Args:
            iterations: Maximum number of generations
            pop_size: Population size
            prob_mut: Mutation probability
            
        Returns:
            Tuple of (best_parameters, best_reward)
        """
        if not SKO_AVAILABLE:
            raise ImportError("GA requires scikit-opt library. Install with: pip install scikit-opt")
            
        if iterations is None:
            iterations = self.num_iterations
            
        if not self._search_bounds:
            raise ValueError("No search bounds available for optimization")
            
        self.logger.info(f"Starting GA search with {iterations} generations, population size {pop_size}")
        
        # Setup GA
        n_dim = len(self._search_bounds)
        lb = [bound[0] for bound in self._search_bounds]
        ub = [bound[1] for bound in self._search_bounds]
        
        ga = GA(func=self._evaluate_scenario, n_dim=n_dim, size_pop=pop_size, max_iter=iterations,
                lb=lb, ub=ub, prob_mut=prob_mut, precision=1e-7)
        
        # Run GA
        best_x, best_y = ga.run()
        
        return best_x, best_y

    def run_search(self) -> Tuple[List[float], float]:
        """
        Run the configured search method.
        
        Returns:
            Tuple of (best_parameters, best_reward)
        """
        if not self._detected_parameters:
            raise ValueError("No parameters detected for fuzzing. Check the route XML file.")
        
        self.logger.info(f"Starting fuzzing with method: {self.search_method}")
        self.logger.info(f"Route: {self.route_file}, Route ID: {self.route_id}")
        self.logger.info(f"Parameters: {list(self._detected_parameters.keys())}")
        self.logger.info(f"Search bounds: {self._search_bounds}")
        
        # Display route information
        display_route_info(self.route_file, self.route_id, self.project_root, self.logger)
        
        # Extract scenario parameters for CSV inclusion
        self.extract_scenario_parameters()
        
        # Clear existing logs
        self.clear_existing_logs()
        
        # Start input monitoring thread
        self.input_thread = threading.Thread(target=self._monitor_user_input, daemon=True)
        self.input_thread.start()
        
        # Start CARLA
        if not self.start_carla():
            raise RuntimeError("Failed to start CARLA")
        
        try:
            # Get the search method and execute it
            search_func = SearchMethodRegistry.get_method(self.search_method)
            result = search_func(self)
            
            return result
        finally:
            # Always cleanup
            self.cleanup()

    # CARLA management methods (from original CarlaExperimentRunner)
    def kill_carla_processes(self, force: bool = False):
        """Kill Carla and related processes."""
        signal_type = "-9" if force else "-TERM"
        processes = ["CarlaUE4", "leaderboard_evaluator.py", "scenario_runner"]
        
        for process in processes:
            try:
                cmd = ["pkill", signal_type, "-f", process]
                subprocess.run(cmd, capture_output=True, check=False)
            except Exception as e:
                self.logger.debug(f"Error killing {process}: {e}")
                
        if force:
            time.sleep(3)
        else:
            time.sleep(2)
            
    def is_carla_responsive(self) -> bool:
        """Check if Carla is running and responsive."""
        try:
            result = subprocess.run(["pgrep", "-f", "CarlaUE4"], 
                                 capture_output=True, check=False)
            return result.returncode == 0
        except Exception:
            return False
            
    def start_carla(self):
        """Start Carla simulator."""
        self.logger.info("Starting Carla simulator...")
        
        # Kill any existing instances
        self.kill_carla_processes(force=True)
        
        # Prepare command
        cmd = ["./CarlaUE4.sh", "-quality-level=Low"]
        if self.headless:
            cmd.append("-RenderOffScreen")
            
        try:
            # Start Carla
            self.carla_process = subprocess.Popen(
                cmd, 
                cwd=str(self.carla_path),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                preexec_fn=os.setsid  # Create new process group
            )
            
            self.carla_running = True
            self.runs_since_restart = 0
            
            # Wait for initialization
            self.logger.info("Waiting for Carla to initialize...")
            time.sleep(10)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start Carla: {e}")
            return False
            
    def run_simulation_with_timeout(self, run_num: int) -> int:
        """Run a single simulation with timeout."""
        self.logger.info(f"Running simulation with route ID {self.route_id} "
                        f"from file {self.route_file} (timeout: {self.timeout_seconds}s)...")
        
        # Prepare environment
        env = os.environ.copy()
        env["CURRENT_RUN_NUMBER"] = str(run_num)
        
        # Prepare command
        simulate_script = self.script_dir / "simulate_ba.sh"
        cmd = ["bash", str(simulate_script), str(self.route_id), self.route_file]
        
        try:
            # Run with timeout
            result = subprocess.run(
                cmd,
                cwd=str(self.script_dir),
                env=env,
                timeout=self.timeout_seconds,
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                self.logger.info("Simulation completed successfully.")
                return 0
            else:
                self.logger.error(f"Simulation failed with exit code {result.returncode}")
                if result.stderr:
                    self.logger.debug(f"Error output: {result.stderr}")
                return result.returncode
                
        except subprocess.TimeoutExpired:
            self.logger.error(f"Simulation TIMED OUT after {self.timeout_seconds} seconds!")
            return 124  # Timeout exit code
        except Exception as e:
            self.logger.error(f"Error running simulation: {e}")
            return 1

    def process_epoch_result(self, run_num: int) -> Dict:
        """Process epoch_result.json and extract key experiment data."""
        epoch_file = self.script_dir / "epoch_result.json"
        
        if not epoch_file.exists():
            self.logger.warning(f"No epoch_result.json found for run {run_num}")
            result = {
                'run_number': run_num,
                'collision_flag': None,
                'min_ttc': None,
                'distance': None,
                'ego_x': None, 'ego_y': None, 'ego_velocity': None, 'ego_yaw': None,
                'npc_x': None, 'npc_y': None, 'npc_velocity': None, 'npc_yaw': None
            }
            result.update(self.scenario_parameters)
            return result
        
        try:
            with open(epoch_file, 'r') as f:
                data = json.load(f)
            
            # Extract basic data
            result = {
                'run_number': run_num,
                'collision_flag': data.get('collision_flag', None),
                'min_ttc': data.get('min_ttc', None),
                'distance': data.get('distance', None),
                'ego_x': None, 'ego_y': None, 'ego_velocity': None, 'ego_yaw': None,
                'npc_x': None, 'npc_y': None, 'npc_velocity': None, 'npc_yaw': None
            }
            
            # Add scenario parameters to the result
            result.update(self.scenario_parameters)
            
            # Extract collision status if available
            collision_status = data.get('collision_status', {})
            if collision_status:
                ego_data = collision_status.get('EGO', [])
                npc_data = collision_status.get('NPC', [])
                
                if len(ego_data) >= 4:
                    result.update({
                        'ego_x': ego_data[0],
                        'ego_y': ego_data[1], 
                        'ego_velocity': ego_data[2],
                        'ego_yaw': ego_data[3]
                    })
                
                if len(npc_data) >= 4:
                    result.update({
                        'npc_x': npc_data[0],
                        'npc_y': npc_data[1],
                        'npc_velocity': npc_data[2],
                        'npc_yaw': npc_data[3]
                    })
            
            # Print results to console
            self.logger.info("=" * 50)
            self.logger.info(f"RUN {run_num} RESULTS:")
            self.logger.info("=" * 50)
            self.logger.info(f"Collision occurred: {result['collision_flag']}")
            self.logger.info(f"Minimum TTC: {result['min_ttc']}")
            self.logger.info(f"Distance: {result['distance']}")
            
            if result['collision_flag']:
                self.logger.info("Collision Details:")
                self.logger.info(f"  EGO - Position: ({result['ego_x']:.2f}, {result['ego_y']:.2f}), "
                               f"Velocity: {result['ego_velocity']:.2f}, Yaw: {result['ego_yaw']:.2f}°")
                self.logger.info(f"  NPC - Position: ({result['npc_x']:.2f}, {result['npc_y']:.2f}), "
                               f"Velocity: {result['npc_velocity']:.2f}, Yaw: {result['npc_yaw']:.2f}°")
            else:
                self.logger.info("No collision detected")
            
            self.logger.info("=" * 50)
            
            return result
            
        except json.JSONDecodeError as e:
            self.logger.error(f"Error parsing epoch_result.json for run {run_num}: {e}")
            result = {
                'run_number': run_num,
                'collision_flag': None,
                'min_ttc': None,
                'distance': None,
                'ego_x': None, 'ego_y': None, 'ego_velocity': None, 'ego_yaw': None,
                'npc_x': None, 'npc_y': None, 'npc_velocity': None, 'npc_yaw': None
            }
            result.update(self.scenario_parameters)
            return result
        except Exception as e:
            self.logger.error(f"Unexpected error processing epoch_result.json for run {run_num}: {e}")
            result = {
                'run_number': run_num,
                'collision_flag': None,
                'min_ttc': None,
                'distance': None,
                'ego_x': None, 'ego_y': None, 'ego_velocity': None, 'ego_yaw': None,
                'npc_x': None, 'npc_y': None, 'npc_velocity': None, 'npc_yaw': None
            }
            result.update(self.scenario_parameters)
            return result

    def save_results_to_csv(self):
        """Save all experiment results to a CSV file including scenario parameters."""
        if not self.experiment_results:
            self.logger.warning("No experiment results to save")
            return
        
        csv_file = self.output_dir / "experiment_results.csv"
        
        try:
            with open(csv_file, 'w', newline='') as f:
                # Define base CSV columns
                base_fieldnames = [
                    'run_number', 'collision_flag', 'min_ttc', 'distance',
                    'ego_x', 'ego_y', 'ego_velocity', 'ego_yaw',
                    'npc_x', 'npc_y', 'npc_velocity', 'npc_yaw'
                ]
                
                # Add scenario parameter columns dynamically
                scenario_fieldnames = []
                if self.scenario_parameters:
                    # Order scenario columns consistently
                    scenario_keys = ['scenario_name', 'scenario_type'] + [k for k in sorted(self.scenario_parameters.keys()) 
                                                                         if k not in ['scenario_name', 'scenario_type']]
                    scenario_fieldnames = scenario_keys
                
                # Combine all fieldnames
                fieldnames = base_fieldnames + scenario_fieldnames
                
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                
                for result in self.experiment_results:
                    writer.writerow(result)
            
            self.logger.info(f"Experiment results saved to: {csv_file}")
            
            # Print summary statistics including scenario info
            total_runs = len(self.experiment_results)
            collisions = sum(1 for r in self.experiment_results if r['collision_flag'] is True)
            collision_rate = (collisions / total_runs * 100) if total_runs > 0 else 0
            
            self.logger.info("=" * 60)
            self.logger.info("EXPERIMENT SUMMARY:")
            self.logger.info("=" * 60)
            if self.scenario_parameters:
                self.logger.info(f"Scenario: {self.scenario_parameters.get('scenario_name', 'Unknown')}")
                self.logger.info(f"Scenario Type: {self.scenario_parameters.get('scenario_type', 'Unknown')}")
            self.logger.info(f"Total runs: {total_runs}")
            self.logger.info(f"Collisions: {collisions}")
            self.logger.info(f"Collision rate: {collision_rate:.1f}%")
            self.logger.info(f"Successful runs: {total_runs - collisions}")
            self.logger.info("=" * 60)
            
        except Exception as e:
            self.logger.error(f"Error saving results to CSV: {e}")
                     
    def clear_existing_logs(self):
        """Clear existing log files to prevent mixing with previous experiments."""
        self.logger.info("Clearing existing log files...")
        
        # Clear epoch result file from previous runs
        epoch_file = self.script_dir / "epoch_result.json"
        if epoch_file.exists():
            try:
                epoch_file.unlink()
                self.logger.debug("Removed previous epoch_result.json")
            except Exception as e:
                self.logger.debug(f"Could not remove epoch_result.json: {e}")
        
        # Clear other output files if needed
        patterns = ["SPEC_*", "*.npy", "*.csv", "*.npz"]
        for pattern in patterns:
            for file_path in self.script_dir.glob(pattern):
                try:
                    file_path.unlink()
                except Exception as e:
                    self.logger.debug(f"Could not remove {file_path}: {e}")

    def extract_scenario_parameters(self):
        """Extract scenario parameters from the route XML for consistent CSV columns."""
        from utils.xml_utils import parse_route_scenarios
        
        scenarios_info = parse_route_scenarios(self.route_file, self.route_id, self.project_root, self.logger)
        
        # Flatten all scenario parameters into a single dict
        all_params = {}
        for scenario_name, info in scenarios_info.items():
            scenario_type = info['type']
            parameters = info['parameters']
            
            # Add scenario type and name
            all_params['scenario_name'] = scenario_name
            all_params['scenario_type'] = scenario_type
            
            # Add all parameters with prefixes to avoid conflicts
            if isinstance(parameters, dict):
                for param_name, param_value in parameters.items():
                    all_params[f'param_{param_name}'] = param_value
            
            # For now, we'll use the first non-Data_Collect scenario
            # In future, this could be enhanced to handle multiple scenarios
            break
        
        self.scenario_parameters = all_params
        return all_params
        
    def cleanup(self):
        """Cleanup all processes and restore terminal."""
        self.logger.info("Cleaning up processes...")
        self.kill_carla_processes(force=True)
        self._restore_terminal()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Scenario Fuzzing Framework for CARLA",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Random search
  python sim_runner.py 1 --method random --iterations 20
  
  # PSO search  
  python sim_runner.py 1 --method pso --iterations 50
  
  # GA search with custom parameters
  python sim_runner.py 2 --method ga --iterations 30 --headless
  
  # Custom route file
  python sim_runner.py 3 --route-file routes_custom --method pso
        """
    )
    
    parser.add_argument("route_id", type=str, help="ID of the route to fuzz")
    parser.add_argument("--method", type=str, default="random", 
                       choices=['random', 'pso', 'ga'],
                       help="Search method to use (default: random)")
    parser.add_argument("--iterations", type=int, default=10,
                       help="Number of iterations/generations (default: 10)")
    parser.add_argument("--route-file", type=str, default="routes_carlo",
                       help="Name of the route file (default: routes_carlo)")
    parser.add_argument("--timeout", type=int, default=300,
                       help="Max seconds to wait for a simulation to complete (default: 300)")
    parser.add_argument("--headless", action="store_true",
                       help="Run Carla without a window")
    parser.add_argument("--seed", type=int, default=42,
                       help="Random seed for reproducibility (default: 42)")
    parser.add_argument("--restart-gap", type=int, default=5,
                       help="Number of runs before restarting Carla (default: 5)")
    parser.add_argument("--reward-function", type=str, default="ttc",
                       help="Reward function to use for optimization. "
                            "Available: collision, distance, safety_margin, ttc, ttc_div_dist, weighted_multi (default: ttc)")
    
    args = parser.parse_args()
    
    # Validate arguments
    if args.iterations <= 0:
        print("Error: iterations must be positive")
        sys.exit(1)
        
    if args.timeout <= 0:
        print("Error: timeout must be positive")
        sys.exit(1)
    
    # Check SKO availability for PSO/GA
    if args.method in ['pso', 'ga'] and not SKO_AVAILABLE:
        print(f"Error: {args.method} requires scikit-opt library.")
        print("Install with: pip install scikit-opt")
        sys.exit(1)
    
    # Validate reward function
    try:
        RewardRegistry.get_function(args.reward_function)
    except ValueError:
        available_functions = RewardRegistry.list_functions()
        print(f"Error: Unknown reward function '{args.reward_function}'")
        print(f"Available reward functions: {available_functions}")
        sys.exit(1)
    
    # Create and run fuzzer
    fuzzer = ScenarioFuzzer(
        route_id=args.route_id,
        search_method=args.method,
        num_iterations=args.iterations,
        route_file=args.route_file,
        timeout_seconds=args.timeout,
        headless=args.headless,
        random_seed=args.seed,
        restart_gap=args.restart_gap,
        reward_function=args.reward_function
    )
    
    try:
        best_params, best_reward = fuzzer.run_search()
        
        print(f"\n🎯 FUZZING COMPLETED!")
        print(f"Method: {args.method}")
        print(f"Best reward: {best_reward:.3f}")
        print(f"Best parameters: {dict(zip(fuzzer._param_names, best_params)) if best_params else 'None'}")
        print(f"Collision found: {'Yes' if best_reward == 0.0 else 'No'}")
        print(f"Results saved to: {fuzzer.output_dir}")
        
    except KeyboardInterrupt:
        print("\nInterrupted by user")
        fuzzer.cleanup()
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}")
        fuzzer.cleanup()
        sys.exit(1)


if __name__ == "__main__":
    main()
