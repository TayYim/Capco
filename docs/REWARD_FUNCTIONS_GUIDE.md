# Reward Functions Guide

The Carlo fuzzing framework supports multiple reward functions to optimize different aspects of scenario generation. All reward functions are designed for **minimization** (lower values indicate better/more critical scenarios).

## Quick Start

Use the `--reward-function` parameter to select a reward function:

```bash
# Use time-to-collision (default)
python src/simulation/sim_runner.py 1 --reward-function ttc

# Use collision detection only
python src/simulation/sim_runner.py 1 --reward-function collision --method pso

# Use distance-based optimization
python src/simulation/sim_runner.py 1 --reward-function distance --iterations 50
```

## Available Reward Functions

### Core Functions

#### `ttc` (Time-to-Collision) - Default
- **Purpose**: Optimize for minimum time-to-collision
- **Best for**: Finding scenarios with close temporal encounters
- **Returns**:
  - `0.0` if collision occurs (optimal)
  - `min_ttc` if no collision (lower is better)
  - `1000.0` for invalid results

#### `collision` (Binary Collision)
- **Purpose**: Simple collision detection
- **Best for**: When only collision occurrence matters
- **Returns**:
  - `0.0` if collision occurs
  - `1.0` if no collision

#### `distance` (Minimum Distance)
- **Purpose**: Optimize for closest spatial encounters
- **Best for**: Finding scenarios with close spatial proximity
- **Returns**:
  - `0.0` if collision occurs
  - `distance` if no collision (lower is better)
  - `1000.0` for invalid results

### Advanced Functions

#### `ttc_div_dist` (TTC/Distance Ratio)
- **Purpose**: Balance temporal and spatial proximity
- **Best for**: Comprehensive near-miss scenarios
- **Logic**: Uses `ttc/distance` ratio when both available, falls back to individual metrics
- **Returns**: Lower ratio indicates faster approach to closer target

#### `weighted_multi` (Multi-Objective)
- **Purpose**: Combine multiple safety factors with weights
- **Best for**: Holistic safety evaluation
- **Factors**:
  - TTC (weight: 0.5)
  - Distance (weight: 0.3) 
  - Velocity (weight: 0.2)

#### `safety_margin` (Safety Margin)
- **Purpose**: Normalized safety metric considering both time and space
- **Best for**: Research on safety margins and risk assessment
- **Logic**: Normalizes TTC and distance, returns inverse of minimum safety margin

## Adding Custom Reward Functions

### Step 1: Define Your Function

Add to `src/rewards.py`:

```python
@RewardRegistry.register('my_custom_reward')
def my_custom_reward(result: Dict) -> float:
    """
    Your custom reward function description.
    
    Args:
        result: Dictionary containing simulation results
        
    Returns:
        Float value (lower is better for optimization)
    """
    collision_flag = result.get('collision_flag', False)
    
    if collision_flag:
        return 0.0  # Best possible - collision found
    
    # Your custom logic here
    # Use available data: min_ttc, distance, ego_velocity, etc.
    
    return your_calculated_reward
```

### Step 2: Available Data Fields

The `result` dictionary contains:

```python
{
    'collision_flag': bool,      # Whether collision occurred
    'min_ttc': float,           # Minimum time-to-collision
    'distance': float,          # Minimum distance between vehicles
    'ego_velocity': float,      # Ego vehicle velocity
    'npc_velocity': float,      # NPC vehicle velocity
    'ego_x': float,            # Ego vehicle X position
    'ego_y': float,            # Ego vehicle Y position
    'ego_yaw': float,          # Ego vehicle yaw angle
    'npc_x': float,            # NPC vehicle X position
    'npc_y': float,            # NPC vehicle Y position
    'npc_yaw': float,          # NPC vehicle yaw angle
    'run_number': int          # Current run number
}
```

### Step 3: Test Your Function

```python
# Test with sample data
test_data = {
    'collision_flag': False,
    'min_ttc': 2.5,
    'distance': 15.0,
    'ego_velocity': 10.0
}

reward = my_custom_reward(test_data)
print(f"Reward: {reward}")
```

## Best Practices

### Function Design
1. **Always minimize**: Lower values should indicate better/more critical scenarios
2. **Handle edge cases**: Check for None values and invalid data
3. **Use appropriate penalties**: Return high values (e.g., 1000.0) for invalid results
4. **Document clearly**: Explain the purpose and logic in docstrings

### Choosing Reward Functions
- **Research goal**: Collision detection → `collision`
- **Research goal**: Near-miss analysis → `ttc` or `distance`
- **Research goal**: Complex safety analysis → `weighted_multi` or `safety_margin`
- **Research goal**: Balanced approach → `ttc_div_dist`

### Performance Considerations
- Keep functions computationally simple for large-scale fuzzing
- Avoid complex calculations that slow down optimization
- Cache expensive computations if needed

## Examples

### Research Example 1: Collision Detection Study
```bash
python src/simulation/sim_runner.py 1 --reward-function collision --method ga --iterations 100
```

### Research Example 2: Near-Miss Analysis
```bash
python src/simulation/sim_runner.py 2 --reward-function ttc_div_dist --method pso --iterations 50
```

### Research Example 3: Safety Margin Research
```bash
python src/simulation/sim_runner.py 3 --reward-function safety_margin --method random --iterations 200
```

## Validation

Test all reward functions with:
```bash
python -c "from src.rewards import validate_all_functions; validate_all_functions()"
```

## Troubleshooting

### Common Issues

1. **"Unknown reward function" error**:
   - Check available functions: `python -c "from src.rewards import RewardRegistry; print(RewardRegistry.list_functions())"`
   - Ensure function is properly registered with `@RewardRegistry.register('name')`

2. **Reward function returns NaN**:
   - Check for division by zero in your calculations
   - Handle None/missing data appropriately

3. **Optimization not converging**:
   - Ensure reward landscape has reasonable gradients
   - Consider scaling your reward values appropriately

### Getting Help

- Check function descriptions: Run the rewards module directly
- Review existing functions in `src/rewards.py` for examples
- Validate your function before running full experiments 