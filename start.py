#!/usr/bin/env python3
"""
Startup script for Log Analysis System
This script helps initialize the system and start the application
"""

import os
import sys
import subprocess
import time
from pathlib import Path

def check_elasticsearch():
    """Check if Elasticsearch is running"""
    try:
        import requests
        es_url = os.getenv('ELASTICSEARCH_URL', 'http://localhost:9201')
        response = requests.get(es_url, timeout=5)
        return response.status_code == 200
    except:
        return False

def install_dependencies():
    """Install Python dependencies"""
    print("Installing Python dependencies...")
    try:
        subprocess.run([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'], check=True)
        print("✓ Dependencies installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ Failed to install dependencies: {e}")
        return False

def check_elasticsearch_installation():
    """Check if Elasticsearch is installed and running"""
    print("Checking Elasticsearch...")
    
    if check_elasticsearch():
        print("✓ Elasticsearch is running")
        return True
    
    print("✗ Elasticsearch is not running")
    print("\nTo start Elasticsearch:")
    print("1. Download from https://www.elastic.co/downloads/elasticsearch")
    print("2. Extract and run: ./bin/elasticsearch")
    print("3. Or use Docker: docker run -p 9201:9200 -e 'discovery.type=single-node' docker.elastic.co/elasticsearch/elasticsearch:8.11.0")
    return False

def create_directories():
    """Create necessary directories"""
    print("Creating directories...")
    directories = ['uploads', 'processed', 'backend']
    
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
        print(f"✓ Created directory: {directory}")

def setup_environment():
    """Setup environment variables"""
    print("Setting up environment...")
    
    env_file = Path('.env')
    if not env_file.exists():
        with open('.env', 'w') as f:
            f.write("""# Log Analysis System Environment Variables
JWT_SECRET=your-secret-key-change-in-production
ELASTICSEARCH_URL=http://localhost:9201
GENAPI_KEY=your-genapi-key-here
GENAPI_URL=https://api.genapi.com/v1
FLASK_ENV=development
FLASK_DEBUG=True
""")
        print("✓ Created .env file")
    else:
        print("✓ .env file already exists")

def start_application():
    """Start the Flask application"""
    print("\nStarting Log Analysis System...")
    print("The application will be available at: http://localhost:5000")
    print("Press Ctrl+C to stop the application")
    print("-" * 50)
    
    try:
        from app import app
        app.run(debug=True, host='0.0.0.0', port=5000)
    except KeyboardInterrupt:
        print("\nApplication stopped by user")
    except Exception as e:
        print(f"Error starting application: {e}")

def main():
    """Main startup function"""
    print("=" * 60)
    print("Log Analysis System - Startup Script")
    print("=" * 60)
    
    # Check Python version
    if sys.version_info < (3, 8):
        print("✗ Python 3.8 or higher is required")
        sys.exit(1)
    
    print(f"✓ Python {sys.version.split()[0]} detected")
    
    # Install dependencies
    if not install_dependencies():
        sys.exit(1)
    
    # Create directories
    create_directories()
    
    # Setup environment
    setup_environment()
    
    # Check Elasticsearch
    if not check_elasticsearch_installation():
        print("\nPlease start Elasticsearch and run this script again")
        sys.exit(1)
    
    # Start application
    start_application()

if __name__ == "__main__":
    main()
