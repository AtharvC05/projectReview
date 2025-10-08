import fitz  # PyMuPDF
import mysql.connector
import os
import logging
from datetime import datetime
from backend.db import connect_db

logger = logging.getLogger(__name__)

def _db():
    """Shared DB connection for this sheet (default via env)."""
    return connect_db()

def fetch_project_details(group_id):
    """Fetch project and members' details from the database by group_id."""
    conn = _db()
    cursor = conn.cursor()
    
    try:
        # Fetch project details
        cursor.execute("SELECT * FROM projects WHERE group_id = %s", (group_id,))
        project_row = cursor.fetchone()
        
        if not project_row:
            raise ValueError(f"Project not found for group_id: {group_id}")
        
        project_desc = [desc[0] for desc in cursor.description]
        project = dict(zip(project_desc, project_row))

        # Fetch member details
        cursor.execute("SELECT roll_no, student_name, contact_details FROM members WHERE group_id = %s", (group_id,))
        members = cursor.fetchall()
        
        if not members:
            raise ValueError(f"No members found for group_id: {group_id}")

        return {
            "group_id": project.get("group_id", group_id),
            "project_title": project.get("project_title", ""),
            "guide_name": project.get("guide_name", ""),
            "mentor_name": project.get("mentor_name", ""),
            "mentor_email": project.get("mentor_email", ""),
            "mentor_mobile": project.get("mentor_mobile", ""),
            "r1_name": project.get("evaluator1_name", ""),  # Reviewer 1
            "r2_name": project.get("evaluator2_name", ""),  # Reviewer 2
            "members": members
        }
        
    except mysql.connector.Error as err:
        logger.error(f"Database query error: {err}")
        raise Exception(f"Database query error: {err}")
    finally:
        cursor.close()
        conn.close()

def process_fields(doc, data):
    """Fill all form fields with data, make transparent and read-only."""
    filled_count = 0
    
    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        widgets = list(page.widgets())
        
        for widget in widgets:
            field_name = getattr(widget, "field_name", None)
            if not field_name:
                continue

            # Make transparent
            try:
                widget.border_width = 0
                widget.fill_color = None
                widget.border_color = None
                widget.border_style = "none"
            except:
                pass
            
            val = data.get(field_name, "")
            val = "" if val is None else str(val)

            if val.strip():
                field_type = getattr(widget, 'field_type', 0)
                
                if field_type == 2:  # Text field
                    widget.field_value = val.strip()
                    filled_count += 1
                    
                elif field_type == 3:  # Button field
                    try:
                        widget.button_value = val.strip()
                        widget.set_checked(val.strip())
                        filled_count += 1
                    except:
                        val_upper = val.strip().upper()
                        if val_upper in ("Y", "YES", "TRUE", "1"):
                            try:
                                widget.check(True)
                            except:
                                widget.field_value = "Y"
                        elif val_upper in ("N", "NO", "FALSE", "0"):
                            try:
                                widget.check(False)
                            except:
                                widget.field_value = "N"
                        else:
                            widget.field_value = val.strip()
                        filled_count += 1
                else:
                    # Unknown field type - try as text
                    widget.field_value = val.strip()
                    filled_count += 1

            # Make read-only
            try:
                widget.field_flags |= 1
            except:
                pass
                
            try:
                widget.update()
            except:
                pass

    return filled_count

def fetch_attendance_data(group_id):
    """Fetch attendance data for a group for Review IV."""
    conn = _db()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT roll_no, student_name, review4_attendance
            FROM members 
            WHERE group_id = %s
            ORDER BY roll_no
        """, (group_id,))
        
        results = cursor.fetchall()
        attendance_data = {}
        
        for roll_no, student_name, is_present in results:
            attendance_data[f"attendance_{roll_no}"] = "1" if is_present else "0"
            
        return attendance_data
        
    except mysql.connector.Error as e:
        logger.error(f"Error fetching attendance (Review IV): {e}")
        return {}
    finally:
        cursor.close()
        conn.close()

def save_attendance_data(group_id, attendance_dict):
    """Save Review IV attendance data for a group."""
    if not group_id or not attendance_dict:
        return
        
    conn = _db()
    cursor = conn.cursor()

    try:
        for field_name, is_present in attendance_dict.items():
            if field_name.startswith('attendance_'):
                roll_no = field_name.replace('attendance_', '')
                attendance_bool = is_present in ['1', 'true', True, 1]
                
                cursor.execute("""
                    UPDATE members
                    SET review4_attendance = %s
                    WHERE group_id = %s AND roll_no = %s
                """, (attendance_bool, group_id, roll_no))

        conn.commit()
        logger.info(f"Attendance saved for Review-IV group {group_id}")

    except mysql.connector.Error as e:
        logger.error(f"Error saving attendance: {e}")
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()

def determine_template_path(num_members, base_template_dir="pdf_template"):
    """Determine which Review IV template to use based on number of members."""
    if num_members <= 4:
        template_path = os.path.join(base_template_dir, "Review-IV-Sheet.pdf")
        template_type = "4_member"
    elif num_members == 5:
        template_path = os.path.join(base_template_dir, "Review-IV-Sheet-5.pdf")
        template_type = "5_member"
    else:
        raise ValueError(f"Unsupported number of members: {num_members}. Supported: 1-5 members.")

    if not os.path.isfile(template_path):
        raise FileNotFoundError(f"PDF template not found: {template_path}")

    logger.info(f"Using template: {template_path} for {num_members} members")
    return template_path, template_type

def generate_review4_pdf(form_data, base_template_dir="pdf_template"):
    """Generate PDF with filled form fields for Review IV Sheet using PyMuPDF, adaptive to 4 or 5 members."""
    if not form_data:
        raise ValueError("form_data cannot be empty")
        
    group_id = form_data.get('group_id')
    if not group_id:
        raise ValueError("group_id is required")

    # Fetch project info and members
    project_info = fetch_project_details(group_id)
    members = project_info.get('members', [])
    num_members = len(members)
    if num_members == 0:
        raise ValueError(f"No members found for group_id: {group_id}")

    # Select template
    template_path, template_type = determine_template_path(num_members, base_template_dir)

    # Date formatting
    date_value = form_data.get("date")
    if date_value:
        if isinstance(date_value, str):
            try:
                parsed_date = datetime.strptime(date_value, "%Y-%m-%d")
                formatted_date = parsed_date.strftime("%d/%m/%Y")
            except ValueError:
                formatted_date = date_value
        else:
            formatted_date = date_value.strftime("%d/%m/%Y")
    else:
        formatted_date = ""

    # Build field values dictionary
    field_values = {
        "group_id": str(project_info.get("group_id") or ""),
        "date": formatted_date,
        "project_title": str(project_info.get("project_title") or ""),
        "guide_name": str(project_info.get("guide_name") or ""),
        "mentor_name": str(project_info.get("mentor_name") or ""),
        "mentor_email": str(project_info.get("mentor_email") or ""),
        "mentor_mobile": str(project_info.get("mentor_mobile") or ""),
        "r1_name": str(project_info.get("r1_name") or ""),
        "r2_name": str(project_info.get("r2_name") or ""),
    }

    # Add student/member info (up to 5)
    max_members = 5 if template_type == "5_member" else 4
    for idx, member in enumerate(members, start=1):
        if idx > max_members:
            break
        if isinstance(member, (list, tuple)) and len(member) >= 3:
            field_values[f'roll_{idx}'] = str(member[0] or '')
            field_values[f'student_{idx}'] = str(member[1] or '')
            field_values[f'contact_{idx}'] = str(member[2] or '')

    # Map form responses for Review IV questions
    que_to_pdf_field_map = {
        'que_4.1.1': '4.1.1id', 'que_4.1.2': '4.1.2id', 'que_4.1.3': '4.1.3id',
        'que_4.1.4': '4.1.4id', 'que_4.1.5': '4.1.5id', 'que_4.1.6': '4.1.6d',
        'f4.1.1': '4.1.1', 'f4.1.2': '4.1.2', 'f4.1.3': '4.1.3',
        'f4.1.4': '4.1.4', 'f4.1.5': '4.1.5', 'f4.1.s1': '4.1.s1',
        'f4.2.1': '4.2.1', 'f4.2.2': '4.2.2', 'f4.2.3': '4.2.3',
        'f4.2.4': '4.2.4', 'f4.2.5': '4.2.5', 'f4.2.s1': '4.2.s1',
        'f4.3.1': '4.3.1', 'f4.3.2': '4.3.2', 'f4.3.3': '4.3.3',
        'f4.3.4': '4.3.4', 'f4.3.5': '4.3.5', 'f4.3.s1': '4.3.s1',
        'f4.4.1': '4.4.1', 'f4.4.2': '4.4.2', 'f4.4.3': '4.4.3',
        'f4.4.4': '4.4.4', 'f4.4.5': '4.4.5', 'f4.4.s1': '4.4.s1',
        'f4.5.1': '4.5.1', 'f4.5.2': '4.5.2', 'f4.5.3': '4.5.3',
        'f4.5.4': '4.5.4', 'f4.5.5': '4.5.5', 'f4.5.s1': '4.5.s1',
        'c4': '4.c'
    }

    # Map form data to PDF fields
    for key, val in form_data.items():
        if key == "date":
            continue
        val_str = str(val or '')
        pdf_key = que_to_pdf_field_map.get(key, key)
        field_values[pdf_key] = val_str

    # Process PDF
    doc = fitz.open(template_path)
    filled_count = process_fields(doc, field_values)

    # Save PDF
    out_dir = "generated_pdfs"
    os.makedirs(out_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"Review_4_{group_id}_{template_type}.pdf"
    output_path = os.path.join(out_dir, output_file)

    doc.save(output_path, garbage=4, deflate=True)
    doc.close()

    if not os.path.isfile(output_path):
        raise IOError(f"PDF generation failed: output file missing: {output_path}")

    logger.info(f"PDF generated: {output_path} with {filled_count} fields filled using {template_type} template")
    return output_path
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Sample data for testing
    sample_data = {
        'group_id': 'BIA-01',  # Must exist in database
        'date': '2025-09-10',
        
        # Question ID fields (Yes/No/NA for checkboxes)
        'que_4.1.1': 'Y',
        'que_4.1.2': 'N', 
        'que_4.1.3': 'Y',
        'que_4.1.4': 'Y',
        'que_4.1.5': 'N',
        'que_4.1.6': 'Y',
        
        # Section 4.1 - Marks (0-10 each)
        'f4.1.1': '8',
        'f4.1.2': '7',
        'f4.1.3': '9', 
        'f4.1.4': '8',
        'f4.1.5': '6',
        'f4.1.s1': '38',  # Sum
        
        # Section 4.2 - Marks (0-10 each) 
        'f4.2.1': '9',
        'f4.2.2': '8',
        'f4.2.3': '7',
        'f4.2.4': '8', 
        'f4.2.5': '9',
        'f4.2.s1': '41',  # Sum
        
        # Section 4.3 - Marks (0-10 each)
        'f4.3.1': '8',
        'f4.3.2': '9',
        'f4.3.3': '7',
        'f4.3.4': '8',
        'f4.3.5': '8', 
        'f4.3.s1': '40',  # Sum
        
        # Section 4.4 - Marks (0-10 each)
        'f4.4.1': '9',
        'f4.4.2': '8',
        'f4.4.3': '8', 
        'f4.4.4': '9',
        'f4.4.5': '7',
        'f4.4.s1': '41',  # Sum
        
        # Comments
        'c4': 'Final project presentation shows excellent completion with comprehensive testing and deployment.',
    }

    try:
        pdf_path = generate_review4_pdf(sample_data)
        print(f"PDF generated: {pdf_path}")
    except Exception as e:
        print(f"Error: {e}")