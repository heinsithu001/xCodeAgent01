#!/usr/bin/env python3
"""
Real-Time Testing Client for DeepSeek R1 0528
Tests the production environment with real-time data processing
"""

import asyncio
import json
import time
import aiohttp
import websockets
from typing import Dict, Any

# Configuration
BACKEND_URL = "http://localhost:12000"
WS_URL = "ws://localhost:12000/ws/real-time"

class RealTimeTestClient:
    """Test client for real-time functionality"""
    
    def __init__(self):
        self.session: aiohttp.ClientSession = None
    
    async def get_session(self):
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session
    
    async def test_system_status(self):
        """Test system status endpoint"""
        print("🔍 Testing system status...")
        
        try:
            session = await self.get_session()
            async with session.get(f"{BACKEND_URL}/api/v1/status") as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ System Status: {data['status']}")
                    print(f"   vLLM Server: {data['vllm_server'].get('status', 'unknown')}")
                    print(f"   Real-time Mode: {data['real_time_mode']}")
                    return True
                else:
                    print(f"❌ Status check failed: HTTP {response.status}")
                    return False
        except Exception as e:
            print(f"❌ Status check error: {e}")
            return False
    
    async def test_code_generation(self):
        """Test real-time code generation"""
        print("\n💻 Testing real-time code generation...")
        
        try:
            session = await self.get_session()
            
            request_data = {
                "prompt": "Create a FastAPI endpoint for real-time data streaming",
                "language": "python",
                "complexity": "advanced",
                "temperature": 0.1,
                "max_tokens": 1024
            }
            
            start_time = time.time()
            async with session.post(
                f"{BACKEND_URL}/api/v1/generate-code",
                json=request_data
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    execution_time = time.time() - start_time
                    
                    print(f"✅ Code generation successful")
                    print(f"   Execution time: {execution_time:.2f}s")
                    print(f"   Model: {data.get('model', 'unknown')}")
                    print(f"   Real-time mode: {data.get('real_time_mode', False)}")
                    print(f"   Code length: {len(data.get('code', ''))} characters")
                    
                    # Show first few lines of generated code
                    code_lines = data.get('code', '').split('\n')[:5]
                    print("   Generated code preview:")
                    for line in code_lines:
                        print(f"     {line}")
                    
                    return True
                else:
                    print(f"❌ Code generation failed: HTTP {response.status}")
                    return False
        except Exception as e:
            print(f"❌ Code generation error: {e}")
            return False
    
    async def test_chat_functionality(self):
        """Test real-time chat"""
        print("\n💬 Testing real-time chat...")
        
        try:
            session = await self.get_session()
            
            request_data = {
                "message": "Explain the benefits of real-time data processing with DeepSeek R1",
                "context": "real_time_systems",
                "temperature": 0.1,
                "max_tokens": 512
            }
            
            start_time = time.time()
            async with session.post(
                f"{BACKEND_URL}/api/v1/chat",
                json=request_data
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    execution_time = time.time() - start_time
                    
                    print(f"✅ Chat response successful")
                    print(f"   Execution time: {execution_time:.2f}s")
                    print(f"   Model: {data.get('model', 'unknown')}")
                    print(f"   Real-time mode: {data.get('real_time_mode', False)}")
                    print(f"   Response length: {len(data.get('response', ''))} characters")
                    
                    # Show response preview
                    response_text = data.get('response', '')[:200]
                    print(f"   Response preview: {response_text}...")
                    
                    return True
                else:
                    print(f"❌ Chat failed: HTTP {response.status}")
                    return False
        except Exception as e:
            print(f"❌ Chat error: {e}")
            return False
    
    async def test_real_time_streaming(self):
        """Test real-time data streaming"""
        print("\n🌊 Testing real-time data streaming...")
        
        try:
            session = await self.get_session()
            
            request_data = {
                "data_type": "performance_metrics",
                "query": "Analyze system performance trends and provide optimization recommendations",
                "processing_mode": "streaming",
                "max_results": 50
            }
            
            start_time = time.time()
            async with session.post(
                f"{BACKEND_URL}/api/v1/real-time-data",
                json=request_data
            ) as response:
                if response.status == 200:
                    chunk_count = 0
                    async for line in response.content:
                        if line.startswith(b'data: '):
                            chunk_data = json.loads(line[6:].decode())
                            chunk_count += 1
                            
                            if chunk_count <= 3:  # Show first few chunks
                                print(f"   📦 Chunk {chunk_count}: {chunk_data.get('content', '')[:50]}...")
                            
                            if chunk_data.get('chunk_id') == 'final':
                                execution_time = time.time() - start_time
                                summary = chunk_data.get('summary', {})
                                print(f"✅ Streaming completed")
                                print(f"   Total chunks: {chunk_count}")
                                print(f"   Execution time: {execution_time:.2f}s")
                                print(f"   Processing time: {summary.get('processing_time', 0):.2f}s")
                                break
                    
                    return True
                else:
                    print(f"❌ Streaming failed: HTTP {response.status}")
                    return False
        except Exception as e:
            print(f"❌ Streaming error: {e}")
            return False
    
    async def test_websocket_connection(self):
        """Test WebSocket real-time connection"""
        print("\n🔌 Testing WebSocket real-time connection...")
        
        try:
            async with websockets.connect(WS_URL) as websocket:
                # Send a real-time data request
                request = {
                    "type": "real_time_data",
                    "payload": {
                        "data_type": "code_analysis",
                        "query": "Analyze this Python function for performance optimization",
                        "processing_mode": "streaming"
                    }
                }
                
                await websocket.send(json.dumps(request))
                
                # Receive responses
                chunk_count = 0
                start_time = time.time()
                
                while True:
                    try:
                        response = await asyncio.wait_for(websocket.recv(), timeout=30)
                        data = json.loads(response)
                        chunk_count += 1
                        
                        if chunk_count <= 3:  # Show first few chunks
                            print(f"   📡 WS Chunk {chunk_count}: {data.get('content', '')[:50]}...")
                        
                        if data.get('chunk_id') == 'final':
                            execution_time = time.time() - start_time
                            print(f"✅ WebSocket streaming completed")
                            print(f"   Total chunks: {chunk_count}")
                            print(f"   Execution time: {execution_time:.2f}s")
                            break
                            
                    except asyncio.TimeoutError:
                        print("⚠️  WebSocket timeout")
                        break
                
                return True
                
        except Exception as e:
            print(f"❌ WebSocket error: {e}")
            return False
    
    async def test_performance_metrics(self):
        """Test performance metrics endpoint"""
        print("\n📊 Testing performance metrics...")
        
        try:
            session = await self.get_session()
            async with session.get(f"{BACKEND_URL}/api/v1/metrics") as response:
                if response.status == 200:
                    data = await response.json()
                    
                    print(f"✅ Metrics retrieved successfully")
                    
                    system_metrics = data.get('system_metrics', {})
                    print(f"   Total requests: {system_metrics.get('total_requests', 0)}")
                    print(f"   Successful requests: {system_metrics.get('successful_requests', 0)}")
                    print(f"   Failed requests: {system_metrics.get('failed_requests', 0)}")
                    
                    real_time_stats = data.get('real_time_stats', {})
                    print(f"   Active connections: {real_time_stats.get('active_connections', 0)}")
                    print(f"   Active streams: {real_time_stats.get('active_streams', 0)}")
                    
                    return True
                else:
                    print(f"❌ Metrics failed: HTTP {response.status}")
                    return False
        except Exception as e:
            print(f"❌ Metrics error: {e}")
            return False
    
    async def run_all_tests(self):
        """Run all tests"""
        print("🚀 Starting DeepSeek R1 0528 Real-Time Tests")
        print("=" * 50)
        
        tests = [
            ("System Status", self.test_system_status),
            ("Code Generation", self.test_code_generation),
            ("Chat Functionality", self.test_chat_functionality),
            ("Real-Time Streaming", self.test_real_time_streaming),
            ("WebSocket Connection", self.test_websocket_connection),
            ("Performance Metrics", self.test_performance_metrics),
        ]
        
        results = []
        
        for test_name, test_func in tests:
            try:
                result = await test_func()
                results.append((test_name, result))
            except Exception as e:
                print(f"❌ {test_name} failed with exception: {e}")
                results.append((test_name, False))
        
        # Summary
        print("\n" + "=" * 50)
        print("📋 Test Results Summary:")
        print("=" * 50)
        
        passed = 0
        for test_name, result in results:
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"   {test_name}: {status}")
            if result:
                passed += 1
        
        print(f"\n🎯 Overall: {passed}/{len(results)} tests passed")
        
        if passed == len(results):
            print("🎉 All tests passed! DeepSeek R1 real-time environment is fully operational!")
        else:
            print("⚠️  Some tests failed. Check the logs for details.")
        
        # Cleanup
        if self.session and not self.session.closed:
            await self.session.close()

async def main():
    """Main test function"""
    client = RealTimeTestClient()
    await client.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main())