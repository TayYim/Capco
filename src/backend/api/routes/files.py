"""
File management API routes.

Handles file operations for experiment results including downloads,
previews, and analysis.
"""

from fastapi import APIRouter, HTTPException, Response, Depends, Query
from fastapi.responses import StreamingResponse
from typing import List, Optional

from models.api import FileInfo, FilePreview, ExperimentAnalysis, APIResponse
from services.file_service import get_file_service, FileService
# No authentication needed for prototype

router = APIRouter()


@router.get("/experiments/{experiment_id}/files", response_model=List[FileInfo])
async def list_experiment_files(
    experiment_id: str,
    file_service: FileService = Depends(get_file_service),
):
    """
    List all files for an experiment.
    
    Args:
        experiment_id: Experiment ID
        
    Returns:
        List of file information
    """
    files = await file_service.list_experiment_files(experiment_id)
    
    if files is None:
        raise HTTPException(
            status_code=404,
            detail=f"Experiment {experiment_id} not found or has no files"
        )
    
    return files


@router.get("/experiments/{experiment_id}/files/{filename}")
async def download_experiment_file(
    experiment_id: str,
    filename: str,
    file_service: FileService = Depends(get_file_service),
):
    """
    Download a specific experiment file.
    
    Args:
        experiment_id: Experiment ID
        filename: File name to download
        
    Returns:
        File content as streaming response
    """
    file_path = await file_service.get_file_path(experiment_id, filename)
    
    if not file_path:
        raise HTTPException(
            status_code=404,
            detail=f"File {filename} not found for experiment {experiment_id}"
        )
    
    def iterfile():
        with open(file_path, "rb") as file_like:
            yield from file_like
    
    # Determine content type
    content_type = "application/octet-stream"
    if filename.endswith(".csv"):
        content_type = "text/csv"
    elif filename.endswith(".json"):
        content_type = "application/json"
    elif filename.endswith(".log"):
        content_type = "text/plain"
    elif filename.endswith(".txt"):
        content_type = "text/plain"
    
    return StreamingResponse(
        iterfile(),
        media_type=content_type,
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/experiments/{experiment_id}/files/{filename}/preview", response_model=FilePreview)
async def preview_experiment_file(
    experiment_id: str,
    filename: str,
    max_lines: int = Query(100, ge=1, le=1000, description="Maximum lines to preview"),
    file_service: FileService = Depends(get_file_service),
):
    """
    Preview file contents without downloading.
    
    Args:
        experiment_id: Experiment ID
        filename: File name to preview
        max_lines: Maximum lines to show
        
    Returns:
        File preview data
    """
    preview = await file_service.preview_file(experiment_id, filename, max_lines)
    
    if not preview:
        raise HTTPException(
            status_code=404,
            detail=f"File {filename} not found or cannot be previewed"
        )
    
    return preview


@router.get("/experiments/{experiment_id}/archive")
async def download_experiment_archive(
    experiment_id: str,
    format: str = Query("zip", regex="^(zip|tar)$", description="Archive format"),
    file_service: FileService = Depends(get_file_service),
):
    """
    Download all experiment files as an archive.
    
    Args:
        experiment_id: Experiment ID
        format: Archive format (zip or tar)
        
    Returns:
        Streaming archive
    """
    stream, filename = await file_service.create_experiment_archive(experiment_id, format)
    
    if not stream or not filename:
        raise HTTPException(
            status_code=404,
            detail=f"Experiment {experiment_id} not found or has no files"
        )
    
    media_type = "application/zip" if format == "zip" else "application/x-tar"
    
    return StreamingResponse(
        stream,
        media_type=media_type,
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/experiments/{experiment_id}/analysis", response_model=ExperimentAnalysis)
async def analyze_experiment_data(
    experiment_id: str,
    file_service: FileService = Depends(get_file_service),
):
    """
    Analyze experiment data and generate insights.
    
    Args:
        experiment_id: Experiment ID
        
    Returns:
        Analysis results and statistics
    """
    analysis = await file_service.analyze_experiment_data(experiment_id)
    
    if not analysis:
        raise HTTPException(
            status_code=404,
            detail=f"Experiment {experiment_id} not found or has no data to analyze"
        )
    
    return analysis


@router.delete("/experiments/{experiment_id}/files", response_model=APIResponse)
async def delete_experiment_files(
    experiment_id: str,
    file_service: FileService = Depends(get_file_service),
):
    """
    Delete all files for an experiment.
    
    Args:
        experiment_id: Experiment ID
        
    Returns:
        Operation result
    """
    success = await file_service.delete_experiment_files(experiment_id)
    
    if not success:
        raise HTTPException(
            status_code=404,
            detail=f"Experiment {experiment_id} not found"
        )
    
    return APIResponse(
        success=True,
        message=f"All files for experiment {experiment_id} have been deleted",
        data=None,
        error=None
    )


@router.post("/admin/cleanup", response_model=APIResponse)
async def cleanup_old_files(
    days_old: int = Query(30, ge=1, description="Delete files older than this many days"),
    dry_run: bool = Query(False, description="Preview what would be deleted"),
    file_service: FileService = Depends(get_file_service),
):
    """
    Clean up old experiment files.
    
    Args:
        days_old: Age threshold in days
        dry_run: If true, only report what would be deleted
        
    Returns:
        Cleanup report
    """
    result = await file_service.cleanup_old_files(days_old, dry_run)
    
    return APIResponse(
        success=True,
        message=result.get("message", "Cleanup completed"),
        data=result,
        error=None
    ) 