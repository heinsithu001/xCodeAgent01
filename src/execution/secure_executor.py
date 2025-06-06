#!/usr/bin/env python3
"""
Secure Code Execution Engine for ZeroCostxCode
Minimal but secure code execution with sandboxing
"""

import asyncio
import subprocess
import tempfile
import os
import uuid
import time
import signal
from pathlib import Path
from typing import Dict, Any, Optional, List
import shutil
import json

class SecureCodeExecutor:
    def __init__(self, workspace_dir: str = "workspace"):
        self.workspace_dir = Path(workspace_dir)
        self.workspace_dir.mkdir(exist_ok=True)
        self.active_processes = {}
        
        # Security limits
        self.max_execution_time = 30  # seconds
        self.max_memory = 512 * 1024 * 1024  # 512MB
        self.max_output_size = 1024 * 1024  # 1MB
        
        # Allowed file extensions
        self.allowed_extensions = {
            '.py': 'python3',
            '.js': 'node',
            '.sh': 'bash',
            '.java': 'javac',
            '.cpp': 'g++',
            '.c': 'gcc'
        }
    
    async def execute_code(self, 
                          code: str, 
                          language: str = "python", 
                          user_id: int = None,
                          filename: str = None) -> Dict[str, Any]:
        """Execute code securely with sandboxing"""
        
        execution_id = str(uuid.uuid4())
        start_time = time.time()
        
        try:
            # Create isolated workspace for this execution
            exec_dir = self.workspace_dir / f"exec_{execution_id}"
            exec_dir.mkdir(exist_ok=True)
            
            # Determine file extension and executor
            if not filename:
                ext_map = {
                    'python': '.py',
                    'javascript': '.js',
                    'bash': '.sh',
                    'java': '.java',
                    'cpp': '.cpp',
                    'c': '.c'
                }
                extension = ext_map.get(language.lower(), '.py')
                filename = f"main{extension}"
            else:
                extension = Path(filename).suffix
            
            if extension not in self.allowed_extensions:
                raise ValueError(f"Unsupported file type: {extension}")
            
            # Write code to file
            code_file = exec_dir / filename
            with open(code_file, 'w', encoding='utf-8') as f:
                f.write(code)
            
            # Execute based on language
            result = await self._execute_by_language(code_file, language, exec_dir)
            
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
    
    async def _execute_by_language(self, code_file: Path, language: str, exec_dir: Path) -> Dict[str, Any]:
        """Execute code based on language"""
        
        if language.lower() == 'python':
            return await self._execute_python(code_file, exec_dir)
        elif language.lower() in ['javascript', 'js']:
            return await self._execute_javascript(code_file, exec_dir)
        elif language.lower() == 'bash':
            return await self._execute_bash(code_file, exec_dir)
        else:
            # Default to Python for unsupported languages
            return await self._execute_python(code_file, exec_dir)
    
    async def _execute_python(self, code_file: Path, exec_dir: Path) -> Dict[str, Any]:
        """Execute Python code"""
        cmd = ['python3', str(code_file)]
        return await self._run_subprocess(cmd, exec_dir)
    
    async def _execute_javascript(self, code_file: Path, exec_dir: Path) -> Dict[str, Any]:
        """Execute JavaScript code"""
        # Check if node is available
        if not shutil.which('node'):
            return {
                "success": False,
                "error": "Node.js not installed",
                "output": "",
                "stderr": "Node.js runtime not found"
            }
        
        cmd = ['node', str(code_file)]
        return await self._run_subprocess(cmd, exec_dir)
    
    async def _execute_bash(self, code_file: Path, exec_dir: Path) -> Dict[str, Any]:
        """Execute Bash script"""
        # Make script executable
        os.chmod(code_file, 0o755)
        cmd = ['bash', str(code_file)]
        return await self._run_subprocess(cmd, exec_dir)
    
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
    
    async def execute_terminal_command(self, 
                                     command: str, 
                                     user_id: int,
                                     session_id: str = None) -> Dict[str, Any]:
        """Execute terminal command with security restrictions"""
        
        # Security: Block dangerous commands
        dangerous_commands = [
            'rm -rf', 'sudo', 'su', 'passwd', 'chmod 777',
            'dd', 'mkfs', 'fdisk', 'mount', 'umount',
            'iptables', 'ufw', 'systemctl', 'service'
        ]
        
        for dangerous in dangerous_commands:
            if dangerous in command.lower():
                return {
                    "success": False,
                    "error": f"Command blocked for security: {dangerous}",
                    "output": "",
                    "stderr": "Security restriction"
                }
        
        # Create user workspace
        user_workspace = self.workspace_dir / f"user_{user_id}"
        user_workspace.mkdir(exist_ok=True)
        
        # Execute command in user workspace
        try:
            process = await asyncio.create_subprocess_shell(
                command,
                cwd=str(user_workspace),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                limit=self.max_output_size
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=self.max_execution_time
            )
            
            return {
                "success": process.returncode == 0,
                "output": stdout.decode('utf-8', errors='replace'),
                "stderr": stderr.decode('utf-8', errors='replace'),
                "return_code": process.returncode,
                "command": command,
                "session_id": session_id
            }
            
        except asyncio.TimeoutError:
            return {
                "success": False,
                "error": "Command timeout",
                "output": "",
                "stderr": "Command killed due to timeout"
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

# Global executor instance
executor = SecureCodeExecutor()