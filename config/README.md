# Configuration Files

This directory contains configuration files for the CARLA scenario fuzzing framework.

## Parameter Ranges Configuration

### File: `parameter_ranges.yaml`

This file defines the parameter ranges used for scenario fuzzing. It provides a hierarchical system for managing parameter ranges across different scenarios and parameter types.

### Quick Start

1. **Use existing configuration**: The default configuration should work for most scenarios automatically.

2. **Add new parameter types**: If you have new parameters that follow standard naming conventions, add them to the appropriate category in `parameter_types`:

```yaml
parameter_types:
  velocity:
    my_new_velocity_param: [5.0, 20.0]
  position:
    my_new_position_param: [10.0, 50.0]
```

3. **Add scenario-specific overrides**: For fine-tuning specific scenarios, add entries to `scenario_overrides`:

```yaml
scenario_overrides:
  MyNewScenario:
    absolute_v: [8.0, 15.0]  # More conservative range
    relative_p: [15.0, 40.0] # Specific position range
```

4. **Test your configuration**: Run the fuzzer to see if your parameters are detected correctly:

```bash
python src/simulation/sim_runner.py YOUR_ROUTE_ID --method random --iterations 5
```

### Documentation

For detailed instructions on setting up parameter ranges for new scenarios, see:
- `docs/PARAMETER_RANGES_GUIDE.md` - Complete guide with examples and best practices

### Key Features

- **Automatic parameter detection** from XML files
- **Hierarchical range resolution** (user overrides → scenario overrides → type defaults → intelligent defaults → fallback)
- **Semantic parameter categorization** (velocity, position, timing)
- **Scenario-specific customization** for fine-tuning
- **Intelligent defaults** based on current XML values
- **Built-in validation** and error handling

### File Structure

```
parameter_ranges.yaml
├── parameter_types/          # Global defaults by parameter category
│   ├── velocity/            # Speed and velocity parameters
│   ├── position/            # Distance and position parameters
│   └── timing/              # Time-related parameters
├── scenario_overrides/      # Scenario-specific range overrides
└── fallback/               # Fallback configuration for unknown parameters
```

### Support

- Check the fuzzer logs for parameter detection and range resolution information
- Use debug mode (`--verbose`) to see detailed parameter resolution
- Refer to the troubleshooting section in the detailed guide for common issues 