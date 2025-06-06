#!/usr/bin/env python3
"""
Simple test server for ZeroCostxCode Professional
"""

import os
import sys
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

app = FastAPI(title="ZeroCostxCode Test Server", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Get the current directory
current_dir = Path(__file__).parent

# Try to find frontend directory
frontend_paths = [
    current_dir / "frontend-professional",
    current_dir / "frontend-v3", 
    current_dir / "frontend-v2"
]

frontend_path = None
for path in frontend_paths:
    if path.exists() and (path / "index.html").exists():
        frontend_path = path
        break

if frontend_path:
    print(f"Using frontend: {frontend_path}")
    app.mount("/static", StaticFiles(directory=str(frontend_path)), name="static")
else:
    print("No frontend directory found")

@app.get("/", response_class=HTMLResponse)
async def serve_frontend():
    """Serve the frontend"""
    if frontend_path and (frontend_path / "index.html").exists():
        with open(frontend_path / "index.html", "r") as f:
            return HTMLResponse(content=f.read())
    else:
        return HTMLResponse(content="""
        <html>
            <head><title>ZeroCostxCode Test</title></head>
            <body>
                <h1>ZeroCostxCode Professional Test Server</h1>
                <p>Frontend not found. Available endpoints:</p>
                <ul>
                    <li><a href="/health">/health</a> - Health check</li>
                    <li><a href="/docs">/docs</a> - API documentation</li>
                </ul>
            </body>
        </html>
        """)

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "frontend_path": str(frontend_path) if frontend_path else "not found",
        "available_frontends": [str(p) for p in frontend_paths if p.exists()]
    }

@app.get("/api/v1/status")
async def api_status():
    """API status endpoint"""
    return {
        "api_version": "v1",
        "status": "running",
        "features": ["basic_ui", "health_check"]
    }

if __name__ == "__main__":
    print("Starting ZeroCostxCode Test Server...")
    print(f"Current directory: {current_dir}")
    print(f"Frontend path: {frontend_path}")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=12000,
        log_level="info"
    )