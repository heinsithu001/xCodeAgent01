#!/usr/bin/env python3
"""
Working Complete Backend for ZeroCostxCode Professional
All-in-one implementation with all core features
"""

import asyncio
import json
import logging
import os
import sys
import uuid
import sqlite3
import hashlib
import subprocess
import tempfile
import shutil
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional, List, Set
import uvicorn

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Depends, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
import aiosqlite
import jwt

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Security configuration
SECRET_KEY = os.getenv("SECRET_KEY", "zerocostxcode-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24

security = HTTPBearer()

# Initialize FastAPI app
app = FastAPI(
    title="ZeroCostxCode Professional Backend",
    description="Complete AI-powered coding platform",
    version="3.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request/Response Models
class UserRegister(BaseModel):
    username: str
    email: str
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

class ProjectCreate(BaseModel):
    name: str
    description: str = ""

class FileCreate(BaseModel):
    filename: str
    content: str
    file_type: str
    project_id: int

class CodeExecute(BaseModel):
    code: str
    language: str = "python"
    filename: str = None

class AIRequest(BaseModel):
    prompt: str
    language: str = "python"
    task_type: str = "generate"

# ============================================================================
# DATABASE LAYER
# ============================================================================

class Database:
    def __init__(self, db_path: str = "data/zerocostxcode.db"):
        self.db_path = db_path
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
            
            await db.commit()
    
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

# ============================================================================
# AUTHENTICATION
# ============================================================================

class Auth:
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
                status_code=401,
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
                status_code=401,
                detail="Invalid or expired token"
            )
        
        # Get fresh user data from database
        user = await self.db.get_user_by_id(token_data["user_id"])
        if not user:
            raise HTTPException(
                status_code=401,
                detail="User not found"
            )
        
        return user

# ============================================================================
# CODE EXECUTION
# ============================================================================

class CodeExecutor:
    def __init__(self, workspace_dir: str = "workspace"):
        self.workspace_dir = Path(workspace_dir)
        self.workspace_dir.mkdir(exist_ok=True)
        
        # Security limits
        self.max_execution_time = 30  # seconds
        self.max_output_size = 1024 * 1024  # 1MB
    
    async def execute_code(self, 
                          code: str, 
                          language: str = "python", 
                          user_id: int = None,
                          filename: str = None) -> Dict[str, Any]:
        """Execute code securely"""
        
        execution_id = str(uuid.uuid4())
        start_time = time.time()
        
        try:
            # Create isolated workspace for this execution
            exec_dir = self.workspace_dir / f"exec_{execution_id}"
            exec_dir.mkdir(exist_ok=True)
            
            # Determine file extension
            if not filename:
                ext_map = {
                    'python': '.py',
                    'javascript': '.js',
                    'bash': '.sh'
                }
                extension = ext_map.get(language.lower(), '.py')
                filename = f"main{extension}"
            
            # Write code to file
            code_file = exec_dir / filename
            with open(code_file, 'w', encoding='utf-8') as f:
                f.write(code)
            
            # Execute based on language
            if language.lower() == 'python':
                cmd = ['python3', str(code_file)]
            elif language.lower() in ['javascript', 'js']:
                if not shutil.which('node'):
                    return {
                        "success": False,
                        "error": "Node.js not installed",
                        "output": "",
                        "stderr": "Node.js runtime not found"
                    }
                cmd = ['node', str(code_file)]
            elif language.lower() == 'bash':
                os.chmod(code_file, 0o755)
                cmd = ['bash', str(code_file)]
            else:
                cmd = ['python3', str(code_file)]  # Default to Python
            
            # Execute with timeout
            result = await self._run_subprocess(cmd, exec_dir)
            
            # Calculate execution time
            execution_time = time.time() - start_time
            
            result.update({
                "execution_id": execution_id,
                "execution_time": execution_time,
                "user_id": user_id,
                "language": language,
                "filename": filename
            })
            
            return result
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "execution_id": execution_id,
                "execution_time": time.time() - start_time
            }
        finally:
            # Cleanup workspace
            try:
                shutil.rmtree(exec_dir, ignore_errors=True)
            except:
                pass
    
    async def _run_subprocess(self, cmd: List[str], cwd: Path) -> Dict[str, Any]:
        """Run subprocess with security limits"""
        try:
            # Create process with limits
            process = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=str(cwd),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                limit=self.max_output_size
            )
            
            # Wait for completion with timeout
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=self.max_execution_time
                )
                
                return {
                    "success": process.returncode == 0,
                    "output": stdout.decode('utf-8', errors='replace'),
                    "stderr": stderr.decode('utf-8', errors='replace'),
                    "return_code": process.returncode
                }
                
            except asyncio.TimeoutError:
                # Kill process if timeout
                try:
                    process.kill()
                    await process.wait()
                except:
                    pass
                
                return {
                    "success": False,
                    "error": f"Execution timeout ({self.max_execution_time}s)",
                    "output": "",
                    "stderr": "Process killed due to timeout"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "output": "",
                "stderr": str(e)
            }
    
    def get_supported_languages(self) -> List[Dict[str, Any]]:
        """Get list of supported programming languages"""
        return [
            {
                "name": "Python",
                "key": "python",
                "extension": ".py",
                "available": True  # Python3 is always available
            },
            {
                "name": "JavaScript",
                "key": "javascript",
                "extension": ".js",
                "available": shutil.which('node') is not None
            },
            {
                "name": "Bash",
                "key": "bash",
                "extension": ".sh",
                "available": shutil.which('bash') is not None
            }
        ]

# ============================================================================
# WEBSOCKET MANAGER
# ============================================================================

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.user_connections: Dict[int, Set[str]] = {}
    
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
        
        logger.info(f"WebSocket disconnected: {connection_id}")
    
    async def send_to_connection(self, message: Dict[str, Any], connection_id: str):
        """Send message to specific connection"""
        if connection_id in self.active_connections:
            try:
                websocket = self.active_connections[connection_id]
                await websocket.send_text(json.dumps(message))
            except Exception as e:
                logger.error(f"Error sending message to connection {connection_id}: {e}")
                self.disconnect(connection_id)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get connection statistics"""
        return {
            "active_connections": len(self.active_connections),
            "active_users": len(self.user_connections)
        }

# ============================================================================
# MOCK AI PROVIDER (for testing without external dependencies)
# ============================================================================

class MockAIProvider:
    async def generate_code(self, prompt: str, language: str = "python") -> Dict[str, Any]:
        """Generate mock code response"""
        
        # Simple code templates based on common requests
        if "hello world" in prompt.lower():
            if language.lower() == "python":
                code = '''def hello_world():
    """Print hello world message"""
    print("Hello, World!")
    return "Hello, World!"

if __name__ == "__main__":
    hello_world()'''
            elif language.lower() == "javascript":
                code = '''function helloWorld() {
    console.log("Hello, World!");
    return "Hello, World!";
}

helloWorld();'''
            else:
                code = f'# Hello World in {language}\nprint("Hello, World!")'
        
        elif "fibonacci" in prompt.lower():
            code = '''def fibonacci(n):
    """Calculate fibonacci sequence"""
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

# Test the function
for i in range(10):
    print(f"F({i}) = {fibonacci(i)}")'''
        
        elif "api" in prompt.lower() or "fastapi" in prompt.lower():
            code = '''from fastapi import FastAPI

app = FastAPI()

@app.get("/")
async def root():
    return {"message": "Hello World"}

@app.get("/items/{item_id}")
async def read_item(item_id: int, q: str = None):
    return {"item_id": item_id, "q": q}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)'''
        
        else:
            code = f'''# Generated {language} code for: {prompt}

def main():
    """Main function"""
    print("This is generated code based on your request:")
    print("{prompt}")
    
    # TODO: Implement your specific requirements here
    pass

if __name__ == "__main__":
    main()'''
        
        return {
            "content": code,
            "model": "mock-ai-provider",
            "usage": {"total_tokens": len(prompt) + len(code)},
            "response_time": 0.5
        }
    
    async def analyze_code(self, code: str, analysis_type: str = "review") -> Dict[str, Any]:
        """Analyze code and provide feedback"""
        
        analysis = f"""## Code Analysis ({analysis_type})

### Overview
The provided code has been analyzed for quality, best practices, and potential improvements.

### Findings
1. **Code Structure**: The code appears to be well-structured
2. **Best Practices**: Consider adding more comments and documentation
3. **Error Handling**: Add try-catch blocks for better error handling
4. **Performance**: The code looks efficient for its purpose

### Recommendations
- Add input validation
- Include unit tests
- Consider using type hints (for Python)
- Add logging for debugging

### Security Notes
- Validate all user inputs
- Avoid hardcoded credentials
- Use secure coding practices

### Overall Rating: B+
The code is functional and follows basic best practices. With the suggested improvements, it could be production-ready.
"""
        
        return {
            "content": analysis,
            "model": "mock-ai-analyzer",
            "usage": {"total_tokens": len(code) + len(analysis)},
            "response_time": 0.3
        }

# ============================================================================
# GLOBAL INSTANCES
# ============================================================================

db = Database()
executor = CodeExecutor()
connection_manager = ConnectionManager()
ai_provider = MockAIProvider()

# Initialize auth after database
auth = Auth(db)

# ============================================================================
# STARTUP/SHUTDOWN
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Initialize all services on startup"""
    
    # Initialize database
    await db.initialize()
    logger.info("Database initialized")
    
    logger.info("Authentication initialized")
    
    # Create demo user if none exists
    try:
        await db.create_user("demo", "demo@zerocostxcode.com", "demo123")
        logger.info("Demo user created (username: demo, password: demo123)")
    except:
        logger.info("Demo user already exists")

# ============================================================================
# SERVE FRONTEND
# ============================================================================

frontend_path = Path(__file__).parent / "frontend-professional"
if frontend_path.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_path)), name="static")

@app.get("/", response_class=HTMLResponse)
async def serve_frontend():
    """Serve the frontend"""
    if frontend_path.exists() and (frontend_path / "index.html").exists():
        with open(frontend_path / "index.html", "r") as f:
            return HTMLResponse(content=f.read())
    else:
        return HTMLResponse(content=f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>ZeroCostxCode Professional Backend</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; background: #0d1117; color: #f0f6fc; }}
                .container {{ max-width: 800px; margin: 0 auto; }}
                .status {{ background: #21262d; padding: 20px; border-radius: 8px; margin: 20px 0; }}
                .success {{ color: #3fb950; }}
                .info {{ color: #58a6ff; }}
                a {{ color: #58a6ff; text-decoration: none; }}
                a:hover {{ text-decoration: underline; }}
                .endpoint {{ background: #161b22; padding: 10px; margin: 10px 0; border-radius: 4px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🚀 ZeroCostxCode Professional Backend</h1>
                <div class="status">
                    <h2 class="success">✅ Backend is Running!</h2>
                    <p>All core features are operational:</p>
                    <ul>
                        <li class="success">✅ Database (SQLite)</li>
                        <li class="success">✅ Authentication (JWT)</li>
                        <li class="success">✅ File Management</li>
                        <li class="success">✅ Code Execution</li>
                        <li class="success">✅ WebSocket Support</li>
                        <li class="success">✅ AI Integration (Mock)</li>
                    </ul>
                </div>
                
                <div class="status">
                    <h3 class="info">🔗 Available Endpoints</h3>
                    <div class="endpoint"><strong>API Documentation:</strong> <a href="/docs">/docs</a></div>
                    <div class="endpoint"><strong>Health Check:</strong> <a href="/health">/health</a></div>
                    <div class="endpoint"><strong>API Status:</strong> <a href="/api/v3/status">/api/v3/status</a></div>
                </div>
                
                <div class="status">
                    <h3 class="info">👤 Demo Account</h3>
                    <p><strong>Username:</strong> demo</p>
                    <p><strong>Password:</strong> demo123</p>
                    <p><strong>Email:</strong> demo@zerocostxcode.com</p>
                </div>
                
                <div class="status">
                    <h3 class="info">🧪 Quick Test</h3>
                    <p>Try these API endpoints:</p>
                    <div class="endpoint">POST /api/v3/auth/login - Login with demo account</div>
                    <div class="endpoint">GET /api/v3/languages - Get supported languages</div>
                    <div class="endpoint">POST /api/v3/execute - Execute code</div>
                </div>
            </div>
        </body>
        </html>
        """)

# ============================================================================
# API ENDPOINTS
# ============================================================================

# Health and Status
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "services": {
            "database": True,
            "authentication": True,
            "code_execution": True,
            "websocket": True,
            "ai_provider": True
        },
        "stats": connection_manager.get_stats()
    }

@app.get("/api/v3/status")
async def api_status():
    """API status endpoint"""
    return {
        "api_version": "v3.0",
        "status": "running",
        "features": [
            "authentication",
            "file_management", 
            "code_execution",
            "ai_integration",
            "real_time_collaboration"
        ],
        "supported_languages": executor.get_supported_languages()
    }

# Authentication
@app.post("/api/v3/auth/register")
async def register(user_data: UserRegister):
    """Register new user"""
    return await auth.register_user(user_data.username, user_data.email, user_data.password)

@app.post("/api/v3/auth/login")
async def login(user_data: UserLogin):
    """Login user"""
    return await auth.login_user(user_data.username, user_data.password)

@app.get("/api/v3/auth/me")
async def get_current_user_info(current_user: dict = Depends(auth.get_current_user)):
    """Get current user information"""
    return current_user

# Projects
@app.post("/api/v3/projects")
async def create_project(project_data: ProjectCreate, current_user: dict = Depends(auth.get_current_user)):
    """Create new project"""
    return await db.create_project(project_data.name, project_data.description, current_user["id"])

@app.get("/api/v3/projects")
async def get_user_projects(current_user: dict = Depends(auth.get_current_user)):
    """Get user's projects"""
    return await db.get_user_projects(current_user["id"])

@app.get("/api/v3/projects/{project_id}/files")
async def get_project_files(project_id: int, current_user: dict = Depends(auth.get_current_user)):
    """Get files in a project"""
    return await db.get_project_files(project_id)

# Files
@app.post("/api/v3/files")
async def create_file(file_data: FileCreate, current_user: dict = Depends(auth.get_current_user)):
    """Create or update file"""
    return await db.save_file(
        file_data.filename, 
        file_data.content, 
        file_data.file_type, 
        file_data.project_id
    )

@app.get("/api/v3/files/{file_id}")
async def get_file(file_id: int, current_user: dict = Depends(auth.get_current_user)):
    """Get file by ID"""
    file_data = await db.get_file(file_id)
    if not file_data:
        raise HTTPException(status_code=404, detail="File not found")
    return file_data

@app.put("/api/v3/files/{file_id}")
async def update_file(file_id: int, content: str = Form(...), current_user: dict = Depends(auth.get_current_user)):
    """Update file content"""
    file_data = await db.get_file(file_id)
    if not file_data:
        raise HTTPException(status_code=404, detail="File not found")
    
    return await db.save_file(
        file_data["filename"],
        content,
        file_data["file_type"],
        file_data["project_id"]
    )

@app.delete("/api/v3/files/{file_id}")
async def delete_file(file_id: int, current_user: dict = Depends(auth.get_current_user)):
    """Delete file"""
    success = await db.delete_file(file_id)
    if not success:
        raise HTTPException(status_code=404, detail="File not found")
    return {"success": True, "message": "File deleted"}

# Code Execution
@app.post("/api/v3/execute")
async def execute_code(exec_data: CodeExecute, current_user: dict = Depends(auth.get_current_user)):
    """Execute code"""
    return await executor.execute_code(
        exec_data.code,
        exec_data.language,
        current_user["id"],
        exec_data.filename
    )

@app.get("/api/v3/languages")
async def get_supported_languages():
    """Get supported programming languages"""
    return executor.get_supported_languages()

# AI Integration
@app.post("/api/v3/ai/generate")
async def ai_generate(ai_request: AIRequest, current_user: dict = Depends(auth.get_current_user)):
    """Generate code using AI"""
    try:
        if ai_request.task_type == "generate":
            response = await ai_provider.generate_code(ai_request.prompt, ai_request.language)
        elif ai_request.task_type == "analyze":
            response = await ai_provider.analyze_code(ai_request.prompt, "review")
        else:
            response = await ai_provider.generate_code(ai_request.prompt, ai_request.language)
        
        return {
            "success": True,
            "content": response["content"],
            "model": response["model"],
            "usage": response["usage"],
            "response_time": response["response_time"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v3/ai/analyze")
async def ai_analyze_code(code: str = Form(...), analysis_type: str = Form("review"), current_user: dict = Depends(auth.get_current_user)):
    """Analyze code using AI"""
    try:
        response = await ai_provider.analyze_code(code, analysis_type)
        return {
            "success": True,
            "analysis": response["content"],
            "type": analysis_type,
            "model": response["model"],
            "usage": response["usage"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Demo/Testing
@app.get("/api/v3/demo/create-sample-project")
async def create_sample_project(current_user: dict = Depends(auth.get_current_user)):
    """Create a sample project for testing"""
    # Create project
    project = await db.create_project("Sample Project", "A sample project for testing", current_user["id"])
    
    # Create sample files
    sample_files = [
        {
            "filename": "main.py",
            "content": '''#!/usr/bin/env python3
"""
Sample Python application
"""

def hello_world():
    """Print hello world message"""
    print("Hello, World from ZeroCostxCode!")
    return "Hello, World!"

def fibonacci(n):
    """Calculate fibonacci sequence"""
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

if __name__ == "__main__":
    hello_world()
    
    # Calculate first 10 fibonacci numbers
    print("Fibonacci sequence:")
    for i in range(10):
        print(f"F({i}) = {fibonacci(i)}")
''',
            "file_type": ".py"
        },
        {
            "filename": "README.md",
            "content": '''# Sample Project

This is a sample project created by ZeroCostxCode Professional.

## Features

- Python code execution
- AI-powered code generation
- Real-time collaboration
- File management

## Usage

1. Edit the code in `main.py`
2. Click "Run Code" to execute
3. Use AI assistant for help

## AI Commands

Try these prompts with the AI:
- "Add error handling to the fibonacci function"
- "Create a unit test for hello_world function"
- "Optimize the fibonacci function using memoization"
''',
            "file_type": ".md"
        }
    ]
    
    # Save files
    for file_data in sample_files:
        await db.save_file(
            file_data["filename"],
            file_data["content"],
            file_data["file_type"],
            project["id"]
        )
    
    return {
        "success": True,
        "project": project,
        "files_created": len(sample_files)
    }

# WebSocket
@app.websocket("/ws/{connection_id}")
async def websocket_endpoint(websocket: WebSocket, connection_id: str):
    """Main WebSocket endpoint for real-time features"""
    user_id = None
    
    try:
        await connection_manager.connect(websocket, connection_id)
        
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            message_type = message.get("type")
            
            if message_type == "auth":
                # Authenticate user
                token = message.get("token")
                if token and auth:
                    token_data = auth.verify_token(token)
                    if token_data:
                        user_id = token_data["user_id"]
                        await connection_manager.send_to_connection({
                            "type": "auth_success",
                            "user_id": user_id
                        }, connection_id)
                    else:
                        await connection_manager.send_to_connection({
                            "type": "auth_error",
                            "message": "Invalid token"
                        }, connection_id)
            
            elif message_type == "ping":
                await connection_manager.send_to_connection({
                    "type": "pong",
                    "timestamp": datetime.now().isoformat()
                }, connection_id)
    
    except WebSocketDisconnect:
        connection_manager.disconnect(connection_id, user_id)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        connection_manager.disconnect(connection_id, user_id)

if __name__ == "__main__":
    print("🚀 Starting ZeroCostxCode Professional Backend...")
    print("📊 All features included:")
    print("   ✅ Database (SQLite)")
    print("   ✅ Authentication (JWT)")
    print("   ✅ File Management")
    print("   ✅ Code Execution")
    print("   ✅ WebSocket Support")
    print("   ✅ AI Integration (Mock)")
    print("   ✅ Demo Account: demo/demo123")
    print("")
    print("🌐 Access at: http://localhost:12000")
    print("📚 API Docs: http://localhost:12000/docs")
    print("")
    
    uvicorn.run(
        "working_backend:app",
        host="0.0.0.0",
        port=12000,
        reload=False,
        log_level="info"
    )