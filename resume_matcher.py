import os
import re
import json
import PyPDF2
from docx import Document
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# Optional: better PDF extraction
try:
    import pdfplumber
    USE_PDFPLUMBER = True
except ImportError:
    USE_PDFPLUMBER = False

def extract_text_from_pdf(file_path):
    text = ""
    if USE_PDFPLUMBER:
        try:
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
            if text.strip():
                return text
        except:
            pass
    try:
        with open(file_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
    except:
        pass
    return text

def extract_text_from_docx(file_path):
    try:
        doc = Document(file_path)
        return "\n".join([para.text for para in doc.paragraphs])
    except:
        return ""

def extract_text_from_txt(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read()
    except:
        return ""

def extract_text_from_jsonl(file_path):
    texts = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    texts.append(extract_text_from_resume_json(data))
                except:
                    continue
        return "\n".join(texts)
    except:
        return ""

def extract_text_from_resume_json(resume):
    text_parts = []
    if resume.get('personal_info', {}).get('summary'):
        text_parts.append(resume['personal_info']['summary'])
    for exp in resume.get('experience', []):
        if exp.get('title'):
            text_parts.append(exp['title'])
        if exp.get('responsibilities'):
            text_parts.append(' '.join(exp['responsibilities']))
        if exp.get('technical_environment', {}).get('technologies'):
            text_parts.append(' '.join(exp['technical_environment']['technologies']))
    skills = resume.get('skills', {})
    for skill_cat in skills.values():
        if isinstance(skill_cat, list):
            for skill in skill_cat:
                if isinstance(skill, dict) and skill.get('name'):
                    text_parts.append(skill['name'])
                elif isinstance(skill, str):
                    text_parts.append(skill)
        elif isinstance(skill_cat, dict):
            for subcat in skill_cat.values():
                if isinstance(subcat, list):
                    for skill in subcat:
                        if isinstance(skill, dict) and skill.get('name'):
                            text_parts.append(skill['name'])
    for edu in resume.get('education', []):
        if edu.get('degree', {}).get('field'):
            text_parts.append(edu['degree']['field'])
        if edu.get('institution', {}).get('name'):
            text_parts.append(edu['institution']['name'])
    for proj in resume.get('projects', []):
        if proj.get('name'):
            text_parts.append(proj['name'])
        if proj.get('description'):
            text_parts.append(proj['description'])
        if proj.get('technologies'):
            text_parts.append(' '.join(proj['technologies']))
    full_text = ' '.join(text_parts)
    full_text = re.sub(r'[^a-zA-Z0-9\s]', ' ', full_text)
    full_text = full_text.lower().strip()
    return full_text

def load_resumes_from_file_paths(file_paths):
    resumes = []
    for file_path in file_paths:
        filename = os.path.basename(file_path)
        ext = filename.lower()
        text = ""
        if ext.endswith('.pdf'):
            text = extract_text_from_pdf(file_path)
        elif ext.endswith('.docx'):
            text = extract_text_from_docx(file_path)
        elif ext.endswith('.txt'):
            text = extract_text_from_txt(file_path)
        elif ext.endswith('.jsonl'):
            text = extract_text_from_jsonl(file_path)
        else:
            continue
        text = re.sub(r'\s+', ' ', text).strip()
        if text:
            resumes.append({'file_name': filename, 'text': text})
    return resumes

def rank_resumes(resume_text_objects, job_description, top_k=None):
    texts = [obj['text'] for obj in resume_text_objects]
    if not texts:
        return []
    all_texts = texts + [job_description]
    vectorizer = TfidfVectorizer(stop_words='english', max_features=5000)
    tfidf_matrix = vectorizer.fit_transform(all_texts)
    similarities = cosine_similarity(tfidf_matrix[-1], tfidf_matrix[:-1]).flatten()
    ranked = list(zip(resume_text_objects, similarities))
    ranked.sort(key=lambda x: x[1], reverse=True)
    if top_k:
        ranked = ranked[:top_k]
    results = []
    for obj, score in ranked:
        results.append({
            'file_name': obj['file_name'],
            'score': round(score*100,1),
            'text_preview': obj['text'][:300] + ('...' if len(obj['text']) > 300 else '')
        })
    return results