#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script for running API error handling tests
"""

import subprocess
import sys
import os

def main():
    os.chdir(r"C:\Users\Satawad_Ta\Documents\GitHub\Python.worktrees\agents-api-request-error-handling-test")
    
    print("=" * 80)
    print("RUNNING API ERROR HANDLING TEST SUITE")
    print("=" * 80)
    print()
    
    # Run first test
    print("\n[1/2] Running test_api_error_handling.py...")
    result1 = subprocess.run(
        [sys.executable, "-m", "pytest", "test_api_error_handling.py", "-v", "--tb=short", "-s"],
        capture_output=False
    )
    
    # Run second test
    print("\n[2/2] Running test_api_integration.py...")
    result2 = subprocess.run(
        [sys.executable, "-m", "pytest", "test_api_integration.py", "-v", "--tb=short", "-s"],
        capture_output=False
    )
    
    print("\n" + "=" * 80)
    print("TEST RESULTS SUMMARY")
    print("=" * 80)
    
    if result1.returncode == 0:
        print("✓ test_api_error_handling.py PASSED")
    else:
        print("✗ test_api_error_handling.py FAILED")
    
    if result2.returncode == 0:
        print("✓ test_api_integration.py PASSED")
    else:
        print("✗ test_api_integration.py FAILED")
    
    return max(result1.returncode, result2.returncode)

if __name__ == "__main__":
    sys.exit(main())
