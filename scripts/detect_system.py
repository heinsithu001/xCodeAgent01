#!/usr/bin/env python3
"""
System Capabilities Detection Script
Detects hardware capabilities and generates optimal configuration for the integration.
"""

import json
import platform
import subprocess
import sys
from pathlib import Path

try:
    import psutil
except ImportError:
    print("Installing psutil...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "psutil"])
    import psutil

def detect_gpu():
    """Detect GPU capabilities"""
    gpu_info = {
        'has_gpu': False,
        'gpu_count': 0,
        'gpu_memory': [],
        'cuda_available': False
    }
    
    try:
        # Try to import torch to check CUDA
        import torch
        gpu_info['cuda_available'] = torch.cuda.is_available()
        if gpu_info['cuda_available']:
            gpu_info['has_gpu'] = True
            gpu_info['gpu_count'] = torch.cuda.device_count()
            for i in range(gpu_info['gpu_count']):
                gpu_props = torch.cuda.get_device_properties(i)
                gpu_memory = gpu_props.total_memory // (1024**3)
                gpu_info['gpu_memory'].append({
                    'device': i,
                    'name': gpu_props.name,
                    'memory_gb': gpu_memory
                })
    except ImportError:
        # Try nvidia-smi as fallback
        try:
            result = subprocess.run(['nvidia-smi', '--query-gpu=name,memory.total', '--format=csv,noheader,nounits'], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                gpu_info['has_gpu'] = True
                lines = result.stdout.strip().split('\n')
                gpu_info['gpu_count'] = len(lines)
                for i, line in enumerate(lines):
                    name, memory = line.split(', ')
                    gpu_info['gpu_memory'].append({
                        'device': i,
                        'name': name.strip(),
                        'memory_gb': int(memory) // 1024
                    })
        except (subprocess.SubprocessError, FileNotFoundError):
            pass
    
    return gpu_info

def detect_system_capabilities():
    """Detect complete system capabilities"""
    
    # Basic system info
    system_info = {
        'platform': platform.system(),
        'platform_release': platform.release(),
        'architecture': platform.machine(),
        'python_version': sys.version,
        'cpu_cores': psutil.cpu_count(),
        'cpu_cores_physical': psutil.cpu_count(logical=False),
        'total_ram_gb': psutil.virtual_memory().total // (1024**3),
        'available_ram_gb': psutil.virtual_memory().available // (1024**3),
    }
    
    # GPU detection
    gpu_info = detect_gpu()
    system_info.update(gpu_info)
    
    # Docker availability
    try:
        result = subprocess.run(['docker', '--version'], capture_output=True, text=True)
        system_info['docker_available'] = result.returncode == 0
        system_info['docker_version'] = result.stdout.strip() if result.returncode == 0 else None
    except FileNotFoundError:
        system_info['docker_available'] = False
        system_info['docker_version'] = None
    
    # Git availability
    try:
        result = subprocess.run(['git', '--version'], capture_output=True, text=True)
        system_info['git_available'] = result.returncode == 0
        system_info['git_version'] = result.stdout.strip() if result.returncode == 0 else None
    except FileNotFoundError:
        system_info['git_available'] = False
        system_info['git_version'] = None
    
    return system_info

def determine_deployment_config(system_info):
    """Determine optimal deployment configuration based on system capabilities"""
    
    config = {
        'deployment_type': 'cpu',
        'model_config': {},
        'performance_tier': 'minimal',
        'recommendations': []
    }
    
    # Determine deployment type based on GPU availability and memory
    if system_info['has_gpu'] and system_info['gpu_memory']:
        max_gpu_memory = max(gpu['memory_gb'] for gpu in system_info['gpu_memory'])
        
        if max_gpu_memory >= 24:
            config['deployment_type'] = 'gpu_high'
            config['performance_tier'] = 'high'
            config['model_config'] = {
                'model_name': 'deepseek-ai/DeepSeek-R1-Distill-Qwen-32B',
                'max_model_len': 32768,
                'tensor_parallel_size': 1,
                'gpu_memory_utilization': 0.8,
                'max_concurrent_requests': 20,
                'batch_size': 8
            }
        elif max_gpu_memory >= 16:
            config['deployment_type'] = 'gpu_standard'
            config['performance_tier'] = 'standard'
            config['model_config'] = {
                'model_name': 'deepseek-ai/DeepSeek-R1-Distill-Qwen-14B',
                'max_model_len': 16384,
                'tensor_parallel_size': 1,
                'gpu_memory_utilization': 0.8,
                'max_concurrent_requests': 15,
                'batch_size': 6
            }
        elif max_gpu_memory >= 8:
            config['deployment_type'] = 'gpu_low'
            config['performance_tier'] = 'standard'
            config['model_config'] = {
                'model_name': 'deepseek-ai/DeepSeek-R1-Distill-Qwen-7B',
                'max_model_len': 8192,
                'tensor_parallel_size': 1,
                'gpu_memory_utilization': 0.7,
                'max_concurrent_requests': 10,
                'batch_size': 4,
                'quantization': 'awq'
            }
        else:
            # GPU too small, fall back to CPU
            config['deployment_type'] = 'cpu'
            config['recommendations'].append("GPU memory too low, falling back to CPU deployment")
    
    # CPU-based configuration
    if config['deployment_type'] == 'cpu':
        if system_info['total_ram_gb'] >= 32:
            config['performance_tier'] = 'high'
            config['model_config'] = {
                'model_name': 'deepseek-ai/DeepSeek-R1-Distill-Qwen-14B',
                'max_model_len': 16384,
                'device': 'cpu',
                'max_concurrent_requests': 8,
                'cpu_threads': system_info['cpu_cores'] // 2,
                'batch_size': 4
            }
        elif system_info['total_ram_gb'] >= 16:
            config['performance_tier'] = 'standard'
            config['model_config'] = {
                'model_name': 'deepseek-ai/DeepSeek-R1-Distill-Qwen-7B',
                'max_model_len': 8192,
                'device': 'cpu',
                'max_concurrent_requests': 4,
                'cpu_threads': system_info['cpu_cores'] // 2,
                'batch_size': 2
            }
        else:
            config['performance_tier'] = 'minimal'
            config['model_config'] = {
                'model_name': 'deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B',
                'max_model_len': 4096,
                'device': 'cpu',
                'max_concurrent_requests': 2,
                'cpu_threads': 2,
                'batch_size': 1,
                'quantization': 'gptq'
            }
            config['recommendations'].append("Limited RAM detected. Consider upgrading for better performance.")
    
    # Add general recommendations
    if not system_info['docker_available']:
        config['recommendations'].append("Docker not available. Manual installation required.")
    
    if system_info['total_ram_gb'] < 8:
        config['recommendations'].append("Very limited RAM. Performance will be significantly reduced.")
    
    return config

def save_configuration(system_info, config, output_dir):
    """Save system detection results and configuration"""
    output_dir = Path(output_dir)
    output_dir.mkdir(exist_ok=True)
    
    # Save system info
    with open(output_dir / 'system_info.json', 'w') as f:
        json.dump(system_info, f, indent=2)
    
    # Save deployment config
    with open(output_dir / 'deployment_config.json', 'w') as f:
        json.dump(config, f, indent=2)
    
    # Generate environment file
    env_content = f"""# Auto-generated configuration based on system capabilities
# Generated on: {platform.node()} - {system_info['platform']}

# System Configuration
DEPLOYMENT_TYPE={config['deployment_type']}
PERFORMANCE_TIER={config['performance_tier']}
CPU_CORES={system_info['cpu_cores']}
TOTAL_RAM_GB={system_info['total_ram_gb']}

# Model Configuration
DEEPSEEK_MODEL={config['model_config']['model_name']}
MAX_MODEL_LENGTH={config['model_config']['max_model_len']}
DEVICE_TYPE={config['model_config'].get('device', 'auto')}
MAX_CONCURRENT_REQUESTS={config['model_config']['max_concurrent_requests']}
BATCH_SIZE={config['model_config']['batch_size']}

# vLLM Server Configuration
VLLM_HOST=0.0.0.0
VLLM_PORT=8000
TRUST_REMOTE_CODE=true

# Integration Configuration
CODEAGENT03_CONFIG=./config/codeagent03.yaml
OPENHANDS_CONFIG=./config/openhands.json
LOG_LEVEL=INFO

# Performance Optimization
"""
    
    # Add device-specific configurations
    if config['deployment_type'].startswith('gpu'):
        env_content += f"""
# GPU Configuration
ENABLE_GPU=true
TENSOR_PARALLEL_SIZE={config['model_config'].get('tensor_parallel_size', 1)}
GPU_MEMORY_UTILIZATION={config['model_config'].get('gpu_memory_utilization', 0.8)}
"""
        if 'quantization' in config['model_config']:
            env_content += f"QUANTIZATION={config['model_config']['quantization']}\n"
    else:
        env_content += f"""
# CPU Configuration
ENABLE_GPU=false
CPU_THREADS={config['model_config'].get('cpu_threads', 2)}
"""
        if 'quantization' in config['model_config']:
            env_content += f"QUANTIZATION={config['model_config']['quantization']}\n"
    
    with open(output_dir / '.env', 'w') as f:
        f.write(env_content)

def print_summary(system_info, config):
    """Print system detection summary"""
    print("\n" + "="*60)
    print("SYSTEM CAPABILITIES DETECTION SUMMARY")
    print("="*60)
    
    print(f"\n🖥️  SYSTEM INFO:")
    print(f"   Platform: {system_info['platform']} {system_info['platform_release']}")
    print(f"   CPU Cores: {system_info['cpu_cores']} ({system_info['cpu_cores_physical']} physical)")
    print(f"   Total RAM: {system_info['total_ram_gb']} GB")
    print(f"   Available RAM: {system_info['available_ram_gb']} GB")
    
    if system_info['has_gpu']:
        print(f"\n🎮 GPU INFO:")
        for gpu in system_info['gpu_memory']:
            print(f"   GPU {gpu['device']}: {gpu['name']} - {gpu['memory_gb']} GB")
    else:
        print(f"\n🎮 GPU INFO: No GPU detected")
    
    print(f"\n⚙️  DEPLOYMENT CONFIG:")
    print(f"   Type: {config['deployment_type']}")
    print(f"   Performance Tier: {config['performance_tier']}")
    print(f"   Model: {config['model_config']['model_name']}")
    print(f"   Max Context: {config['model_config']['max_model_len']} tokens")
    print(f"   Concurrent Requests: {config['model_config']['max_concurrent_requests']}")
    
    if config['recommendations']:
        print(f"\n⚠️  RECOMMENDATIONS:")
        for rec in config['recommendations']:
            print(f"   • {rec}")
    
    print(f"\n✅ Configuration files saved to: ./config/")
    print("="*60)

def main():
    """Main function"""
    print("🔍 Detecting system capabilities...")
    
    # Detect system capabilities
    system_info = detect_system_capabilities()
    
    # Determine optimal configuration
    config = determine_deployment_config(system_info)
    
    # Save configuration
    config_dir = Path(__file__).parent.parent / 'config'
    save_configuration(system_info, config, config_dir)
    
    # Print summary
    print_summary(system_info, config)
    
    return system_info, config

if __name__ == "__main__":
    main()