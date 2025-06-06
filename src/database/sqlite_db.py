#!/usr/bin/env python3
"""
SQLite Database Implementation for ZeroCostxCode
Minimal database layer with all essential features
"""

import sqlite3
import asyncio
import aiosqlite
import json
import hashlib
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path
import os

class ZeroCostDatabase:
    def __init__(self, db_path: str = "data/zerocostxcode.db"):
        self.db_path = db_path
        # Ensure data directory exists
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        
    async def initialize(self):
        """Initialize database with required tables"""
        async with aiosqlite.connect(self.db_path) as db:
            # Users table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_active BOOLEAN DEFAULT 1
                )
            """)
            
            # Projects table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS projects (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    description TEXT,
                    owner_id INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (owner_id) REFERENCES users (id)
                )
            """)
            
            # Files table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS files (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    filename TEXT NOT NULL,
                    content TEXT,
                    file_type TEXT,
                    project_id INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (project_id) REFERENCES projects (id)
                )
            """)
            
            # Sessions table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY,
                    user_id INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP,
                    is_active BOOLEAN DEFAULT 1,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            """)
            
            await db.commit()
    
    # User Management
    async def create_user(self, username: str, email: str, password: str) -> Dict[str, Any]:
        """Create a new user"""
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(
                    "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
                    (username, email, password_hash)
                )
                user_id = cursor.lastrowid
                await db.commit()
                
                return {
                    "id": user_id,
                    "username": username,
                    "email": email,
                    "created_at": datetime.now().isoformat()
                }
        except sqlite3.IntegrityError:
            raise ValueError("Username or email already exists")
    
    async def authenticate_user(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """Authenticate user and return user data"""
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT id, username, email, created_at FROM users WHERE username = ? AND password_hash = ? AND is_active = 1",
                (username, password_hash)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    return {
                        "id": row[0],
                        "username": row[1],
                        "email": row[2],
                        "created_at": row[3]
                    }
        return None
    
    async def get_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user by ID"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT id, username, email, created_at FROM users WHERE id = ? AND is_active = 1",
                (user_id,)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    return {
                        "id": row[0],
                        "username": row[1],
                        "email": row[2],
                        "created_at": row[3]
                    }
        return None
    
    # Project Management
    async def create_project(self, name: str, description: str, owner_id: int) -> Dict[str, Any]:
        """Create a new project"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "INSERT INTO projects (name, description, owner_id) VALUES (?, ?, ?)",
                (name, description, owner_id)
            )
            project_id = cursor.lastrowid
            await db.commit()
            
            return {
                "id": project_id,
                "name": name,
                "description": description,
                "owner_id": owner_id,
                "created_at": datetime.now().isoformat()
            }
    
    async def get_user_projects(self, user_id: int) -> List[Dict[str, Any]]:
        """Get all projects for a user"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT id, name, description, created_at, updated_at FROM projects WHERE owner_id = ?",
                (user_id,)
            ) as cursor:
                rows = await cursor.fetchall()
                return [
                    {
                        "id": row[0],
                        "name": row[1],
                        "description": row[2],
                        "created_at": row[3],
                        "updated_at": row[4]
                    }
                    for row in rows
                ]
    
    # File Management
    async def save_file(self, filename: str, content: str, file_type: str, project_id: int) -> Dict[str, Any]:
        """Save or update a file"""
        async with aiosqlite.connect(self.db_path) as db:
            # Check if file exists
            async with db.execute(
                "SELECT id FROM files WHERE filename = ? AND project_id = ?",
                (filename, project_id)
            ) as cursor:
                existing = await cursor.fetchone()
            
            if existing:
                # Update existing file
                await db.execute(
                    "UPDATE files SET content = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (content, existing[0])
                )
                file_id = existing[0]
            else:
                # Create new file
                cursor = await db.execute(
                    "INSERT INTO files (filename, content, file_type, project_id) VALUES (?, ?, ?, ?)",
                    (filename, content, file_type, project_id)
                )
                file_id = cursor.lastrowid
            
            await db.commit()
            
            return {
                "id": file_id,
                "filename": filename,
                "file_type": file_type,
                "project_id": project_id,
                "updated_at": datetime.now().isoformat()
            }
    
    async def get_file(self, file_id: int) -> Optional[Dict[str, Any]]:
        """Get file by ID"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT id, filename, content, file_type, project_id, created_at, updated_at FROM files WHERE id = ?",
                (file_id,)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    return {
                        "id": row[0],
                        "filename": row[1],
                        "content": row[2],
                        "file_type": row[3],
                        "project_id": row[4],
                        "created_at": row[5],
                        "updated_at": row[6]
                    }
        return None
    
    async def get_project_files(self, project_id: int) -> List[Dict[str, Any]]:
        """Get all files in a project"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT id, filename, file_type, created_at, updated_at FROM files WHERE project_id = ?",
                (project_id,)
            ) as cursor:
                rows = await cursor.fetchall()
                return [
                    {
                        "id": row[0],
                        "filename": row[1],
                        "file_type": row[2],
                        "created_at": row[3],
                        "updated_at": row[4]
                    }
                    for row in rows
                ]
    
    async def delete_file(self, file_id: int) -> bool:
        """Delete a file"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("DELETE FROM files WHERE id = ?", (file_id,))
            await db.commit()
            return cursor.rowcount > 0
    
    # Session Management
    async def create_session(self, user_id: int, expires_at: datetime) -> str:
        """Create a new session"""
        session_id = str(uuid.uuid4())
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT INTO sessions (id, user_id, expires_at) VALUES (?, ?, ?)",
                (session_id, user_id, expires_at.isoformat())
            )
            await db.commit()
        
        return session_id
    
    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session by ID"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                """SELECT s.id, s.user_id, s.expires_at, u.username 
                   FROM sessions s 
                   JOIN users u ON s.user_id = u.id 
                   WHERE s.id = ? AND s.is_active = 1""",
                (session_id,)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    return {
                        "id": row[0],
                        "user_id": row[1],
                        "expires_at": row[2],
                        "username": row[3]
                    }
        return None
    
    async def invalidate_session(self, session_id: str):
        """Invalidate a session"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE sessions SET is_active = 0 WHERE id = ?",
                (session_id,)
            )
            await db.commit()

# Global database instance
db = ZeroCostDatabase()