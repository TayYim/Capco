"""
WebSocket handlers for real-time console log streaming.

Provides real-time streaming of experiment logs and progress
updates to connected clients.
"""

import asyncio
import json
import sys
from typing import Dict, Set
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from pathlib import Path

# Add the backend directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Simple log streaming functionality to avoid import issues
import aiofiles
import asyncio
from pathlib import Path

# Store active log streaming tasks
active_log_tasks = {}

async def simple_log_streaming(experiment_id: str):
    """Simple log streaming function."""
    try:
        # Try to find log file for the experiment
        output_base = Path("../../..") / "output" 
        possible_log_paths = [
            output_base / f"experiment_{experiment_id}" / "fuzzing.log",
            output_base / experiment_id / "fuzzing.log",
        ]
        
        log_file = None
        
        # First try direct experiment directories
        for pattern in possible_log_paths:
            if pattern.exists():
                log_file = pattern
                break
        
        if not log_file:
            await manager.broadcast_log("No log file found for experiment", experiment_id, "INFO")
            return
        
        # Start monitoring from the end of the file
        last_position = log_file.stat().st_size if log_file.exists() else 0
        
        while True:
            try:
                if not log_file.exists():
                    await asyncio.sleep(1)
                    continue
                
                current_size = log_file.stat().st_size
                
                if current_size > last_position:
                    # File has grown, read new content
                    async with aiofiles.open(log_file, 'r', encoding='utf-8', errors='replace') as f:
                        await f.seek(last_position)
                        new_content = await f.read()
                        
                        if new_content:
                            # Process new lines
                            lines = new_content.split('\n')
                            for line in lines:
                                line = line.strip()
                                if line:
                                    # Simple log level detection based on content
                                    level = "INFO"  # Default to INFO
                                    line_lower = line.lower()
                                    if any(word in line_lower for word in ["error", "failed", "exception"]):
                                        level = "ERROR"
                                    elif any(word in line_lower for word in ["warning", "warn"]):
                                        level = "WARNING"
                                    elif any(word in line_lower for word in ["collision", "found"]):
                                        level = "SUCCESS"
                                    
                                    await manager.broadcast_log(line, experiment_id, level)
                            
                            last_position = current_size
                
                elif current_size < last_position:
                    # File was truncated, start from beginning
                    last_position = 0
                    await manager.broadcast_log("Log file was rotated", experiment_id, "INFO")
                
                # Wait before checking again
                await asyncio.sleep(0.5)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                await manager.broadcast_log(f"Error monitoring log: {str(e)}", experiment_id, "ERROR")
                await asyncio.sleep(2)
                
    except Exception as e:
        await manager.broadcast_log(f"Fatal error streaming logs: {str(e)}", experiment_id, "ERROR")
# No authentication needed for prototype

router = APIRouter()

# Store active WebSocket connections
active_connections: Dict[str, Set[WebSocket]] = {}


class ConnectionManager:
    """Manages WebSocket connections for experiment log streaming."""
    
    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, experiment_id: str):
        """Accept a new WebSocket connection for an experiment."""
        await websocket.accept()
        
        if experiment_id not in self.active_connections:
            self.active_connections[experiment_id] = set()
        
        self.active_connections[experiment_id].add(websocket)
    
    def disconnect(self, websocket: WebSocket, experiment_id: str):
        """Remove a WebSocket connection."""
        if experiment_id in self.active_connections:
            self.active_connections[experiment_id].discard(websocket)
            
            # Clean up empty sets
            if not self.active_connections[experiment_id]:
                del self.active_connections[experiment_id]
    
    async def send_message(self, message: dict, experiment_id: str):
        """Send a message to all connected clients for an experiment."""
        if experiment_id not in self.active_connections:
            return
        
        # Create a copy of the set to avoid modification during iteration
        connections = self.active_connections[experiment_id].copy()
        
        for connection in connections:
            try:
                await connection.send_text(json.dumps(message))
            except Exception:
                # Remove failed connections
                self.disconnect(connection, experiment_id)
    
    async def broadcast_log(self, log_line: str, experiment_id: str, log_level: str = "INFO"):
        """Broadcast a log line to all connected clients."""
        message = {
            "type": "log",
            "experiment_id": experiment_id,
            "level": log_level,
            "message": log_line,
            "timestamp": asyncio.get_event_loop().time()
        }
        await self.send_message(message, experiment_id)
    
    async def broadcast_progress(self, progress_data: dict, experiment_id: str):
        """Broadcast progress updates to all connected clients."""
        message = {
            "type": "progress",
            "experiment_id": experiment_id,
            "data": progress_data,
            "timestamp": asyncio.get_event_loop().time()
        }
        await self.send_message(message, experiment_id)


# Global connection manager
manager = ConnectionManager()


@router.websocket("/console/{experiment_id}")
async def websocket_console_logs(
    websocket: WebSocket,
    experiment_id: str
):
    """
    WebSocket endpoint for streaming console logs.
    
    Streams real-time console logs for the specified experiment
    to connected clients.
    """
    await manager.connect(websocket, experiment_id)
    
    try:
        # Send initial connection confirmation
        await websocket.send_text(json.dumps({
            "type": "connection",
            "status": "connected",
            "experiment_id": experiment_id,
            "message": f"Connected to console logs for experiment {experiment_id}"
        }))
        
        # Start log streaming for this experiment
        task = asyncio.create_task(simple_log_streaming(experiment_id))
        active_log_tasks[experiment_id] = task
        
        # Keep connection alive and handle client messages
        while True:
            try:
                # Wait for client messages (like ping/pong for keep-alive)
                data = await websocket.receive_text()
                message = json.loads(data)
                
                if message.get("type") == "ping":
                    await websocket.send_text(json.dumps({
                        "type": "pong",
                        "timestamp": asyncio.get_event_loop().time()
                    }))
                
            except asyncio.TimeoutError:
                # Send periodic heartbeat
                await websocket.send_text(json.dumps({
                    "type": "heartbeat",
                    "timestamp": asyncio.get_event_loop().time()
                }))
    
    except WebSocketDisconnect:
        manager.disconnect(websocket, experiment_id)
    except Exception as e:
        # Log error and clean up connection
        print(f"WebSocket error for experiment {experiment_id}: {e}")
        manager.disconnect(websocket, experiment_id)


@router.websocket("/progress/{experiment_id}")
async def websocket_progress_updates(
    websocket: WebSocket,
    experiment_id: str
):
    """
    WebSocket endpoint for streaming progress updates.
    
    Streams real-time progress information for the specified
    experiment to connected clients.
    """
    await manager.connect(websocket, f"{experiment_id}_progress")
    
    try:
        # Send initial connection confirmation
        await websocket.send_text(json.dumps({
            "type": "connection",
            "status": "connected",
            "experiment_id": experiment_id,
            "message": f"Connected to progress updates for experiment {experiment_id}"
        }))
        
        # Keep connection alive
        while True:
            try:
                data = await websocket.receive_text()
                message = json.loads(data)
                
                if message.get("type") == "ping":
                    await websocket.send_text(json.dumps({
                        "type": "pong",
                        "timestamp": asyncio.get_event_loop().time()
                    }))
            
            except asyncio.TimeoutError:
                continue
    
    except WebSocketDisconnect:
        manager.disconnect(websocket, f"{experiment_id}_progress")
    except Exception as e:
        print(f"WebSocket error for progress {experiment_id}: {e}")
        manager.disconnect(websocket, f"{experiment_id}_progress")


async def stream_logs_for_experiment(experiment_id: str):
    """
    Stream logs for a specific experiment.
    
    Monitors log files and streams new content to connected WebSocket clients.
    """
    try:
        # Use the simple log streaming function
        await simple_log_streaming(experiment_id)
    except Exception as e:
        # Send error message to connected clients
        await manager.broadcast_log(
            f"Error streaming logs: {str(e)}", 
            experiment_id, 
            "ERROR"
        )


async def broadcast_progress_update(experiment_id: str, progress_data: dict):
    """
    Public function to broadcast progress updates from experiments.
    
    Called by the experiment service to send progress updates
    to connected WebSocket clients.
    """
    await manager.broadcast_progress(progress_data, experiment_id)


async def broadcast_log_message(experiment_id: str, message: str, level: str = "INFO"):
    """
    Public function to broadcast log messages from experiments.
    
    Called by the experiment service to send log messages
    to connected WebSocket clients.
    """
    await manager.broadcast_log(message, experiment_id, level) 