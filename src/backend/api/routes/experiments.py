"""
Experiment management API routes.

Provides endpoints for creating, starting, stopping, and monitoring
fuzzing experiments.
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Query
from fastapi.responses import FileResponse

from models.experiment import (
    ExperimentCreate,
    ExperimentStatus,
    ExperimentResult,
    ExperimentListItem,
    ExperimentUpdate
)
from models.api import PaginatedResponse
from services.experiment_service import ExperimentService, get_experiment_service
# No authentication needed for prototype

router = APIRouter()


@router.post("/experiments", response_model=ExperimentStatus, status_code=status.HTTP_201_CREATED)
async def create_experiment(
    request: ExperimentCreate,
    background_tasks: BackgroundTasks,
    experiment_service: ExperimentService = Depends(get_experiment_service)
) -> ExperimentStatus:
    """
    Create a new fuzzing experiment.
    
    Creates a new experiment with the specified configuration.
    Optionally starts the experiment immediately if start_immediately is True.
    """
    try:
        experiment = await experiment_service.create_experiment(
            config=request.config
        )
        
        if request.start_immediately:
            background_tasks.add_task(
                experiment_service.start_experiment,
                experiment.id
            )
        
        return experiment
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create experiment: {str(e)}"
        )


@router.get("/experiments", response_model=List[ExperimentListItem])
async def list_experiments(
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of experiments to return"),
    offset: int = Query(0, ge=0, description="Number of experiments to skip"),
    status_filter: Optional[str] = None,
    search_method: Optional[str] = None,
    experiment_service: ExperimentService = Depends(get_experiment_service)
) -> List[ExperimentListItem]:
    """
    List experiments with optional filtering.
    
    Returns a paginated list of experiments with optional filters
    for status and search method.
    """
    try:
        experiments = await experiment_service.list_experiments(
            limit=limit,
            offset=offset,
            status_filter=status_filter,
            search_method=search_method
        )
        return experiments
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list experiments: {str(e)}"
        )


@router.get("/experiments/{experiment_id}", response_model=ExperimentStatus)
async def get_experiment(
    experiment_id: str,
    experiment_service: ExperimentService = Depends(get_experiment_service)
) -> ExperimentStatus:
    """
    Get detailed information about a specific experiment.
    
    Returns comprehensive experiment information including
    configuration, status, and results.
    """
    try:
        experiment = await experiment_service.get_experiment(experiment_id)
        
        if not experiment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Experiment {experiment_id} not found"
            )
        
        return experiment
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get experiment: {str(e)}"
        )


@router.patch("/experiments/{experiment_id}", response_model=ExperimentStatus)
async def update_experiment(
    experiment_id: str,
    update: ExperimentUpdate,
    experiment_service: ExperimentService = Depends(get_experiment_service)
) -> ExperimentStatus:
    """
    Update experiment configuration or metadata.
    
    Allows updating experiment settings and metadata.
    Running experiments cannot have their core configuration changed.
    """
    try:
        experiment = await experiment_service.update_experiment(experiment_id, update)
        
        if not experiment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Experiment {experiment_id} not found"
            )
        
        return experiment
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update experiment: {str(e)}"
        )


@router.post("/experiments/{experiment_id}/start", response_model=ExperimentStatus)
async def start_experiment(
    experiment_id: str,
    background_tasks: BackgroundTasks,
    experiment_service: ExperimentService = Depends(get_experiment_service)
) -> ExperimentStatus:
    """
    Start a fuzzing experiment.
    
    Begins execution of the specified experiment in the background.
    Returns the updated experiment status.
    """
    try:
        # Start experiment in background
        background_tasks.add_task(
            experiment_service.start_experiment,
            experiment_id
        )
        
        # Return updated status
        experiment = await experiment_service.get_experiment(experiment_id)
        if not experiment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Experiment {experiment_id} not found"
            )
        
        return experiment
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start experiment: {str(e)}"
        )


@router.post("/experiments/{experiment_id}/stop", response_model=ExperimentStatus)
async def stop_experiment(
    experiment_id: str,
    experiment_service: ExperimentService = Depends(get_experiment_service)
) -> ExperimentStatus:
    """
    Stop a running fuzzing experiment.
    
    Gracefully stops the specified experiment and returns
    the final status.
    """
    try:
        status_info = await experiment_service.stop_experiment(experiment_id)
        
        if not status_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Experiment {experiment_id} not found"
            )
        
        return status_info
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to stop experiment: {str(e)}"
        )


@router.get("/experiments/{experiment_id}/status", response_model=ExperimentStatus)
async def get_experiment_status(
    experiment_id: str,
    experiment_service: ExperimentService = Depends(get_experiment_service)
) -> ExperimentStatus:
    """
    Get the current status of an experiment.
    
    Returns real-time status information including progress,
    current iteration, and any errors.
    """
    try:
        experiment = await experiment_service.get_experiment(experiment_id)
        
        if not experiment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Experiment {experiment_id} not found"
            )
        
        return experiment
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get experiment status: {str(e)}"
        )


@router.get("/experiments/{experiment_id}/results", response_model=ExperimentResult)
async def get_experiment_results(
    experiment_id: str,
    experiment_service: ExperimentService = Depends(get_experiment_service)
) -> ExperimentResult:
    """
    Get experiment results and analysis.
    
    Returns comprehensive results including statistics,
    best solutions, and performance metrics.
    """
    try:
        results = await experiment_service.get_experiment_results(experiment_id)
        
        if not results:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Results for experiment {experiment_id} not found"
            )
        
        return results
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get experiment results: {str(e)}"
        )


@router.get("/experiments/{experiment_id}/logs")
async def get_experiment_logs(
    experiment_id: str,
    lines: int = Query(100, ge=1, le=10000, description="Number of log lines to return"),
    experiment_service: ExperimentService = Depends(get_experiment_service)
) -> Dict[str, Any]:
    """
    Get experiment logs.
    
    Returns recent log entries for the specified experiment.
    """
    try:
        # TODO: Implement log retrieval functionality
        return {
            "experiment_id": experiment_id,
            "logs": ["Log functionality not yet implemented"],
            "lines_returned": 1
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get experiment logs: {str(e)}"
        )


@router.delete("/experiments/{experiment_id}")
async def delete_experiment(
    experiment_id: str,
    experiment_service: ExperimentService = Depends(get_experiment_service)
) -> Dict[str, str]:
    """
    Delete an experiment and its associated data.
    
    Permanently removes the experiment and all its data.
    Running experiments will be stopped first.
    """
    try:
        success = await experiment_service.delete_experiment(experiment_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Experiment {experiment_id} not found"
            )
        
        return {"message": f"Experiment {experiment_id} deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete experiment: {str(e)}"
        ) 