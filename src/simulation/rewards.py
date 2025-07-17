"""
Reward Functions for Scenario Fuzzing

This module provides a flexible framework for defining reward functions used in
scenario-based fuzzing. All reward functions should be designed for minimization
(lower values are better).

Usage:
    from rewards import RewardRegistry
    
    # Get available reward functions
    available = RewardRegistry.list_functions()
    
    # Get a specific reward function
    reward_func = RewardRegistry.get_function('ttc')
    
    # Calculate reward
    reward = reward_func(result_data)

Adding New Reward Functions:
    @RewardRegistry.register('your_function_name')
    def your_reward_function(result: Dict) -> float:
        # Your implementation here
        # Return lower values for better scenarios
        pass
"""

from typing import Dict, Callable, List
import math
import logging

logger = logging.getLogger(__name__)


class RewardRegistry:
    """Registry for reward functions with automatic discovery and validation."""
    
    _functions: Dict[str, Callable[[Dict], float]] = {}
    
    @classmethod
    def register(cls, name: str):
        """Decorator to register a reward function."""
        def decorator(func: Callable[[Dict], float]):
            if name in cls._functions:
                logger.warning(f"Overwriting existing reward function: {name}")
            cls._functions[name] = func
            logger.debug(f"Registered reward function: {name}")
            return func
        return decorator
    
    @classmethod
    def get_function(cls, name: str) -> Callable[[Dict], float]:
        """Get a reward function by name."""
        if name not in cls._functions:
            available = cls.list_functions()
            raise ValueError(f"Unknown reward function: '{name}'. Available: {available}")
        return cls._functions[name]
    
    @classmethod
    def list_functions(cls) -> List[str]:
        """List all available reward function names."""
        return sorted(cls._functions.keys())
    
    @classmethod
    def validate_function(cls, name: str, test_data: Dict) -> bool:
        """Validate that a reward function works with test data."""
        try:
            func = cls.get_function(name)
            result = func(test_data)
            return isinstance(result, (int, float)) and not math.isnan(result)
        except Exception as e:
            logger.error(f"Reward function '{name}' failed validation: {e}")
            return False


# ============================================================================
# Core Reward Functions
# ============================================================================

@RewardRegistry.register('ttc')
def time_to_collision_reward(result: Dict) -> float:
    """
    Time-to-collision based reward (default behavior).
    
    Returns:
        0.0 if collision occurs (best possible)
        min_ttc if no collision (lower TTC = better)
        1000.0 for invalid results (penalty)
    """
    collision_flag = result.get('collision_flag', False)
    min_ttc = result.get('min_ttc', None)
    
    if collision_flag:
        return 0.0  # Best possible - collision found
    elif min_ttc is not None and min_ttc > 0:
        return min_ttc  # Lower TTC is better
    else:
        return 1000.0  # Penalty for invalid results


@RewardRegistry.register('collision')
def collision_only_reward(result: Dict) -> float:
    """
    Binary collision reward - only cares about collision occurrence.
    
    Returns:
        0.0 if collision occurs
        1.0 if no collision
    """
    collision_flag = result.get('collision_flag', False)
    return 0.0 if collision_flag else 1.0


@RewardRegistry.register('distance')
def distance_reward(result: Dict) -> float:
    """
    Distance-based reward - prioritizes closer encounters.
    
    Returns:
        0.0 if collision occurs
        distance value if no collision (lower = better)
        1000.0 for invalid results
    """
    collision_flag = result.get('collision_flag', False)
    distance = result.get('distance', None)
    
    if collision_flag:
        return 0.0  # Best possible
    elif distance is not None and distance > 0:
        return distance  # Lower distance is better
    else:
        return 1000.0  # Penalty


@RewardRegistry.register('ttc_div_dist')
def ttc_distance_ratio_reward(result: Dict) -> float:
    """
    Combined TTC and distance reward using ratio.
    
    Balances both time-to-collision and distance for more nuanced evaluation.
    
    Returns:
        0.0 if collision occurs
        ttc/distance ratio if both available (lower = better)
        Individual metric if only one available
        1000.0 for invalid results
    """
    collision_flag = result.get('collision_flag', False)
    min_ttc = result.get('min_ttc', None)
    distance = result.get('distance', None)
    
    if collision_flag:
        return 0.0  # Best possible
    
    # Use ratio if both metrics available
    if min_ttc is not None and distance is not None and min_ttc > 0 and distance > 0:
        return min_ttc / distance  # Lower ratio = better (close + fast approach)
    
    # Fall back to individual metrics
    elif min_ttc is not None and min_ttc > 0:
        return min_ttc
    elif distance is not None and distance > 0:
        return distance
    else:
        return 1000.0  # Penalty


# ============================================================================
# Advanced Reward Functions
# ============================================================================

@RewardRegistry.register('weighted_multi')
def weighted_multi_objective_reward(result: Dict) -> float:
    """
    Multi-objective reward combining multiple factors with weights.
    
    Combines TTC, distance, and velocity considerations.
    """
    collision_flag = result.get('collision_flag', False)
    
    if collision_flag:
        return 0.0  # Best possible
    
    min_ttc = result.get('min_ttc', None)
    distance = result.get('distance', None)
    ego_velocity = result.get('ego_velocity', None)
    
    # Base penalty
    reward = 1000.0
    
    # TTC component (weight: 0.5)
    if min_ttc is not None and min_ttc > 0:
        ttc_component = min_ttc * 0.5
        reward = min(reward, ttc_component)
    
    # Distance component (weight: 0.3)
    if distance is not None and distance > 0:
        dist_component = distance * 0.3
        reward = min(reward, dist_component)
    
    # Velocity component (weight: 0.2) - higher velocity makes scenarios more dangerous
    if ego_velocity is not None and ego_velocity > 0:
        vel_component = (1.0 / (ego_velocity + 1.0)) * 0.2  # Inverse relationship
        reward = min(reward, ttc_component + dist_component + vel_component)
    
    return reward


@RewardRegistry.register('safety_margin')
def safety_margin_reward(result: Dict) -> float:
    """
    Safety margin based reward considering both spatial and temporal safety.
    
    Uses a safety metric that combines distance and time considerations.
    """
    collision_flag = result.get('collision_flag', False)
    
    if collision_flag:
        return 0.0  # Best possible
    
    min_ttc = result.get('min_ttc', None)
    distance = result.get('distance', None)
    
    # Safety margin calculation
    if min_ttc is not None and distance is not None and min_ttc > 0 and distance > 0:
        # Safety margin as minimum of normalized TTC and distance
        # Normalize by typical values: TTC ~5s, distance ~50m
        normalized_ttc = min_ttc / 5.0
        normalized_distance = distance / 50.0
        safety_margin = min(normalized_ttc, normalized_distance)
        return 1.0 / (safety_margin + 0.1)  # Lower safety margin = higher risk = lower reward
    
    # Fall back to available metrics
    elif min_ttc is not None and min_ttc > 0:
        return min_ttc
    elif distance is not None and distance > 0:
        return distance
    else:
        return 1000.0  # Penalty


# ============================================================================
# Utility Functions
# ============================================================================

def validate_all_functions():
    """Validate all registered reward functions with test data."""
    test_data = {
        'collision_flag': False,
        'min_ttc': 2.5,
        'distance': 15.0,
        'ego_velocity': 10.0,
        'npc_velocity': 8.0,
        'run_number': 1
    }
    
    print("Validating reward functions:")
    for name in RewardRegistry.list_functions():
        is_valid = RewardRegistry.validate_function(name, test_data)
        status = "✅" if is_valid else "❌"
        print(f"  {status} {name}")
    
    return all(RewardRegistry.validate_function(name, test_data) 
              for name in RewardRegistry.list_functions())


def get_function_descriptions() -> Dict[str, str]:
    """Get descriptions of all available reward functions."""
    descriptions = {}
    for name in RewardRegistry.list_functions():
        func = RewardRegistry.get_function(name)
        # Extract first line of docstring as description
        if func.__doc__:
            description = func.__doc__.strip().split('\n')[0]
            descriptions[name] = description
        else:
            descriptions[name] = "No description available"
    return descriptions


if __name__ == "__main__":
    # Demo and validation
    print("Available Reward Functions:")
    descriptions = get_function_descriptions()
    for name, desc in descriptions.items():
        print(f"  {name}: {desc}")
    
    print(f"\nValidation Results:")
    validate_all_functions() 