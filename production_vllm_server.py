#!/usr/bin/env python3
"""
Production vLLM Server for DeepSeek-R1-0528
Real model deployment with optimized configuration
"""

import os
import sys
import time
import logging
import subprocess
import psutil
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ProductionVLLMConfig:
    """Production configuration for vLLM server"""
    
    def __init__(self):
        # Model configuration
        self.model_name = "deepseek-ai/DeepSeek-R1-0528"
        self.host = "0.0.0.0"
        self.port = 8000
        
        # Performance settings
        self.max_model_len = 32768
        self.trust_remote_code = True
        self.device = self.detect_device()
        self.tensor_parallel_size = self.get_optimal_tp_size()
        self.gpu_memory_utilization = 0.85
        self.max_num_seqs = 256
        self.max_num_batched_tokens = 8192
        
        # Advanced settings
        self.enable_chunked_prefill = True
        self.max_num_batched_tokens = 8192
        self.block_size = 16
        self.swap_space = 4  # GB
        
    def detect_device(self) -> str:
        """Detect optimal device configuration"""
        try:
            import torch
            if torch.cuda.is_available():
                gpu_count = torch.cuda.device_count()
                total_memory = sum(torch.cuda.get_device_properties(i).total_memory 
                                 for i in range(gpu_count)) / (1024**3)  # GB
                
                logger.info(f"Detected {gpu_count} GPU(s) with {total_memory:.1f}GB total memory")
                
                if total_memory >= 80:  # High-end setup
                    return "cuda"
                elif total_memory >= 24:  # Mid-range setup
                    return "cuda"
                else:  # Low VRAM
                    logger.warning("Low GPU memory detected. Consider using CPU mode.")
                    return "cuda"
            else:
                logger.info("No CUDA GPUs detected, using CPU")
                return "cpu"
        except ImportError:
            logger.warning("PyTorch not installed, defaulting to CPU")
            return "cpu"
    
    def get_optimal_tp_size(self) -> int:
        """Get optimal tensor parallel size"""
        try:
            import torch
            if torch.cuda.is_available():
                gpu_count = torch.cuda.device_count()
                total_memory = sum(torch.cuda.get_device_properties(i).total_memory 
                                 for i in range(gpu_count)) / (1024**3)
                
                # DeepSeek-R1-0528 is approximately 67B parameters
                # Rough estimate: need ~134GB for FP16, ~67GB for INT8
                if total_memory >= 160:  # Multiple high-end GPUs
                    return min(gpu_count, 4)
                elif total_memory >= 80:  # High-end single GPU or dual setup
                    return min(gpu_count, 2)
                else:  # Single GPU or limited memory
                    return 1
            else:
                return 1
        except ImportError:
            return 1
    
    def get_memory_settings(self) -> dict:
        """Get memory optimization settings"""
        total_ram = psutil.virtual_memory().total / (1024**3)  # GB
        
        if self.device == "cpu":
            # CPU mode settings
            return {
                "max_model_len": min(self.max_model_len, 16384),  # Reduce for CPU
                "block_size": 8,  # Smaller blocks for CPU
                "max_num_seqs": min(self.max_num_seqs, 64),  # Fewer sequences
                "swap_space": min(self.swap_space, total_ram * 0.1)
            }
        else:
            # GPU mode settings
            return {
                "max_model_len": self.max_model_len,
                "block_size": self.block_size,
                "max_num_seqs": self.max_num_seqs,
                "swap_space": self.swap_space
            }

def check_requirements():
    """Check if all requirements are met"""
    logger.info("Checking system requirements...")
    
    # Check Python version
    if sys.version_info < (3, 8):
        logger.error("Python 3.8+ is required")
        return False
    
    # Check available memory
    total_ram = psutil.virtual_memory().total / (1024**3)
    available_ram = psutil.virtual_memory().available / (1024**3)
    
    logger.info(f"Total RAM: {total_ram:.1f}GB, Available: {available_ram:.1f}GB")
    
    if available_ram < 16:
        logger.warning("Low available RAM. DeepSeek-R1-0528 requires significant memory.")
        logger.warning("Consider closing other applications or using a smaller model.")
    
    # Check disk space
    disk_usage = psutil.disk_usage('/')
    free_space = disk_usage.free / (1024**3)
    
    logger.info(f"Free disk space: {free_space:.1f}GB")
    
    if free_space < 50:
        logger.warning("Low disk space. Model download requires ~50GB+")
        return False
    
    return True

def install_vllm():
    """Install vLLM if not available"""
    try:
        import vllm
        logger.info("vLLM is already installed")
        return True
    except ImportError:
        logger.info("Installing vLLM...")
        try:
            # Install vLLM with CUDA support
            subprocess.check_call([
                sys.executable, "-m", "pip", "install", 
                "vllm", "--extra-index-url", "https://download.pytorch.org/whl/cu118"
            ])
            logger.info("vLLM installed successfully")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to install vLLM: {e}")
            return False

def start_vllm_server(config: ProductionVLLMConfig):
    """Start vLLM server with production configuration"""
    logger.info("Starting vLLM server with DeepSeek-R1-0528...")
    
    # Build command
    cmd = [
        "python", "-m", "vllm.entrypoints.openai.api_server",
        "--model", config.model_name,
        "--host", config.host,
        "--port", str(config.port),
        "--trust-remote-code",
    ]
    
    # Add device-specific settings
    if config.device == "cuda":
        cmd.extend([
            "--tensor-parallel-size", str(config.tensor_parallel_size),
            "--gpu-memory-utilization", str(config.gpu_memory_utilization),
        ])
    else:
        cmd.extend([
            "--device", "cpu",
        ])
    
    # Add memory settings
    memory_settings = config.get_memory_settings()
    cmd.extend([
        "--max-model-len", str(memory_settings["max_model_len"]),
        "--block-size", str(memory_settings["block_size"]),
        "--max-num-seqs", str(memory_settings["max_num_seqs"]),
        "--swap-space", str(memory_settings["swap_space"]),
    ])
    
    # Advanced optimizations
    if config.enable_chunked_prefill:
        cmd.append("--enable-chunked-prefill")
    
    logger.info(f"vLLM command: {' '.join(cmd)}")
    
    # Set environment variables
    env = os.environ.copy()
    env["CUDA_VISIBLE_DEVICES"] = "0"  # Use first GPU
    env["HF_HOME"] = str(Path.home() / ".cache" / "huggingface")
    
    # Start the server
    try:
        process = subprocess.Popen(cmd, env=env)
        logger.info(f"vLLM server started with PID: {process.pid}")
        
        # Save PID for cleanup
        with open(".vllm_production_pid", "w") as f:
            f.write(str(process.pid))
        
        return process
    except Exception as e:
        logger.error(f"Failed to start vLLM server: {e}")
        return None

def main():
    """Main function to start production vLLM server"""
    logger.info("🚀 Starting Production vLLM Server for DeepSeek-R1-0528")
    
    # Check requirements
    if not check_requirements():
        logger.error("System requirements not met")
        sys.exit(1)
    
    # Install vLLM if needed
    if not install_vllm():
        logger.error("Failed to install vLLM")
        sys.exit(1)
    
    # Create configuration
    config = ProductionVLLMConfig()
    
    logger.info("Configuration:")
    logger.info(f"  Model: {config.model_name}")
    logger.info(f"  Device: {config.device}")
    logger.info(f"  Tensor Parallel Size: {config.tensor_parallel_size}")
    logger.info(f"  Max Model Length: {config.max_model_len}")
    logger.info(f"  GPU Memory Utilization: {config.gpu_memory_utilization}")
    
    # Start server
    process = start_vllm_server(config)
    
    if process:
        logger.info("✅ vLLM server starting...")
        logger.info("📊 Server will be available at:")
        logger.info(f"   • OpenAI API: http://{config.host}:{config.port}/v1")
        logger.info(f"   • Health Check: http://{config.host}:{config.port}/health")
        logger.info(f"   • Models: http://{config.host}:{config.port}/v1/models")
        logger.info("")
        logger.info("⏳ Model loading may take several minutes...")
        logger.info("💡 Monitor progress in the logs above")
        logger.info("")
        logger.info("🛑 To stop: kill $(cat .vllm_production_pid)")
        
        try:
            process.wait()
        except KeyboardInterrupt:
            logger.info("Stopping vLLM server...")
            process.terminate()
            process.wait()
    else:
        logger.error("❌ Failed to start vLLM server")
        sys.exit(1)

if __name__ == "__main__":
    main()