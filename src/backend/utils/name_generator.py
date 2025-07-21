"""
Name generator for creating memorable experiment names.

Generates human-friendly names by combining adjectives and animals
to make experiments easily identifiable and memorable.
"""

import random
from typing import Optional


# Lists of adjectives and animals for name generation
ADJECTIVES = [
    "Agile", "Bold", "Clever", "Dynamic", "Elegant", "Fast", "Graceful", "Heavy",
    "Intelligent", "Jolly", "Keen", "Lightning", "Mighty", "Noble", "Optimized",
    "Precise", "Quick", "Robust", "Swift", "Turbulent", "Ultra", "Vibrant",
    "Wild", "Xenial", "Youthful", "Zealous", "Active", "Brave", "Careful",
    "Daring", "Epic", "Fearless", "Giant", "Heroic", "Intense", "Joyful",
    "Kind", "Legendary", "Majestic", "Nimble", "Outstanding", "Powerful",
    "Quiet", "Rapid", "Strong", "Tactical", "Ultimate", "Victorious",
    "Wonderful", "Xtreme", "Young", "Zestful"
]

ANIMALS = [
    "Falcon", "Tiger", "Eagle", "Wolf", "Lion", "Shark", "Panther", "Cheetah",
    "Hawk", "Bear", "Fox", "Lynx", "Jaguar", "Leopard", "Raven", "Phoenix",
    "Dragon", "Griffin", "Viper", "Cobra", "Stallion", "Mustang", "Bronco",
    "Rhino", "Bison", "Moose", "Elk", "Deer", "Gazelle", "Antelope",
    "Dolphin", "Whale", "Orca", "Barracuda", "Manta", "Octopus", "Squid",
    "Owl", "Condor", "Albatross", "Pelican", "Heron", "Crane", "Swan",
    "Badger", "Wolverine", "Weasel", "Ferret", "Otter", "Beaver", "Marmot"
]

# Alternative naming schemes for variety
TECH_ADJECTIVES = [
    "Quantum", "Neural", "Binary", "Digital", "Cyber", "Virtual", "Matrix",
    "Nano", "Micro", "Mega", "Turbo", "Hyper", "Ultra", "Meta", "Proto",
    "Alpha", "Beta", "Gamma", "Delta", "Omega", "Prime", "Core", "Edge"
]

OBJECTS = [
    "Quest", "Mission", "Trial", "Test", "Probe", "Scan", "Search", "Hunt",
    "Explorer", "Finder", "Seeker", "Scout", "Tracker", "Analyzer", "Monitor",
    "Detector", "Sensor", "Engine", "Runner", "Walker", "Driver", "Pilot"
]


def generate_experiment_name(style: str = "animal") -> str:
    """
    Generate a random experiment name.
    
    Args:
        style: Style of name generation ("animal", "tech", "mixed")
        
    Returns:
        Random experiment name
    """
    if style == "tech":
        return f"{random.choice(TECH_ADJECTIVES)} {random.choice(OBJECTS)}"
    elif style == "mixed":
        # Randomly choose between animal and tech style
        if random.random() < 0.7:
            return f"{random.choice(ADJECTIVES)} {random.choice(ANIMALS)}"
        else:
            return f"{random.choice(TECH_ADJECTIVES)} {random.choice(OBJECTS)}"
    else:  # default "animal" style
        return f"{random.choice(ADJECTIVES)} {random.choice(ANIMALS)}"


def generate_unique_name(existing_names: Optional[set[str]] = None, style: str = "animal", max_attempts: int = 100) -> str:
    """
    Generate a unique experiment name not in the existing set.
    
    Args:
        existing_names: Set of existing names to avoid
        style: Style of name generation
        max_attempts: Maximum attempts to find unique name
        
    Returns:
        Unique experiment name
    """
    if existing_names is None:
        existing_names = set()
    
    for _ in range(max_attempts):
        name = generate_experiment_name(style)
        if name not in existing_names:
            return name
    
    # If we can't find a unique name, add a number suffix
    base_name = generate_experiment_name(style)
    counter = 1
    while f"{base_name} #{counter}" in existing_names:
        counter += 1
    
    return f"{base_name} #{counter}"


def validate_experiment_name(name: str) -> tuple[bool, str]:
    """
    Validate an experiment name.
    
    Args:
        name: The name to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not name or not name.strip():
        return False, "Name cannot be empty"
    
    if len(name.strip()) < 2:
        return False, "Name must be at least 2 characters long"
    
    if len(name.strip()) > 100:
        return False, "Name must be less than 100 characters"
    
    # Check for invalid characters (basic validation)
    invalid_chars = set('<>:"/\\|?*')
    if any(char in name for char in invalid_chars):
        return False, f"Name cannot contain these characters: {' '.join(invalid_chars)}"
    
    return True, ""


# Predefined name suggestions for common scenarios
SCENARIO_NAMES = {
    "collision": ["Crash Hunter", "Impact Seeker", "Collision Finder", "Safety Probe"],
    "performance": ["Speed Demon", "Performance Beast", "Turbo Scanner", "Quick Explorer"],
    "safety": ["Guardian Angel", "Safety Shield", "Protective Eagle", "Secure Falcon"],
    "stress": ["Pressure Test", "Stress Warrior", "Endurance Tiger", "Limit Pusher"]
}


def suggest_names_for_scenario(scenario_type: str = "general", count: int = 5) -> list[str]:
    """
    Suggest appropriate names for a given scenario type.
    
    Args:
        scenario_type: Type of scenario (collision, performance, safety, stress, etc.)
        count: Number of suggestions to generate
        
    Returns:
        List of suggested names
    """
    suggestions = []
    
    # Add predefined suggestions if available
    if scenario_type in SCENARIO_NAMES:
        suggestions.extend(SCENARIO_NAMES[scenario_type])
    
    # Fill remaining slots with random names
    while len(suggestions) < count:
        if scenario_type in ["collision", "crash"]:
            # Use more aggressive adjectives for collision scenarios
            aggressive_adj = ["Fierce", "Brutal", "Intense", "Savage", "Violent", "Crushing"]
            name = f"{random.choice(aggressive_adj)} {random.choice(ANIMALS)}"
        else:
            name = generate_experiment_name("mixed")
        
        if name not in suggestions:
            suggestions.append(name)
    
    return suggestions[:count]