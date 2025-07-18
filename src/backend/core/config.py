"""
Configuration management for the FastAPI backend.

Handles environment variables, application settings, and
configuration validation.
"""

from functools import lru_cache
from typing import List
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings."""
    
    # Server configuration
    host: str = Field(default="127.0.0.1", description="Server host")
    port: int = Field(default=8000, description="Server port")
    debug: bool = Field(default=True, description="Debug mode")
    
    # CORS configuration
    allowed_origins: List[str] = Field(
        default=["http://localhost:3000", "http://127.0.0.1:3000"],
        description="Allowed CORS origins"
    )
    
    # Fuzzing framework paths
    carla_path: str = Field(
        default="/home/tay/Applications/CARLA_LB",
        description="Path to CARLA installation"
    )
    project_root: str = Field(
        default="/home/tay/Workspace/Carlo",
        description="Path to project root directory"
    )
    
    # Experiment configuration
    max_concurrent_experiments: int = Field(
        default=1,
        description="Maximum number of concurrent experiments"
    )
    default_timeout: int = Field(
        default=300,
        description="Default experiment timeout in seconds"
    )
    
    # File storage configuration
    output_dir: str = Field(
        default="output",
        description="Directory for experiment outputs"
    )
    max_file_size: int = Field(
        default=100 * 1024 * 1024,  # 100MB
        description="Maximum file upload size in bytes"
    )
    
    # Database configuration (optional)
    database_url: str = Field(
        default="sqlite:///./experiments.db",
        description="Database URL for experiment history"
    )
    
    # No security configuration needed for prototype
    
    # Logging configuration
    log_level: str = Field(
        default="INFO",
        description="Logging level"
    )
    
    class Config:
        env_file = ".env"
        env_prefix = "FUZZING_"


@lru_cache()
def get_settings() -> Settings:
    """Get application settings (cached)."""
    return Settings() 