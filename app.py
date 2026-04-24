import os
import shutil
import uuid
import sqlite3
import json
import logging
from datetime import datetime
from flask import Flask, render_template, request, jsonify
from werkzeug.utils import secure_filename
from resume_matcher import load_resumes_from_file_paths, rank_resumes

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'temp_uploads'
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500 MB
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

DB_NAME = 'resume_matches.db'

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS queries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_description TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            top_k INTEGER NOT NULL,
            results_json TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()
    logger.info("Database initialized")

def save_query(job_description, top_k, results):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute(
        'INSERT INTO queries (job_description, timestamp, top_k, results_json) VALUES (?, ?, ?, ?)',
        (job_description, datetime.now().isoformat(), top_k, json.dumps(results))
    )
    conn.commit()
    conn.close()

def get_recent_queries(limit=10):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('SELECT id, job_description, timestamp, top_k, results_json FROM queries ORDER BY timestamp DESC LIMIT ?', (limit,))
    rows = c.fetchall()
    conn.close()
    queries = []
    for row in rows:
        queries.append({
            'id': row[0],
            'job_description': row[1],
            'timestamp': row[2],
            'top_k': row[3],
            'results': json.loads(row[4])
        })
    return queries

# API endpoint for past results
@app.route('/api/query/<int:query_id>', methods=['GET'])
def get_query_results(query_id):
    try:
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute('SELECT results_json FROM queries WHERE id = ?', (query_id,))
        row = c.fetchone()
        conn.close()
        if row:
            return jsonify(json.loads(row[0]))
        else:
            return jsonify({'error': 'Query not found'}), 404
    except Exception as e:
        logger.exception("API error")
        return jsonify({'error': str(e)}), 500

# Main page
@app.route('/', methods=['GET', 'POST'])
def index():
    error = None
    results = None
    job_description = ''
    top_k = 5

    if request.method == 'POST':
        job_description = request.form.get('job_description', '').strip()
        try:
            top_k = int(request.form.get('top_k', 5))
            top_k = max(1, min(top_k, 50))
        except:
            top_k = 5

        if not job_description:
            error = "Please enter a job description."
        elif 'folder' not in request.files:
            error = "Please select a folder."
        else:
            files = request.files.getlist('folder')
            if not files or files[0].filename == '':
                error = "No folder selected."
            else:
                session_id = str(uuid.uuid4())
                temp_dir = os.path.join(app.config['UPLOAD_FOLDER'], session_id)
                os.makedirs(temp_dir, exist_ok=True)
                saved_paths = []
                try:
                    for file in files:
                        if file.filename:
                            filename = secure_filename(file.filename)
                            filepath = os.path.join(temp_dir, filename)
                            file.save(filepath)
                            saved_paths.append(filepath)
                    resumes = load_resumes_from_file_paths(saved_paths)
                    if not resumes:
                        error = "No valid resume files found (PDF, DOCX, TXT, JSONL)."
                    else:
                        results = rank_resumes(resumes, job_description, top_k)
                        save_query(job_description, top_k, results)
                        logger.info(f"New search returned {len(results)} results")
                except Exception as e:
                    logger.exception("Processing error")
                    error = f"Processing error: {str(e)}"
                finally:
                    shutil.rmtree(temp_dir, ignore_errors=True)

    recent = get_recent_queries()
    return render_template('index.html', error=error, results=results,
                           job_description=job_description, top_k=top_k,
                           recent_queries=recent)

if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=5000)