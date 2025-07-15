"""
XML utility functions for parsing and extracting route and scenario information.

This module provides functions to parse CARLA route XML files and extract
scenario parameters for experiment configuration.
"""

import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, Optional, Tuple
import logging


def parse_route_scenarios(route_file: str, route_id: str, project_root: Path, logger=None) -> Dict[str, Dict[str, str]]:
    """
    Parse the route XML file and extract scenario parameters for the specified route.
    
    Args:
        route_file: Name of the route file (without .xml extension)
        route_id: ID of the route to search for
        project_root: Path to the project root directory
        logger: Optional logger instance to use for logging
        
    Returns:
        Dictionary containing scenario information with structure:
        {
            'scenario_name': {
                'type': 'scenario_type',
                'parameters': {'param1': 'value1', 'param2': 'value2', ...}
            }
        }
        Returns empty dict if route not found or parsing fails.
    """
    if logger is None:
        logger = logging.getLogger(__name__)
    route_xml_path = project_root / "dependencies" / "leaderboard" / "data" / f"{route_file}.xml"
    
    if not route_xml_path.exists():
        logger.error(f"Route file not found: {route_xml_path}")
        return {}
    
    try:
        tree = ET.parse(route_xml_path)
        root = tree.getroot()
        
        # Find the route with matching ID
        target_route = None
        for route in root.findall('route'):
            if route.get('id') == str(route_id):
                target_route = route
                break
        
        if target_route is None:
            logger.error(f"Route with ID {route_id} not found in {route_file}.xml")
            return {}
        
        logger.info(f"Found route ID {route_id} in town {target_route.get('town', 'Unknown')}")
        
        # Extract scenario parameters
        scenarios_info = {}
        scenarios = target_route.find('scenarios')
        
        if scenarios is None:
            logger.warning(f"No scenarios found for route ID {route_id}")
            return {}
        
        for scenario in scenarios.findall('scenario'):
            scenario_name = scenario.get('name', 'Unknown')
            scenario_type = scenario.get('type', 'Unknown')
            
            # Skip scenarios ending with 'Data_Collect'
            if scenario_type.endswith('Data_Collect'):
                logger.debug(f"Skipping data collection scenario: {scenario_name}")
                continue
            
            # Extract all parameters except trigger_point
            parameters = {}
            for child in scenario:
                if child.tag != 'trigger_point':
                    param_name = child.tag
                    param_value = child.get('value', child.text if child.text else 'N/A')
                    parameters[param_name] = param_value
            
            if parameters:
                scenarios_info[scenario_name] = {
                    'type': scenario_type,
                    'parameters': parameters
                }
                logger.info(f"Found scenario: {scenario_name} (type: {scenario_type})")
                for param_name, param_value in parameters.items():
                    logger.info(f"  - {param_name}: {param_value}")
            else:
                logger.info(f"Found scenario: {scenario_name} (type: {scenario_type}) - No parameters")
        
        return scenarios_info
        
    except ET.ParseError as e:
        logger.error(f"Error parsing XML file {route_xml_path}: {e}")
        return {}
    except Exception as e:
        logger.error(f"Unexpected error parsing route file: {e}")
        return {}


def get_route_town(route_file: str, route_id: str, project_root: Path, logger=None) -> Optional[str]:
    """
    Get the town name for a specific route.
    
    Args:
        route_file: Name of the route file (without .xml extension)
        route_id: ID of the route to search for
        project_root: Path to the project root directory
        logger: Optional logger instance to use for logging
        
    Returns:
        Town name if found, None otherwise
    """
    if logger is None:
        logger = logging.getLogger(__name__)
    route_xml_path = project_root / "dependencies" / "leaderboard" / "data" / f"{route_file}.xml"
    
    if not route_xml_path.exists():
        logger.error(f"Route file not found: {route_xml_path}")
        return None
    
    try:
        tree = ET.parse(route_xml_path)
        root = tree.getroot()
        
        # Find the route with matching ID
        for route in root.findall('route'):
            if route.get('id') == str(route_id):
                return route.get('town', 'Unknown')
        
        logger.error(f"Route with ID {route_id} not found in {route_file}.xml")
        return None
        
    except ET.ParseError as e:
        logger.error(f"Error parsing XML file {route_xml_path}: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error parsing route file: {e}")
        return None


def display_route_info(route_file: str, route_id: str, project_root: Path, logger=None) -> bool:
    """
    Display route information and scenario parameters in a formatted way.
    
    Args:
        route_file: Name of the route file (without .xml extension)
        route_id: ID of the route to analyze
        project_root: Path to the project root directory
        logger: Optional logger instance to use for logging
        
    Returns:
        True if route information was successfully displayed, False otherwise
    """
    if logger is None:
        logger = logging.getLogger(__name__)
    
    logger.info("=" * 60)
    logger.info(f"ROUTE ANALYSIS: {route_file}.xml - Route ID {route_id}")
    logger.info("=" * 60)
    
    # Get town information
    town = get_route_town(route_file, route_id, project_root, logger)
    if town:
        logger.info(f"Town: {town}")
    
    # Get scenario information
    scenarios_info = parse_route_scenarios(route_file, route_id, project_root, logger)
    
    if not scenarios_info:
        logger.warning("No valid scenarios found for processing!")
        logger.info("=" * 60)
        return False
    
    logger.info(f"Found {len(scenarios_info)} scenario(s) to process:")
    
    for idx, (scenario_name, info) in enumerate(scenarios_info.items(), 1):
        logger.info(f"\n{idx}. Scenario: {scenario_name}")
        logger.info(f"   Type: {info['type']}")
        logger.info("   Parameters:")
        
        for param_name, param_value in info['parameters'].items():
            logger.info(f"     • {param_name}: {param_value}")
    
    logger.info("=" * 60)
    return True


def validate_route_exists(route_file: str, route_id: str, project_root: Path) -> bool:
    """
    Check if a route with the given ID exists in the specified route file.
    
    Args:
        route_file: Name of the route file (without .xml extension)
        route_id: ID of the route to check
        project_root: Path to the project root directory
        
    Returns:
        True if route exists, False otherwise
    """
    logger = logging.getLogger(__name__)
    route_xml_path = project_root / "dependencies" / "leaderboard" / "data" / f"{route_file}.xml"
    
    if not route_xml_path.exists():
        logger.error(f"Route file not found: {route_xml_path}")
        return False
    
    try:
        tree = ET.parse(route_xml_path)
        root = tree.getroot()
        
        # Check if route with matching ID exists
        for route in root.findall('route'):
            if route.get('id') == str(route_id):
                return True
        
        return False
        
    except ET.ParseError as e:
        logger.error(f"Error parsing XML file {route_xml_path}: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error parsing route file: {e}")
        return False


def get_route_waypoints(route_file: str, route_id: str, project_root: Path) -> Optional[list]:
    """
    Extract waypoints for a specific route.
    
    Args:
        route_file: Name of the route file (without .xml extension)
        route_id: ID of the route to search for
        project_root: Path to the project root directory
        
    Returns:
        List of waypoint dictionaries with x, y, z coordinates, None if not found
    """
    logger = logging.getLogger(__name__)
    route_xml_path = project_root / "dependencies" / "leaderboard" / "data" / f"{route_file}.xml"
    
    if not route_xml_path.exists():
        logger.error(f"Route file not found: {route_xml_path}")
        return None
    
    try:
        tree = ET.parse(route_xml_path)
        root = tree.getroot()
        
        # Find the route with matching ID
        for route in root.findall('route'):
            if route.get('id') == str(route_id):
                waypoints = []
                waypoint_elements = route.find('waypoints')
                
                if waypoint_elements is not None:
                    for position in waypoint_elements.findall('position'):
                        waypoint = {
                            'x': float(position.get('x', 0)),
                            'y': float(position.get('y', 0)),
                            'z': float(position.get('z', 0))
                        }
                        waypoints.append(waypoint)
                
                return waypoints
        
        logger.error(f"Route with ID {route_id} not found in {route_file}.xml")
        return None
        
    except ET.ParseError as e:
        logger.error(f"Error parsing XML file {route_xml_path}: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error parsing route file: {e}")
        return None 