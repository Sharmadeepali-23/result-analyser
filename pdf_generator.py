"""
pdf_generator.py - FPDF2 Report Card PDF and ZIP Generation Logic
"""
import os
import zipfile
from datetime import datetime
from fpdf import FPDF


class ReportCardPDF(FPDF):
    def header(self):
        # Top banner background
        self.set_fill_color(30, 41, 59)  # Slate dark #1e293b
        self.rect(0, 0, 210, 20, 'F')
        
        # Header title
        self.set_font('Helvetica', 'B', 15)
        self.set_text_color(255, 255, 255)
        self.set_xy(10, 5)
        self.cell(190, 10, 'OFFICIAL STUDENT ACADEMIC REPORT CARD', align='C')
        self.ln(18)

    def footer(self):
        self.set_y(-15)
        self.set_font('Helvetica', 'I', 8)
        self.set_text_color(148, 163, 184)
        self.cell(0, 10, f'Page {self.page_no()} | Generated on {datetime.now().strftime("%B %d, %Y - %H:%M")} | Exam Result Analyzer', align='C')


def generate_report_card(student, subject_columns, output_path):
    """
    Generates an individual student PDF report card using fpdf2.

    Parameters:
        student (dict/Series): Student record containing Roll_No, Name, Marks, Grade, Status, Rank, etc.
        subject_columns (list): List of subject column names.
        output_path (str): File path to save the generated PDF.
    """
    pdf = ReportCardPDF(orientation='P', unit='mm', format='A4')
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    
    # Title Subheading / School Header
    pdf.set_font('Helvetica', 'B', 12)
    pdf.set_text_color(51, 65, 85)
    pdf.cell(0, 8, 'EXAM RESULT & PERFORMANCE EVALUATION', align='C', new_x='LMARGIN', new_y='NEXT')
    pdf.set_font('Helvetica', '', 9)
    pdf.set_text_color(100, 116, 139)
    pdf.cell(0, 5, 'Session: 2026-2027 | Term Evaluation Report', align='C', new_x='LMARGIN', new_y='NEXT')
    pdf.ln(5)
    
    # ---------------------------------------------------------
    # Student Details Box (Glassmorphic / Card Style)
    # ---------------------------------------------------------
    pdf.set_fill_color(248, 250, 252)  # #f8fafc light background
    pdf.set_draw_color(226, 232, 240)  # #e2e8f0 border
    pdf.rect(10, 42, 190, 28, 'DF')
    
    pdf.set_xy(15, 45)
    pdf.set_font('Helvetica', 'B', 11)
    pdf.set_text_color(30, 41, 59)
    pdf.cell(30, 6, 'Student Name:')
    pdf.set_font('Helvetica', '', 11)
    pdf.cell(70, 6, str(student['Name']))
    
    pdf.set_font('Helvetica', 'B', 11)
    pdf.cell(25, 6, 'Roll No:')
    pdf.set_font('Helvetica', '', 11)
    pdf.cell(50, 6, str(student['Roll_No']), new_x='LMARGIN', new_y='NEXT')
    
    pdf.set_x(15)
    pdf.set_font('Helvetica', 'B', 11)
    pdf.cell(30, 6, 'Overall Rank:')
    pdf.set_font('Helvetica', 'B', 11)
    pdf.set_text_color(124, 58, 237)  # Purple accent for rank
    pdf.cell(70, 6, f"Rank {int(student['Rank'])}")
    
    pdf.set_font('Helvetica', 'B', 11)
    pdf.set_text_color(30, 41, 59)
    pdf.cell(25, 6, 'Final Result:')
    
    # Status Badge color in details
    if str(student['Status']).upper() == 'PASS':
        pdf.set_text_color(16, 185, 129)  # Green
    else:
        pdf.set_text_color(239, 68, 68)    # Red
    pdf.set_font('Helvetica', 'B', 11)
    pdf.cell(50, 6, str(student['Status']).upper(), new_x='LMARGIN', new_y='NEXT')
    
    pdf.ln(12)
    
    # ---------------------------------------------------------
    # Marks Breakdown Table
    # ---------------------------------------------------------
    pdf.set_font('Helvetica', 'B', 11)
    pdf.set_text_color(30, 41, 59)
    pdf.cell(0, 7, 'SUBJECT MARKS BREAKDOWN', new_x='LMARGIN', new_y='NEXT')
    pdf.ln(2)
    
    # Table Headers
    pdf.set_fill_color(30, 41, 59)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font('Helvetica', 'B', 10)
    
    col_widths = [15, 75, 35, 35, 30]  # S.No, Subject Name, Max Marks, Marks Obtained, Status
    headers = ['#', 'Subject Name', 'Max Marks', 'Marks Obtained', 'Status']
    
    for i in range(len(headers)):
        pdf.cell(col_widths[i], 8, headers[i], border=1, align='C', fill=True)
    pdf.ln()
    
    # Table Rows
    pdf.set_font('Helvetica', '', 10)
    pdf.set_text_color(51, 65, 85)
    
    for idx, subj in enumerate(subject_columns, 1):
        mark = float(student[subj])
        subj_status = 'PASS' if mark >= 33 else 'FAIL'
        
        # Alternating background colors for table rows
        if idx % 2 == 0:
            pdf.set_fill_color(241, 245, 249)
        else:
            pdf.set_fill_color(255, 255, 255)
            
        pdf.cell(col_widths[0], 7, str(idx), border=1, align='C', fill=True)
        pdf.cell(col_widths[1], 7, str(subj), border=1, align='L', fill=True)
        pdf.cell(col_widths[2], 7, '100', border=1, align='C', fill=True)
        
        # Highlight individual failed subject mark
        if mark < 33:
            pdf.set_text_color(220, 38, 38) # Red text
            pdf.set_font('Helvetica', 'B', 10)
        else:
            pdf.set_text_color(51, 65, 85)
            pdf.set_font('Helvetica', '', 10)
            
        pdf.cell(col_widths[3], 7, f"{mark:.1f}", border=1, align='C', fill=True)
        
        if subj_status == 'PASS':
            pdf.set_text_color(16, 185, 129)
        else:
            pdf.set_text_color(239, 68, 68)
        pdf.set_font('Helvetica', 'B', 9)
        pdf.cell(col_widths[4], 7, subj_status, border=1, align='C', fill=True)
        
        pdf.ln()
        
    pdf.ln(8)
    
    # ---------------------------------------------------------
    # Performance Summary Metrics (Cards)
    # ---------------------------------------------------------
    total_subjects = len(subject_columns)
    max_possible = total_subjects * 100
    
    pdf.set_font('Helvetica', 'B', 11)
    pdf.set_text_color(30, 41, 59)
    pdf.cell(0, 7, 'OVERALL SUMMARY & EVALUATION', new_x='LMARGIN', new_y='NEXT')
    pdf.ln(2)
    
    # Draw summary grid
    card_width = 44
    card_height = 20
    start_x = 10
    start_y = pdf.get_y()
    
    metrics = [
        ('TOTAL MARKS', f"{float(student['Total_Marks']):.1f} / {max_possible}", (30, 41, 59)),
        ('PERCENTAGE', f"{float(student['Percentage']):.2f}%", (2, 132, 199)),
        ('GRADE', str(student['Grade']), (217, 119, 6)),
        ('CLASS RANK', f"#{int(student['Rank'])}", (124, 58, 237))
    ]
    
    for idx, (title, val, text_color) in enumerate(metrics):
        x = start_x + (idx * (card_width + 4.5))
        pdf.set_xy(x, start_y)
        pdf.set_fill_color(248, 250, 252)
        pdf.set_draw_color(203, 213, 225)
        pdf.rect(x, start_y, card_width, card_height, 'DF')
        
        pdf.set_xy(x, start_y + 3)
        pdf.set_font('Helvetica', 'B', 8)
        pdf.set_text_color(100, 116, 139)
        pdf.cell(card_width, 4, title, align='C')
        
        pdf.set_xy(x, start_y + 9)
        pdf.set_font('Helvetica', 'B', 13)
        pdf.set_text_color(*text_color)
        pdf.cell(card_width, 7, val, align='C')
        
    pdf.set_y(start_y + card_height + 15)
    
    # ---------------------------------------------------------
    # Grading Scale Legend & Signatures
    # ---------------------------------------------------------
    pdf.set_font('Helvetica', 'I', 8)
    pdf.set_text_color(148, 163, 184)
    pdf.cell(0, 5, 'Grading Scale: A+ (>=90%), A (80-89%), B (70-79%), C (60-69%), D (50-59%), F (<50%)', align='L', new_x='LMARGIN', new_y='NEXT')
    pdf.cell(0, 5, 'Passing Criteria: Min 33 marks in each subject and Min 40% overall percentage.', align='L', new_x='LMARGIN', new_y='NEXT')
    
    pdf.ln(18)
    
    # Signature Lines
    sig_y = pdf.get_y()
    pdf.set_draw_color(148, 163, 184)
    
    pdf.line(20, sig_y, 70, sig_y)
    pdf.line(140, sig_y, 190, sig_y)
    
    pdf.set_xy(20, sig_y + 2)
    pdf.set_font('Helvetica', 'B', 9)
    pdf.set_text_color(71, 85, 105)
    pdf.cell(50, 5, 'Class Teacher Signature', align='C')
    
    pdf.set_xy(140, sig_y + 2)
    pdf.cell(50, 5, 'Principal / Controller of Exams', align='C')
    
    # Save output
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    pdf.output(output_path)
    return output_path


def generate_all_reports_zip(df, subject_columns, reports_dir, zip_output_path):
    """
    Generates individual PDF report cards for all students in df
    and packages them into a single ZIP file.

    Returns:
        str: Path to the generated ZIP file.
    """
    os.makedirs(reports_dir, exist_ok=True)
    os.makedirs(os.path.dirname(zip_output_path), exist_ok=True)
    
    pdf_files = []
    for idx, student in df.iterrows():
        roll_no = str(student['Roll_No']).replace('/', '_').replace('\\', '_')
        pdf_filename = f"Report_Card_{roll_no}.pdf"
        pdf_path = os.path.join(reports_dir, pdf_filename)
        generate_report_card(student, subject_columns, pdf_path)
        pdf_files.append((pdf_filename, pdf_path))
        
    # Package into ZIP
    with zipfile.ZipFile(zip_output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for filename, filepath in pdf_files:
            zipf.write(filepath, arcname=filename)
            
    return zip_output_path
