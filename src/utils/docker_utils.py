"""
Docker utilities for checking container availability.

Provides functions to check if Docker containers are running
and accessible for the Apollo agent integration.
"""

import subprocess
import logging
import yaml
from pathlib import Path
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


def check_docker_container(container_name: str) -> bool:
    """
    Check if a Docker container exists (running or stopped).
    
    Args:
        container_name: Name of the container to check
        
    Returns:
        True if container exists, False otherwise
    """
    try:
        # Use docker ps -a to check if container exists (running or stopped)
        result = subprocess.run(
            ["docker", "ps", "-a", "--filter", f"name={container_name}", "--format", "{{.Names}}"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            # Check if the container name appears in the output
            existing_containers = result.stdout.strip().split('\n')
            return container_name in existing_containers
        else:
            logger.warning(f"Docker command failed: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        logger.warning(f"Docker command timed out while checking container {container_name}")
        return False
    except FileNotFoundError:
        logger.warning("Docker command not found - Docker may not be installed")
        return False
    except Exception as e:
        logger.warning(f"Error checking Docker container {container_name}: {e}")
        return False


def load_apollo_config() -> Optional[Dict[str, Any]]:
    """
    Load Apollo configuration from the config file.
    
    Returns:
        Apollo configuration dictionary or None if not found
    """
    try:
        # Find the config file relative to the project root (Carlo/)
        # From src/utils/docker_utils.py, go up to Carlo/ then to config/
        config_path = Path(__file__).parent.parent.parent / "config" / "apollo_config.yaml"
        
        if not config_path.exists():
            logger.warning(f"Apollo config file not found at {config_path}")
            return None
            
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
            
        return config
        
    except Exception as e:
        logger.warning(f"Error loading Apollo config: {e}")
        return None


def get_apollo_container_name() -> Optional[str]:
    """
    Get the Apollo container name from configuration.
    
    Returns:
        Container name from config or None if not found
    """
    config = load_apollo_config()
    if config and 'container_name' in config:
        return config['container_name']
    return None


def check_apollo_availability() -> bool:
    """
    Check if Apollo container exists (running or stopped).
    
    Returns:
        True if Apollo container exists, False otherwise
    """
    container_name = get_apollo_container_name()
    if not container_name:
        logger.warning("No Apollo container name found in configuration")
        return False
        
    return check_docker_container(container_name) 