#!/usr/bin/env python3
"""
Comprehensive Full Stack Test Suite
Tests frontend, backend, and vLLM integration with real DeepSeek-R1-0528
"""

import asyncio
import json
import time
import requests
import aiohttp
from typing import Dict, Any, List
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FullStackTester:
    def __init__(self, backend_url: str = "http://localhost:12000", vllm_url: str = "http://localhost:8000"):
        self.backend_url = backend_url.rstrip('/')
        self.vllm_url = vllm_url.rstrip('/')
        self.test_results = []
        self.session_id = None
        
    def log_test(self, test_name: str, success: bool, details: str = "", response_time: float = 0):
        """Log test result"""
        result = {
            "test": test_name,
            "success": success,
            "details": details,
            "response_time": response_time,
            "timestamp": datetime.now().isoformat()
        }
        self.test_results.append(result)
        
        status = "✅ PASS" if success else "❌ FAIL"
        logger.info(f"{status} {test_name} ({response_time:.2f}s)")
        if details:
            logger.info(f"    Details: {details}")
    
    def test_vllm_server(self) -> bool:
        """Test vLLM server connectivity and model availability"""
        logger.info("🤖 Testing vLLM Server...")
        
        try:
            # Test health endpoint
            start_time = time.time()
            response = requests.get(f"{self.vllm_url}/health", timeout=10)
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                self.log_test("vLLM Health Check", True, f"Status: {data}", response_time)
            else:
                self.log_test("vLLM Health Check", False, f"HTTP {response.status_code}", response_time)
                return False
            
            # Test models endpoint
            start_time = time.time()
            response = requests.get(f"{self.vllm_url}/v1/models", timeout=10)
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                models = [model["id"] for model in data.get("data", [])]
                self.log_test("vLLM Models List", True, f"Models: {models}", response_time)
                
                # Check if DeepSeek model is available
                deepseek_available = any("deepseek" in model.lower() for model in models)
                if deepseek_available:
                    self.log_test("DeepSeek Model Available", True, "DeepSeek-R1-0528 found", 0)
                else:
                    self.log_test("DeepSeek Model Available", False, "DeepSeek-R1-0528 not found", 0)
                    
            else:
                self.log_test("vLLM Models List", False, f"HTTP {response.status_code}", response_time)
                return False
            
            # Test completion endpoint
            start_time = time.time()
            test_payload = {
                "model": "deepseek-ai/DeepSeek-R1-0528",
                "prompt": "Hello, this is a test. Please respond with 'Test successful'.",
                "max_tokens": 50,
                "temperature": 0.1
            }
            
            response = requests.post(
                f"{self.vllm_url}/v1/completions",
                json=test_payload,
                timeout=60
            )
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                response_text = data.get("choices", [{}])[0].get("text", "")
                self.log_test("vLLM Completion Test", True, f"Response: {response_text[:100]}...", response_time)
            else:
                self.log_test("vLLM Completion Test", False, f"HTTP {response.status_code}", response_time)
                return False
                
            return True
            
        except requests.exceptions.ConnectionError:
            self.log_test("vLLM Server Connection", False, "Connection refused - server not running?", 0)
            return False
        except requests.exceptions.Timeout:
            self.log_test("vLLM Server Connection", False, "Request timeout", 0)
            return False
        except Exception as e:
            self.log_test("vLLM Server Connection", False, str(e), 0)
            return False
    
    def test_backend_server(self) -> bool:
        """Test backend server connectivity and API endpoints"""
        logger.info("🔧 Testing Backend Server...")
        
        try:
            # Test health endpoint
            start_time = time.time()
            response = requests.get(f"{self.backend_url}/health", timeout=10)
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                self.log_test("Backend Health Check", True, f"Status: {data.get('status')}", response_time)
            else:
                self.log_test("Backend Health Check", False, f"HTTP {response.status_code}", response_time)
                return False
            
            # Test status endpoint
            start_time = time.time()
            response = requests.get(f"{self.backend_url}/api/v3/status", timeout=15)
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                success = data.get("success", False)
                vllm_status = data.get("vllm_server", {}).get("status", "unknown")
                self.log_test("Backend Status Check", success, f"vLLM: {vllm_status}", response_time)
            else:
                self.log_test("Backend Status Check", False, f"HTTP {response.status_code}", response_time)
                return False
            
            # Test performance endpoint
            start_time = time.time()
            response = requests.get(f"{self.backend_url}/api/v3/performance", timeout=10)
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                metrics = data.get("metrics", {})
                self.log_test("Backend Performance", True, f"Requests: {metrics.get('requests_total', 0)}", response_time)
            else:
                self.log_test("Backend Performance", False, f"HTTP {response.status_code}", response_time)
            
            return True
            
        except requests.exceptions.ConnectionError:
            self.log_test("Backend Server Connection", False, "Connection refused - server not running?", 0)
            return False
        except Exception as e:
            self.log_test("Backend Server Connection", False, str(e), 0)
            return False
    
    def test_chat_endpoints(self) -> bool:
        """Test chat functionality with different modes"""
        logger.info("💬 Testing Chat Endpoints...")
        
        test_cases = [
            {
                "name": "Demo Mode Chat",
                "payload": {
                    "message": "Hello, can you help me write a Python function to calculate factorial?",
                    "execution_mode": "demo"
                }
            },
            {
                "name": "Production Mode Chat",
                "payload": {
                    "message": "Write a Python function to implement binary search with proper error handling.",
                    "execution_mode": "production",
                    "temperature": 0.1,
                    "max_tokens": 1024
                }
            },
            {
                "name": "Hybrid Mode Chat",
                "payload": {
                    "message": "Explain the difference between list and tuple in Python with examples.",
                    "execution_mode": "hybrid"
                }
            }
        ]
        
        all_passed = True
        
        for test_case in test_cases:
            try:
                start_time = time.time()
                response = requests.post(
                    f"{self.backend_url}/api/v3/chat",
                    json=test_case["payload"],
                    timeout=120  # Longer timeout for model inference
                )
                response_time = time.time() - start_time
                
                if response.status_code == 200:
                    data = response.json()
                    success = data.get("success", False)
                    
                    if success:
                        response_text = data.get("data", {}).get("response", "")
                        session_id = data.get("session_id")
                        
                        if session_id and not self.session_id:
                            self.session_id = session_id
                        
                        self.log_test(
                            test_case["name"],
                            True,
                            f"Response length: {len(response_text)} chars",
                            response_time
                        )
                    else:
                        error = data.get("error", "Unknown error")
                        self.log_test(test_case["name"], False, f"API Error: {error}", response_time)
                        all_passed = False
                else:
                    self.log_test(test_case["name"], False, f"HTTP {response.status_code}", response_time)
                    all_passed = False
                    
            except requests.exceptions.Timeout:
                self.log_test(test_case["name"], False, "Request timeout", 0)
                all_passed = False
            except Exception as e:
                self.log_test(test_case["name"], False, str(e), 0)
                all_passed = False
        
        return all_passed
    
    def test_code_generation(self) -> bool:
        """Test code generation endpoint"""
        logger.info("🔨 Testing Code Generation...")
        
        test_cases = [
            {
                "name": "Python Function Generation",
                "payload": {
                    "prompt": "Create a function to merge two sorted lists",
                    "language": "python",
                    "complexity": "intermediate",
                    "include_tests": True
                }
            },
            {
                "name": "JavaScript Function Generation",
                "payload": {
                    "prompt": "Create a debounce function for handling user input",
                    "language": "javascript",
                    "complexity": "advanced",
                    "include_tests": False
                }
            }
        ]
        
        all_passed = True
        
        for test_case in test_cases:
            try:
                start_time = time.time()
                response = requests.post(
                    f"{self.backend_url}/api/v3/generate-code",
                    json=test_case["payload"],
                    timeout=120
                )
                response_time = time.time() - start_time
                
                if response.status_code == 200:
                    data = response.json()
                    success = data.get("success", False)
                    
                    if success:
                        code = data.get("data", {}).get("code", "")
                        self.log_test(
                            test_case["name"],
                            True,
                            f"Generated {len(code)} chars of code",
                            response_time
                        )
                    else:
                        error = data.get("error", "Unknown error")
                        self.log_test(test_case["name"], False, f"API Error: {error}", response_time)
                        all_passed = False
                else:
                    self.log_test(test_case["name"], False, f"HTTP {response.status_code}", response_time)
                    all_passed = False
                    
            except Exception as e:
                self.log_test(test_case["name"], False, str(e), 0)
                all_passed = False
        
        return all_passed
    
    def test_code_analysis(self) -> bool:
        """Test code analysis endpoint"""
        logger.info("🔍 Testing Code Analysis...")
        
        sample_code = """
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)
"""
        
        try:
            start_time = time.time()
            response = requests.post(
                f"{self.backend_url}/api/v3/analyze-code",
                json={
                    "code": sample_code,
                    "analysis_type": "performance",
                    "include_suggestions": True
                },
                timeout=60
            )
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                success = data.get("success", False)
                
                if success:
                    analysis = data.get("data", {}).get("analysis", "")
                    self.log_test(
                        "Code Analysis",
                        True,
                        f"Analysis length: {len(analysis)} chars",
                        response_time
                    )
                    return True
                else:
                    error = data.get("error", "Unknown error")
                    self.log_test("Code Analysis", False, f"API Error: {error}", response_time)
                    return False
            else:
                self.log_test("Code Analysis", False, f"HTTP {response.status_code}", response_time)
                return False
                
        except Exception as e:
            self.log_test("Code Analysis", False, str(e), 0)
            return False
    
    def test_session_management(self) -> bool:
        """Test session management"""
        logger.info("📝 Testing Session Management...")
        
        if not self.session_id:
            self.log_test("Session Management", False, "No session ID available from previous tests", 0)
            return False
        
        try:
            start_time = time.time()
            response = requests.get(
                f"{self.backend_url}/api/v3/sessions/{self.session_id}",
                timeout=10
            )
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                success = data.get("success", False)
                
                if success:
                    session = data.get("session", {})
                    message_count = len(session.get("messages", []))
                    self.log_test(
                        "Session Retrieval",
                        True,
                        f"Session has {message_count} messages",
                        response_time
                    )
                    return True
                else:
                    self.log_test("Session Retrieval", False, "Session not found", response_time)
                    return False
            else:
                self.log_test("Session Retrieval", False, f"HTTP {response.status_code}", response_time)
                return False
                
        except Exception as e:
            self.log_test("Session Retrieval", False, str(e), 0)
            return False
    
    def test_frontend_serving(self) -> bool:
        """Test frontend serving"""
        logger.info("🌐 Testing Frontend Serving...")
        
        try:
            start_time = time.time()
            response = requests.get(f"{self.backend_url}/", timeout=10)
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                content = response.text
                
                # Check for key frontend elements
                checks = [
                    ("HTML Document", "<!DOCTYPE html>" in content),
                    ("Title Present", "<title>" in content),
                    ("Config Script", "config.js" in content),
                    ("API Base URL", "API_BASE_URL" in content)
                ]
                
                all_checks_passed = all(check[1] for check in checks)
                
                if all_checks_passed:
                    self.log_test(
                        "Frontend Serving",
                        True,
                        f"HTML content loaded ({len(content)} chars)",
                        response_time
                    )
                    return True
                else:
                    failed_checks = [check[0] for check in checks if not check[1]]
                    self.log_test(
                        "Frontend Serving",
                        False,
                        f"Missing elements: {failed_checks}",
                        response_time
                    )
                    return False
            else:
                self.log_test("Frontend Serving", False, f"HTTP {response.status_code}", response_time)
                return False
                
        except Exception as e:
            self.log_test("Frontend Serving", False, str(e), 0)
            return False
    
    def run_all_tests(self) -> Dict[str, Any]:
        """Run all tests and return comprehensive results"""
        logger.info("🚀 Starting Full Stack Test Suite")
        logger.info("=" * 60)
        
        start_time = time.time()
        
        # Run tests in order
        test_functions = [
            ("vLLM Server", self.test_vllm_server),
            ("Backend Server", self.test_backend_server),
            ("Frontend Serving", self.test_frontend_serving),
            ("Chat Endpoints", self.test_chat_endpoints),
            ("Code Generation", self.test_code_generation),
            ("Code Analysis", self.test_code_analysis),
            ("Session Management", self.test_session_management)
        ]
        
        results = {}
        
        for test_name, test_func in test_functions:
            logger.info(f"\n📋 Running {test_name} tests...")
            results[test_name] = test_func()
        
        total_time = time.time() - start_time
        
        # Calculate summary
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result["success"])
        failed_tests = total_tests - passed_tests
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        summary = {
            "total_tests": total_tests,
            "passed": passed_tests,
            "failed": failed_tests,
            "success_rate": success_rate,
            "total_time": total_time,
            "test_results": self.test_results,
            "category_results": results
        }
        
        # Print summary
        logger.info("\n" + "=" * 60)
        logger.info("📊 TEST SUMMARY")
        logger.info("=" * 60)
        logger.info(f"Total Tests: {total_tests}")
        logger.info(f"Passed: {passed_tests}")
        logger.info(f"Failed: {failed_tests}")
        logger.info(f"Success Rate: {success_rate:.1f}%")
        logger.info(f"Total Time: {total_time:.2f}s")
        
        if failed_tests > 0:
            logger.info("\n❌ Failed Tests:")
            for result in self.test_results:
                if not result["success"]:
                    logger.info(f"  - {result['test']}: {result['details']}")
        
        logger.info("\n🎯 Overall Status: " + ("✅ PASS" if success_rate >= 80 else "❌ FAIL"))
        
        return summary

def main():
    """Main function to run the test suite"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Full Stack Test Suite for xCodeAgent")
    parser.add_argument("--backend-url", default="http://localhost:12000", help="Backend URL")
    parser.add_argument("--vllm-url", default="http://localhost:8000", help="vLLM URL")
    parser.add_argument("--output", help="Output file for test results (JSON)")
    
    args = parser.parse_args()
    
    # Run tests
    tester = FullStackTester(args.backend_url, args.vllm_url)
    results = tester.run_all_tests()
    
    # Save results if requested
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(results, f, indent=2)
        logger.info(f"\n💾 Results saved to {args.output}")
    
    # Exit with appropriate code
    exit_code = 0 if results["success_rate"] >= 80 else 1
    exit(exit_code)

if __name__ == "__main__":
    main()