# backend/commonBackend.py
from backend.db import get_connection, close_connection, add_year_prefix, strip_year_prefix, get_academic_year
import re
from typing import List, Dict, Optional, Any



# ==================== SECURITY UTILITIES ====================

def validate_review_number(review_number: int) -> bool:
    """Validate review number is within acceptable range"""
    return isinstance(review_number, int) and 0 <= review_number <= 6


def validate_group_id(group_id: str) -> bool:
    """Validate group ID format"""
    # Allow alphanumeric, hyphens, underscores, and length up to 40 chars
    return bool(re.match(r'^[A-Za-z0-9\-_]{1,40}$', group_id))


def validate_roll_no(roll_no: str) -> bool:
    """Validate roll number format"""
    # Allow alphanumeric, hyphens, underscores, and length up to 30 chars
    return bool(re.match(r'^[A-Za-z0-9\-_]{1,30}$', roll_no))



def validate_criteria_id(criteria_id: str) -> bool:
    """Validate criteria ID format"""
    # Only allow alphanumeric and underscores
    return bool(re.match(r'^[a-z_]{1,50}$', criteria_id))


def sanitize_table_name(review_number: int, table_type: str) -> Optional[str]:
    """
    Safely construct table name with whitelist validation
    
    Args:
        review_number: The review number (0-5)
        table_type: Type of table ('marks', 'group_responses', 'performance_criteria', 'questions')
    
    Returns:
        Safe table name or None if invalid
    """
    if not validate_review_number(review_number):
        return None
    
    # Whitelist of allowed table types
    allowed_types = {'marks', 'group_responses', 'performance_criteria', 'questions'}
    if table_type not in allowed_types:
        return None
    
    return f"review{review_number}_{table_type}"


def sanitize_column_name(review_number: int, column_type: str) -> Optional[str]:
    """
    Safely construct column name with whitelist validation
    
    Args:
        review_number: The review number (0-5)
        column_type: Type of column (e.g., 'attendance')
    
    Returns:
        Safe column name or None if invalid
    """
    if not validate_review_number(review_number):
        return None
    
    # Whitelist of allowed column types
    allowed_types = {'attendance'}
    if column_type not in allowed_types:
        return None
    
    return f"review{review_number}_{column_type}"


# ==================== ATTENDANCE FUNCTIONS ====================

def fetch_members(group_id: str, review_number: int = 1) -> List[Dict]:
    """Fetch all members with attendance for a specific review"""
    if not validate_review_number(review_number):
        print(f"Invalid review number: {review_number}")
        return []
    
    if not validate_group_id(group_id):
        print(f"Invalid group_id format: {group_id}")
        return []
    
    conn = get_connection()
    if not conn:
        return []

    try:
        cursor = conn.cursor(dictionary=True)
        
        # Safely construct column name
        attendance_col = sanitize_column_name(review_number, 'attendance')
        if not attendance_col:
            print("Failed to sanitize column name")
            return []
        
        # Use parameterized query - column name is sanitized above
        query = f"""
            SELECT roll_no, student_name as name, {attendance_col} as attendance
            FROM members 
            WHERE group_id = %s
            ORDER BY roll_no
        """
        
        cursor.execute(query, (add_year_prefix(group_id),))
        members = cursor.fetchall()
        
        # Strip prefixes
        for m in members:
            m['roll_no'] = strip_year_prefix(m['roll_no'])
            
        print(f"Fetched {len(members)} members for review {review_number}")
        return members

    except Exception as e:
        print(f"Error fetching members: {e}")
        return []

    finally:
        close_connection(conn)


def update_review_attendance(review_number: int, group_id: str, attendance: List[Dict]) -> bool:
    """Generic function to update attendance for any review"""
    if not validate_review_number(review_number):
        print(f"Invalid review number: {review_number}")
        return False
    
    if not validate_group_id(group_id):
        print(f"Invalid group_id format: {group_id}")
        return False
    
    conn = get_connection()
    if not conn:
        return False

    try:
        cursor = conn.cursor()
        attendance_col = sanitize_column_name(review_number, 'attendance')
        
        if not attendance_col:
            print("Failed to sanitize column name")
            return False
        
        db_group_id = add_year_prefix(group_id)
        for record in attendance:
            roll_no = record.get("roll_no", "")
            
            # Validate roll number
            if not validate_roll_no(roll_no):
                print(f"Invalid roll_no: {roll_no}")
                continue
            
            present = 1 if record.get("present") else 0
            db_roll_no = add_year_prefix(roll_no)

            # Parameterized query with sanitized column name
            query = f"""
                UPDATE members 
                SET {attendance_col} = %s 
                WHERE roll_no = %s AND group_id = %s
            """
            cursor.execute(query, (present, db_roll_no, db_group_id))

        conn.commit()
        print(f"Attendance updated for group {group_id} - Review {review_number}")
        return True

    except Exception as e:
        conn.rollback()
        print(f"Error updating attendance: {e}")
        return False

    finally:
        close_connection(conn)


def get_group_members_for_review(review_number: int, group_id: str) -> List[Dict]:
    """Generic function to fetch group members with attendance for any review"""
    if not validate_review_number(review_number):
        return []
    
    if not validate_group_id(group_id):
        return []
    
    conn = get_connection()
    if not conn:
        return []

    try:
        cursor = conn.cursor(dictionary=True)
        attendance_col = sanitize_column_name(review_number, 'attendance')
        
        if not attendance_col:
            return []
        
        query = f"""
            SELECT roll_no, student_name, {attendance_col} as attendance
            FROM members 
            WHERE group_id = %s
            ORDER BY roll_no
        """
        cursor.execute(query, (add_year_prefix(group_id),))
        
        members = cursor.fetchall()
        for m in members:
            m['roll_no'] = strip_year_prefix(m['roll_no'])
        return members

    except Exception as e:
        print(f"Error fetching group members: {e}")
        return []

    finally:
        close_connection(conn)



# ==================== MARKS FUNCTIONS ====================

def save_review_marks(review_number: int, marks_list: List[Dict]) -> bool:
    """Generic function to save/update marks for any review using UPSERT"""
    if not validate_review_number(review_number):
        print(f"Invalid review number: {review_number}")
        return False
    
    conn = get_connection()
    if not conn:
        return False

    try:
        cursor = conn.cursor(dictionary=True)
        updated_count = 0
        inserted_count = 0
        
        # Get table name safely
        table_name = sanitize_table_name(review_number, 'marks')
        if not table_name:
            print("Failed to sanitize table name")
            return False
        
        # Get column names using parameterized query
        cursor.execute("""
            SELECT COLUMN_NAME 
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_SCHEMA = DATABASE() 
            AND TABLE_NAME = %s
            AND COLUMN_NAME NOT IN ('id', 'group_id', 'roll_no', 'total', 'created_at', 'updated_at')
        """, (table_name,))
        
        criteria_columns = [row['COLUMN_NAME'] for row in cursor.fetchall()]
        
        # Validate all criteria column names
        for col in criteria_columns:
            if not validate_criteria_id(col):
                print(f"Invalid criteria column name: {col}")
                return False
        
        for marks in marks_list:
            group_id = marks.get("group_id", "")
            roll_no = marks.get("roll_no", "")
            
            # Validate inputs
            if not validate_group_id(group_id) or not validate_roll_no(roll_no):
                print(f"Invalid group_id or roll_no: {group_id}, {roll_no}")
                continue
            
            db_group_id = add_year_prefix(group_id)
            db_roll_no = add_year_prefix(roll_no)

            # Build dynamic column list and values
            columns_str = ', '.join(criteria_columns)
            placeholders = ', '.join(['%s'] * len(criteria_columns))
            update_str = ', '.join([f"{col} = VALUES({col})" for col in criteria_columns])
            
            # Extract and validate values
            values = [db_group_id, db_roll_no]
            for col in criteria_columns:
                val = marks.get(col, 0)
                # Validate numeric values for numeric columns, allow strings for text columns
                if isinstance(val, (int, float)):
                    values.append(val)
                elif isinstance(val, str) and len(val) <= 10:  # Allow short strings
                    values.append(val)
                else:
                    values.append(0)
            
            query = f"""
                INSERT INTO {table_name} 
                (group_id, roll_no, {columns_str})
                VALUES (%s, %s, {placeholders})
                ON DUPLICATE KEY UPDATE {update_str}
            """
            
            cursor.execute(query, values)
            
            if cursor.rowcount == 1:
                inserted_count += 1
            elif cursor.rowcount == 2:
                updated_count += 1

        conn.commit()
        print(f"Review {review_number} Marks saved: {inserted_count} inserted, {updated_count} updated")
        return True

    except Exception as e:
        conn.rollback()
        print(f"Error saving review{review_number} marks: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        close_connection(conn)


def get_review_marks(review_number: int, group_id: str) -> List[Dict]:
    """Generic function to fetch existing marks for any review"""
    if not validate_review_number(review_number):
        return []
    
    if not validate_group_id(group_id):
        return []
    
    conn = get_connection()
    if not conn:
        return []

    try:
        cursor = conn.cursor(dictionary=True)
        table_name = sanitize_table_name(review_number, 'marks')
        
        if not table_name:
            return []
        
        query = f"""
            SELECT * FROM {table_name}
            WHERE group_id = %s
            ORDER BY roll_no
        """
        cursor.execute(query, (add_year_prefix(group_id),))
        
        marks = cursor.fetchall()
        for row in marks:
            row['group_id'] = strip_year_prefix(row['group_id'])
            row['roll_no'] = strip_year_prefix(row['roll_no'])
        return marks

    except Exception as e:
        print(f"Error fetching review{review_number} marks: {e}")
        return []

    finally:
        close_connection(conn)


# ==================== RESPONSES FUNCTIONS ====================

def save_review_responses(review_number: int, group_id: str, date: str, 
                          comments: str, responses: List[Dict]) -> Dict[str, Any]:
    """Generic function to save/update questionnaire responses for any review"""
    if not validate_review_number(review_number):
        return {'success': False, 'error': 'Invalid review number'}
    
    if not validate_group_id(group_id):
        return {'success': False, 'error': 'Invalid group ID format'}
    
    conn = get_connection()
    if not conn:
        return {'success': False, 'error': 'Database connection failed'}

    try:
        cursor = conn.cursor(dictionary=True)
        table_name = sanitize_table_name(review_number, 'group_responses')
        
        if not table_name:
            return {'success': False, 'error': 'Invalid table name'}
        
        # Get valid columns from the table
        cursor.execute("""
            SELECT COLUMN_NAME 
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_SCHEMA = DATABASE() 
            AND TABLE_NAME = %s
            AND COLUMN_NAME NOT IN ('id', 'created_at', 'updated_at')
        """, (table_name,))
        
        valid_columns = {row['COLUMN_NAME'] for row in cursor.fetchall()}
        
        db_group_id = add_year_prefix(group_id)
        columns = ['group_id', 'submission_date', 'comments']
        values = [db_group_id, date, comments[:1000] if comments else None]  # Limit comment length
        updates = ['comments = VALUES(comments)', 'submission_date = VALUES(submission_date)']
        
        resp_list = [{'question_code': k, 'response_value': v} for k, v in responses.items()] if isinstance(responses, dict) else responses
        for resp in resp_list:
            # Sanitize question code
            col_name = resp['question_code'].replace('.', '_')
            
            # Validate column exists in table
            if col_name not in valid_columns:
                print(f"Invalid column name: {col_name}")
                continue
            
            # Validate response value
            resp_value = resp['response_value']
            if isinstance(resp_value, (int, float, str)):
                if isinstance(resp_value, str) and len(resp_value) > 50:
                    resp_value = resp_value[:50]  # Limit string length
                
                columns.append(col_name)
                values.append(resp_value)
                updates.append(f"{col_name} = VALUES({col_name})")
        
        placeholders = ', '.join(['%s'] * len(values))
        columns_str = ', '.join(columns)
        updates_str = ', '.join(updates)
        
        query = f"""
            INSERT INTO {table_name} ({columns_str})
            VALUES ({placeholders})
            ON DUPLICATE KEY UPDATE {updates_str}
        """
        
        cursor.execute(query, values)
        was_updated = cursor.rowcount == 2
        action = 'updated' if was_updated else 'inserted'
        
        conn.commit()
        print(f"Review {review_number} Responses {action}: Group={group_id}")
        
        return {
            'success': True,
            'action': action,
            'group_id': strip_year_prefix(db_group_id)
        }

    except Exception as e:
        conn.rollback()
        print(f"Error saving review{review_number} responses: {e}")
        import traceback
        traceback.print_exc()
        return {'success': False, 'error': str(e)}

    finally:
        close_connection(conn)


def get_review_responses(review_number: int, group_id: str) -> Optional[Dict]:
    """Generic function to fetch questionnaire responses for any review"""
    if not validate_review_number(review_number):
        return None
    
    if not validate_group_id(group_id):
        return None
    
    conn = get_connection()
    if not conn:
        return None

    try:
        cursor = conn.cursor(dictionary=True)
        table_name = sanitize_table_name(review_number, 'group_responses')
        
        if not table_name:
            return None
        
        cursor.execute(f"""
            SELECT * FROM {table_name} 
            WHERE group_id = %s
        """, (add_year_prefix(group_id),))
        
        submission = cursor.fetchone()
        
        if not submission:
            print(f"No submission found for group_id: {group_id} in review {review_number}")
            return None
        
        # Extract question responses
        response_fields = [k for k in submission.keys() if k.startswith('que_')]
        responses = {}
        
        for field in response_fields:
            if submission[field] is not None:
                # Convert que_N_M_P back to que_N.M.P
                parts = field.split('_')
                if len(parts) == 4:
                    original_key = f"{parts[0]}_{parts[1]}.{parts[2]}.{parts[3]}"
                else:
                    original_key = field
                responses[original_key] = submission[field]
        
        # Format date safely
        from datetime import date as date_type
        submission_date = submission['submission_date']
        if isinstance(submission_date, date_type):
            date_str = submission_date.strftime('%Y-%m-%d')
        else:
            date_str = str(submission_date)
        
        result = {
            'group_id': strip_year_prefix(submission['group_id']),
            'submission_date': date_str,
            'comments': submission['comments'] or '',
            'created_at': str(submission['created_at']),
            'updated_at': str(submission['updated_at']),
            'responses': responses
        }
        
        return result

    except Exception as e:
        print(f"Error fetching review{review_number} responses: {e}")
        import traceback
        traceback.print_exc()
        return None


    finally:
        close_connection(conn)


# ==================== CRITERIA FETCHING ====================

def get_performance_criteria(review_number: int) -> List[Dict]:
    """Fetch performance criteria for a specific review"""
    if not validate_review_number(review_number):
        return []
    
    conn = get_connection()
    if not conn:
        return []

    try:
        cursor = conn.cursor(dictionary=True)
        table_name = sanitize_table_name(review_number, 'performance_criteria')
        
        if not table_name:
            return []
        
        cursor.execute(f"""
            SELECT criteria_id, criteria_text, max_marks, display_order
            FROM {table_name}
            ORDER BY display_order
        """)
        
        criteria = cursor.fetchall()
        return criteria

    except Exception as e:
        print(f"Error fetching review{review_number} criteria: {e}")
        return []

    finally:
        close_connection(conn)


def get_review_questions(review_number: int) -> List[Dict]:
    """Fetch questions for a specific review"""
    if not validate_review_number(review_number):
        return []
    
    conn = get_connection()
    if not conn:
        return []

    try:
        cursor = conn.cursor(dictionary=True)
        table_name = sanitize_table_name(review_number, 'questions')
        
        if not table_name:
            return []
        
        cursor.execute(f"""
            SELECT question_id, section, question_text, display_order
            FROM {table_name}
            ORDER BY display_order
        """)
        
        questions = cursor.fetchall()
        return questions

    except Exception as e:
        print(f"Error fetching review{review_number} questions: {e}")
        return []

    finally:
        close_connection(conn)
        
# ==================== PDF METADATA FUNCTIONS ====================

def get_available_pdf_reports() -> List[Dict]:
    """
    Fetch all available PDF reports metadata from database
    Returns list of reports that can be generated on-demand
    """
    conn = get_connection()
    if not conn:
        return []
    
    try:
        cursor = conn.cursor(dictionary=True)
        reports = []
        active_year = get_academic_year()
        
        # Query for each review type (0-4, 6)
        for review_num in [0, 1, 2, 3, 4, 6]:
            table_name = sanitize_table_name(review_num, 'group_responses')
            if not table_name:
                continue
            
            query = f"""
                SELECT 
                    r.group_id,
                    r.submission_date,
                    r.created_at,
                    p.project_title,
                    p.guide_name,
                    p.division,
                    p.project_domain,
                    p.mentor_name,
                    p.mentor_email,
                    p.mentor_mobile,
                    {review_num} AS review_number
                FROM {table_name} r
                JOIN projects p ON r.group_id = p.group_id
                WHERE r.group_id LIKE %s
                ORDER BY r.created_at DESC, p.group_id
            """
            
            cursor.execute(query, (f"{active_year}_%",))
            review_reports = cursor.fetchall()
            
            # Convert datetime objects to readable strings and strip prefix
            for report in review_reports:
                report['group_id'] = strip_year_prefix(report['group_id'])
                report['academic_year'] = active_year  # Always use admin-set year
                if report.get('created_at'):
                    from datetime import datetime
                    if isinstance(report['created_at'], datetime):
                        report['created_at'] = report['created_at'].strftime('%Y-%m-%d %H:%M')
                if report.get('submission_date'):
                    from datetime import date as date_type
                    if isinstance(report['submission_date'], date_type):
                        report['submission_date'] = report['submission_date'].strftime('%d/%m/%Y')
            
            reports.extend(review_reports)
        
        print(f"Found {len(reports)} available PDF reports for AY {active_year}")
        return reports
    
    except Exception as e:
        print(f"Error fetching available PDF reports: {e}")
        import traceback
        traceback.print_exc()
        return []
    
    finally:
        close_connection(conn)


def check_pdf_data_availability(review_number: int, group_id: str) -> Dict[str, Any]:
    """
    Check if all required data is available to generate a PDF
    """
    if not validate_review_number(review_number):
        return {'available': False, 'error': 'Invalid review number'}
    
    if not validate_group_id(group_id):
        return {'available': False, 'error': 'Invalid group ID'}
    
    conn = get_connection()
    if not conn:
        return {'available': False, 'error': 'Database connection failed'}
    
    try:
        cursor = conn.cursor(dictionary=True)
        db_group_id = add_year_prefix(group_id)
        
        # Check if project exists
        cursor.execute("SELECT COUNT(*) as count FROM projects WHERE group_id = %s", (db_group_id,))
        if cursor.fetchone()['count'] == 0:
            return {'available': False, 'error': f'Project not found for group {group_id}'}
        
        # Check if members exist
        cursor.execute("SELECT COUNT(*) as count FROM members WHERE group_id = %s", (db_group_id,))
        if cursor.fetchone()['count'] == 0:
            return {'available': False, 'error': f'No members found for group {group_id}'}
        
        # Check if responses exist
        responses_table = sanitize_table_name(review_number, 'group_responses')
        if not responses_table:
            return {'available': False, 'error': 'Invalid table name'}
        
        cursor.execute(f"SELECT COUNT(*) as count FROM {responses_table} WHERE group_id = %s", (db_group_id,))
        if cursor.fetchone()['count'] == 0:
            return {'available': False, 'error': f'No review {review_number} responses found for group {group_id}'}
        
        # Check if marks exist (optional, but helpful)
        marks_table = sanitize_table_name(review_number, 'marks')
        if marks_table:
            cursor.execute(f"SELECT COUNT(*) as count FROM {marks_table} WHERE group_id = %s", (db_group_id,))
            marks_count = cursor.fetchone()['count']
            if marks_count == 0:
                print(f"Warning: No marks found for review {review_number}, group {group_id}")
        
        return {'available': True, 'message': 'All required data is available'}
    
    except Exception as e:
        print(f"Error checking PDF data availability: {e}")
        import traceback
        traceback.print_exc()
        return {'available': False, 'error': str(e)}
    
    finally:
        close_connection(conn)


def log_pdf_generation(review_number: int, group_id: str, 
                       generated_by: str = None, 
                       ip_address: str = None,
                       user_agent: str = None) -> bool:
    """
    Log PDF generation activity (optional tracking)
    """
    if not validate_review_number(review_number) or not validate_group_id(group_id):
        return False
    
    conn = get_connection()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        
        # Check if table exists first
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM information_schema.tables 
            WHERE table_schema = DATABASE() 
            AND table_name = 'pdf_generation_logs'
        """)
        
        if cursor.fetchone()[0] == 0:
            print("Warning: pdf_generation_logs table does not exist. Skipping logging.")
            return False
        
        query = """
            INSERT INTO pdf_generation_logs 
            (review_number, group_id, generated_by, ip_address, user_agent)
            VALUES (%s, %s, %s, %s, %s)
        """
        
        cursor.execute(query, (
            review_number, 
            add_year_prefix(group_id), 
            generated_by[:100] if generated_by else None,
            ip_address[:45] if ip_address else None,
            user_agent[:500] if user_agent else None
        ))
        
        conn.commit()
        print(f"Logged PDF generation: Review {review_number}, Group {group_id}")
        return True
    
    except Exception as e:
        conn.rollback()
        print(f"Error logging PDF generation: {e}")
        return False
    
    finally:
        close_connection(conn)
        
        
# ==================== ATTENDANCE DASHBOARD FUNCTIONS ====================

def get_all_groups_with_attendance() -> List[Dict]:
    """
    Fetch all groups with their members and attendance data
    Used by attendance dashboard
    """
    conn = get_connection()
    if not conn:
        return []
    
    try:
        cursor = conn.cursor(dictionary=True)
        
        # Fetch all members with attendance data for the current year
        query = """
            SELECT 
                member_id,
                group_id,
                roll_no,
                student_name,
                contact_details,
                review0_attendance,
                review1_attendance,
                review2_attendance,
                review3_attendance,
                review4_attendance,
                review6_attendance
            FROM members
            WHERE group_id LIKE %s
            ORDER BY group_id, roll_no
        """
        
        cursor.execute(query, (f"{get_academic_year()}_%",))
        members = cursor.fetchall()
        
        # Group members by group_id (stripped)
        groups_dict = {}
        for member in members:
            group_id = strip_year_prefix(member['group_id'])
            roll_no = strip_year_prefix(member['roll_no'])
            
            if group_id not in groups_dict:
                groups_dict[group_id] = {
                    'group_id': group_id,
                    'members': []
                }
            
            groups_dict[group_id]['members'].append({
                'member_id': member['member_id'],
                'roll_no': roll_no,
                'student_name': member['student_name'],
                'contact_details': member['contact_details'],
                'review0_attendance': bool(member['review0_attendance']),
                'review1_attendance': bool(member['review1_attendance']),
                'review2_attendance': bool(member['review2_attendance']),
                'review3_attendance': bool(member['review3_attendance']),
                'review4_attendance': bool(member['review4_attendance']),
                'review6_attendance': bool(member['review6_attendance'])
            })
        
        # Convert dictionary to list
        groups = list(groups_dict.values())
        
        print(f"Fetched {len(groups)} groups with total {len(members)} members")
        return groups
        
    except Exception as e:
        print(f"Error fetching all groups with attendance: {e}")
        import traceback
        traceback.print_exc()
        return []
    
    finally:
        close_connection(conn)


def generate_attendance_pdf_report() -> Dict[str, Any]:
    """
    Generate attendance PDF report for all groups in current academic year
    """
    conn = get_connection()
    if not conn:
        return {'success': False, 'error': 'Database connection failed'}
    
    try:
        cursor = conn.cursor(dictionary=True)
        
        # Fetch all members with attendance and project info for current year
        query = """
            SELECT 
                m.group_id,
                m.roll_no,
                m.student_name,
                m.review0_attendance,
                m.review1_attendance,
                m.review2_attendance,
                m.review3_attendance,
                m.review4_attendance,
                m.review6_attendance,
                p.project_title,
                p.division
            FROM members m
            LEFT JOIN projects p ON m.group_id = p.group_id
            WHERE m.group_id LIKE %s
            ORDER BY m.group_id, m.roll_no
        """
        
        cursor.execute(query, (f"{get_academic_year()}_%",))
        members = cursor.fetchall()
        
        if not members:
            return {'success': False, 'error': 'No attendance data found'}
        
        # Import PDF libraries
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib.units import inch
        from datetime import datetime
        import io
        
        # Create PDF in memory
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer, 
            pagesize=A4,
            topMargin=0.5*inch, 
            bottomMargin=0.5*inch,
            leftMargin=0.5*inch, 
            rightMargin=0.5*inch
        )
        
        elements = []
        styles = getSampleStyleSheet()
        
        # Title
        title = Paragraph(
            f"<b>Attendance Report - Generated on {datetime.now().strftime('%Y-%m-%d %H:%M')} (AY: {get_academic_year()})</b>",
            styles['Title']
        )
        elements.append(title)
        elements.append(Spacer(1, 0.3*inch))
        
        # Group data by group_id
        groups_dict = {}
        for member in members:
            group_id = strip_year_prefix(member['group_id'])
            member['group_id'] = group_id
            member['roll_no'] = strip_year_prefix(member['roll_no'])
            if group_id not in groups_dict:
                groups_dict[group_id] = {
                    'project_title': member.get('project_title', 'N/A'),
                    'division': member.get('division', 'N/A'),
                    'members': []
                }
            groups_dict[group_id]['members'].append(member)
        
        # Create table for each group
        for group_id, group_data in groups_dict.items():
            # Group header
            group_header = Paragraph(
                f"<b>Group: {group_id} | Project: {group_data['project_title']} | Division: {group_data['division']}</b>",
                styles['Heading2']
            )
            elements.append(group_header)
            elements.append(Spacer(1, 0.1*inch))
            
            # Table data
            table_data = [
                ['Roll No', 'Student Name', 'Review 1', 'Review 2', 'SEM-I Mock', 'Review 3', 'Review 4', 'SEM-II Mock']
            ]
            
            for member in group_data['members']:
                table_data.append([
                    member['roll_no'],
                    member['student_name'],
                    'P' if member['review1_attendance'] else 'A',
                    'P' if member['review2_attendance'] else 'A',
                    'P' if member.get('review0_attendance') else 'A',
                    'P' if member['review3_attendance'] else 'A',
                    'P' if member['review4_attendance'] else 'A',
                    'P' if member.get('review6_attendance') else 'A'
                ])
            
            # Create table
            table = Table(table_data, colWidths=[1.1*inch, 2.0*inch, 0.65*inch, 0.65*inch, 0.85*inch, 0.65*inch, 0.65*inch, 0.85*inch])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 9),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey])
            ]))
            
            elements.append(table)
            elements.append(Spacer(1, 0.3*inch))
        
        # Build PDF
        doc.build(elements)
        buffer.seek(0)
        
        print(f"Generated attendance PDF report for {len(groups_dict)} groups")
        return {
            'success': True,
            'buffer': buffer,
            'filename': f'Attendance_Report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'
        }
        
    except Exception as e:
        print(f"Error generating attendance PDF: {e}")
        import traceback
        traceback.print_exc()
        return {'success': False, 'error': str(e)}
    
    finally:
        close_connection(conn)