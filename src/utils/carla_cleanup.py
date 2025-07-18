#!/usr/bin/env python3
"""
CARLA cleanup utility for ensuring clean simulation environment.

This script provides functions to properly clean up CARLA processes
and ensure port availability before starting new experiments.
"""

import subprocess
import time
import logging
from typing import List, Optional


def kill_carla_processes(logger: Optional[logging.Logger] = None) -> bool:
    """
    Kill all CARLA-related processes.
    
    Args:
        logger: Optional logger for output
        
    Returns:
        True if cleanup was successful
    """
    if logger is None:
        logger = logging.getLogger(__name__)
    
    try:
        # List of processes to kill
        processes = [
            "CarlaUE4", 
            "leaderboard_evaluator.py", 
            "scenario_runner",
            "python.*leaderboard_evaluator",
            "python.*scenario_runner"
        ]
        
        logger.info("Killing CARLA-related processes...")
        
        # First try graceful termination
        for process in processes:
            try:
                cmd = ["pkill", "-TERM", "-f", process]
                result = subprocess.run(cmd, capture_output=True, check=False)
                if result.returncode == 0:
                    logger.debug(f"Terminated process: {process}")
            except Exception as e:
                logger.debug(f"Error terminating {process}: {e}")
        
        # Wait for graceful shutdown
        time.sleep(3)
        
        # Force kill remaining processes
        for process in processes:
            try:
                cmd = ["pkill", "-9", "-f", process]
                result = subprocess.run(cmd, capture_output=True, check=False)
                if result.returncode == 0:
                    logger.debug(f"Force killed process: {process}")
            except Exception as e:
                logger.debug(f"Error force killing {process}: {e}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error during process cleanup: {e}")
        return False


def cleanup_carla_ports(ports: Optional[List[int]] = None, logger: Optional[logging.Logger] = None) -> bool:
    """
    Clean up processes using CARLA ports.
    
    Args:
        ports: List of ports to clean up (default: common CARLA ports)
        logger: Optional logger for output
        
    Returns:
        True if cleanup was successful
    """
    if logger is None:
        logger = logging.getLogger(__name__)
    
    if ports is None:
        # Common CARLA ports
        ports = [2000, 2001, 2002, 8000, 8001, 8002]
    
    try:
        logger.info("Cleaning up CARLA ports...")
        
        for port in ports:
            try:
                # Kill processes using the port
                cmd = ["fuser", "-k", f"{port}/tcp"]
                subprocess.run(cmd, capture_output=True, check=False, stderr=subprocess.DEVNULL)
                logger.debug(f"Cleaned up port: {port}")
            except Exception as e:
                logger.debug(f"Error cleaning port {port}: {e}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error during port cleanup: {e}")
        return False


def full_carla_cleanup(logger: Optional[logging.Logger] = None) -> bool:
    """
    Perform a complete CARLA cleanup including processes and ports.
    
    Args:
        logger: Optional logger for output
        
    Returns:
        True if cleanup was successful
    """
    if logger is None:
        logger = logging.getLogger(__name__)
    
    try:
        logger.info("Performing full CARLA cleanup...")
        
        # Kill processes
        kill_carla_processes(logger)
        
        # Clean up ports
        cleanup_carla_ports(logger=logger)
        
        # Wait for cleanup to complete
        time.sleep(2)
        
        logger.info("CARLA cleanup completed")
        return True
        
    except Exception as e:
        logger.error(f"Error during full cleanup: {e}")
        return False


def is_carla_running(logger: Optional[logging.Logger] = None) -> bool:
    """
    Check if CARLA is currently running.
    
    Args:
        logger: Optional logger for output
        
    Returns:
        True if CARLA is running
    """
    if logger is None:
        logger = logging.getLogger(__name__)
    
    try:
        result = subprocess.run(["pgrep", "-f", "CarlaUE4"], 
                               capture_output=True, check=False)
        is_running = result.returncode == 0
        
        if is_running:
            logger.debug("CARLA is currently running")
        else:
            logger.debug("CARLA is not running")
            
        return is_running
        
    except Exception as e:
        logger.debug(f"Error checking CARLA status: {e}")
        return False


if __name__ == "__main__":
    # Simple command line interface
    import argparse
    
    parser = argparse.ArgumentParser(description="CARLA cleanup utility")
    parser.add_argument("--kill", action="store_true", help="Kill CARLA processes")
    parser.add_argument("--ports", action="store_true", help="Clean up CARLA ports")
    parser.add_argument("--full", action="store_true", help="Full cleanup (processes + ports)")
    parser.add_argument("--check", action="store_true", help="Check if CARLA is running")
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
    logger = logging.getLogger(__name__)
    
    if args.check:
        if is_carla_running(logger):
            print("CARLA is running")
        else:
            print("CARLA is not running")
    elif args.kill:
        kill_carla_processes(logger)
    elif args.ports:
        cleanup_carla_ports(logger=logger)
    elif args.full:
        full_carla_cleanup(logger)
    else:
        print("Use --help for usage information") 