"""
System API routes.

Handles system health checks, status monitoring, and system information.
"""

from fastapi import APIRouter, Depends
from datetime import datetime

from models.configuration import SystemInfo, ConfigurationStatus
from models.api import APIResponse
from services.parameter_service import get_parameter_service, ParameterService
# No authentication needed for prototype

router = APIRouter()


@router.get("/health")
async def health_check():
    """
    Basic health check endpoint.
    
    Returns:
        Simple health status
    """
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "CapCo Fuzzing Backend"
    }


@router.get("/status", response_model=ConfigurationStatus)
async def system_status(
    parameter_service: ParameterService = Depends(get_parameter_service),
):
    """
    Get detailed system status and configuration validation.
    
    Returns:
        System status with validation results
    """
    return await parameter_service.get_configuration_status()


@router.get("/info", response_model=SystemInfo)
async def system_info(
    parameter_service: ParameterService = Depends(get_parameter_service),
):
    """
    Get comprehensive system information.
    
    Returns:
        Detailed system information including available methods and status
    """
    return await parameter_service.get_system_info()


@router.get("/version")
async def version_info():
    """
    Get version information.
    
    Returns:
        Version and build information
    """
    return {
        "version": "1.0.0",
        "build_date": "2024-01-01",
        "api_version": "v1",
        "framework": "FastAPI",
        "python_version": "3.8+",
        "features": [
            "Scenario Fuzzing",
            "Multiple Search Algorithms",
            "Real-time Monitoring",
            "File Management",
            "WebSocket Streaming"
        ]
    }


@router.post("/reset", response_model=APIResponse)
async def reset_system(
    parameter_service: ParameterService = Depends(get_parameter_service),
):
    """
    Reset system configuration to defaults.
    
    **WARNING: This will reset all configuration to defaults!**
    
    Returns:
        Reset operation result
    """
    try:
        await parameter_service.reset_configuration()
        return APIResponse(
            success=True,
            message="System configuration has been reset to defaults",
            data=None,
            error=None
        )
    except Exception as e:
        return APIResponse(
            success=False,
            message="Failed to reset configuration",
            data=None,
            error=str(e)
        ) 