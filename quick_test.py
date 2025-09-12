#!/usr/bin/env python3
"""
Quick test script to verify the database fix
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

def test_database_initialization():
    """Test database initialization with the fix"""
    print("Testing database initialization...")
    try:
        from backend.database import DatabaseManager
        db = DatabaseManager()
        print("✓ Database client created successfully")
        
        # Test connection
        info = db.es.info()
        print("✓ Elasticsearch connection successful")
        
        # Initialize database
        db.initialize_database()
        print("✓ Database initialized successfully")
        return True
    except Exception as e:
        print(f"✗ Database initialization failed: {e}")
        return False

def test_imports():
    """Test all imports"""
    print("Testing imports...")
    try:
        from backend.auth import AuthManager
        print("✓ Auth module imported")
        
        from backend.database import DatabaseManager
        print("✓ Database module imported")
        
        # Test log processor import (this might fail due to missing dependencies)
        try:
            from backend.log_processor import LogProcessor
            print("✓ Log processor imported")
        except Exception as e:
            print(f"⚠ Log processor import failed: {e}")
        
        # Test embedding service import (this might fail due to missing dependencies)
        try:
            from backend.embedding_service import EmbeddingService
            print("✓ Embedding service imported")
        except Exception as e:
            print(f"⚠ Embedding service import failed: {e}")
        
        return True
    except Exception as e:
        print(f"✗ Import failed: {e}")
        return False

def main():
    print("=" * 50)
    print("Quick Test - Database Fix Verification")
    print("=" * 50)
    
    tests = [
        ("Elasticsearch Connection", test_elasticsearch_connection),
        ("Database Initialization", test_database_initialization),
        ("Module Imports", test_imports),
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
        print("✓ All tests passed! The database fix worked.")
        print("\nNext steps:")
        print("1. Start Elasticsearch: docker run -d --name elasticsearch -p 9200:9200 -p 9300:9300 -e 'discovery.type=single-node' -e 'xpack.security.enabled=false' docker.elastic.co/elasticsearch/elasticsearch:8.11.0")
        print("2. Run the full test: python test_system.py")
        print("3. Start the app: python app.py")
    else:
        print("✗ Some tests failed. Check the errors above.")

if __name__ == "__main__":
    main()
