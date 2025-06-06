#!/usr/bin/env python3
"""
Simple JWT Authentication System for ZeroCostxCode
Minimal but secure authentication implementation
"""

import jwt
import hashlib
import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import os

# Security configuration
SECRET_KEY = os.getenv("SECRET_KEY", "zerocostxcode-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24

security = HTTPBearer()

class SimpleAuth:
    def __init__(self, database):
        self.db = database
    
    def create_access_token(self, user_data: Dict[str, Any]) -> str:
        """Create JWT access token"""
        expire = datetime.utcnow() + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
        to_encode = {
            "user_id": user_data["id"],
            "username": user_data["username"],
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "access"
        }
        
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt
    
    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify JWT token and return user data"""
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            
            # Check if token is expired
            if datetime.utcnow() > datetime.fromtimestamp(payload["exp"]):
                return None
            
            return {
                "user_id": payload["user_id"],
                "username": payload["username"]
            }
        except jwt.PyJWTError:
            return None
    
    async def register_user(self, username: str, email: str, password: str) -> Dict[str, Any]:
        """Register a new user"""
        # Basic validation
        if len(username) < 3:
            raise HTTPException(status_code=400, detail="Username must be at least 3 characters")
        if len(password) < 6:
            raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
        if "@" not in email:
            raise HTTPException(status_code=400, detail="Invalid email format")
        
        try:
            user = await self.db.create_user(username, email, password)
            token = self.create_access_token(user)
            
            return {
                "user": user,
                "access_token": token,
                "token_type": "bearer"
            }
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
    
    async def login_user(self, username: str, password: str) -> Dict[str, Any]:
        """Login user and return token"""
        user = await self.db.authenticate_user(username, password)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password"
            )
        
        token = self.create_access_token(user)
        
        return {
            "user": user,
            "access_token": token,
            "token_type": "bearer"
        }
    
    async def get_current_user(self, credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
        """Get current user from JWT token"""
        token_data = self.verify_token(credentials.credentials)
        
        if not token_data:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token"
            )
        
        # Get fresh user data from database
        user = await self.db.get_user_by_id(token_data["user_id"])
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )
        
        return user

# Utility functions for password hashing
def hash_password(password: str) -> str:
    """Hash password using SHA256"""
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password: str, hashed: str) -> bool:
    """Verify password against hash"""
    return hash_password(password) == hashed

# Create auth instance (will be initialized with database)
auth = None

def init_auth(database):
    """Initialize auth with database"""
    global auth
    auth = SimpleAuth(database)
    return auth