"""
API routes for configuration management.

Handles system configuration, parameter ranges,
and settings management for the fuzzing framework.
"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends, status, UploadFile, File
from fastapi.responses import Response

from models.configuration import (
    SystemConfiguration, ConfigurationUpdate, ConfigurationStatus,
    ParameterRange, ParameterRangeUpdate, ParameterRangeImport,
    ParameterRangeExport, SystemInfo
)
from services.parameter_service import ParameterService, get_parameter_service
# No authentication needed for prototype

router = APIRouter()


@router.get("/config", response_model=SystemConfiguration)
async def get_system_configuration(
    parameter_service: ParameterService = Depends(get_parameter_service),
) -> SystemConfiguration:
    """
    Get current system configuration.
    
    Returns comprehensive system configuration including
    CARLA settings, experiment defaults, and file settings.
    """
    try:
        return await parameter_service.get_system_configuration()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get system configuration: {str(e)}"
        )


@router.put("/config", response_model=SystemConfiguration)
async def update_system_configuration(
    update_data: ConfigurationUpdate,
    parameter_service: ParameterService = Depends(get_parameter_service),
) -> SystemConfiguration:
    """
    Update system configuration.
    
    Updates system-wide settings and validates the new configuration.
    """
    try:
        return await parameter_service.update_system_configuration(update_data)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update system configuration: {str(e)}"
        )


@router.get("/config/status", response_model=ConfigurationStatus)
async def get_configuration_status(
    parameter_service: ParameterService = Depends(get_parameter_service),
) -> ConfigurationStatus:
    """
    Get configuration validation status.
    
    Returns the validation status of the current configuration
    including any errors or warnings.
    """
    try:
        return await parameter_service.get_configuration_status()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get configuration status: {str(e)}"
        )


@router.get("/config/parameters", response_model=List[ParameterRange])
async def get_parameter_ranges(
    scenario_type: Optional[str] = None,
    parameter_service: ParameterService = Depends(get_parameter_service),
) -> List[ParameterRange]:
    """
    Get parameter ranges configuration.
    
    Returns parameter ranges, optionally filtered by scenario type.
    """
    try:
        return await parameter_service.get_parameter_ranges(scenario_type)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get parameter ranges: {str(e)}"
        )


@router.put("/config/parameters", response_model=List[ParameterRange])
async def update_parameter_ranges(
    update_data: ParameterRangeUpdate,
    parameter_service: ParameterService = Depends(get_parameter_service),
) -> List[ParameterRange]:
    """
    Update parameter ranges.
    
    Updates parameter ranges for specified scenario types.
    """
    try:
        return await parameter_service.update_parameter_ranges(update_data)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update parameter ranges: {str(e)}"
        )


@router.post("/config/parameters/import")
async def import_parameter_ranges(
    file: UploadFile = File(...),
    override_existing: bool = False,
    validate_only: bool = False,
    parameter_service: ParameterService = Depends(get_parameter_service),
):
    """
    Import parameter ranges from YAML file.
    
    Allows bulk import of parameter range configurations.
    """
    try:
        if not file.filename.endswith(('.yaml', '.yml')):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only YAML files are supported for import"
            )
        
        content = await file.read()
        import_data = ParameterRangeImport(
            file_content=content.decode('utf-8'),
            override_existing=override_existing,
            validate_only=validate_only
        )
        
        result = await parameter_service.import_parameter_ranges(import_data)
        return result
    
    except HTTPException:
        raise
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file encoding. Please use UTF-8."
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to import parameter ranges: {str(e)}"
        )


@router.post("/config/parameters/export")
async def export_parameter_ranges(
    export_data: ParameterRangeExport,
    parameter_service: ParameterService = Depends(get_parameter_service),
):
    """
    Export parameter ranges to file.
    
    Exports parameter ranges in YAML or JSON format.
    """
    try:
        content, filename = await parameter_service.export_parameter_ranges(export_data)
        
        media_type = "application/x-yaml" if export_data.format == "yaml" else "application/json"
        
        return Response(
            content=content,
            media_type=media_type,
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to export parameter ranges: {str(e)}"
        )


@router.get("/config/info", response_model=SystemInfo)
async def get_system_info(
    parameter_service: ParameterService = Depends(get_parameter_service),
) -> SystemInfo:
    """
    Get comprehensive system information.
    
    Returns version information, available methods, functions,
    and system status.
    """
    try:
        return await parameter_service.get_system_info()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get system info: {str(e)}"
        )


@router.post("/config/reset")
async def reset_configuration(
    parameter_service: ParameterService = Depends(get_parameter_service),
):
    """
    Reset configuration to defaults.
    
    Resets all configuration settings to their default values.
    This action cannot be undone.
    """
    try:
        await parameter_service.reset_configuration()
        return {"message": "Configuration reset to defaults successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reset configuration: {str(e)}"
        ) 