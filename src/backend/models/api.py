"""
Pydantic models for general API responses and data structures.

Defines common API response models and utility data structures.
"""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


class FileInfo(BaseModel):
    """Information about a file."""
    
    name: str = Field(description="File name")
    size: int = Field(description="File size in bytes")
    modified: str = Field(description="Last modification time (ISO format)")
    type: str = Field(description="MIME type")


class FilePreview(BaseModel):
    """Preview of file contents."""
    
    filename: str = Field(description="File name")
    content: str = Field(description="File content preview")
    is_truncated: bool = Field(description="Whether content is truncated")
    total_lines: int = Field(description="Total lines in file")
    displayed_lines: int = Field(description="Number of lines displayed")


class ExperimentAnalysis(BaseModel):
    """Analysis results for an experiment."""
    
    experiment_id: str = Field(description="Experiment ID")
    summary: Dict[str, Any] = Field(description="Summary statistics")
    trends: Dict[str, Any] = Field(description="Trend analysis")
    parameters: Dict[str, Any] = Field(description="Parameter analysis")


class APIResponse(BaseModel):
    """Generic API response wrapper."""
    
    success: bool = Field(description="Whether the operation was successful")
    message: Optional[str] = Field(description="Response message")
    data: Optional[Any] = Field(description="Response data")
    error: Optional[str] = Field(description="Error message if unsuccessful")


class PaginatedResponse(BaseModel):
    """Paginated response wrapper."""
    
    items: List[Any] = Field(description="Items in current page")
    total: int = Field(description="Total number of items")
    page: int = Field(description="Current page number")
    size: int = Field(description="Page size")
    pages: int = Field(description="Total number of pages")


class LogMessage(BaseModel):
    """Log message structure for WebSocket streaming."""
    
    timestamp: str = Field(description="Message timestamp")
    level: str = Field(description="Log level")
    message: str = Field(description="Log message content")
    experiment_id: Optional[str] = Field(description="Associated experiment ID")


class ProgressUpdate(BaseModel):
    """Progress update for running experiments."""
    
    experiment_id: str = Field(description="Experiment ID")
    iteration: int = Field(description="Current iteration number")
    total_iterations: int = Field(description="Total iterations planned")
    progress_percent: float = Field(description="Progress percentage (0-100)")
    status: str = Field(description="Current status")
    message: Optional[str] = Field(description="Status message")
    current_reward: Optional[float] = Field(description="Current best reward")
    collision_found: bool = Field(default=False, description="Whether collision has been found")


class ValidationError(BaseModel):
    """Validation error details."""
    
    field: str = Field(description="Field that failed validation")
    message: str = Field(description="Error message")
    value: Optional[Any] = Field(description="Invalid value")


class BulkOperationResult(BaseModel):
    """Result of a bulk operation."""
    
    total: int = Field(description="Total items processed")
    success: int = Field(description="Successfully processed items")
    failed: int = Field(description="Failed items")
    errors: List[str] = Field(default=[], description="Error messages")
    details: Optional[Dict[str, Any]] = Field(description="Additional details") 