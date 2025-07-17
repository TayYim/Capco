# Scenario Fuzzing Framework

A comprehensive, modular fuzzing framework for finding critical scenarios in CARLA autonomous vehicle simulations. This framework supports multiple search algorithms including random search, Particle Swarm Optimization (PSO), and Genetic Algorithms (GA).

## Overview

The Scenario Fuzzing Framework automatically searches for parameter combinations that lead to critical scenarios (near-collisions or collisions) in autonomous vehicle simulations. By systematically exploring the parameter space of driving scenarios, it helps identify edge cases and potential safety issues.

### Key Features

- **Multiple Search Algorithms**: Random search, PSO, and GA
- **Modular Architecture**: Easy to extend with new search methods
- **Automatic Parameter Detection**: Extracts mutable parameters from scenario XML files
- **Comprehensive Result Tracking**: CSV histories, JSON summaries, detailed logs
- **Production Ready**: Robust error handling, signal management, cleanup
- **Interactive Demo**: User-friendly demonstration scripts

### Search Methods

1. **Random Search**: Baseline method that randomly samples the parameter space
2. **PSO (Particle Swarm Optimization)**: Efficient continuous optimization inspired by swarm behavior
3. **GA (Genetic Algorithm)**: Evolutionary approach good for complex multi-modal problems

## Quick Start

### Prerequisites

```bash
# Required packages
pip install numpy pandas

# Optional for PSO/GA (recommended)
pip install scikit-opt
```

### Basic Usage

```bash
# Random search (always available)
python src/simulation/sim_runner.py 1 --method random --iterations 20

# PSO search (requires scikit-opt)
python src/simulation/sim_runner.py 1 --method pso --iterations 50

# GA search (requires scikit-opt)
python src/simulation/sim_runner.py 1 --method ga --iterations 30
```

### Interactive Demo

```bash
# Run the interactive demo
./run_fuzzing_demo.sh
```

## Detailed Usage

### Command Line Interface

```bash
python src/simulation/sim_runner.py <route_id> [options]

Options:
  --method {random,pso,ga}     Search method (default: random)
  --iterations N               Number of iterations (default: 10)
  --route-file NAME           Route file name (default: routes_carlo)
  --timeout N                 Simulation timeout seconds (default: 300)
  --headless                  Run CARLA without graphics
  --seed N                    Random seed (default: 42)
  --restart-gap N             Restart CARLA every N runs (default: 5)
```

### Examples

```bash
# Quick random test
python src/simulation/sim_runner.py 1 --method random --iterations 10

# Comprehensive PSO search
python src/simulation/sim_runner.py 1 --method pso --iterations 100 --headless

# GA with custom timeout
python src/simulation/sim_runner.py 2 --method ga --iterations 50 --timeout 600

# Custom route file
python src/simulation/sim_runner.py 3 --route-file routes_custom --method pso
```

### Demo Script

The demo script provides an interactive way to explore the framework:

```bash
# Run interactive demo
./run_fuzzing_demo.sh

# Or use the Python demo directly
python src/simulation/demo_fuzzing.py 1 --method pso --iterations 20
python src/simulation/demo_fuzzing.py 1 --compare-all
python src/simulation/demo_fuzzing.py 1 --quick-test
```

## Algorithm Configuration

### Random Search

No additional configuration needed. Good for:
- Quick baseline tests
- Simple parameter spaces
- When other methods are unavailable

### PSO (Particle Swarm Optimization)

Default parameters (can be customized in code):
- Population size: 20
- Inertia weight (w): 0.8
- Cognitive parameter (c1): 0.5
- Social parameter (c2): 0.5

Good for:
- Continuous optimization problems
- Balanced exploration/exploitation
- Medium-complexity parameter spaces

### GA (Genetic Algorithm)

Default parameters (can be customized in code):
- Population size: 50
- Mutation probability: 0.1
- Precision: 1e-7

Good for:
- Complex multi-modal problems
- Large parameter spaces
- When global optimum is important

## Parameter Configuration

### Automatic Parameter Detection

The framework automatically detects mutable parameters from XML scenario files by looking for elements with `mutable="true"` attributes.

### Custom Parameter Ranges

You can customize parameter ranges by modifying the `DEFAULT_PARAMETER_RANGES` in the code:

```python
DEFAULT_PARAMETER_RANGES = {
    'absolute_v': (5.0, 25.0),      # Vehicle velocity in m/s
    'relative_p': (5.0, 80.0),      # Relative position in meters  
    'relative_v': (-15.0, 15.0),    # Relative velocity in m/s
    'r_ego': (10.0, 70.0),         # Ego position range
    'v_ego': (0.1, 17.0),          # Ego velocity range
    # Add more parameters as needed
}
```

## Understanding Results

### Output Files

Each fuzzing run creates an output directory with:

- `search_history.csv`: Complete search history with all parameters and results
- `best_solution.json`: Best parameter combination found
- `experiment_results.csv`: Detailed simulation results
- `fuzzing.log`: Detailed execution log

### Reward Interpretation

The framework uses a reward system where **lower values indicate more critical scenarios**:

- **0.0**: Collision detected (most critical)
- **Low values (0.1-2.0)**: Very close calls, near-misses
- **Medium values (2.0-10.0)**: Somewhat risky scenarios
- **High values (>10.0)**: Safe scenarios with large safety margins

### Key Metrics

- **min_ttc**: Minimum time-to-collision during scenario
- **collision_flag**: Whether a collision occurred
- **distance**: Final distance between vehicles
- **Parameters**: The scenario parameter values that produced this result

## Extending the Framework

### Adding New Search Methods

1. Create a new search method function:

```python
@SearchMethodRegistry.register('my_method')
@search_method_decorator('my_method')
def search_my_method(self, iterations: int = None) -> Tuple[List[float], float]:
    """Your custom search method."""
    # Implementation here
    return best_parameters, best_reward
```

2. Add it to the supported methods list:

```python
SUPPORTED_SEARCH_METHODS = ['random', 'pso', 'ga', 'my_method']
```

### Adding New Parameter Types

1. Extend `DEFAULT_PARAMETER_RANGES` with your parameter bounds
2. Ensure your XML scenarios have `mutable="true"` attributes
3. The framework will automatically detect and include them

## Troubleshooting

### Common Issues

**ImportError: No module named 'sko'**
```bash
pip install scikit-opt
```

**CARLA connection issues**
- Check CARLA path in configuration
- Ensure CARLA is not already running
- Try increasing timeout values

**No parameters detected**
- Verify XML files have `mutable="true"` attributes
- Check route ID exists in the XML file
- Verify file paths are correct

**Simulation timeouts**
- Increase `--timeout` value
- Use `--headless` for better performance
- Check system resources

### Performance Tips

1. **Use headless mode** for production runs: `--headless`
2. **Start with random search** to validate setup
3. **Use appropriate iteration counts**:
   - Random: 20-50 iterations
   - PSO: 50-100 iterations
   - GA: 30-80 iterations
4. **Monitor system resources** during long runs
5. **Use restart-gap** to prevent CARLA memory issues

### Debugging

1. Check `fuzzing.log` for detailed execution information
2. Use `--timeout` to prevent hanging simulations
3. Start with `--quick-test` mode for validation
4. Monitor CARLA processes: `ps aux | grep -i carla`

## Best Practices

### Method Selection

- **Random Search**: Quick tests, baselines, simple scenarios
- **PSO**: Balanced approach, most scenarios, good default choice
- **GA**: Complex scenarios, thorough exploration, when PSO plateaus

### Parameter Tuning

1. Start with default ranges and adjust based on results
2. Use domain knowledge to set realistic bounds
3. Consider parameter interactions and dependencies
4. Monitor convergence in search_history.csv

### Production Usage

1. Use appropriate iteration counts for your time budget
2. Run multiple seeds for statistical significance
3. Archive results with descriptive names
4. Document parameter ranges and reasoning

## Advanced Usage

### Batch Processing

```bash
# Run multiple routes
for route in 1 2 3; do
    python src/simulation/sim_runner.py $route --method pso --iterations 50
done

# Compare methods across routes
python src/simulation/demo_fuzzing.py 1 --compare-all --iterations 30
python src/simulation/demo_fuzzing.py 2 --compare-all --iterations 30
```

### Result Analysis

```python
import pandas as pd

# Load and analyze results
df = pd.read_csv('output/fuzzing_*/search_history.csv')
print(df.groupby('method')['reward'].describe())

# Plot convergence
import matplotlib.pyplot as plt
df.groupby('method')['reward'].plot()
plt.show()
```

## Contributing

### Code Style

- Follow PEP 8 for Python code
- Use type hints where possible
- Add docstrings to all public methods
- Include examples in docstrings

### Testing

- Test new search methods with known scenarios
- Validate parameter detection with various XML formats
- Ensure proper cleanup and error handling

### Documentation

- Update this README for new features
- Add examples for new functionality
- Document parameter ranges and their meanings

## License

[Your license information here]

## Support

For issues and questions:
1. Check the troubleshooting section above
2. Review the logs in `fuzzing.log`
3. Open an issue with:
   - Command used
   - Error messages
   - System information
   - Log excerpts 