#!/usr/bin/env python3
"""
Simple test script to verify core functionality
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_elasticsearch_connection():
    """Test Elasticsearch connection"""
    print("Testing Elasticsearch connection...")
    try:
        import requests
        response = requests.get('http://localhost:9200', timeout=5)
        if response.status_code == 200:
            print("✓ Elasticsearch is running")
            return True
        else:
            print(f"✗ Elasticsearch returned status code: {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ Cannot connect to Elasticsearch: {e}")
        return False

def test_database_connection():
    """Test database connection with minimal configuration"""
    print("Testing database connection...")
    try:
        from elasticsearch import Elasticsearch
        
        # Simple connection test for version 8.x
        es = Elasticsearch("http://localhost:9200")
        info = es.info()
        print("✓ Elasticsearch connection successful")
        print(f"  Cluster: {info['cluster_name']}")
        print(f"  Version: {info['version']['number']}")
        return True
    except Exception as e:
        print(f"✗ Database connection failed: {e}")
        return False

def test_basic_imports():
    """Test basic imports"""
    print("Testing basic imports...")
    try:
        import requests
        print("✓ requests imported")
        
        import json
        print("✓ json imported")
        
        from elasticsearch import Elasticsearch
        print("✓ elasticsearch imported")
        
        return True
    except Exception as e:
        print(f"✗ Basic imports failed: {e}")
        return False

def main():
    print("=" * 50)
    print("Simple Test - Core Functionality")
    print("=" * 50)
    
    tests = [
        ("Elasticsearch Connection", test_elasticsearch_connection),
        ("Database Connection", test_database_connection),
        ("Basic Imports", test_basic_imports),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n{test_name}:")
        print("-" * 30)
        if test_func():
            passed += 1
        else:
            print(f"✗ {test_name} failed")
    
    print("\n" + "=" * 50)
    print(f"Results: {passed}/{total} tests passed")
    print("=" * 50)
    
    if passed == total:
        print("✓ All core tests passed!")
        print("\nNext steps:")
        print("1. Install missing dependencies: pip install -r requirements.txt")
        print("2. Run the full test: python test_system.py")
        print("3. Start the app: python app.py")
    else:
        print("✗ Some tests failed. Check the errors above.")
        print("\nTroubleshooting:")
        print("1. Make sure Elasticsearch is running: http://localhost:9200")
        print("2. Install dependencies: pip install -r requirements.txt")

if __name__ == "__main__":
    main()
