#!/usr/bin/env python3
"""
Python script to automate running multiple Carla experiments.
"""

import argparse
import subprocess
import signal
import sys
import os
import time
import threading
import select
import termios
import tty
from pathlib import Path
from datetime import datetime
import shutil
import logging
import sys
import json
import csv
from typing import Optional, List, Tuple, Dict

# Add src directory to Python path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.xml_utils import display_route_info, parse_route_scenarios, validate_route_exists


class CarlaExperimentRunner:
    """Manages the execution of multiple Carla experiments."""
    
    def __init__(self, route_id: str, num_runs: int, route_file: str = "routes_carlo",
                 restart_gap: int = 5, timeout_seconds: int = 300, headless: bool = False):
        self.route_id = route_id
        self.num_runs = num_runs
        self.route_file = route_file
        self.restart_gap = restart_gap
        self.timeout_seconds = timeout_seconds
        self.headless = headless
        
        # Paths
        self.carla_path = Path("/home/tay/Applications/CARLA_LB") # TODO: get it from config file
        self.script_dir = Path(__file__).parent.absolute()
        self.project_root = self.script_dir.parent.parent
        
        # State variables
        self.should_exit = False
        self.carla_running = False
        self.runs_since_restart = 0
        self.carla_process: Optional[subprocess.Popen] = None
        
        # Setup output directory
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.output_dir = self.project_root / "output" / f"experiment_{route_file}_{route_id}_{timestamp}"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Setup logging
        self.setup_logging()
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        # Thread for monitoring user input
        self.input_thread = None
        self.old_settings = None
        
        # Data collection for experiment results
        self.experiment_results = []
        
        # Scenario parameters for this experiment
        self.scenario_parameters = {}
        
    def setup_logging(self):
        """Setup logging to both console and file."""
        log_format = '%(asctime)s - %(levelname)s - %(message)s'
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter('%(levelname)s - %(message)s')
        console_handler.setFormatter(console_formatter)
        
        # File handler
        log_file = self.output_dir / "experiment.log"
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
                    
    def create_summary_log(self) -> Path:
        """Create experiment summary log file."""
        summary_log = self.output_dir / "experiment_summary.log"
        
        with open(summary_log, 'w') as f:
            f.write(f"Experiment Summary - Route ID: {self.route_id}, "
                   f"Route File: {self.route_file}, Runs: {self.num_runs}, "
                   f"Restart Gap: {self.restart_gap}, Started: {datetime.now()}\n")
        
        return summary_log
        
    def log_run_result(self, summary_log: Path, run_num: int, status: str, details: str = ""):
        """Log run result to summary file."""
        with open(summary_log, 'a') as f:
            timestamp = datetime.now()
            f.write(f"Run {run_num} of {self.num_runs} {status} at {timestamp}")
            if details:
                f.write(f" {details}")
            f.write("\n")
            
    def run_experiments(self):
        """Main method to run all experiments."""
        self.logger.info(f"Starting {self.num_runs} experiments with route ID {self.route_id}")
        self.logger.info(f"Using route file: {self.route_file}")
        self.logger.info(f"All results will be saved to: {self.output_dir}")
        self.logger.info(f"Using restart gap of {self.restart_gap} runs")
        self.logger.info(f"Using timeout of {self.timeout_seconds} seconds per simulation")
        self.logger.info(f"Headless mode: {self.headless}")
        self.logger.info("Press 'q' at any time to gracefully terminate after the current run completes.")
        
        # Display route and scenario information
        display_route_info(self.route_file, self.route_id, self.project_root, self.logger)
        
        # Extract scenario parameters for CSV inclusion
        self.extract_scenario_parameters()
        
        # Clear existing logs before starting runs
        self.clear_existing_logs()
        
        # Create summary log
        summary_log = self.create_summary_log()
        
        # Start input monitoring thread
        self.input_thread = threading.Thread(target=self._monitor_user_input, daemon=True)
        self.input_thread.start()
        
        try:
            for run in range(1, self.num_runs + 1):
                if self.should_exit:
                    self.logger.info("Script ended by user.")
                    self.log_run_result(summary_log, run, "terminated early", 
                                      "by user request")
                    break
                    
                self.logger.info(f"Starting run {run} of {self.num_runs} with route ID {self.route_id}")
                self.log_run_result(summary_log, run, "started")
                
                # Check if we need to start/restart Carla
                if not self.carla_running or self.runs_since_restart >= self.restart_gap:
                    if self.carla_running:
                        self.logger.info(f"Restarting Carla after {self.runs_since_restart} runs...")
                        self.kill_carla_processes()
                        
                    if not self.start_carla():
                        self.logger.error("Failed to start Carla. Skipping run.")
                        self.log_run_result(summary_log, run, "skipped", 
                                          "- failed to start Carla")
                        continue
                        
                # Increment counter
                self.runs_since_restart += 1
                
                # Check if Carla is responsive
                if not self.is_carla_responsive():
                    self.logger.error("Carla is not responsive before starting simulation!")
                    self.log_run_result(summary_log, run, "failed", 
                                      "- Carla not responsive before start")
                    
                    # Try to restart
                    if not self.start_carla():
                        self.logger.error("Carla still not responsive after restart! Skipping run.")
                        self.log_run_result(summary_log, run, "skipped", 
                                          "- Carla not responsive after restart")
                        continue
                        
                # Run the simulation
                run_status = self.run_simulation_with_timeout(run)
                
                # Handle simulation result
                if run_status == 124:  # Timeout
                    self.logger.error(f"Simulation TIMED OUT after {self.timeout_seconds} seconds!")
                    self.log_run_result(summary_log, run, "timed out", 
                                      f"after {self.timeout_seconds} seconds")
                    
                    # Force kill and restart
                    self.kill_carla_processes(force=True)
                    self.carla_running = False
                    self.runs_since_restart = 0
                    
                elif run_status != 0:
                    self.logger.error(f"Simulation failed with exit code {run_status}")
                    self.log_run_result(summary_log, run, "failed", 
                                      f"with exit code {run_status}")
                    
                    # Check if Carla is still responsive
                    if not self.is_carla_responsive():
                        self.logger.info("Carla seems to have crashed. Will restart for next run.")
                        self.kill_carla_processes(force=True)
                        self.carla_running = False
                        self.runs_since_restart = 0
                        
                else:
                    self.logger.info(f"Run {run} completed successfully")
                    self.log_run_result(summary_log, run, "completed successfully")
                    
                # Process and collect experiment results
                run_result = self.process_epoch_result(run)
                self.experiment_results.append(run_result)
                
                # Wait between runs (except for last run)
                if run < self.num_runs and not self.should_exit:
                    self.logger.info("Waiting before next run...")
                    time.sleep(5)
                    
        finally:
            # Cleanup
            self.cleanup()
            
        # Save experiment results to CSV
        self.save_results_to_csv()
        
        # Final summary
        self.logger.info(f"All {self.num_runs} experiment runs completed.")
        self.logger.info(f"All results saved to: {self.output_dir}")
        
        with open(summary_log, 'a') as f:
            f.write(f"Experiment completed at {datetime.now()}\n")
            
    def cleanup(self):
        """Cleanup all processes and restore terminal."""
        self.logger.info("Cleaning up processes...")
        self.kill_carla_processes(force=True)
        self._restore_terminal()

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
            for param_name, param_value in parameters.items():
                all_params[f'param_{param_name}'] = param_value
            
            # For now, we'll use the first non-Data_Collect scenario
            # In future, this could be enhanced to handle multiple scenarios
            break
        
        self.scenario_parameters = all_params
        return all_params




def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Automate running multiple Carla experiments",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python sim_runner.py 1 10                              # Run route 1, 10 times
  python sim_runner.py 2 5 --restart-gap 3              # Restart Carla every 3 runs
  python sim_runner.py 3 20 --timeout 600               # 10 minute timeout per sim
  python sim_runner.py 4 15 --headless                  # Run without graphics
  python sim_runner.py 1 5 --route-file routes_custom   # Use custom route file
        """
    )
    
    parser.add_argument("route_id", type=str, help="ID of the route to run")
    parser.add_argument("number_of_runs", type=int, help="Total number of experiment runs")
    parser.add_argument("--route-file", type=str, default="routes_carlo",
                       help="Name of the route file (default: routes_carlo)")
    parser.add_argument("--restart-gap", type=int, default=5,
                       help="Number of runs before restarting Carla (default: 5)")
    parser.add_argument("--timeout", type=int, default=300,
                       help="Max seconds to wait for a simulation to complete (default: 300)")
    parser.add_argument("--headless", action="store_true",
                       help="Run Carla without a window")
    
    args = parser.parse_args()
    
    # Validate arguments
    if args.number_of_runs <= 0:
        print("Error: number_of_runs must be positive")
        sys.exit(1)
        
    if args.restart_gap <= 0:
        print("Error: restart_gap must be positive")
        sys.exit(1)
        
    if args.timeout <= 0:
        print("Error: timeout must be positive")
        sys.exit(1)
    
    # Create and run experiment runner
    runner = CarlaExperimentRunner(
        route_id=args.route_id,
        num_runs=args.number_of_runs,
        route_file=args.route_file,
        restart_gap=args.restart_gap,
        timeout_seconds=args.timeout,
        headless=args.headless
    )
    
    try:
        runner.run_experiments()
    except KeyboardInterrupt:
        print("\nInterrupted by user")
        runner.cleanup()
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}")
        runner.cleanup()
        sys.exit(1)


if __name__ == "__main__":
    main()
