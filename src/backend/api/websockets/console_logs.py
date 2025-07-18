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

from utils.log_streamer import LogStreamer, get_log_streamer
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
    experiment_id: str,
    log_streamer: LogStreamer = Depends(get_log_streamer)
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
        asyncio.create_task(
            stream_logs_for_experiment(experiment_id, log_streamer)
        )
        
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


async def stream_logs_for_experiment(experiment_id: str, log_streamer: LogStreamer):
    """
    Stream logs for a specific experiment.
    
    Monitors log files and streams new content to connected WebSocket clients.
    """
    try:
        async for log_line, log_level in log_streamer.stream_experiment_logs(experiment_id):
            await manager.broadcast_log(log_line, experiment_id, log_level)
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