# Parameter Ranges Configuration Guide

This guide explains how to configure parameter ranges for scenario fuzzing in the CARLA framework. The parameter range system uses a hierarchical configuration approach that makes it easy to manage ranges for different scenarios and parameter types.

## Overview

The fuzzing framework uses parameter ranges to determine the valid values for each fuzzable parameter during search. The system automatically resolves ranges using the following priority order:

1. **User-provided overrides** (highest priority) - command line or explicit parameters
2. **Scenario-specific overrides** - defined in the configuration file
3. **Parameter type defaults** - semantic categories (velocity, position, timing)
4. **Intelligent defaults** - based on current XML values
5. **Fallback ranges** - conservative defaults (lowest priority)

## Configuration File Structure

The main configuration file is located at `config/parameter_ranges.yaml`. It has three main sections:

### 1. Parameter Types (Global Defaults)

```yaml
parameter_types:
  # Velocity parameters (m/s)
  velocity:
    absolute_v: [5.0, 25.0]      # Vehicle absolute velocity
    relative_v: [-15.0, 15.0]    # Relative velocity difference
    v_ego: [0.1, 17.0]           # Ego vehicle velocity
    v_1: [0.0, 15.0]             # NPC 1 velocity
    
  # Position parameters (m)
  position:
    relative_p: [5.0, 80.0]      # Relative position distance
    r_ego: [10.0, 70.0]          # Ego position range
    r_1: [10.0, 70.0]            # NPC 1 position range
    
  # Timing parameters (s)
  timing:
    delay: [0.1, 3.0]            # Scenario trigger delay
    duration: [1.0, 10.0]        # Scenario duration
```

### 2. Scenario-Specific Overrides

```yaml
scenario_overrides:
  OSG_CutIn_One:
    absolute_v: [8.0, 20.0]      # More conservative for cut-in
    relative_p: [10.0, 50.0]     # Closer range for cut-in
    
  OSG_Junction:
    v_ego: [1.0, 12.0]           # Lower speeds at junctions
    r_1: [20.0, 60.0]            # NPC positioning for junctions
```

### 3. Fallback Configuration

```yaml
fallback:
  strategy: "intelligent_defaults"  # Options: intelligent_defaults, conservative, wide_range
  conservative_defaults:
    velocity_range: [1.0, 15.0]
    position_range: [5.0, 50.0]
    timing_range: [0.1, 5.0]
```

## Adding Ranges for New Scenarios

### Step 1: Identify Your Scenario Parameters

First, examine your scenario XML to identify the fuzzable parameters:

```xml
<scenario name="MyNewScenario_1" type="MyNewScenario">
    <trigger_point x="100" y="200" z="0.5" yaw="90" />
    <my_velocity value="15.0" />
    <my_distance value="30.0" />
    <my_timing value="2.5" />
</scenario>
```

In this example, the fuzzable parameters are:
- `my_velocity` (velocity type)
- `my_distance` (position type)  
- `my_timing` (timing type)

### Step 2: Choose Configuration Strategy

You have several options for setting ranges:

#### Option A: Use Existing Parameter Types (Recommended)

If your parameters follow standard naming conventions, they may automatically inherit from parameter types:

```yaml
# Add to parameter_types if using standard names
parameter_types:
  velocity:
    my_velocity: [5.0, 25.0]     # Add your velocity parameter
  position:
    my_distance: [10.0, 80.0]   # Add your position parameter
  timing:
    my_timing: [0.5, 5.0]       # Add your timing parameter
```

#### Option B: Create Scenario-Specific Overrides

For scenario-specific tuning, add to the `scenario_overrides` section:

```yaml
scenario_overrides:
  MyNewScenario:
    my_velocity: [8.0, 20.0]     # Conservative velocity range
    my_distance: [15.0, 60.0]    # Specific distance range
    my_timing: [1.0, 4.0]        # Specific timing range
```

#### Option C: Rely on Intelligent Defaults

If you don't specify ranges, the system will create intelligent defaults based on the current XML values:

- **Velocity parameters**: 50% to 150% of current value
- **Position parameters**: 70% to 130% of current value  
- **Timing parameters**: 50% to 200% of current value
- **Generic parameters**: 80% to 120% of current value

### Step 3: Test Your Configuration

Run a simple test to verify your configuration works:

```bash
python src/simulation/sim_runner.py YOUR_ROUTE_ID --method random --iterations 5
```

Check the log output for parameter range information:

```
INFO - Parameter ranges loaded from: config/parameter_ranges.yaml
INFO - Scenario type detected: MyNewScenario
INFO - Using scenario-specific overrides for MyNewScenario
INFO - Search bounds set for 3 parameters: ['my_velocity', 'my_distance', 'my_timing']
```

## Best Practices

### 1. Parameter Naming Conventions

Use descriptive names that indicate parameter type:

- **Velocity**: `*_v`, `*velocity*`, `*speed*`
- **Position**: `*_p`, `*position*`, `*_r`, `*distance*`
- **Timing**: `*time*`, `*delay*`, `*duration*`

### 2. Range Selection Guidelines

- **Safety First**: Start with conservative ranges, then gradually expand
- **Physical Realism**: Ensure ranges represent realistic driving scenarios
- **Scenario Context**: Consider the specific scenario requirements

| Parameter Type | Typical Range | Notes |
|---------------|---------------|-------|
| Vehicle Speed | 0-30 m/s | City: 0-15 m/s, Highway: 5-30 m/s |
| Position Distance | 5-100 m | Depends on scenario scale |
| Timing Delays | 0.1-5.0 s | Human reaction times: 0.2-2.0 s |

### 3. Scenario-Specific Considerations

| Scenario Type | Speed Ranges | Position Ranges | Special Notes |
|--------------|--------------|-----------------|---------------|
| Cut-in | 8-20 m/s | 10-50 m | Conservative for safety |
| Junction | 1-12 m/s | 15-60 m | Lower speeds at intersections |
| Highway | 15-30 m/s | 20-150 m | Higher speeds, longer distances |
| Parking | 0.5-5 m/s | 1-20 m | Very low speeds, short distances |

## Advanced Configuration

### Multiple NPCs

For scenarios with multiple NPCs, use numbered parameters:

```yaml
scenario_overrides:
  MyMultiNPCScenario:
    v_1: [5.0, 15.0]        # First NPC velocity
    v_2: [8.0, 20.0]        # Second NPC velocity
    r_1: [20.0, 50.0]       # First NPC position
    r_2: [30.0, 70.0]       # Second NPC position
```

### Conditional Parameters

Some parameters may depend on others. While the current system doesn't support dependencies directly, you can set complementary ranges:

```yaml
scenario_overrides:
  MyScenario:
    leading_vehicle_speed: [10.0, 20.0]
    following_vehicle_speed: [8.0, 18.0]  # Slightly lower to allow following
    gap_distance: [10.0, 50.0]           # Reasonable following distance
```

## Troubleshooting

### Common Issues

1. **Parameter Not Found**
   ```
   WARNING - No range found for parameter my_param, skipping
   ```
   **Solution**: Add the parameter to `parameter_types` or `scenario_overrides`

2. **Invalid Range Format**
   ```
   WARNING - Invalid range for velocity.my_speed: [20, 10]
   ```
   **Solution**: Ensure min_value ≤ max_value and both are numbers

3. **Configuration File Not Found**
   ```
   WARNING - Parameter ranges config file not found: config/parameter_ranges.yaml
   ```
   **Solution**: Ensure the config file exists in the correct location

### Debug Mode

Enable debug logging to see detailed parameter resolution:

```bash
python src/simulation/sim_runner.py YOUR_ROUTE_ID --method random --iterations 5 --verbose
```

This will show how each parameter range is resolved:

```
DEBUG - Using scenario override for absolute_v in OSG_CutIn_One: (8.0, 20.0)
DEBUG - Using parameter type default for relative_p: (5.0, 80.0)
DEBUG - Using intelligent default for new_param: (12.0, 18.0)
```

## Example Complete Configuration

Here's a complete example for a new scenario:

```yaml
# Add to config/parameter_ranges.yaml

parameter_types:
  velocity:
    # ... existing parameters ...
    approach_speed: [5.0, 25.0]
    crossing_speed: [1.0, 15.0]
  
  position:
    # ... existing parameters ...
    approach_distance: [20.0, 100.0]
    crossing_distance: [5.0, 30.0]

scenario_overrides:
  PedestrianCrossing:
    approach_speed: [8.0, 15.0]     # Conservative approach
    crossing_speed: [1.0, 8.0]      # Slow crossing
    approach_distance: [30.0, 80.0] # Sufficient detection distance
    crossing_distance: [8.0, 25.0]  # Crosswalk width range
```

This configuration provides both global defaults and scenario-specific fine-tuning for a pedestrian crossing scenario.

## Summary

The parameter range system is designed to be:
- **Easy to use**: Automatic detection and intelligent defaults
- **Easy to maintain**: Centralized YAML configuration
- **Flexible**: Multiple levels of customization
- **Safe**: Conservative defaults with validation

Start with the existing configuration, add your scenario-specific overrides as needed, and gradually refine ranges based on your testing results. 