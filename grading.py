"""
grading.py - Core Grading, Validation, and Ranking Logic using Pandas
"""
import pandas as pd
import numpy as np

def validate_and_read_csv(file_path):
    """
    Validates and reads the uploaded CSV file.
    
    Checks:
    1. Valid CSV file structure and non-empty.
    2. Presence of mandatory columns: 'Roll_No' and 'Name'.
    3. Presence of at least one subject column.
    4. Numeric validation for subject marks (must be numbers between 0 and 100).
    5. Checks for duplicate Roll_No entries.

    Returns:
        tuple: (df, subject_columns, error_message)
    """
    try:
        df = pd.read_csv(file_path)
    except Exception as e:
        return None, [], f"Could not parse CSV file. Error details: {str(e)}"
    
    # Drop completely empty rows if any
    df = df.dropna(how='all').reset_index(drop=True)

    if df.empty:
        return None, [], "Uploaded CSV file is empty."
    
    # Strip whitespace from column names
    df.columns = df.columns.astype(str).str.strip()
    
    # Check for required mandatory columns (case-insensitive check for flexibility)
    col_mapping = {}
    for col in df.columns:
        col_lower = col.lower().replace(" ", "_")
        if col_lower in ["roll_no", "rollno", "roll"]:
            col_mapping[col] = "Roll_No"
        elif col_lower in ["name", "student_name", "studentname"]:
            col_mapping[col] = "Name"
            
    df = df.rename(columns=col_mapping)
    
    if "Roll_No" not in df.columns:
        return None, [], "Missing required column 'Roll_No' in CSV file."
    if "Name" not in df.columns:
        return None, [], "Missing required column 'Name' in CSV file."
    
    # Format Roll_No and Name cleanly as strings
    df['Roll_No'] = df['Roll_No'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
    df['Name'] = df['Name'].astype(str).str.strip()
    
    # Check for empty Roll_No or Name values
    if (df['Roll_No'] == '').any() or (df['Roll_No'].str.lower() == 'nan').any():
        return None, [], "CSV contains missing or empty 'Roll_No' values."
    if (df['Name'] == '').any() or (df['Name'].str.lower() == 'nan').any():
        return None, [], "CSV contains missing or empty 'Name' values."

    # Identify subject columns (everything except Roll_No and Name)
    subject_columns = [col for col in df.columns if col not in ["Roll_No", "Name"]]
    
    if not subject_columns:
        return None, [], "CSV must contain at least one subject marks column."
        
    # Check duplicate Roll_No
    duplicate_rolls = df[df.duplicated("Roll_No", keep=False)]["Roll_No"].tolist()
    if duplicate_rolls:
        unique_dups = list(set(duplicate_rolls))
        return None, [], f"Duplicate Roll_No found in CSV: {', '.join(map(str, unique_dups))}. Roll numbers must be unique."

    # Validate numeric marks for each subject column
    for col in subject_columns:
        converted = pd.to_numeric(df[col], errors='coerce')
        nan_rows = df[converted.isna()]
        
        if not nan_rows.empty:
            invalid_names = nan_rows["Name"].tolist()
            return None, [], f"Missing or non-numeric mark found in subject '{col}' for student(s): {', '.join(map(str, invalid_names))}."
            
        # Check mark range 0 to 100
        out_of_bounds = df[(converted < 0) | (converted > 100)]
        if not out_of_bounds.empty:
            invalid_names = out_of_bounds["Name"].tolist()
            return None, [], f"Marks must be between 0 and 100. Invalid values in '{col}' for student(s): {', '.join(map(str, invalid_names))}."

        # Assign numeric values back
        df[col] = converted.astype(float)
        
    return df, subject_columns, None


def calculate_grade(percentage):
    """
    Returns grade based on percentage:
    90-100: A+
    80-89.99: A
    70-79.99: B
    60-69.99: C
    50-59.99: D
    Below 50: F
    """
    if percentage >= 90:
        return 'A+'
    elif percentage >= 80:
        return 'A'
    elif percentage >= 70:
        return 'B'
    elif percentage >= 60:
        return 'C'
    elif percentage >= 50:
        return 'D'
    else:
        return 'F'


def process_grading(df, subject_columns, pass_subject_min=33, pass_overall_min=40):
    """
    Calculates Total Marks, Percentage, Grade, Pass/Fail Status, and Class Rank.
    """
    df = df.copy()
    num_subjects = len(subject_columns)
    max_total_marks = num_subjects * 100
    
    # 1. Calculate Total Marks
    df['Total_Marks'] = df[subject_columns].sum(axis=1).round(2)
    
    # 2. Calculate Percentage
    df['Percentage'] = ((df['Total_Marks'] / max_total_marks) * 100).round(2)
    
    # 3. Assign Grade based on Percentage
    df['Grade'] = df['Percentage'].apply(calculate_grade)
    
    # 4. Assign Pass/Fail Status
    has_failed_subject = (df[subject_columns] < pass_subject_min).any(axis=1)
    has_failed_overall = df['Percentage'] < pass_overall_min
    
    df['Status'] = np.where(has_failed_subject | has_failed_overall, 'Fail', 'Pass')
    
    # 5. Calculate Rank (method='min' handles ties)
    df['Rank'] = df['Total_Marks'].rank(ascending=False, method='min').astype(int)
    
    # Sort by Rank ascending
    df = df.sort_values(by=['Rank', 'Name'], ascending=[True, True]).reset_index(drop=True)
    
    return df


def compute_summary_stats(df, subject_columns):
    """
    Computes overall class analytics and subject-wise statistics.
    """
    total_students = len(df)
    if total_students == 0:
        return {}
        
    passed_count = int((df['Status'] == 'Pass').sum())
    failed_count = total_students - passed_count
    pass_percentage = round(float((passed_count / total_students) * 100), 2)
    class_average = round(float(df['Percentage'].mean()), 2)
    
    # Top scorer
    top_scorer_row = df.loc[df['Total_Marks'].idxmax()]
    top_scorer = {
        'Roll_No': str(top_scorer_row['Roll_No']),
        'Name': str(top_scorer_row['Name']),
        'Total_Marks': float(top_scorer_row['Total_Marks']),
        'Percentage': float(top_scorer_row['Percentage']),
        'Rank': int(top_scorer_row['Rank'])
    }
    
    # Lowest scorer
    lowest_scorer_row = df.loc[df['Total_Marks'].idxmin()]
    lowest_scorer = {
        'Roll_No': str(lowest_scorer_row['Roll_No']),
        'Name': str(lowest_scorer_row['Name']),
        'Total_Marks': float(lowest_scorer_row['Total_Marks']),
        'Percentage': float(lowest_scorer_row['Percentage']),
        'Rank': int(lowest_scorer_row['Rank'])
    }
    
    # Subject-wise statistics
    subject_stats = []
    for col in subject_columns:
        avg_score = round(float(df[col].mean()), 2)
        max_score = round(float(df[col].max()), 2)
        min_score = round(float(df[col].min()), 2)
        pass_count = int((df[col] >= 33).sum())
        subj_pass_percentage = round(float((pass_count / total_students) * 100), 1)
        
        subject_stats.append({
            'subject': str(col),
            'average': avg_score,
            'max': max_score,
            'min': min_score,
            'pass_percentage': subj_pass_percentage
        })
        
    return {
        'total_students': total_students,
        'passed_count': passed_count,
        'failed_count': failed_count,
        'pass_percentage': pass_percentage,
        'class_average': class_average,
        'top_scorer': top_scorer,
        'lowest_scorer': lowest_scorer,
        'subject_stats': subject_stats,
        'total_subjects': len(subject_columns)
    }
