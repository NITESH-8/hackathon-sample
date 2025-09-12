@echo off
echo Starting Elasticsearch...
docker-compose up -d elasticsearch

echo Waiting for Elasticsearch to be ready...
timeout /t 10 /nobreak > nul

echo Starting Flask application...
set ELASTICSEARCH_URL=http://localhost:9201
python app.py
