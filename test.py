# test_security.py - Security Testing Script
"""
Run this script to test your application's security measures
Usage: python3 test_security.py
"""

import requests
import json
from typing import Dict, List, Tuple

# Configure your application URL
BASE_URL = "http://localhost:5000"  # Change to your URL

class SecurityTester:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.session = requests.Session()
        self.results = []
    
    def test(self, name: str, passed: bool, details: str = ""):
        """Record test result"""
        status = "✓ PASS" if passed else "✗ FAIL"
        self.results.append({
            'test': name,
            'passed': passed,
            'details': details
        })
        print(f"{status} - {name}")
        if details:
            print(f"  Details: {details}")
    
    def print_summary(self):
        """Print test summary"""
        total = len(self.results)
        passed = sum(1 for r in self.results if r['passed'])
        failed = total - passed
        
        print("\n" + "="*60)
        print(f"Security Test Summary: {passed}/{total} tests passed")
        print("="*60)
        
        if failed > 0:
            print("\nFailed Tests:")
            for r in self.results:
                if not r['passed']:
                    print(f"  - {r['test']}: {r['details']}")
    
    # ========== SQL Injection Tests ==========
    
    def test_sql_injection_group_id(self):
        """Test SQL injection in group_id parameter"""
        payloads = [
            "'; DROP TABLE members;--",
            "' OR '1'='1",
            "1' UNION SELECT password FROM users--",
            "admin'--",
        ]
        
        for payload in payloads:
            try:
                response = self.session.get(
                    f"{self.base_url}/api/members",
                    params={'group_id': payload, 'review_number': 1}
                )
                
                # Should return 400/401 or empty result, not 500 or database error
                if response.status_code == 500:
                    self.test(
                        f"SQL Injection - group_id: {payload[:20]}",
                        False,
                        "Server returned 500 error - possible SQL injection"
                    )
                    return
                
                # Check response doesn't contain SQL error messages
                body = response.text.lower()
                sql_errors = ['mysql', 'syntax error', 'sqlstate', 'database error']
                if any(err in body for err in sql_errors):
                    self.test(
                        f"SQL Injection - group_id: {payload[:20]}",
                        False,
                        "Response contains SQL error messages"
                    )
                    return
                    
            except Exception as e:
                pass
        
        self.test("SQL Injection - group_id", True, "All payloads handled safely")
    
    def test_sql_injection_review_number(self):
        """Test SQL injection in review_number parameter"""
        payloads = [
            "1 OR 1=1",
            "1'; DROP TABLE members;--",
            "999999",
            "-1",
            "abc"
        ]
        
        for payload in payloads:
            try:
                response = self.session.get(
                    f"{self.base_url}/api/review{payload}/marks",
                    params={'group_id': 'TEST001'}
                )
                
                if response.status_code == 500:
                    self.test(
                        f"SQL Injection - review_number: {payload}",
                        False,
                        "Server error on malicious input"
                    )
                    return
            except Exception:
                pass
        
        self.test("SQL Injection - review_number", True, "All payloads handled safely")
    
    # ========== XSS Tests ==========
    
    def test_xss_reflected(self):
        """Test reflected XSS vulnerabilities"""
        payloads = [
            "<script>alert('XSS')</script>",
            "<img src=x onerror=alert('XSS')>",
            "javascript:alert('XSS')",
            "<svg onload=alert('XSS')>"
        ]
        
        for payload in payloads:
            try:
                response = self.session.post(
                    f"{self.base_url}/api/review1/responses",
                    json={
                        'group_id': payload,
                        'date': '2025-01-01',
                        'comments': payload,
                        'responses': []
                    }
                )
                
                # Check if payload is reflected without sanitization
                if payload in response.text:
                    self.test(
                        f"XSS - Reflected: {payload[:30]}",
                        False,
                        "Payload reflected without sanitization"
                    )
                    return
            except Exception:
                pass
        
        self.test("XSS - Reflected", True, "XSS payloads sanitized")
    
    # ========== Authentication Tests ==========
    
    def test_authentication_required(self):
        """Test that endpoints require authentication"""
        endpoints = [
            '/api/members',
            '/api/review1/marks',
            '/api/review1/responses',
            '/api/review1/config'
        ]
        
        # Clear any existing session
        self.session.cookies.clear()
        
        failed_endpoints = []
        for endpoint in endpoints:
            try:
                response = self.session.get(f"{self.base_url}{endpoint}")
                if response.status_code == 200:
                    failed_endpoints.append(endpoint)
            except Exception:
                pass
        
        if failed_endpoints:
            self.test(
                "Authentication Required",
                False,
                f"Endpoints accessible without auth: {', '.join(failed_endpoints)}"
            )
        else:
            self.test("Authentication Required", True, "All endpoints protected")
    
    # ========== CSRF Tests ==========
    
    def test_csrf_protection(self):
        """Test CSRF token requirement"""
        try:
            # Try POST without CSRF token
            response = self.session.post(
                f"{self.base_url}/api/review1/marks",
                json={'marks': []}
            )
            
            # Should get 400 or 403 due to missing CSRF token
            if response.status_code in [400, 403]:
                self.test("CSRF Protection", True, "CSRF token required")
            elif response.status_code == 200:
                self.test("CSRF Protection", False, "POST succeeded without CSRF token")
            else:
                self.test("CSRF Protection", None, f"Unexpected status: {response.status_code}")
        except Exception as e:
            self.test("CSRF Protection", None, f"Error: {str(e)}")
    
    # ========== Security Headers Tests ==========
    
    def test_security_headers(self):
        """Test presence of security headers"""
        required_headers = {
            'Strict-Transport-Security': 'HSTS',
            'X-Content-Type-Options': 'nosniff',
            'X-Frame-Options': 'DENY or SAMEORIGIN',
            'X-XSS-Protection': '1',
            'Content-Security-Policy': 'CSP'
        }
        
        try:
            response = self.session.get(f"{self.base_url}/")
            
            missing_headers = []
            for header, description in required_headers.items():
                if header not in response.headers:
                    missing_headers.append(f"{header} ({description})")
            
            if missing_headers:
                self.test(
                    "Security Headers",
                    False,
                    f"Missing: {', '.join(missing_headers)}"
                )
            else:
                self.test("Security Headers", True, "All required headers present")
        except Exception as e:
            self.test("Security Headers", None, f"Error: {str(e)}")
    
    # ========== HTTPS Tests ==========
    
    def test_https_enforcement(self):
        """Test HTTPS enforcement"""
        if self.base_url.startswith('http://'):
            self.test(
                "HTTPS Enforcement",
                False,
                "Application running on HTTP (use HTTPS in production)"
            )
        else:
            self.test("HTTPS Enforcement", True, "Application using HTTPS")
    
    # ========== Rate Limiting Tests ==========
    
    def test_rate_limiting(self):
        """Test rate limiting on login endpoint"""
        print("\nTesting rate limiting (this may take a minute)...")
        
        attempts = 0
        rate_limited = False
        
        try:
            for i in range(10):
                response = self.session.post(
                    f"{self.base_url}/api/login",
                    json={'username': 'test', 'password': 'test'}
                )
                attempts += 1
                
                if response.status_code == 429:
                    rate_limited = True
                    break
            
            if rate_limited:
                self.test(
                    "Rate Limiting",
                    True,
                    f"Rate limit triggered after {attempts} attempts"
                )
            else:
                self.test(
                    "Rate Limiting",
                    False,
                    f"No rate limit after {attempts} attempts"
                )
        except Exception as e:
            self.test("Rate Limiting", None, f"Error: {str(e)}")
    
    # ========== Input Validation Tests ==========
    
    def test_input_validation(self):
        """Test input validation"""
        test_cases = [
            ('group_id', 'A' * 1000, "Very long group_id"),
            ('roll_no', '../../../etc/passwd', "Path traversal in roll_no"),
            ('comments', 'A' * 10000, "Very long comments"),
        ]
        
        failed_cases = []
        
        for field, value, description in test_cases:
            try:
                data = {
                    'group_id': 'TEST001',
                    'date': '2025-01-01',
                    'comments': '',
                    'responses': []
                }
                data[field] = value
                
                response = self.session.post(
                    f"{self.base_url}/api/review1/responses",
                    json=data
                )
                
                # Should reject invalid input (400, 413) not 500
                if response.status_code == 500:
                    failed_cases.append(description)
            except Exception:
                pass
        
        if failed_cases:
            self.test(
                "Input Validation",
                False,
                f"Server errors on: {', '.join(failed_cases)}"
            )
        else:
            self.test("Input Validation", True, "Invalid inputs handled properly")
    
    # ========== Error Handling Tests ==========
    
    def test_error_disclosure(self):
        """Test that errors don't expose sensitive information"""
        try:
            # Trigger an error
            response = self.session.get(f"{self.base_url}/api/review999/marks")
            
            sensitive_terms = [
                'traceback', 'stack trace', 'exception',
                'mysql', 'sqlstate', 'database error',
                '/var/www', '/home/', 'server.py'
            ]
            
            body = response.text.lower()
            exposed = [term for term in sensitive_terms if term in body]
            
            if exposed:
                self.test(
                    "Error Information Disclosure",
                    False,
                    f"Error exposed: {', '.join(exposed)}"
                )
            else:
                self.test("Error Information Disclosure", True, "No sensitive info in errors")
        except Exception as e:
            self.test("Error Information Disclosure", None, f"Error: {str(e)}")
    
    # ========== Run All Tests ==========
    
    def run_all_tests(self):
        """Run all security tests"""
        print("="*60)
        print("Running Security Tests")
        print("="*60)
        print(f"Target: {self.base_url}\n")
        
        print("SQL Injection Tests:")
        self.test_sql_injection_group_id()
        self.test_sql_injection_review_number()
        
        print("\nXSS Tests:")
        self.test_xss_reflected()
        
        print("\nAuthentication Tests:")
        self.test_authentication_required()
        
        print("\nCSRF Tests:")
        self.test_csrf_protection()
        
        print("\nSecurity Headers Tests:")
        self.test_security_headers()
        
        print("\nHTTPS Tests:")
        self.test_https_enforcement()
        
        print("\nRate Limiting Tests:")
        self.test_rate_limiting()
        
        print("\nInput Validation Tests:")
        self.test_input_validation()
        
        print("\nError Handling Tests:")
        self.test_error_disclosure()
        
        self.print_summary()


if __name__ == "__main__":
    import sys
    
    # Allow custom URL from command line
    url = sys.argv[1] if len(sys.argv) > 1 else BASE_URL
    
    tester = SecurityTester(url)
    tester.run_all_tests()
    
    # Exit with error code if any tests failed
    failed = sum(1 for r in tester.results if not r['passed'])
    sys.exit(1 if failed > 0 else 0)