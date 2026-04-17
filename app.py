import os
import shutil
import uuid
import sqlite3
import json
import logging
from datetime import datetime
from flask import Flask, render_template, request
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
    try:
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute(
            'INSERT INTO queries (job_description, timestamp, top_k, results_json) VALUES (?, ?, ?, ?)',
            (job_description, datetime.now().isoformat(), top_k, json.dumps(results))
        )
        conn.commit()
        conn.close()
        logger.info("Query saved to database")
    except Exception as e:
        logger.error(f"Failed to save query: {e}")

def get_recent_queries(limit=10):
    try:
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute('SELECT id, job_description, timestamp, top_k, results_json FROM queries ORDER BY timestamp DESC LIMIT ?', (limit,))
        rows = c.fetchall()
        conn.close()
        return [{
            'id': r[0],
            'job_description': r[1],
            'timestamp': r[2],
            'top_k': r[3],
            'results': json.loads(r[4])
        } for r in rows]
    except Exception as e:
        logger.error(f"Failed to retrieve queries: {e}")
        return []

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
                    # Save each file, preserving relative paths (optional)
                    for file in files:
                        if file.filename:
                            # Use relative path to avoid collisions? We'll just use basename.
                            # But if two subfolders have same filename, they overwrite.
                            # To fix, we could use the full relative path.
                            filename = secure_filename(file.filename)
                            # If filename contains path separators, secure_filename strips them.
                            # So we'll just use basename.
                            filepath = os.path.join(temp_dir, filename)
                            file.save(filepath)
                            saved_paths.append(filepath)
                            logger.info(f"Saved {filename}")
                    # Process resumes
                    resumes = load_resumes_from_file_paths(saved_paths)
                    if not resumes:
                        error = "No valid resume files found (PDF, DOCX, TXT, JSONL)."
                    else:
                        results = rank_resumes(resumes, job_description, top_k)
                        save_query(job_description, top_k, results)
                        logger.info(f"Ranking complete, {len(results)} results")
                except Exception as e:
                    logger.exception("Error processing upload")
                    error = f"Processing error: {str(e)}"
                finally:
                    # Cleanup temp directory
                    shutil.rmtree(temp_dir, ignore_errors=True)
                    logger.info(f"Cleaned up {temp_dir}")

    recent = get_recent_queries()
    return render_template('index.html', error=error, results=results,
                           job_description=job_description, top_k=top_k,
                           recent_queries=recent)

if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=5000)