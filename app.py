from flask import Flask, request, jsonify, send_from_directory, send_file
from flask_cors import CORS
import os
import uuid
from datetime import datetime
import bcrypt
import json
from werkzeug.utils import secure_filename
import threading
import time
import shutil

# Import our modules
from backend.auth import AuthManager
from backend.database import DatabaseManager
from backend.log_processor import LogProcessor
from backend.embedding_service import EmbeddingService
from backend.similarity_service import SimilarityService
from backend.storage_service import StorageService
from backend.genapi_service import GenAPIService
from backend.conversation_service import ConversationService

app = Flask(__name__, static_folder=None)
CORS(app)

# Configuration
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['PROCESSED_FOLDER'] = 'processed'
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB max file size

# Create necessary directories
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['PROCESSED_FOLDER'], exist_ok=True)

import os as _os
# Limit parallelism to reduce contention on Windows/CPU
_os.environ.setdefault('OMP_NUM_THREADS', '1')
_os.environ.setdefault('MKL_NUM_THREADS', '1')
_os.environ.setdefault('TOKENIZERS_PARALLELISM', 'false')

# Initialize services
auth_manager = AuthManager()
db_manager = DatabaseManager()
log_processor = LogProcessor()
embedding_service = EmbeddingService()
similarity_service = SimilarityService()
storage_service = StorageService()
genapi_service = GenAPIService()
conversation_service = ConversationService()

# Non-blocking warm-up for embedding model to avoid first-request latency
def _warmup_embeddings_async():
    try:
        import threading
        def _run():
            try:
                if embedding_service and embedding_service.model:
                    embedding_service._get_embedding("warmup")
            except Exception:
                pass
        threading.Thread(target=_run, daemon=True).start()
    except Exception:
        pass
_warmup_embeddings_async()

# Job tracking for async operations
jobs = {}

# ----------------------
# Static file serving
# ----------------------
_BUILD_DIR = os.path.join(os.path.dirname(__file__), 'build')
_FRONTEND_DIR = os.path.join(os.path.dirname(__file__), 'frontend')

@app.route('/')
def index():
    try:
        if os.path.exists(os.path.join(_BUILD_DIR, 'index.html')):
            return send_from_directory('build', 'index.html')
        return send_from_directory('frontend', 'index.html')
    except Exception:
        return jsonify({'message': 'UI not built. Please run npm run build.'}), 200

@app.route('/<path:path>')
def serve_static(path):
    # Prefer built assets if present, else fallback to the simple frontend
    build_path = os.path.join(_BUILD_DIR, path)
    if os.path.exists(build_path):
        directory = 'build'
    else:
        directory = 'frontend'
    file_path = os.path.join(os.path.dirname(__file__), directory, path)
    if os.path.exists(file_path):
        return send_from_directory(directory, path)
    # SPA fallback: if it's not an actual file request (no dot), serve index.html
    if '.' not in path:
        try:
            if os.path.exists(os.path.join(_BUILD_DIR, 'index.html')):
                return send_from_directory('build', 'index.html')
            return send_from_directory('frontend', 'index.html')
        except Exception:
            return jsonify({'message': 'UI not built. Please run npm run build.'}), 200
    return jsonify({'error': 'Not Found'}), 404

# Explicit static route to serve built assets (avoids Flask's default static folder)
@app.route('/static/<path:filename>')
def serve_built_static(filename):
    build_static_path = os.path.join(_BUILD_DIR, 'static', filename)
    if os.path.exists(build_static_path):
        return send_from_directory(os.path.join('build', 'static'), filename)
    # Fallback to simple frontend static if present
    frontend_static_path = os.path.join(_FRONTEND_DIR, 'static', filename)
    if os.path.exists(frontend_static_path):
        return send_from_directory(os.path.join('frontend', 'static'), filename)
    return jsonify({'error': 'Not Found'}), 404

# Authentication endpoints
@app.route('/auth/signup', methods=['POST'])
def signup():
    try:
        data = request.get_json()
        userid = data.get('userid')
        password = data.get('password')
        teamid = data.get('teamid')
        
        if not all([userid, password, teamid]):
            return jsonify({'error': 'Missing required fields'}), 400
        
        result = auth_manager.signup(userid, password, teamid)
        if result['success']:
            return jsonify({'message': 'User created successfully', 'user_id': result['user_id']}), 201
        else:
            return jsonify({'error': result['error']}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/auth/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        userid = data.get('userid')
        password = data.get('password')
        
        if not all([userid, password]):
            return jsonify({'error': 'Missing userid or password'}), 400
        
        result = auth_manager.login(userid, password)
        if result['success']:
            return jsonify({
                'message': 'Login successful',
                'user_id': result['user_id'],
                'team_id': result['team_id'],
                'token': result['token']
            }), 200
        else:
            return jsonify({'error': result['error']}), 401
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/profile/me', methods=['GET'])
def get_profile():
    try:
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        user_data = auth_manager.verify_token(token)
        
        if not user_data:
            return jsonify({'error': 'Invalid token'}), 401
        
        profile = db_manager.get_user_profile(user_data['user_id'])
        conversations = db_manager.get_user_conversations(user_data['user_id'])
        
        return jsonify({
            'profile': profile,
            'conversations': conversations
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/profile/me', methods=['PATCH'])
def update_profile():
    try:
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        user_data = auth_manager.verify_token(token)
        
        if not user_data:
            return jsonify({'error': 'Invalid token'}), 401
        
        data = request.get_json()
        result = db_manager.update_user_profile(user_data['user_id'], data)
        
        if result['success']:
            return jsonify({'message': 'Profile updated successfully'}), 200
        else:
            return jsonify({'error': result['error']}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Log processing endpoints
@app.route('/records', methods=['POST'])
def upload_log():
    try:
        print(f"Upload request received. Headers: {dict(request.headers)}")
        print(f"Form data: {dict(request.form)}")
        print(f"Files: {list(request.files.keys())}")
        
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        user_data = auth_manager.verify_token(token)
        
        if not user_data:
            print("Invalid token")
            return jsonify({'error': 'Invalid token'}), 401
        
        if 'file' not in request.files:
            print("No file in request")
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        context = request.form.get('context', '')
        visibility = request.form.get('visibility', 'self')
        
        print(f"File: {file.filename}, Size: {file.content_length}, Context: {context}, Visibility: {visibility}")
        
        if file.filename == '':
            print("Empty filename")
            return jsonify({'error': 'No file selected'}), 400
        
        # Save uploaded file
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{uuid.uuid4()}_{filename}")
        print(f"Saving file to: {file_path}")
        file.save(file_path)
        
        # Create job for processing
        job_id = str(uuid.uuid4())
        jobs[job_id] = {
            'status': 'queued',
            'progress': 0,
            'user_id': user_data['user_id'],
            'team_id': user_data['team_id'],
            'file_path': file_path,
            'context': context,
            'visibility': visibility,
            'created_at': datetime.now().isoformat()
        }
        
        print(f"Created job {job_id} for user {user_data['user_id']}")
        
        # Start processing in background
        thread = threading.Thread(target=process_log_async, args=(job_id,))
        thread.start()
        
        return jsonify({'job_id': job_id, 'message': 'File uploaded, processing started'}), 202
    except Exception as e:
        print(f"Upload error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

def process_log_async(job_id):
    """Process log file asynchronously"""
    try:
        job = jobs[job_id]
        job['status'] = 'running'
        job['progress'] = 10
        
        # Stage 4: Log Reduction
        processed_file = log_processor.process_log_file(
            job['file_path'], 
            user_id=job['user_id'],
            team_id=job['team_id'],
            context=job['context']
        )
        job['progress'] = 30
        
        # Stage 5: Generate Embeddings (optional in SPARSE_MODE)
        sparse_mode = os.getenv('SPARSE_MODE', 'false').lower() in ('1', 'true', 'yes')
        if sparse_mode:
            embeddings = {}
        else:
            embeddings = embedding_service.generate_embeddings(processed_file)
        job['progress'] = 60
        
        # Stage 6: Store in database
        record_id = storage_service.store_record(
            user_id=job['user_id'],
            team_id=job['team_id'],
            raw_file_path=job['file_path'],
            processed_file_path=processed_file,
            context=job['context'],
            embeddings=embeddings,
            visibility=job['visibility']
        )
        job['progress'] = 90
        
        # Stage 7: Find similar records (skip in SPARSE_MODE)
        if sparse_mode:
            similar_records = []
        else:
            similar_records = similarity_service.find_similar_records(
                embeddings, 
                user_id=job['user_id'],
                team_id=job['team_id']
            )
        
        job['status'] = 'completed'
        job['progress'] = 100
        job['record_id'] = record_id
        job['similar_records'] = similar_records
        job['finished_at'] = datetime.now().isoformat()
        
    except Exception as e:
        jobs[job_id]['status'] = 'failed'
        jobs[job_id]['error'] = str(e)
        jobs[job_id]['finished_at'] = datetime.now().isoformat()

@app.route('/jobs/<job_id>', methods=['GET'])
def get_job_status(job_id):
    try:
        if job_id not in jobs:
            return jsonify({'error': 'Job not found'}), 404
        
        return jsonify(jobs[job_id]), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/debug/records', methods=['GET'])
def debug_records():
    """Debug endpoint to see all records in database"""
    try:
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        user_data = auth_manager.verify_token(token)
        
        if not user_data:
            return jsonify({'error': 'Invalid token'}), 401
        
        # Get all records without filtering
        query = {"query": {"match_all": {}}, "size": 1000}
        result = db_manager.es.search(index=db_manager.indices['records'], body=query)
        all_records = [hit['_source'] for hit in result['hits']['hits']]
        
        return jsonify({
            'total_records': len(all_records),
            'records': all_records,
            'user_data': user_data
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/records', methods=['GET'])
def get_records():
    try:
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        user_data = auth_manager.verify_token(token)
        
        if not user_data:
            return jsonify({'error': 'Invalid token'}), 401
        
        visibility = request.args.get('visibility', 'all')
        # Optional tag filter (temporary pass-through)
        tag = request.args.get('tag')
        if tag:
            os.environ['REQ_TAG'] = tag
        else:
            # Clear any previous request-scoped tag
            if 'REQ_TAG' in os.environ:
                del os.environ['REQ_TAG']

        print(f"DEBUG: Getting records for user_id={user_data['user_id']}, team_id={user_data['team_id']}, visibility={visibility}")
        
        records = db_manager.get_records(
            user_id=user_data['user_id'],
            team_id=user_data['team_id'],
            visibility=visibility
        )
        
        print(f"DEBUG: Found {len(records)} records")
        
        return jsonify({'records': records}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/records/signals', methods=['GET'])
def get_signals():
    try:
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        user_data = auth_manager.verify_token(token)
        if not user_data:
            return jsonify({'error': 'Invalid token'}), 401

        visibility = request.args.get('visibility', 'all')
        prefix = request.args.get('q')
        try:
            size = int(request.args.get('size', '50'))
        except Exception:
            size = 50

        counts = db_manager.aggregate_signals(
            user_id=user_data['user_id'],
            team_id=user_data['team_id'],
            visibility=visibility,
            prefix=prefix,
            size=size
        )
        return jsonify({ 'signals': counts }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/download', methods=['GET'])
def download():
    try:
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        user_data = auth_manager.verify_token(token)
        if not user_data:
            return jsonify({'error': 'Invalid token'}), 401

        path = request.args.get('path', '')
        if not path or not os.path.exists(path):
            return jsonify({'error': 'File not found'}), 404

        # Very simple guard: only allow serving from uploads or processed directories
        abs_path = os.path.abspath(path)
        uploads_root = os.path.abspath(app.config['UPLOAD_FOLDER'])
        processed_root = os.path.abspath(app.config['PROCESSED_FOLDER'])
        if not (abs_path.startswith(uploads_root) or abs_path.startswith(processed_root)):
            return jsonify({'error': 'Access denied'}), 403

        return send_file(abs_path, as_attachment=True)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/records/<record_id>', methods=['GET'])
def get_record(record_id):
    try:
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        user_data = auth_manager.verify_token(token)
        
        if not user_data:
            return jsonify({'error': 'Invalid token'}), 401
        
        record = db_manager.get_record(record_id, user_data['user_id'], user_data['team_id'])
        if not record:
            return jsonify({'error': 'Record not found'}), 404
        
        # Add processed content to the record
        if record.get('processed_file_path') and os.path.exists(record['processed_file_path']):
            try:
                with open(record['processed_file_path'], 'r', encoding='utf-8') as f:
                    record['processed_content'] = f.read()
            except Exception as e:
                record['processed_content'] = f"Error reading processed file: {str(e)}"
        else:
            record['processed_content'] = "Processed file not found"
        
        return jsonify(record), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/records/<record_id>/similar', methods=['GET'])
def get_similar_records(record_id):
    try:
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        user_data = auth_manager.verify_token(token)
        
        if not user_data:
            return jsonify({'error': 'Invalid token'}), 401
        
        # Threshold and limit from query params with sensible defaults
        try:
            min_similarity = float(request.args.get('min') or request.args.get('threshold') or os.getenv('SIMILARITY_THRESHOLD', '0.8'))
        except Exception:
            min_similarity = 0.8
        try:
            max_results = int(request.args.get('limit') or os.getenv('SIMILARITY_MAX_RESULTS', '200'))
        except Exception:
            max_results = 200

        # Return more (scrollable) results
        similar_records = similarity_service.get_similar_records(
            record_id,
            user_id=user_data['user_id'],
            team_id=user_data['team_id'],
            min_similarity=min_similarity,
            max_results=max_results
        )
        
        return jsonify({'similar_records': similar_records}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/genapi/analyze', methods=['POST'])
def analyze_with_genapi():
    try:
        print(f"GenAPI analyze request received")
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        user_data = auth_manager.verify_token(token)
        
        if not user_data:
            print("Invalid token for GenAPI analysis")
            return jsonify({'error': 'Invalid token'}), 401
        
        data = request.get_json()
        record_id = data.get('record_id')
        context = data.get('context', '')
        
        print(f"Analyzing record {record_id} with context: {context}")
        
        if not record_id:
            return jsonify({'error': 'Record ID required'}), 400
        
        # Get record data
        record = db_manager.get_record(record_id, user_data['user_id'], user_data['team_id'])
        if not record:
            print(f"Record {record_id} not found")
            return jsonify({'error': 'Record not found'}), 404
        
        print(f"Found record, processed file: {record.get('processed_file_path')}")
        
        # Build enhanced context with dev feedback hints from similar records (top 10)
        try:
            similar_records = similarity_service.get_similar_records(
                record_id,
                user_id=user_data['user_id'],
                team_id=user_data['team_id'],
                min_similarity=0.0,
                max_results=200
            ) or []
        except Exception:
            similar_records = []

        dev_hints = []
        dev_hint_sources = []
        # Include from similar records owned by the same user only and above their per-record dev_feedback_threshold
        mine_similar = [r for r in (similar_records or []) if r.get('owner_user_id') == user_data['user_id']]
        for item in mine_similar:
            df = (item.get('dev_feedback') or '').strip()
            if not df:
                continue
            try:
                src_threshold = float(item.get('dev_feedback_threshold') or 0)
            except Exception:
                src_threshold = 0.0
            sim_pct = float(item.get('similarity_score') or 0)
            if sim_pct <= 1:
                sim_pct = sim_pct * 100.0
            if sim_pct >= src_threshold:
                dev_hints.append(df)
                rid = (item.get('record_id') or '').strip()
                if rid:
                    dev_hint_sources.append(rid)
            if len(dev_hints) >= 10:
                break

        enhanced_context = context or ''
        if dev_hints:
            bullets = "\n".join([f"- {h}" for h in dev_hints[:10]])
            enhanced_context = (enhanced_context + "\n\nDeveloper Feedback Hints (from similar cases):\n" + bullets).strip()

        # Analyze with GenAPI (pass dev hints explicitly)
        analysis = genapi_service.analyze_log(
            record['processed_file_path'],
            context=enhanced_context,
            dev_hints=dev_hints
        )
        
        print(f"GenAPI analysis completed: {analysis}")
        
        # Attach dev feedback sources for UI
        try:
            if isinstance(analysis, dict):
                analysis['dev_feedback_sources'] = dev_hint_sources
        except Exception:
            pass

        # Store analysis results
        db_manager.update_record_analysis(record_id, analysis)
        
        return jsonify(analysis), 200
    except Exception as e:
        print(f"GenAPI analysis error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/ask', methods=['POST'])
def ask_question():
    try:
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        user_data = auth_manager.verify_token(token)
        
        if not user_data:
            return jsonify({'error': 'Invalid token'}), 401
        
        data = request.get_json()
        record_id = data.get('record_id')
        question = data.get('question')
        conversation_id = data.get('conversation_id')
        
        if not all([record_id, question]):
            return jsonify({'error': 'Record ID and question required'}), 400
        
        # Determine if question needs DB query or GenAPI call
        response = genapi_service.handle_question(
            question=question,
            record_id=record_id,
            user_id=user_data['user_id'],
            team_id=user_data['team_id'],
            conversation_id=conversation_id
        )
        
        return jsonify(response), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/records/<record_id>/visibility', methods=['PATCH'])
def update_record_visibility(record_id):
    try:
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        user_data = auth_manager.verify_token(token)
        
        if not user_data:
            return jsonify({'error': 'Invalid token'}), 401
        
        data = request.get_json()
        visibility = data.get('visibility')
        
        if visibility not in ['public', 'team', 'self']:
            return jsonify({'error': 'Invalid visibility level'}), 400
        
        result = db_manager.update_record_visibility(
            record_id, 
            user_data['user_id'], 
            visibility
        )
        
        if result['success']:
            return jsonify({'message': 'Visibility updated successfully'}), 200
        else:
            return jsonify({'error': result['error']}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/records/<record_id>/tags', methods=['PATCH'])
def add_record_tags(record_id):
    try:
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        user_data = auth_manager.verify_token(token)
        if not user_data:
            return jsonify({'error': 'Invalid token'}), 401

        data = request.get_json() or {}
        tags = data.get('tags') or []
        if not isinstance(tags, list):
            return jsonify({'error': 'tags must be a list of strings'}), 400

        result = db_manager.update_record_tags(record_id, user_data['user_id'], tags)
        if result.get('success'):
            return jsonify({'tags': result.get('tags', [])}), 200
        return jsonify({'error': result.get('error', 'Failed to update')}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/records/<record_id>/tags', methods=['DELETE'])
def delete_record_tags(record_id):
    try:
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        user_data = auth_manager.verify_token(token)
        if not user_data:
            return jsonify({'error': 'Invalid token'}), 401

        data = request.get_json() or {}
        tags = data.get('tags') or []
        if not isinstance(tags, list):
            return jsonify({'error': 'tags must be a list of strings'}), 400

        result = db_manager.remove_record_tags(record_id, user_data['user_id'], tags)
        if result.get('success'):
            return jsonify({'tags': result.get('tags', [])}), 200
        return jsonify({'error': result.get('error', 'Failed to update')}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/records/<record_id>/context', methods=['PATCH'])
def update_record_context(record_id):
    try:
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        user_data = auth_manager.verify_token(token)

        if not user_data:
            return jsonify({'error': 'Invalid token'}), 401

        data = request.get_json() or {}
        context = data.get('context', '')

        result = db_manager.update_record_context(record_id, user_data['user_id'], context)
        if result.get('success'):
            return jsonify({'message': 'Context updated successfully', 'context': context}), 200
        return jsonify({'error': result.get('error', 'Failed to update')}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/records/<record_id>/dev_feedback', methods=['PATCH'])
def update_record_dev_feedback(record_id):
    try:
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        user_data = auth_manager.verify_token(token)

        if not user_data:
            return jsonify({'error': 'Invalid token'}), 401

        data = request.get_json() or {}
        dev_feedback = data.get('dev_feedback', '')

        result = db_manager.update_record_dev_feedback(record_id, user_data['user_id'], dev_feedback)
        if result.get('success'):
            return jsonify({'message': 'Dev feedback updated successfully', 'dev_feedback': dev_feedback}), 200
        return jsonify({'error': result.get('error', 'Failed to update')}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/records/<record_id>/dev_feedback_threshold', methods=['PATCH'])
def update_record_dev_feedback_threshold(record_id):
    try:
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        user_data = auth_manager.verify_token(token)

        if not user_data:
            return jsonify({'error': 'Invalid token'}), 401

        data = request.get_json() or {}
        threshold = data.get('dev_feedback_threshold')

        result = db_manager.update_record_dev_feedback_threshold(record_id, user_data['user_id'], threshold)
        if result.get('success'):
            return jsonify({'message': 'Dev feedback threshold updated successfully', 'dev_feedback_threshold': result.get('dev_feedback_threshold')}), 200
        return jsonify({'error': result.get('error', 'Failed to update')}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Chat/Conversation endpoints
@app.route('/chat/conversation/<record_id>', methods=['GET'])
def get_conversation(record_id):
    """Get or create conversation for a record"""
    try:
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        user_data = auth_manager.verify_token(token)
        
        if not user_data:
            return jsonify({'error': 'Invalid token'}), 401
        
        conversation = conversation_service.get_conversation_by_record(
            record_id, 
            user_data['user_id']
        )
        
        if not conversation:
            return jsonify({'error': 'Failed to create conversation'}), 500
        
        return jsonify({
            'conversation_id': conversation['conversation_id'],
            'messages': conversation['messages'],
            'created_at': conversation['created_at']
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/chat/conversation/<conversation_id>/message', methods=['POST'])
def send_message(conversation_id):
    """Send a message in the conversation"""
    try:
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        user_data = auth_manager.verify_token(token)
        
        if not user_data:
            return jsonify({'error': 'Invalid token'}), 401
        
        data = request.get_json()
        message = data.get('message')
        
        if not message:
            return jsonify({'error': 'Message required'}), 400
        
        # Ask question and get AI response
        result = conversation_service.ask_question(
            conversation_id,
            message,
            user_data['user_id']
        )
        
        return jsonify(result), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/chat/conversation/<conversation_id>/history', methods=['GET'])
def get_conversation_history(conversation_id):
    """Get conversation history"""
    try:
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        user_data = auth_manager.verify_token(token)
        
        if not user_data:
            return jsonify({'error': 'Invalid token'}), 401
        
        messages = conversation_service.get_conversation_history(
            conversation_id,
            user_data['user_id']
        )
        
        return jsonify({'messages': messages}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# -------------------------------------
# Public API endpoints (credential-based)
# -------------------------------------

@app.route('/api/signup', methods=['POST'])
def api_signup():
    """API 1: Sign up via API (no JWT required)
    Input JSON: { userid, password, teamid }
    Output: { success: true/false }
    """
    try:
        data = request.get_json() or {}
        userid = data.get('userid')
        password = data.get('password')
        teamid = data.get('teamid')
        if not all([userid, password, teamid]):
            return jsonify({ 'success': False, 'error': 'Missing required fields' }), 400

        result = auth_manager.signup(userid, password, teamid)
        return jsonify({ 'success': bool(result.get('success')) }), (201 if result.get('success') else 400)
    except Exception as e:
        return jsonify({ 'success': False, 'error': str(e) }), 500

@app.route('/api/upload_log', methods=['POST'])
def api_upload_log():
    """API 2: Upload log by path and return record_id
    Input JSON: { userid, password, log_path, visibility?, tag?, context? }
    Output: { record_id } or { error }
    """
    try:
        data = request.get_json() or {}
        userid = data.get('userid')
        password = data.get('password')
        log_path = data.get('log_path')
        visibility = data.get('visibility', 'self')
        add_tag = data.get('tag')
        context = data.get('context', '')

        if not all([userid, password, log_path]):
            return jsonify({ 'error': 'userid, password and log_path are required' }), 400

        # Authenticate user
        login_result = auth_manager.login(userid, password)
        if not login_result.get('success'):
            return jsonify({ 'error': 'Invalid credentials' }), 401
        user_id = login_result['user_id']
        team_id = login_result['team_id']

        # Ensure source path exists
        if not os.path.exists(log_path) or not os.path.isfile(log_path):
            return jsonify({ 'error': 'log_path not found' }), 404

        # Copy into uploads folder with a safe filename
        src_filename = os.path.basename(log_path)
        safe_name = f"{uuid.uuid4()}_{secure_filename(src_filename)}"
        dest_path = os.path.join(app.config['UPLOAD_FOLDER'], safe_name)
        shutil.copyfile(log_path, dest_path)

        # Process synchronously (same as async flow but inline)
        processed_file = log_processor.process_log_file(
            dest_path,
            user_id=user_id,
            team_id=team_id,
            context=context
        )

        sparse_mode = os.getenv('SPARSE_MODE', 'false').lower() in ('1', 'true', 'yes')
        if sparse_mode:
            embeddings = {}
        else:
            embeddings = embedding_service.generate_embeddings(processed_file)

        record_id = storage_service.store_record(
            user_id=user_id,
            team_id=team_id,
            raw_file_path=dest_path,
            processed_file_path=processed_file,
            context=context,
            embeddings=embeddings,
            visibility=visibility if visibility in ['public','team','self'] else 'self'
        )

        # Optional: attach custom tag
        if add_tag and isinstance(add_tag, str) and add_tag.strip():
            try:
                db_manager.update_record_tags(record_id, user_id, [add_tag.strip()])
            except Exception:
                pass

        return jsonify({ 'record_id': record_id }), 200
    except Exception as e:
        return jsonify({ 'error': str(e) }), 500

@app.route('/api/records/<record_id>/genapi', methods=['POST'])
def api_get_genapi(record_id):
    """API 3: Get full GenAI response for a record with credential-based access.
    Input JSON: { userid, password }
    Output: { genapi } or { error }
    """
    try:
        data = request.get_json() or {}
        userid = data.get('userid')
        password = data.get('password')
        if not all([userid, password, record_id]):
            return jsonify({ 'error': 'Missing required fields' }), 400

        login_result = auth_manager.login(userid, password)
        if not login_result.get('success'):
            return jsonify({ 'error': 'Invalid credentials' }), 401

        user_id = login_result['user_id']
        team_id = login_result['team_id']

        # Permission-checked fetch
        record = db_manager.get_record(record_id, user_id, team_id)
        if not record:
            return jsonify({ 'error': 'Access denied or record not found' }), 403

        return jsonify({ 'genapi': record.get('genapi', {}) }), 200
    except Exception as e:
        return jsonify({ 'error': str(e) }), 500
if __name__ == '__main__':
    # Wait for Elasticsearch to be ready, then initialize database with robust retries
    import time as _time
    from elastic_transport import ConnectionError as _ESConnectionError

    def _wait_for_elasticsearch(es_client, max_wait_seconds: int = 60) -> bool:
        start = _time.time()
        print("Starting Elasticsearch wait...")
        print(f"ES client: {es_client}")
        print(f"ES URL: {es_client._transport.node_pool.get().base_url}")
        while True:
            try:
                result = es_client.ping()
                print(f"ES ping result: {result}")
                if result:
                    print("Elasticsearch ping successful.")
                    return True
            except Exception as e:
                print(f"ES ping failed: {e}")
            elapsed = int(_time.time() - start)
            if elapsed % 5 == 0:
                print(f"Waiting for Elasticsearch... {elapsed}s elapsed")
            if _time.time() - start > max_wait_seconds:
                print("Elasticsearch not ready within timeout window.")
                return False
            _time.sleep(2)

    if not _wait_for_elasticsearch(db_manager.es, max_wait_seconds=int(os.getenv('ES_STARTUP_WAIT_SECS', '300'))):
        print("ERROR: Elasticsearch not ready after timeout. Exiting.")
        exit(1)

    attempt = 0
    while True:
        attempt += 1
        try:
            print(f"Initializing database (attempt {attempt})...")
            db_manager.initialize_database()
            print("Database initialized.")
            break
        except (_ESConnectionError, Exception) as e:
            print(f"Database initialization failed (attempt {attempt}): {e}")
            _time.sleep(min(5 * attempt, 15))

    app.run(debug=True, host='0.0.0.0', port=5000)
