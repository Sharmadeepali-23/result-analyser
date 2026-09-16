"""
app.py - Main Flask Web Application for Exam Result Analyzer & Auto-Grading
"""
import os
import json
import uuid
import pandas as pd
from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file
from werkzeug.utils import secure_filename

from grading import validate_and_read_csv, process_grading, compute_summary_stats
from pdf_generator import generate_report_card, generate_all_reports_zip

app = Flask(__name__)
app.secret_key = 'exam_analyzer_secret_key_2026'

# Application Configuration
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
REPORTS_FOLDER = os.path.join(BASE_DIR, 'reports')
SAMPLE_CSV_PATH = os.path.join(BASE_DIR, 'sample_students.csv')
ALLOWED_EXTENSIONS = {'csv'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['REPORTS_FOLDER'] = REPORTS_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB max upload limit

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(REPORTS_FOLDER, exist_ok=True)


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def load_current_dataset():
    """
    Helper function to retrieve current dataset stored in session cache.
    Returns (df, subject_columns) or (None, None).
    """
    dataset_id = session.get('dataset_id')
    if not dataset_id:
        return None, None
        
    cache_path = os.path.join(UPLOAD_FOLDER, f"dataset_{dataset_id}.json")
    meta_path = os.path.join(UPLOAD_FOLDER, f"meta_{dataset_id}.json")
    
    if not os.path.exists(cache_path) or not os.path.exists(meta_path):
        return None, None
        
    with open(meta_path, 'r') as f:
        meta = json.load(f)
        
    df = pd.read_json(cache_path, orient='records', dtype={'Roll_No': str})
    df['Roll_No'] = df['Roll_No'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
    return df, meta.get('subject_columns', [])


@app.route('/')
def upload_page():
    """Renders the CSV file upload page."""
    return render_template('upload.html')


@app.route('/upload', methods=['POST'])
def upload_file():
    """Handles CSV file upload, validation, grading processing, and session storage."""
    if 'file' not in request.files:
        flash('No file part in the upload request.', 'error')
        return redirect(url_for('upload_page'))
        
    file = request.files['file']
    
    if file.filename == '':
        flash('No file selected. Please choose a CSV file to upload.', 'error')
        return redirect(url_for('upload_page'))
        
    if not allowed_file(file.filename):
        flash('Invalid file extension. Please upload a valid CSV file (.csv).', 'error')
        return redirect(url_for('upload_page'))
        
    try:
        # Save file to uploads directory
        filename = secure_filename(file.filename)
        saved_path = os.path.join(app.config['UPLOAD_FOLDER'], f"uploaded_{filename}")
        file.save(saved_path)
        
        # 1. Validate & Read CSV
        df, subject_columns, error_msg = validate_and_read_csv(saved_path)
        if error_msg:
            flash(error_msg, 'error')
            return redirect(url_for('upload_page'))
            
        # 2. Process Auto-Grading & Ranking
        processed_df = process_grading(df, subject_columns)
        
        # 3. Store processed result in dataset cache
        dataset_id = str(uuid.uuid4())
        cache_path = os.path.join(app.config['UPLOAD_FOLDER'], f"dataset_{dataset_id}.json")
        meta_path = os.path.join(app.config['UPLOAD_FOLDER'], f"meta_{dataset_id}.json")
        
        processed_df.to_json(cache_path, orient='records')
        with open(meta_path, 'w') as f:
            json.dump({'subject_columns': subject_columns}, f)
            
        session['dataset_id'] = dataset_id
        flash(f'Successfully processed results for {len(processed_df)} students across {len(subject_columns)} subjects!', 'success')
        return redirect(url_for('results'))

    except Exception as e:
        flash(f'An unexpected error occurred while processing the file: {str(e)}', 'error')
        return redirect(url_for('upload_page'))


@app.route('/results')
def results():
    """Displays the results dashboard with sortable/filterable table and summary statistics."""
    df, subject_columns = load_current_dataset()
    
    if df is None or df.empty:
        flash('No active dataset found. Please upload a CSV file to view results.', 'error')
        return redirect(url_for('upload_page'))
        
    # Calculate global analytics before filtering
    stats = compute_summary_stats(df, subject_columns)
    
    # Filter & Search Parameters
    search_query = request.args.get('search', '').strip()
    status_filter = request.args.get('status', '').strip()
    grade_filter = request.args.get('grade', '').strip()
    sort_by = request.args.get('sort_by', 'Rank').strip()
    
    filtered_df = df.copy()
    
    # Search filter (Roll_No or Name)
    if search_query:
        search_lower = search_query.lower()
        filtered_df = filtered_df[
            filtered_df['Name'].astype(str).str.lower().str.contains(search_lower) |
            filtered_df['Roll_No'].astype(str).str.lower().str.contains(search_lower)
        ]
        
    # Status filter (Pass / Fail)
    if status_filter in ['Pass', 'Fail']:
        filtered_df = filtered_df[filtered_df['Status'] == status_filter]
        
    # Grade filter (A+, A, B, C, D, F)
    if grade_filter:
        filtered_df = filtered_df[filtered_df['Grade'] == grade_filter]
        
    # Sorting
    if sort_by == 'Name':
        filtered_df = filtered_df.sort_values(by='Name', ascending=True)
    elif sort_by == 'Roll_No':
        filtered_df = filtered_df.sort_values(by='Roll_No', ascending=True)
    elif sort_by == 'Total_Marks':
        filtered_df = filtered_df.sort_values(by='Total_Marks', ascending=False)
    elif sort_by == 'Percentage':
        filtered_df = filtered_df.sort_values(by='Percentage', ascending=False)
    else:  # Default sort by Rank
        filtered_df = filtered_df.sort_values(by='Rank', ascending=True)
        
    students_list = filtered_df.to_dict(orient='records')
    
    current_filters = {
        'search': search_query,
        'status': status_filter,
        'grade': grade_filter,
        'sort_by': sort_by
    }
    
    return render_template('results.html',
                           students=students_list,
                           subject_columns=subject_columns,
                           stats=stats,
                           current_filters=current_filters)


@app.route('/download/pdf/<roll_no>')
def download_pdf(roll_no):
    """Generates and downloads individual PDF report card for a student."""
    df, subject_columns = load_current_dataset()
    if df is None:
        flash('Session expired or dataset not found. Please upload again.', 'error')
        return redirect(url_for('upload_page'))
        
    # Find student row
    student_rows = df[df['Roll_No'].astype(str) == str(roll_no)]
    if student_rows.empty:
        flash(f'Student with Roll No {roll_no} not found.', 'error')
        return redirect(url_for('results'))
        
    student = student_rows.iloc[0].to_dict()
    safe_roll = str(roll_no).replace('/', '_').replace('\\', '_')
    pdf_filename = f"Report_Card_{safe_roll}.pdf"
    pdf_path = os.path.join(app.config['REPORTS_FOLDER'], pdf_filename)
    
    generate_report_card(student, subject_columns, pdf_path)
    
    return send_file(pdf_path, mimetype='application/pdf', as_attachment=True, download_name=pdf_filename)


@app.route('/download/all_zip')
def download_all_zip():
    """Generates PDF report cards for all students and downloads as ZIP."""
    df, subject_columns = load_current_dataset()
    if df is None or df.empty:
        flash('Session expired or dataset not found. Please upload again.', 'error')
        return redirect(url_for('upload_page'))
        
    dataset_id = session.get('dataset_id', 'all')
    zip_filename = f"All_Student_Report_Cards_{dataset_id[:8]}.zip"
    zip_path = os.path.join(app.config['REPORTS_FOLDER'], zip_filename)
    
    generate_all_reports_zip(df, subject_columns, app.config['REPORTS_FOLDER'], zip_path)
    
    return send_file(zip_path, mimetype='application/zip', as_attachment=True, download_name='All_Student_Report_Cards.zip')


@app.route('/sample_csv')
def download_sample():
    """Serves the pre-populated sample CSV file."""
    if os.path.exists(SAMPLE_CSV_PATH):
        return send_file(SAMPLE_CSV_PATH, mimetype='text/csv', as_attachment=True, download_name='sample_students.csv')
    else:
        flash('Sample CSV file not found on server.', 'error')
        return redirect(url_for('upload_page'))


if __name__ == '__main__':
    print("Starting Exam Result Analyzer Flask Server...")
    print("Open http://127.0.0.1:5000 in your web browser.")
    app.run(host='127.0.0.1', port=5000, debug=True)
