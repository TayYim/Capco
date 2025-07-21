"""
Apollo Configuration Loader

Simple utility for loading Apollo container name and user name from apollo_config.yaml
"""

import os
import yaml
import subprocess
import logging
from pathlib import Path
from typing import Optional, Union


class ApolloConfigLoader:
    """Simple Apollo configuration loader for container name and user name."""
    
    def __init__(self, config_path: Optional[Union[str, Path]] = None):
        """Initialize the loader with optional config path."""
        self.config_path = self._resolve_config_path(config_path)
        self._config_data = None
        
    def _resolve_config_path(self, config_path: Optional[Union[str, Path]]) -> Path:
        """Resolve the Apollo configuration file path."""
        if config_path:
            return Path(config_path)
        
        # Auto-detect: find project root and look for config/apollo_config.yaml
        current_file = Path(__file__).resolve()
        for parent in current_file.parents:
            config_dir = parent / "config"
            if config_dir.exists() and (config_dir / "parameter_ranges.yaml").exists():
                return config_dir / "apollo_config.yaml"
        
        # Fallback
        project_root = current_file.parent.parent.parent
        return project_root / "config" / "apollo_config.yaml"
        
    def load_config(self) -> dict:
        """Load and return the Apollo configuration."""
        if self._config_data is not None:
            return self._config_data
            
        if not self.config_path.exists():
            raise FileNotFoundError(f"Apollo config file not found: {self.config_path}")
            
        try:
            with open(self.config_path, 'r') as f:
                self._config_data = yaml.safe_load(f)
                return self._config_data
        except yaml.YAMLError as e:
            raise yaml.YAMLError(f"Invalid YAML in Apollo config: {e}")
            
    def get_container_name(self) -> str:
        """Get Apollo container name."""
        config = self.load_config()
        return config.get('container_name', 'apollo_dev_tay')
        
    def get_user_name(self) -> str:
        """Get Apollo user name, auto-detecting if needed."""
        config = self.load_config()
        user_name = config.get('user_name')
        
        # Auto-detect if user_name is null
        if user_name is None:
            try:
                result = subprocess.run(['whoami'], capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    return result.stdout.strip()
            except Exception:
                pass
            # Fallback to 'tay'
            return 'tay'
            
        return user_name


# Global instance
_loader = None

def get_apollo_config_loader(config_path: Optional[Union[str, Path]] = None) -> ApolloConfigLoader:
    """Get the global Apollo config loader."""
    global _loader
    if _loader is None:
        _loader = ApolloConfigLoader(config_path)
    return _loader

def get_apollo_container_name() -> str:
    """Quick function to get Apollo container name."""
    return get_apollo_config_loader().get_container_name()

def get_apollo_user_name() -> str:
    """Quick function to get Apollo user name."""
    return get_apollo_config_loader().get_user_name() 