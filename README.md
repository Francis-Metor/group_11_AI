# Resume Matcher

A web application that helps recruiters find the most relevant candidates for a job. You select a folder containing CV files (PDF, DOCX, TXT, or JSONL), paste a job description, and the app ranks the CVs by how well they match the job.

## Features

- Select a folder with multiple CV files using a graphical folder picker.
- Supports PDF, DOCX, plain text, and JSONL resume files.
- Computes a relevance score for each resume using TF-IDF and cosine similarity.
- Shows the top matching resumes with scores and a preview of the extracted text.
- Saves every search query in a local SQLite database.
- Click on a past query to reload the job description.

## Requirements

- Python 3.8 or higher
- The packages listed in `requirements.txt`

## Installation

1. Download or clone the project folder.
2. Open a terminal inside the project folder.
3. Install the required packages:

   ```bash
   pip install -r requirements.txt

   resume_matcher/
├── app.py                 # Flask web server
├── resume_matcher.py      # Text extraction and ranking logic
├── templates/
│   └── index.html         # Web page template
├── static/
│   └── style.css          # Styling for the web page
├── temp_uploads/          # Temporary folder for uploaded files (auto‑created)
├── resume_matches.db      # SQLite database (auto‑created)
└── requirements.txt       # Python dependencies

## To run this Flask project
1. run the app.py file
2. search http://127.0.0.1:5000 in your browser to acess the running project
