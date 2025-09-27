# simple_data_manager.py

from flask import Blueprint, render_template, request, jsonify, send_file, session
import logging
import io
import pandas as pd
import mysql.connector
from datetime import datetime
import re
import json
import base64
import openpyxl
import os
import hashlib
import threading
import time
import fcntl
import backend.sheet1 as sheet1

logger = logging.getLogger(__name__)

bp = Blueprint('simple_data_manager', __name__, template_folder='templates')

# Single file configuration
STORAGE_DIR = 'stored_files'
SINGLE_FILE_PATH = os.path.join(STORAGE_DIR, 'master_project_data.xlsx')
SINGLE_METADATA_PATH = os.path.join(STORAGE_DIR, 'master_metadata.json')
FILE_LOCK_PATH = os.path.join(STORAGE_DIR, 'master.lock')

# Global state for writer/reader control
current_writer = None
writer_lock = threading.Lock()
last_modification_time = None

def ensure_storage_directory():
    """Ensure storage directory exists"""
    os.makedirs(STORAGE_DIR, exist_ok=True)

def get_user_session_id():
    """Get or create a session ID for the user"""
    if 'user_session_id' not in session:
        session['user_session_id'] = hashlib.md5(
            (str(datetime.now()) + str(request.remote_addr or '')).encode()
        ).hexdigest()
    return session['user_session_id']

def is_writer(session_id):
    """Check if current session is the active writer"""
    global current_writer
    with writer_lock:
        return current_writer == session_id

def acquire_writer_lock(session_id):
    """Acquire writer permissions"""
    global current_writer
    with writer_lock:
        if current_writer is None or current_writer == session_id:
            current_writer = session_id
            return True
        return False

def release_writer_lock(session_id):
    """Release writer permissions"""
    global current_writer
    with writer_lock:
        if current_writer == session_id:
            current_writer = None
            return True
        return False

def normalize_name(name: str) -> str:
    if not name:
        return ""
    name = name.lower()
    name = name.replace("\n", " ").replace("\r", " ")
    name = name.replace(".", "")
    name = re.sub(r"\b(dr|prof|professor)\b", "", name)
    name = re.sub(r"\b[a-z]\b", "", name)
    name = re.sub(r"\s+", " ", name)
    return name.strip()

def normalize_column_name(column_name: str) -> str:
    """Normalize column names to handle various naming conventions"""
    if not column_name or pd.isna(column_name):
        return None
    
    col_name = str(column_name).strip().lower()
    col_name = re.sub(r'[_\-\s]+', ' ', col_name)
    col_name = re.sub(r'[^\w\s]', '', col_name)
    col_name = re.sub(r'\s+', ' ', col_name).strip()
    
    # Group No. variations
    if any(pattern in col_name for pattern in [
        'group no', 'grp no', 'group number', 'group id', 'grp id'
    ]):
        return 'Group No.'
    
    # Roll No. variations
    if any(pattern in col_name for pattern in [
        'roll no', 'roll number', 'rollno', 'roll', 'student id'
    ]):
        return 'Roll No.'
    
    # Student Name variations
    if any(pattern in col_name for pattern in [
        'name of the group member', 'name of group member', 'group member name',
        'name of members', 'member name', 'student name', 'name'
    ]) and 'guide' not in col_name and 'company' not in col_name and 'panel' not in col_name:
        return 'Name of the group member'
    
    # Contact Details variations
    if any(pattern in col_name for pattern in [
        'contact details', 'contact', 'phone', 'mobile', 'email', 'contact info'
    ]):
        return 'Contact details'
    
    # Project Domain variations
    if any(pattern in col_name for pattern in [
        'project domain', 'projects domain', 'domain', 'field', 'area'
    ]):
        return 'Project Domain'
    
    # Project Title variations
    if any(pattern in col_name for pattern in [
        'title of the project', 'project title', 'title', 'final title',
        'project name', 'title of project'
    ]):
        return 'Title of the Project'
    
    # Sponsor Company variations
    if any(pattern in col_name for pattern in [
        'name of the sponsored company', 'sponsored company', 'sponsor company',
        'company name', 'sponsoring company', 'name of sponsored'
    ]):
        return 'Name of the sponsored company '
    
    # Guide Name variations
    if any(pattern in col_name for pattern in [
        'name of the guide', 'guide name', 'guide', 'supervisor',
        'mentor name', 'faculty guide'
    ]):
        return 'Name of the Guide'
    
    # Schedule-related columns
    if any(pattern in col_name for pattern in ['track', 'panel no', 'panel number']):
        return 'Track'
    
    if any(pattern in col_name for pattern in [
        'name of the panel', 'panel name', 'panel members', 'panel professors',
        'evaluators', 'panel faculty'
    ]):
        return 'Name of the Panel'
    
    if any(pattern in col_name for pattern in [
        'group id', 'groups', 'group nos', 'assigned groups'
    ]):
        return 'Group ID'
    
    if any(pattern in col_name for pattern in [
        'location', 'room', 'venue', 'place'
    ]):
        return 'Location'
    
    return column_name

def normalize_dataframe_columns(df):
    """Normalize all column names in a DataFrame"""
    if df is None or df.empty:
        return df
    
    column_mapping = {}
    for col in df.columns:
        normalized = normalize_column_name(col)
        if normalized:
            column_mapping[col] = normalized
    
    return df.rename(columns=column_mapping)

def detect_and_normalize_sheets_robust(xls):
    """More robust sheet detection that handles edge cases"""
    sheet_names = xls.sheet_names
    detected_sheets = {
        'div_a': None,
        'div_b': None, 
        'schedule': None
    }
    
    logger.info(f"Available sheets: {sheet_names}")
    
    for sheet_name in sheet_names:
        sheet_upper = sheet_name.upper().strip()
        logger.info(f"Processing sheet: '{sheet_name}' -> '{sheet_upper}'")
        
        # Check for Division A
        if any(pattern in sheet_upper for pattern in [
            'FINAL DIV A', 'FINALDIVA', 'FINAL_DIV_A', 'FINAL-DIV-A',
            'DIV A', 'DIVA', 'DIV-A', 'DIV_A', 
            'DIVISION A', 'DIVISIONA', 'DIVISION-A', 'DIVISION_A'
        ]):
            detected_sheets['div_a'] = sheet_name
            logger.info(f"Detected Division A sheet: {sheet_name}")
            
        # Check for Division B  
        elif any(pattern in sheet_upper for pattern in [
            'FINAL DIV B', 'FINALDIVB', 'FINAL_DIV_B', 'FINAL-DIV-B',
            'DIV B', 'DIVB', 'DIV-B', 'DIV_B',
            'DIVISION B', 'DIVISIONB', 'DIVISION-B', 'DIVISION_B'
        ]):
            detected_sheets['div_b'] = sheet_name
            logger.info(f"Detected Division B sheet: {sheet_name}")
            
        # Check for Schedule
        elif any(pattern in sheet_upper for pattern in [
            'SCHEDULE', 'SCHED', 'PANEL SCHEDULE', 'EVALUATION SCHEDULE',
            'PANEL_SCHEDULE', 'EVALUATION_SCHEDULE', 'PANEL-SCHEDULE'
        ]):
            detected_sheets['schedule'] = sheet_name
            logger.info(f"Detected Schedule sheet: {sheet_name}")
    
    logger.info(f"Final detection results: {detected_sheets}")
    return detected_sheets

def save_master_file(file_content, metadata):
    """Save the master Excel file with proper locking"""
    global last_modification_time
    ensure_storage_directory()
    
    try:
        # Save Excel file
        with open(SINGLE_FILE_PATH, 'wb') as f:
            f.write(file_content)
        
        # Save metadata
        metadata['last_modified'] = datetime.now().isoformat()
        with open(SINGLE_METADATA_PATH, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        last_modification_time = datetime.now()
        logger.info("Master file saved successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error saving master file: {e}")
        return False

def load_master_file():
    """Load the master Excel file"""
    ensure_storage_directory()
    
    try:
        if not os.path.exists(SINGLE_FILE_PATH) or not os.path.exists(SINGLE_METADATA_PATH):
            return None, None
        
        # Load Excel file
        with open(SINGLE_FILE_PATH, 'rb') as f:
            file_content = f.read()
        
        # Load metadata
        with open(SINGLE_METADATA_PATH, 'r') as f:
            metadata = json.load(f)
        
        return file_content, metadata
        
    except Exception as e:
        logger.error(f"Error loading master file: {e}")
        return None, None

def update_master_file_cell(sheet_name, row, col, new_value):
    """Update a specific cell in the master file"""
    global last_modification_time
    
    try:
        if not os.path.exists(SINGLE_FILE_PATH):
            return False
            
        # Load workbook
        wb = openpyxl.load_workbook(SINGLE_FILE_PATH)
        
        # Find the correct worksheet
        ws = None
        for ws_name in wb.sheetnames:
            if ws_name.upper() == sheet_name.upper():
                ws = wb[ws_name]
                break
        
        if ws:
            # Update the cell (openpyxl uses 1-based indexing)
            ws.cell(row=row + 1, column=col + 1, value=new_value)
            
            # Save the workbook
            wb.save(SINGLE_FILE_PATH)
            last_modification_time = datetime.now()
            
            # Update metadata
            metadata = {}
            if os.path.exists(SINGLE_METADATA_PATH):
                with open(SINGLE_METADATA_PATH, 'r') as f:
                    metadata = json.load(f)
            
            metadata['last_modified'] = last_modification_time.isoformat()
            metadata['last_cell_update'] = {
                'sheet': sheet_name,
                'row': row,
                'col': col,
                'value': new_value,
                'timestamp': last_modification_time.isoformat()
            }
            
            with open(SINGLE_METADATA_PATH, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            return True
            
    except Exception as e:
        logger.error(f"Error updating master file cell: {e}")
        return False

def process_division_enhanced_with_normalization(df, division_name):
    """Enhanced division processing with column normalization"""
    if df is None or df.empty:
        return 0, 0
    
    df = normalize_dataframe_columns(df)
    
    conn = sheet1.connect_db()
    cur = conn.cursor(dictionary=True)
    
    group_id = None
    processed_groups = []
    processed_members = 0
    
    logger.info(f"Processing division {division_name} with {len(df)} rows")
    logger.info(f"Columns available: {list(df.columns)}")
    
    for i, row in df.iterrows():
        try:
            # Check if 'Group No.' column exists and get its position
            group_no_col = None
            for col_idx, col_name in enumerate(df.columns):
                if 'Group No.' in str(col_name):
                    group_no_col = col_idx
                    break
            
            if group_no_col is not None:
                group_no_value = df.iloc[i, group_no_col]
                
                # Safe null check and conversion
                if pd.notna(group_no_value) and str(group_no_value).strip() not in ['', 'nan', 'None']:
                    group_id = str(group_no_value).strip()
                    
                    # Normalize group ID format
                    if group_id.startswith('BI'):
                        pass  # Already in correct format
                    elif group_id.startswith('BIA') or group_id.startswith('BIB'):
                        if '-' not in group_id and len(group_id) >= 5:
                            group_id = f"{group_id[:3]}-{group_id[3:]}"
                    
                    # Insert project data using iloc for safe access
                    try:
                        # Find column indices for project data
                        project_domain_col = next((idx for idx, col in enumerate(df.columns) if 'Project Domain' in str(col)), None)
                        project_title_col = next((idx for idx, col in enumerate(df.columns) if 'Title of the Project' in str(col)), None)
                        sponsor_company_col = next((idx for idx, col in enumerate(df.columns) if 'sponsored company' in str(col)), None)
                        guide_name_col = next((idx for idx, col in enumerate(df.columns) if 'Guide' in str(col)), None)
                        
                        def safe_get_value(col_idx):
                            if col_idx is not None:
                                val = df.iloc[i, col_idx]
                                return str(val).strip() if pd.notna(val) else ""
                            return ""
                        
                        project_domain = safe_get_value(project_domain_col)[:255]
                        project_title = safe_get_value(project_title_col)[:500]
                        sponsor_company = safe_get_value(sponsor_company_col)[:255]
                        guide_name = safe_get_value(guide_name_col)[:100]
                        
                        cur.execute(
                            """INSERT IGNORE INTO projects 
                               (group_id, division, project_domain, project_title, sponsor_company, guide_name, 
                                mentor_name, mentor_email, mentor_mobile, evaluator1_name, evaluator2_name) 
                               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                            (group_id, division_name, project_domain, project_title, sponsor_company, guide_name, "", "", "", "", "")
                        )
                        
                        if group_id not in processed_groups:
                            processed_groups.append(group_id)
                            logger.debug(f"Added project: {group_id}")
                            
                    except Exception as project_error:
                        logger.error(f"Error inserting project {group_id}: {str(project_error)}")
            
            # Process member data using iloc for safe access
            if group_id:  # Only process if we have a valid group_id
                # Find column indices for member data
                roll_no_col = next((idx for idx, col in enumerate(df.columns) if 'Roll No.' in str(col)), None)
                student_name_col = next((idx for idx, col in enumerate(df.columns) if 'group member' in str(col).lower()), None)
                contact_details_col = next((idx for idx, col in enumerate(df.columns) if 'Contact' in str(col)), None)
                
                def safe_get_member_value(col_idx):
                    if col_idx is not None:
                        val = df.iloc[i, col_idx]
                        if pd.notna(val):
                            return str(val).strip()
                    return ""
                
                roll_no = safe_get_member_value(roll_no_col)
                student_name = safe_get_member_value(student_name_col)
                
                # Only proceed if both have valid non-empty values
                if roll_no and roll_no not in ['nan', 'None'] and student_name and student_name not in ['nan', 'None']:
                    try:
                        contact_details = safe_get_member_value(contact_details_col)
                        
                        # Clean up contact details
                        if contact_details and contact_details != 'nan':
                            # Remove decimal points from contact details if present
                            if '.' in contact_details and contact_details.replace('.', '').isdigit():
                                contact_details = contact_details.split('.')[0]
                        else:
                            contact_details = ""
                        
                        cur.execute(
                            "INSERT IGNORE INTO members (group_id, roll_no, student_name, contact_details) VALUES (%s, %s, %s, %s)",
                            (group_id, roll_no, student_name, contact_details)
                        )
                        processed_members += 1
                        logger.debug(f"Processed member: {group_id} - {roll_no} - {student_name} - {contact_details}")
                        
                    except Exception as member_error:
                        logger.error(f"Error inserting member for {group_id}: {str(member_error)}")
                
        except Exception as row_error:
            logger.error(f"Error processing row {i} in {division_name}: {str(row_error)}")
            continue
            
    conn.commit()
    cur.close()
    conn.close()
    
    logger.info(f"Division {division_name}: Processed {len(processed_groups)} groups and {processed_members} members")
    return len(processed_groups), processed_members

def extract_all_group_ids(row_data):
    """Extract group IDs from row data"""
    all_groups = set()
    
    for cell_value in row_data:
        if not cell_value:
            continue
        
        cell_str = str(cell_value).upper().strip()
        
        # Standard format: BIA-01, BIB-02
        standard_matches = re.findall(r'\b(BI[AB]-?\s*\d{1,2})\b', cell_str)
        for match in standard_matches:
            clean_match = re.sub(r'(BI[AB])[-\s]*(\d{1,2})', r'\1-\2', match)
            if len(clean_match) == 5:
                clean_match = f"{clean_match[:4]}0{clean_match[4:]}"
            all_groups.add(clean_match)
        
        # No hyphen format: BIA01, BIB02
        no_hyphen_matches = re.findall(r'\b(BI[AB]\d{1,2})\b', cell_str)
        for match in no_hyphen_matches:
            if len(match) == 5:
                formatted = f"{match[:3]}-{match[3:]}"
            elif len(match) == 4:
                formatted = f"{match[:3]}-0{match[3:]}"
            else:
                formatted = match
            all_groups.add(formatted)
        
        # Space format: BIA 01, BIB 02
        space_matches = re.findall(r'\b(BI[AB])\s+(\d{1,2})\b', cell_str)
        for prefix, num in space_matches:
            formatted = f"{prefix}-{num.zfill(2)}"
            all_groups.add(formatted)
    
    return sorted(list(all_groups))

def assign_evaluators_from_panel(panel_professors, group_ids):
    """Assign evaluators from panel professors"""
    if not panel_professors or len(panel_professors) < 2:
        panel_professors = ["Default Prof 1", "Default Prof 2", "Default Prof 3"]
    
    assignments = []
    conn = sheet1.connect_db()
    cur = conn.cursor(dictionary=True)
    
    for i, group_id in enumerate(group_ids):
        cur.execute("SELECT guide_name FROM projects WHERE group_id = %s", (group_id,))
        proj_row = cur.fetchone()
        guide_name = proj_row['guide_name'] if proj_row else ""

        available_evaluators = [prof for prof in panel_professors 
                              if normalize_name(prof) != normalize_name(guide_name)]
        
        eval1 = available_evaluators[0] if len(available_evaluators) > 0 else "Default Eval 1"
        eval2 = available_evaluators[1] if len(available_evaluators) > 1 else "Default Eval 2"
        
        assignments.append({
            'group_id': group_id,
            'guide': guide_name or "",
            'evaluator1': eval1 or "",
            'evaluator2': eval2 or ""
        })
    
    cur.close()
    conn.close()
    return assignments

def process_all_data_with_normalization(div_a, div_b, sched):
    """Process all data with column normalization"""
    conn = sheet1.connect_db()
    cur = conn.cursor(dictionary=True)
    
    # Clear existing data
    cur.execute("DELETE FROM panel_assignments")
    cur.execute("DELETE FROM members")
    cur.execute("DELETE FROM projects")
    conn.commit()
    
    # Process divisions with normalization
    div_a_groups, div_a_members = process_division_enhanced_with_normalization(div_a, 'A')
    div_b_groups, div_b_members = process_division_enhanced_with_normalization(div_b, 'B')
    
    # Process schedule with normalization
    schedule_processed = 0
    all_scheduled_groups = set()
    
    # Normalize schedule DataFrame
    sched = normalize_dataframe_columns(sched)
    
    for i, row in sched.iterrows():
        try:
            track = row.get('Track')
            if pd.isnull(track):
                continue
                
            track = int(track)
            
            # Use normalized column name
            panel_text = str(row.get('Name of the Panel', ''))
            panel_profs = []
            if panel_text and panel_text != 'nan':
                prof_lines = panel_text.replace('\n', '|').replace(',', '|').split('|')
                for prof in prof_lines:
                    clean_prof = prof.strip()
                    if len(clean_prof) > 3 and not clean_prof.isdigit():
                        panel_profs.append(clean_prof)
            
            if not panel_profs:
                panel_profs = [
                    f"Default Panel {track} Prof 1",
                    f"Default Panel {track} Prof 2",
                    f"Default Panel {track} Prof 3"
                ]
            
            # Use normalized column name
            location = str(row.get('Location', '')).strip() if pd.notnull(row.get('Location', '')) else f"Room {track}"
            
            # Extract group IDs
            row_values = [str(val) for val in row.values if pd.notnull(val)]
            group_ids = extract_all_group_ids(row_values)
            
            if not group_ids:
                continue
            
            assignments = assign_evaluators_from_panel(panel_profs, group_ids)
            
            for assignment in assignments:
                try:
                    group_id = assignment['group_id']

                    # ✅ Ensure the project exists before inserting panel assignment
                    cur.execute("SELECT group_id FROM projects WHERE group_id = %s", (group_id,))
                    if not cur.fetchone():
                        logger.warning(f"Skipping schedule group {group_id}, not found in projects")
                        continue
                    
                    cur.execute("""
                        INSERT INTO panel_assignments
                        (group_id, track, panel_professors, location, guide, reviewer1, reviewer2, reviewer3)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        ON DUPLICATE KEY UPDATE
                        track=VALUES(track), panel_professors=VALUES(panel_professors), 
                        location=VALUES(location), guide=VALUES(guide),
                        reviewer1=VALUES(reviewer1), reviewer2=VALUES(reviewer2)
                    """, (
                        group_id, track, '\n'.join(panel_profs), location,
                        assignment['guide'], assignment['evaluator1'], assignment['evaluator2'], None
                    ))
                    
                    cur.execute("""
                        UPDATE projects 
                        SET evaluator1_name = %s, evaluator2_name = %s 
                        WHERE group_id = %s
                    """, (assignment['evaluator1'], assignment['evaluator2'], group_id))
                    
                    all_scheduled_groups.add(group_id)
                    
                except Exception as assignment_error:
                    logger.error(f"Error assigning {assignment['group_id']}: {str(assignment_error)}")
            
            schedule_processed += 1
            
        except Exception as e:
            logger.warning(f"Error processing schedule row {i}: {str(e)}")
            continue
    
    conn.commit()
    cur.close()
    conn.close()
    
    return {
        'div_a_groups': div_a_groups,
        'div_b_groups': div_b_groups,
        'scheduled_groups': len(all_scheduled_groups),
        'total_processed': div_a_groups + div_b_groups
    }

def generate_cell_mapping(div_a, div_b, sched, div_a_sheet, div_b_sheet, schedule_sheet):
    """Generate mapping between visual cells and database fields"""
    mapping = {
        'div_a': {},
        'div_b': {},
        'schedule': {}
    }
    
    # Map Division A editable fields
    for i, row in div_a.iterrows():
        actual_row = i + 4  # Account for skipped rows
        if pd.notnull(row.get('Roll No.', '')):
            mapping['div_a'][f'{actual_row}'] = {
                'roll_no': {'col': 'B', 'value': str(row.get('Roll No.', ''))},
                'student_name': {'col': 'C', 'value': str(row.get('Name of the group member', ''))},
                'contact_details': {'col': 'D', 'value': str(row.get('Contact details', ''))},
            }
    
    # Map Division B editable fields  
    for i, row in div_b.iterrows():
        actual_row = i + 4
        if pd.notnull(row.get('Roll No.', '')):
            mapping['div_b'][f'{actual_row}'] = {
                'roll_no': {'col': 'B', 'value': str(row.get('Roll No.', ''))},
                'student_name': {'col': 'C', 'value': str(row.get('Name of the group member', ''))},
                'contact_details': {'col': 'D', 'value': str(row.get('Contact details', ''))},
            }
    
    # Map Schedule editable fields
    for i, row in sched.iterrows():
        actual_row = i + 3
        if pd.notnull(row.get('Track', '')):
            mapping['schedule'][f'{actual_row}'] = {
                'track': {'col': 'A', 'value': str(row.get('Track', ''))},
                'panel_professors': {'col': 'B', 'value': str(row.get('Name of the Panel', ''))},
                'group_ids': {'col': 'C', 'value': str(row.get('Group ID', ''))},
                'location': {'col': 'D', 'value': str(row.get('Location', ''))}
            }
    
    return mapping

def update_main_database_tables(cursor, sheet_name, row, col, new_value):
    """Update main database tables based on sheet type and position"""
    try:
        sheet_upper = sheet_name.upper()
        
        # Load metadata to get actual sheet names
        file_content, metadata = load_master_file()
        
        if not metadata:
            logger.warning("No metadata found for database sync")
            return False
        
        sheet_names = metadata.get('sheet_names', {})
        
        # Determine which type of sheet we're dealing with
        if sheet_name in [sheet_names.get('div_a'), 'div_a'] or 'DIV A' in sheet_upper or 'DIVA' in sheet_upper:
            return update_division_database(cursor, 'A', row, col, new_value)
        elif sheet_name in [sheet_names.get('div_b'), 'div_b'] or 'DIV B' in sheet_upper or 'DIVB' in sheet_upper:
            return update_division_database(cursor, 'B', row, col, new_value)
        elif sheet_name in [sheet_names.get('schedule'), 'schedule'] or 'SCHEDULE' in sheet_upper:
            return update_schedule_database(cursor, row, col, new_value)
        
        return False
        
    except Exception as e:
        logger.error(f"Database sync error: {e}")
        return False

def update_division_database(cursor, division, row, col, new_value):
    """Update projects/members tables based on division and position"""
    try:
        if row <= 3:  # Skip header rows
            return False
        
        data_row = row - 4
        
        # Get all groups for this division to map row to group
        cursor.execute("""
            SELECT DISTINCT p.group_id
            FROM projects p 
            WHERE p.division = %s 
            ORDER BY p.group_id
        """, (division,))
        division_projects = cursor.fetchall()
        
        if not division_projects or data_row >= len(division_projects):
            logger.warning(f"No project found for division {division}, row {data_row}")
            return False
        
        target_project = division_projects[data_row]
        group_id = target_project['group_id']
        
        logger.info(f"Updating division {division}, group {group_id}, col {col} to '{new_value}'")
        
        # Column mapping based on typical Excel structure
        if col == 0:  # Group No.
            cursor.execute("UPDATE projects SET group_id = %s WHERE group_id = %s", (new_value, group_id))
            cursor.execute("UPDATE members SET group_id = %s WHERE group_id = %s", (new_value, group_id))
            
        elif col == 1:  # Roll No.
            cursor.execute("SELECT id FROM members WHERE group_id = %s ORDER BY id LIMIT 1", (group_id,))
            member = cursor.fetchone()
            if member:
                cursor.execute("UPDATE members SET roll_no = %s WHERE id = %s", (new_value, member['id']))
            
        elif col == 2:  # Student Name
            cursor.execute("SELECT id FROM members WHERE group_id = %s ORDER BY id LIMIT 1", (group_id,))
            member = cursor.fetchone()
            if member:
                cursor.execute("UPDATE members SET student_name = %s WHERE id = %s", (new_value, member['id']))
            
        elif col == 3:  # Contact Details
            cursor.execute("SELECT id FROM members WHERE group_id = %s ORDER BY id LIMIT 1", (group_id,))
            member = cursor.fetchone()
            if member:
                cursor.execute("UPDATE members SET contact_details = %s WHERE id = %s", (new_value, member['id']))
            
        elif col == 4:  # Project Domain
            cursor.execute("UPDATE projects SET project_domain = %s WHERE group_id = %s", (new_value[:255], group_id))
            
        elif col == 5:  # Project Title
            cursor.execute("UPDATE projects SET project_title = %s WHERE group_id = %s", (new_value[:500], group_id))
            
        elif col == 6:  # Sponsor Company
            cursor.execute("UPDATE projects SET sponsor_company = %s WHERE group_id = %s", (new_value[:255], group_id))
            
        elif col == 7:  # Guide Name
            cursor.execute("UPDATE projects SET guide_name = %s WHERE group_id = %s", (new_value[:100], group_id))
            
        else:
            logger.info(f"Column {col} not mapped for division updates")
            return False
        
        logger.info(f"Successfully updated division {division}, group {group_id}")
        return True
        
    except Exception as e:
        logger.error(f"Division database update error: {e}")
        return False

def update_schedule_database(cursor, row, col, new_value):
    """Update panel_assignments table based on schedule position"""
    try:
        if row <= 2:  # Skip header rows
            return False
        
        data_row = row - 3
        
        # Get all tracks to map row to track
        cursor.execute("SELECT DISTINCT track FROM panel_assignments ORDER BY track")
        tracks = cursor.fetchall()
        
        if not tracks or data_row >= len(tracks):
            logger.warning(f"No track found for schedule row {data_row}")
            return False
        
        target_track = tracks[data_row]['track']
        
        logger.info(f"Updating schedule track {target_track}, col {col} to '{new_value}'")
        
        # Column mapping for schedule
        if col == 0:  # Track
            old_track = target_track
            cursor.execute("UPDATE panel_assignments SET track = %s WHERE track = %s", (new_value, old_track))
            
        elif col == 1:  # Panel Professors
            cursor.execute("UPDATE panel_assignments SET panel_professors = %s WHERE track = %s", (new_value, target_track))
            
        elif col == 2:  # Group IDs
            logger.info("Group ID updates in schedule may require special handling")
            return False
            
        elif col == 3:  # Location
            cursor.execute("UPDATE panel_assignments SET location = %s WHERE track = %s", (new_value, target_track))
            
        else:
            logger.info(f"Column {col} not mapped for schedule updates")
            return False
        
        logger.info(f"Successfully updated schedule track {target_track}")
        return True
        
    except Exception as e:
        logger.error(f"Schedule database update error: {e}")
        return False

# API Endpoints

@bp.route('/simple-data-manager')
def simple_data_manager_page():
    return render_template('simple-data-manager.html')

@bp.route('/api/check-master-file', methods=['GET'])
def check_master_file():
    """Check if master file exists and get user permissions"""
    try:
        session_id = get_user_session_id()
        file_content, metadata = load_master_file()
        
        user_is_writer = is_writer(session_id)
        can_acquire_writer = current_writer is None
        
        response = {
            'has_file': file_content is not None,
            'is_writer': user_is_writer,
            'can_acquire_writer': can_acquire_writer,
            'current_writer': current_writer,
            'metadata': metadata if metadata else {}
        }
        
        if metadata:
            response['upload_date'] = metadata.get('last_modified', 'Unknown')
            response['last_cell_update'] = metadata.get('last_cell_update', {})
        
        return jsonify(response)
            
    except Exception as e:
        logger.error(f"Error checking master file: {e}")
        return jsonify({'has_file': False, 'error': str(e)})

@bp.route('/api/acquire-writer-permission', methods=['POST'])
def acquire_writer_permission():
    """Acquire writer permissions"""
    try:
        session_id = get_user_session_id()
        success = acquire_writer_lock(session_id)
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Writer permissions acquired',
                'session_id': session_id
            })
        else:
            return jsonify({
                'success': False,
                'message': f'Another user currently has writer permissions'
            }), 409
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/api/release-writer-permission', methods=['POST'])
def release_writer_permission():
    """Release writer permissions"""
    try:
        session_id = get_user_session_id()
        success = release_writer_lock(session_id)
        
        return jsonify({
            'success': success,
            'message': 'Writer permissions released' if success else 'You were not the active writer'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/api/load-master-file', methods=['POST'])
def load_master_file_endpoint():
    """Load the master file"""
    try:
        file_content, metadata = load_master_file()
        
        if not file_content or not metadata:
            return jsonify({'success': False, 'error': 'No master file found'}), 404
        
        # Convert file content to base64
        original_b64 = base64.b64encode(file_content).decode('utf-8')
        
        # Process the file and extract data
        xls = pd.ExcelFile(io.BytesIO(file_content))
        sheet_names = metadata.get('sheet_names', {})
        
        # Load and process data
        div_a = pd.read_excel(xls, sheet_name=sheet_names['div_a'], skiprows=3)
        div_b = pd.read_excel(xls, sheet_name=sheet_names['div_b'], skiprows=3)
        sched = pd.read_excel(xls, sheet_name=sheet_names['schedule'], skiprows=2)

        # Process with normalization
        extracted_data = process_all_data_with_normalization(div_a, div_b, sched)
        
        # Generate cell mapping
        cell_mapping = generate_cell_mapping(div_a, div_b, sched, 
                                           sheet_names['div_a'], 
                                           sheet_names['div_b'], 
                                           sheet_names['schedule'])
        
        return jsonify({
            'success': True,
            'original_file': original_b64,
            'extracted_data': extracted_data,
            'cell_mapping': cell_mapping,
            'sheet_names': sheet_names,
            'message': f'Loaded master file from {metadata.get("last_modified", "Unknown")}'
        })
        
    except Exception as e:
        logger.error(f"Error loading master file: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/api/import-master-excel', methods=['POST'])
def import_master_excel():
    """Import and replace the master Excel file (writer only)"""
    try:
        session_id = get_user_session_id()
        
        # Check writer permissions
        if not is_writer(session_id):
            return jsonify({
                'success': False, 
                'error': 'Only the active writer can upload files'
            }), 403
        
        file = request.files.get('excel')
        if not file:
            return jsonify({'success': False, 'error': 'No file provided'}), 400

        file_content = file.read()
        
        # Store original file for visual rendering
        original_b64 = base64.b64encode(file_content).decode('utf-8')
        
        # Extract data using enhanced normalization
        xls = pd.ExcelFile(io.BytesIO(file_content))
        detected_sheets = detect_and_normalize_sheets_robust(xls)
        
        # Check if all required sheets were found
        missing_sheets = [key for key, value in detected_sheets.items() if value is None]
        if missing_sheets:
            available_sheets = list(xls.sheet_names)
            return jsonify({
                'success': False,
                'error': f"Could not detect {missing_sheets} sheets. Available: {available_sheets}"
            }), 400

        # Prepare metadata
        metadata = {
            'sheet_names': {
                'div_a': detected_sheets['div_a'],
                'div_b': detected_sheets['div_b'],
                'schedule': detected_sheets['schedule']
            },
            'upload_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'original_filename': file.filename,
            'uploaded_by': session_id
        }
        
        # Save master file
        save_success = save_master_file(file_content, metadata)
        
        if not save_success:
            return jsonify({'success': False, 'error': 'Failed to save master file'}), 500
        
        # Process data
        div_a = pd.read_excel(xls, sheet_name=detected_sheets['div_a'], skiprows=3)
        div_b = pd.read_excel(xls, sheet_name=detected_sheets['div_b'], skiprows=3)
        sched = pd.read_excel(xls, sheet_name=detected_sheets['schedule'], skiprows=2)
        
        # Normalize column names
        div_a = normalize_dataframe_columns(div_a)
        div_b = normalize_dataframe_columns(div_b)
        sched = normalize_dataframe_columns(sched)
        
        # Process with enhanced normalization
        extracted_data = process_all_data_with_normalization(div_a, div_b, sched)
        
        # Generate cell mapping
        cell_mapping = generate_cell_mapping(div_a, div_b, sched, 
                                           detected_sheets['div_a'], 
                                           detected_sheets['div_b'], 
                                           detected_sheets['schedule'])
        
        return jsonify({
            'success': True,
            'original_file': original_b64,
            'extracted_data': extracted_data,
            'cell_mapping': cell_mapping,
            'sheet_names': metadata['sheet_names'],
            'message': 'Master Excel file imported and replaced successfully'
        })
        
    except Exception as e:
        logger.error(f"Master import error: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/api/update-master-cell', methods=['POST'])
def update_master_cell():
    """Update a cell in the master file (writer only)"""
    try:
        session_id = get_user_session_id()
        
        # Check writer permissions
        if not is_writer(session_id):
            return jsonify({
                'success': False, 
                'error': 'Only the active writer can modify cells'
            }), 403
        
        data = request.get_json()
        sheet_name = data.get('sheet_name')
        row = data.get('row')
        col = data.get('col')
        new_value = data.get('value', '')
        
        # Update master file
        success = update_master_file_cell(sheet_name, row, col, new_value)
        
        if success:
            # Also update database
            conn = sheet1.connect_db()
            cur = conn.cursor(dictionary=True)
            
            db_success = update_main_database_tables(cur, sheet_name, row, col, new_value)
            
            conn.commit()
            cur.close()
            conn.close()
            
            return jsonify({
                'success': True,
                'message': f'Updated cell [{row},{col}] in master file',
                'database_synced': db_success,
                'last_modified': last_modification_time.isoformat() if last_modification_time else None
            })
        else:
            return jsonify({'success': False, 'error': 'Failed to update master file'}), 500
        
    except Exception as e:
        logger.error(f"Master cell update error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/api/export-master-excel', methods=['POST'])
def export_master_excel():
    """Export the current master Excel file"""
    try:
        if not os.path.exists(SINGLE_FILE_PATH):
            return jsonify({'success': False, 'error': 'No master file to export'}), 404
        
        return send_file(
            SINGLE_FILE_PATH,
            as_attachment=True,
            download_name=f'master_project_data_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx',
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        
    except Exception as e:
        logger.error(f"Master export error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/api/get-file-changes', methods=['GET'])
def get_file_changes():
    """Get recent file changes for real-time updates"""
    try:
        file_content, metadata = load_master_file()
        
        if not metadata:
            return jsonify({'success': False, 'error': 'No master file found'})
        
        return jsonify({
            'success': True,
            'last_modified': metadata.get('last_modified'),
            'last_cell_update': metadata.get('last_cell_update', {}),
            'current_writer': current_writer,
            'has_changes': metadata.get('last_cell_update') is not None
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@bp.route('/api/debug-master', methods=['GET'])
def debug_master():
    """Debug endpoint to check master file and database content"""
    try:
        file_content, metadata = load_master_file()
        
        conn = sheet1.connect_db()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("SELECT COUNT(*) as count FROM projects")
        projects_count = cursor.fetchone()
        
        cursor.execute("SELECT COUNT(*) as count FROM members")
        members_count = cursor.fetchone()
        
        cursor.execute("SELECT * FROM members LIMIT 3")
        sample_members = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'master_file_exists': file_content is not None,
            'metadata': metadata,
            'current_writer': current_writer,
            'database': {
                'projects_count': projects_count['count'],
                'members_count': members_count['count'],
                'sample_members': sample_members
            }
        })
        
    except Exception as e:
        return jsonify({'error': str(e)})