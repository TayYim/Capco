"""
API routes for scenario management.

Handles scenario discovery, information retrieval,
and parameter validation for fuzzing experiments.
"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends, Query, status

from models.scenario import (
    ScenarioInfo, RouteInfo, RouteListItem, RouteFileInfo,
    ScenarioValidation, ScenarioSearch, ScenarioStatistics,
    ParameterValidation
)
from models.experiment import ExperimentConfig
from services.scenario_service import ScenarioService, get_scenario_service
from core.security import get_current_user_optional

router = APIRouter()


@router.get("/scenarios/files", response_model=List[RouteFileInfo])
async def list_route_files(
    scenario_service: ScenarioService = Depends(get_scenario_service),
    current_user: dict = Depends(get_current_user_optional)
) -> List[RouteFileInfo]:
    """
    List all available route files.
    
    Returns information about all route XML files available
    for fuzzing experiments.
    """
    try:
        return await scenario_service.list_route_files()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list route files: {str(e)}"
        )


@router.get("/scenarios/{route_file}", response_model=List[RouteListItem])
async def list_routes(
    route_file: str,
    scenario_service: ScenarioService = Depends(get_scenario_service),
    current_user: dict = Depends(get_current_user_optional)
) -> List[RouteListItem]:
    """
    List all routes in a specific route file.
    
    Returns summary information about all routes available
    in the specified route file.
    """
    try:
        routes = await scenario_service.list_routes(route_file)
        if not routes:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Route file {route_file} not found or contains no routes"
            )
        return routes
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list routes: {str(e)}"
        )


@router.get("/scenarios/{route_file}/{route_id}", response_model=RouteInfo)
async def get_route_info(
    route_file: str,
    route_id: str,
    scenario_service: ScenarioService = Depends(get_scenario_service),
    current_user: dict = Depends(get_current_user_optional)
) -> RouteInfo:
    """
    Get detailed information about a specific route.
    
    Returns comprehensive information about the route including
    all scenarios, parameters, and metadata.
    """
    try:
        route_info = await scenario_service.get_route_info(route_file, route_id)
        if not route_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Route {route_id} not found in {route_file}"
            )
        return route_info
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get route info: {str(e)}"
        )


@router.post("/scenarios/{route_file}/{route_id}/validate", response_model=ScenarioValidation)
async def validate_scenario_config(
    route_file: str,
    route_id: str,
    config: ExperimentConfig,
    scenario_service: ScenarioService = Depends(get_scenario_service),
    current_user: dict = Depends(get_current_user_optional)
) -> ScenarioValidation:
    """
    Validate experiment configuration for a specific scenario.
    
    Checks if the experiment configuration is valid for the
    specified route and scenario combination.
    """
    try:
        # Ensure route exists
        route_info = await scenario_service.get_route_info(route_file, route_id)
        if not route_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Route {route_id} not found in {route_file}"
            )
        
        # Validate configuration
        validation = await scenario_service.validate_experiment_config(
            route_file, route_id, config
        )
        return validation
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to validate scenario config: {str(e)}"
        )


@router.post("/scenarios/search", response_model=List[RouteListItem])
async def search_scenarios(
    search_criteria: ScenarioSearch,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    scenario_service: ScenarioService = Depends(get_scenario_service),
    current_user: dict = Depends(get_current_user_optional)
) -> List[RouteListItem]:
    """
    Search for scenarios based on criteria.
    
    Finds scenarios that match the specified search criteria
    such as scenario type, town, or parameter requirements.
    """
    try:
        return await scenario_service.search_scenarios(
            search_criteria, limit, offset
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to search scenarios: {str(e)}"
        )


@router.get("/scenarios/statistics", response_model=ScenarioStatistics)
async def get_scenario_statistics(
    route_file: Optional[str] = Query(None),
    scenario_service: ScenarioService = Depends(get_scenario_service),
    current_user: dict = Depends(get_current_user_optional)
) -> ScenarioStatistics:
    """
    Get statistics about available scenarios.
    
    Returns comprehensive statistics about scenarios, parameters,
    and their usage across the available route files.
    """
    try:
        return await scenario_service.get_scenario_statistics(route_file)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get scenario statistics: {str(e)}"
        )


@router.get("/scenarios/{route_file}/{route_id}/parameters")
async def get_fuzzable_parameters(
    route_file: str,
    route_id: str,
    scenario_service: ScenarioService = Depends(get_scenario_service),
    current_user: dict = Depends(get_current_user_optional)
):
    """
    Get fuzzable parameters for a specific route.
    
    Returns detailed information about all parameters that can
    be fuzzed for the specified route.
    """
    try:
        parameters = await scenario_service.get_fuzzable_parameters(route_file, route_id)
        if parameters is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Route {route_id} not found in {route_file}"
            )
        return parameters
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get fuzzable parameters: {str(e)}"
        )


@router.get("/scenarios/{route_file}/{route_id}/preview")
async def preview_scenario_xml(
    route_file: str,
    route_id: str,
    scenario_service: ScenarioService = Depends(get_scenario_service),
    current_user: dict = Depends(get_current_user_optional)
):
    """
    Get a preview of the scenario XML.
    
    Returns the XML content for the specified route for
    inspection and debugging purposes.
    """
    try:
        xml_content = await scenario_service.get_scenario_xml_preview(route_file, route_id)
        if not xml_content:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Route {route_id} not found in {route_file}"
            )
        
        return {
            "route_file": route_file,
            "route_id": route_id,
            "xml_content": xml_content
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get XML preview: {str(e)}"
        )


@router.get("/scenarios/types")
async def get_scenario_types(
    scenario_service: ScenarioService = Depends(get_scenario_service),
    current_user: dict = Depends(get_current_user_optional)
) -> List[str]:
    """
    Get list of all available scenario types.
    
    Returns a list of unique scenario types found across
    all route files.
    """
    try:
        return await scenario_service.get_scenario_types()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get scenario types: {str(e)}"
        )


@router.get("/scenarios/towns")
async def get_available_towns(
    scenario_service: ScenarioService = Depends(get_scenario_service),
    current_user: dict = Depends(get_current_user_optional)
) -> List[str]:
    """
    Get list of all available CARLA towns.
    
    Returns a list of towns that are referenced in the
    available scenario files.
    """
    try:
        return await scenario_service.get_available_towns()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get available towns: {str(e)}"
        ) 