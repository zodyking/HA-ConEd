#!/usr/bin/env python3
"""
Test script to verify Python server setup and TOTP generation
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from database import init_database
import pyotp

def test_pyotp():
    """Test PyOTP generation"""
    print("Testing PyOTP...")
    test_secret = "LEONOWJLZM7GE3DM"
    totp = pyotp.TOTP(test_secret)
    code = totp.now()
    print(f"[OK] TOTP code generated: {code}")
    return True

def test_database():
    """Test database initialization"""
    print("Testing database...")
    try:
        init_database()
        print("[OK] Database initialized successfully")
        return True
    except Exception as e:
        print(f"[FAIL] Database initialization failed: {e}")
        return False

def test_imports():
    """Test all required imports"""
    print("Testing imports...")
    try:
        import fastapi
        import uvicorn
        import pyotp
        import playwright
        import cryptography
        import pydantic
        print("[OK] All imports successful")
        return True
    except ImportError as e:
        print(f"[FAIL] Import failed: {e}")
        return False

if __name__ == "__main__":
    print("=" * 50)
    print("ConEd Scraper - Server Setup Test")
    print("=" * 50)
    print()
    
    results = []
    results.append(("Imports", test_imports()))
    results.append(("Database", test_database()))
    results.append(("PyOTP", test_pyotp()))
    
    print()
    print("=" * 50)
    print("Test Results:")
    print("=" * 50)
    for name, result in results:
        status = "[PASS]" if result else "[FAIL]"
        print(f"{name}: {status}")
    
    all_passed = all(result for _, result in results)
    if all_passed:
        print()
        print("[OK] All tests passed! Server is ready.")
        sys.exit(0)
    else:
        print()
        print("[FAIL] Some tests failed. Please check the errors above.")
        sys.exit(1)
