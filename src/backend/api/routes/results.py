"""
API routes for results management.

Handles result file operations, downloads, and
data analysis for completed experiments.
"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends, Query, status
from fastapi.responses import FileResponse, StreamingResponse

from services.file_service import FileService, get_file_service
from core.security import get_current_user_optional

router = APIRouter()


@router.get("/results/files/{experiment_id}")
async def list_experiment_files(
    experiment_id: str,
    file_service: FileService = Depends(get_file_service),
    current_user: dict = Depends(get_current_user_optional)
) -> List[dict]:
    """
    List all files for an experiment.
    
    Returns information about all files generated
    by the specified experiment.
    """
    try:
        files = await file_service.list_experiment_files(experiment_id)
        if files is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Experiment {experiment_id} not found"
            )
        return files
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list experiment files: {str(e)}"
        )


@router.get("/results/download/{experiment_id}/{filename}")
async def download_file(
    experiment_id: str,
    filename: str,
    file_service: FileService = Depends(get_file_service),
    current_user: dict = Depends(get_current_user_optional)
):
    """
    Download a specific experiment file.
    
    Downloads the requested file if it exists and belongs
    to the specified experiment.
    """
    try:
        file_path = await file_service.get_file_path(experiment_id, filename)
        
        if not file_path or not file_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"File {filename} not found for experiment {experiment_id}"
            )
        
        return FileResponse(
            path=str(file_path),
            filename=filename,
            media_type='application/octet-stream'
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to download file: {str(e)}"
        )


@router.get("/results/download-archive/{experiment_id}")
async def download_experiment_archive(
    experiment_id: str,
    format: str = Query("zip", regex="^(zip|tar)$"),
    file_service: FileService = Depends(get_file_service),
    current_user: dict = Depends(get_current_user_optional)
):
    """
    Download all experiment files as an archive.
    
    Creates and downloads a ZIP or TAR archive containing
    all files from the specified experiment.
    """
    try:
        archive_stream, filename = await file_service.create_experiment_archive(
            experiment_id, format
        )
        
        if archive_stream is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Experiment {experiment_id} not found or has no files"
            )
        
        media_type = "application/zip" if format == "zip" else "application/x-tar"
        
        return StreamingResponse(
            archive_stream,
            media_type=media_type,
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create archive: {str(e)}"
        )


@router.get("/results/preview/{experiment_id}/{filename}")
async def preview_file(
    experiment_id: str,
    filename: str,
    max_lines: int = Query(100, ge=1, le=1000),
    file_service: FileService = Depends(get_file_service),
    current_user: dict = Depends(get_current_user_optional)
):
    """
    Preview file contents.
    
    Returns a preview of text file contents with optional
    line limiting for large files.
    """
    try:
        preview_data = await file_service.preview_file(
            experiment_id, filename, max_lines
        )
        
        if preview_data is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"File {filename} not found for experiment {experiment_id}"
            )
        
        return preview_data
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to preview file: {str(e)}"
        )


@router.get("/results/analysis/{experiment_id}")
async def get_experiment_analysis(
    experiment_id: str,
    file_service: FileService = Depends(get_file_service),
    current_user: dict = Depends(get_current_user_optional)
):
    """
    Get experiment data analysis.
    
    Returns statistical analysis and summaries of
    experiment results and performance data.
    """
    try:
        analysis = await file_service.analyze_experiment_data(experiment_id)
        
        if analysis is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Experiment {experiment_id} not found or has no data"
            )
        
        return analysis
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to analyze experiment data: {str(e)}"
        )


@router.delete("/results/{experiment_id}")
async def delete_experiment_files(
    experiment_id: str,
    file_service: FileService = Depends(get_file_service),
    current_user: dict = Depends(get_current_user_optional)
):
    """
    Delete all files for an experiment.
    
    Permanently removes all files associated with
    the specified experiment. Cannot be undone.
    """
    try:
        success = await file_service.delete_experiment_files(experiment_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Experiment {experiment_id} not found"
            )
        
        return {"message": f"All files for experiment {experiment_id} deleted successfully"}
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete experiment files: {str(e)}"
        )


@router.post("/results/cleanup")
async def cleanup_old_files(
    days_old: int = Query(30, ge=1, le=365),
    dry_run: bool = Query(False),
    file_service: FileService = Depends(get_file_service),
    current_user: dict = Depends(get_current_user_optional)
):
    """
    Cleanup old experiment files.
    
    Removes experiment files older than the specified number of days.
    Use dry_run=true to see what would be deleted without actually deleting.
    """
    try:
        result = await file_service.cleanup_old_files(days_old, dry_run)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cleanup old files: {str(e)}"
        ) 