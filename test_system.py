#!/usr/bin/env python3
"""
Test script for Log Analysis System
This script tests the basic functionality of the system
"""

import os
import sys
import time
import requests
import json
from pathlib import Path

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_elasticsearch_connection():
    """Test Elasticsearch connection"""
    print("Testing Elasticsearch connection...")
    try:
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
    """Test database initialization"""
    print("Testing database initialization...")
    try:
        from backend.database import DatabaseManager
        db = DatabaseManager()
        db.initialize_database()
        print("✓ Database initialized successfully")
        return True
    except Exception as e:
        print(f"✗ Database initialization failed: {e}")
        return False

def test_authentication():
    """Test authentication system"""
    print("Testing authentication system...")
    try:
        from backend.auth import AuthManager
        auth = AuthManager()
        
        # Test password hashing
        password = "test_password"
        hashed = auth.hash_password(password)
        if auth.verify_password(password, hashed):
            print("✓ Password hashing works")
        else:
            print("✗ Password hashing failed")
            return False
        
        # Test token generation
        token = auth.generate_token("test_user", "test_team")
        user_data = auth.verify_token(token)
        if user_data and user_data['user_id'] == "test_user":
            print("✓ Token generation and verification works")
        else:
            print("✗ Token generation/verification failed")
            return False
        
        return True
    except Exception as e:
        print(f"✗ Authentication test failed: {e}")
        return False

def test_log_processing():
    """Test log processing functionality"""
    print("Testing log processing...")
    try:
        from backend.log_processor import LogProcessor
        from backend.embedding_service import EmbeddingService
        
        # Create a test log file
        test_log_content = """2024-01-01 10:00:00 INFO System started
2024-01-01 10:00:01 ERROR Database connection failed
2024-01-01 10:00:02 WARN Memory usage high
2024-01-01 10:00:03 INFO Service initialized
2024-01-01 10:00:04 CRITICAL System crash detected
"""
        
        test_file = Path("test_log.txt")
        with open(test_file, 'w') as f:
            f.write(test_log_content)
        
        # Test log processor
        processor = LogProcessor()
        processed_file = processor.process_log_file(
            str(test_file), 
            "test_user", 
            "test_team", 
            "Test log"
        )
        
        if Path(processed_file).exists():
            print("✓ Log processing works")
        else:
            print("✗ Log processing failed")
            return False
        
        # Test embedding service
        embedding_service = EmbeddingService()
        embeddings = embedding_service.generate_embeddings(processed_file)
        
        if embeddings and 'record_embedding' in embeddings:
            print("✓ Embedding generation works")
        else:
            print("✗ Embedding generation failed")
            return False
        
        # Cleanup
        test_file.unlink()
        Path(processed_file).unlink()
        
        return True
    except Exception as e:
        print(f"✗ Log processing test failed: {e}")
        return False

def test_api_endpoints():
    """Test API endpoints"""
    print("Testing API endpoints...")
    try:
        base_url = "http://localhost:5000"
        
        # Test if the server is running
        try:
            response = requests.get(f"{base_url}/", timeout=5)
            if response.status_code == 200:
                print("✓ Web server is running")
            else:
                print(f"✗ Web server returned status code: {response.status_code}")
                return False
        except Exception as e:
            print(f"✗ Cannot connect to web server: {e}")
            print("Make sure to start the application first with: python app.py")
            return False
        
        return True
    except Exception as e:
        print(f"✗ API test failed: {e}")
        return False

def create_sample_log():
    """Create a sample log file for testing"""
    print("Creating sample log file...")
    
    sample_log = """2024-01-15 09:30:15 INFO [systemd] Starting systemd service manager
2024-01-15 09:30:16 INFO [systemd] Started systemd service manager
2024-01-15 09:30:17 INFO [kernel] Linux version 5.4.0-74-generic
2024-01-15 09:30:18 INFO [kernel] Command line: BOOT_IMAGE=/boot/vmlinuz-5.4.0-74-generic
2024-01-15 09:30:19 INFO [kernel] KERNEL supported cpus:
2024-01-15 09:30:20 INFO [kernel] CPU: Intel(R) Core(TM) i7-8700K CPU @ 3.70GHz
2024-01-15 09:30:21 INFO [kernel] Memory: 16GB available
2024-01-15 09:30:22 INFO [kernel] Freeing unused kernel memory
2024-01-15 09:30:23 INFO [systemd] Started systemd-resolved.service
2024-01-15 09:30:24 INFO [systemd] Started systemd-networkd.service
2024-01-15 09:30:25 ERROR [network] Failed to connect to DHCP server
2024-01-15 09:30:26 WARN [network] Using fallback IP configuration
2024-01-15 09:30:27 INFO [network] Network interface eth0 configured
2024-01-15 09:30:28 INFO [systemd] Started NetworkManager.service
2024-01-15 09:30:29 INFO [systemd] Started dbus.service
2024-01-15 09:30:30 CRITICAL [database] Database connection failed: Connection refused
2024-01-15 09:30:31 ERROR [database] Retrying database connection...
2024-01-15 09:30:32 ERROR [database] Database connection failed: Connection refused
2024-01-15 09:30:33 WARN [database] Using cached data
2024-01-15 09:30:34 INFO [application] Application started successfully
2024-01-15 09:30:35 INFO [application] Loading configuration from /etc/app/config.json
2024-01-15 09:30:36 INFO [application] Configuration loaded successfully
2024-01-15 09:30:37 INFO [application] Starting web server on port 8080
2024-01-15 09:30:38 INFO [application] Web server started successfully
2024-01-15 09:30:39 INFO [application] Application ready to accept connections
"""
    
    with open("sample_log.txt", "w") as f:
        f.write(sample_log)
    
    print("✓ Sample log file created: sample_log.txt")

def main():
    """Main test function"""
    print("=" * 60)
    print("Log Analysis System - Test Script")
    print("=" * 60)
    
    tests = [
        ("Elasticsearch Connection", test_elasticsearch_connection),
        ("Database Initialization", test_database_initialization),
        ("Authentication System", test_authentication),
        ("Log Processing", test_log_processing),
        ("API Endpoints", test_api_endpoints),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n{test_name}:")
        print("-" * 40)
        if test_func():
            passed += 1
        else:
            print(f"✗ {test_name} failed")
    
    print("\n" + "=" * 60)
    print(f"Test Results: {passed}/{total} tests passed")
    print("=" * 60)
    
    if passed == total:
        print("✓ All tests passed! The system is ready to use.")
        create_sample_log()
        print("\nNext steps:")
        print("1. Start the application: python app.py")
        print("2. Open http://localhost:5000 in your browser")
        print("3. Create an account and upload the sample_log.txt file")
    else:
        print("✗ Some tests failed. Please check the errors above.")
        print("\nTroubleshooting:")
        print("1. Make sure Elasticsearch is running: http://localhost:9200")
        print("2. Install dependencies: pip install -r requirements.txt")
        print("3. Check the error messages above for specific issues")

if __name__ == "__main__":
    main()
