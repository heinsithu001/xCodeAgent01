#!/usr/bin/env python3
"""
Real-time WebSocket Manager for ZeroCostxCode
Handles real-time collaboration and terminal sessions
"""

import asyncio
import json
import uuid
from typing import Dict, List, Set, Any, Optional
from fastapi import WebSocket, WebSocketDisconnect
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class ConnectionManager:
    def __init__(self):
        # Active WebSocket connections
        self.active_connections: Dict[str, WebSocket] = {}
        
        # User to connection mapping
        self.user_connections: Dict[int, Set[str]] = {}
        
        # Project collaboration rooms
        self.project_rooms: Dict[int, Set[str]] = {}
        
        # Terminal sessions
        self.terminal_sessions: Dict[str, Dict[str, Any]] = {}
        
        # File collaboration sessions
        self.file_sessions: Dict[int, Dict[str, Any]] = {}
    
    async def connect(self, websocket: WebSocket, connection_id: str, user_id: int = None):
        """Accept new WebSocket connection"""
        await websocket.accept()
        
        self.active_connections[connection_id] = websocket
        
        if user_id:
            if user_id not in self.user_connections:
                self.user_connections[user_id] = set()
            self.user_connections[user_id].add(connection_id)
        
        logger.info(f"WebSocket connected: {connection_id} (user: {user_id})")
    
    def disconnect(self, connection_id: str, user_id: int = None):
        """Remove WebSocket connection"""
        if connection_id in self.active_connections:
            del self.active_connections[connection_id]
        
        if user_id and user_id in self.user_connections:
            self.user_connections[user_id].discard(connection_id)
            if not self.user_connections[user_id]:
                del self.user_connections[user_id]
        
        # Remove from project rooms
        for project_id, connections in self.project_rooms.items():
            connections.discard(connection_id)
        
        logger.info(f"WebSocket disconnected: {connection_id}")
    
    async def send_personal_message(self, message: Dict[str, Any], user_id: int):
        """Send message to specific user"""
        if user_id in self.user_connections:
            message_str = json.dumps(message)
            for connection_id in self.user_connections[user_id].copy():
                try:
                    websocket = self.active_connections.get(connection_id)
                    if websocket:
                        await websocket.send_text(message_str)
                except Exception as e:
                    logger.error(f"Error sending message to user {user_id}: {e}")
                    self.disconnect(connection_id, user_id)
    
    async def send_to_connection(self, message: Dict[str, Any], connection_id: str):
        """Send message to specific connection"""
        if connection_id in self.active_connections:
            try:
                websocket = self.active_connections[connection_id]
                await websocket.send_text(json.dumps(message))
            except Exception as e:
                logger.error(f"Error sending message to connection {connection_id}: {e}")
                self.disconnect(connection_id)
    
    async def broadcast_to_project(self, message: Dict[str, Any], project_id: int, exclude_connection: str = None):
        """Broadcast message to all users in a project"""
        if project_id in self.project_rooms:
            message_str = json.dumps(message)
            for connection_id in self.project_rooms[project_id].copy():
                if connection_id != exclude_connection:
                    try:
                        websocket = self.active_connections.get(connection_id)
                        if websocket:
                            await websocket.send_text(message_str)
                    except Exception as e:
                        logger.error(f"Error broadcasting to project {project_id}: {e}")
                        self.disconnect(connection_id)
    
    def join_project_room(self, connection_id: str, project_id: int):
        """Add connection to project collaboration room"""
        if project_id not in self.project_rooms:
            self.project_rooms[project_id] = set()
        self.project_rooms[project_id].add(connection_id)
    
    def leave_project_room(self, connection_id: str, project_id: int):
        """Remove connection from project room"""
        if project_id in self.project_rooms:
            self.project_rooms[project_id].discard(connection_id)
            if not self.project_rooms[project_id]:
                del self.project_rooms[project_id]
    
    # Terminal Session Management
    async def create_terminal_session(self, user_id: int, connection_id: str) -> str:
        """Create new terminal session"""
        session_id = str(uuid.uuid4())
        
        self.terminal_sessions[session_id] = {
            "user_id": user_id,
            "connection_id": connection_id,
            "created_at": datetime.now().isoformat(),
            "active": True,
            "history": []
        }
        
        return session_id
    
    async def handle_terminal_command(self, session_id: str, command: str, executor) -> Dict[str, Any]:
        """Handle terminal command execution"""
        if session_id not in self.terminal_sessions:
            return {"error": "Terminal session not found"}
        
        session = self.terminal_sessions[session_id]
        user_id = session["user_id"]
        
        # Execute command
        result = await executor.execute_terminal_command(command, user_id, session_id)
        
        # Add to history
        session["history"].append({
            "command": command,
            "result": result,
            "timestamp": datetime.now().isoformat()
        })
        
        # Send result to connection
        await self.send_to_connection({
            "type": "terminal_output",
            "session_id": session_id,
            "command": command,
            "result": result
        }, session["connection_id"])
        
        return result
    
    def close_terminal_session(self, session_id: str):
        """Close terminal session"""
        if session_id in self.terminal_sessions:
            self.terminal_sessions[session_id]["active"] = False
            del self.terminal_sessions[session_id]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get connection statistics"""
        return {
            "active_connections": len(self.active_connections),
            "active_users": len(self.user_connections),
            "project_rooms": len(self.project_rooms),
            "terminal_sessions": len(self.terminal_sessions),
            "file_sessions": len(self.file_sessions)
        }

# Global connection manager
connection_manager = ConnectionManager()