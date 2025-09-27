import fitz  # PyMuPDF
import os
import mysql.connector
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

def connect_db():
    """Database connection with error handling."""
    try:
        return mysql.connector.connect(
            host="localhost",
            user="root", 
            password="1234",
            database="project_review",
            autocommit=True,
        )
    except mysql.connector.Error as e:
        logger.error(f"Database connection error: {e}")
        raise

def fetch_project_details(group_id):
    """Fetch project and members info from DB; raise error if not found."""
    conn = connect_db()
    cursor = conn.cursor()
    
    try:
        # Fetch project details
        cursor.execute("SELECT * FROM projects WHERE group_id=%s", (group_id,))
        project_row = cursor.fetchone()
        
        if not project_row:
            raise ValueError(f"Project not found for group_id: {group_id}")
        
        project_desc = [desc[0] for desc in cursor.description]
        project = dict(zip(project_desc, project_row))
        
        # Fetch member details
        cursor.execute(
            "SELECT roll_no, student_name, contact_details FROM members WHERE group_id=%s", (group_id,)
        )
        members = cursor.fetchall()
        
        if not members:
            raise ValueError(f"No members found for group_id: {group_id}")
        
    except mysql.connector.Error as e:
        logger.error(f"Database error: {e}")
        raise
    finally:
        cursor.close()
        conn.close()

    return {
        "group_id": project.get("group_id", group_id),
        "project_title": project.get("project_title", ""),
        "guide_name": project.get("guide_name", ""),
        "mentor_name": project.get("mentor_name", ""),
        "mentor_email": project.get("mentor_email", ""),
        "mentor_mobile": project.get("mentor_mobile", ""),
        "r1_name": project.get("evaluator1_name", ""),  # Reviewer 1
        "r2_name": project.get("evaluator2_name", ""),  # Reviewer 2
        "members": members,
    }

def determine_template_path(num_members, base_template_dir="pdf_template"):
    """Determine which template to use based on number of members."""
    if num_members <= 4:
        template_path = os.path.join(base_template_dir, "Review-III-Sheet.pdf")
        template_type = "4_member"
    elif num_members == 5:
        template_path = os.path.join(base_template_dir, "Review-III-Sheet-5.pdf")
        template_type = "5_member"
    else:
        raise ValueError(f"Unsupported number of members: {num_members}. Supported: 1-5 members.")
    
    if not os.path.isfile(template_path):
        raise FileNotFoundError(f"PDF template not found: {template_path}")
    
    logger.info(f"Using template: {template_path} for {num_members} members")
    return template_path, template_type


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

def build_performance_evaluation_fields(form_data, num_members, template_type):
    """Build performance evaluation field mappings based on template type and number of members."""
    performance_fields = {}
    
    # Performance evaluation criteria with their corresponding field patterns
    criteria_mapping = {
        'perf_1': 'System Architecture & Literature Survey',
        'perf_2': 'Project Design',
        'perf_3': 'Methodology /Algorithms and Project Features',
        'perf_4': 'Project Planning',
        'perf_5': 'Basic details of Implementation',
        'perf_6': 'Presentation Skills',
        'perf_7': 'Question and Answer',
        'perf_8': 'Summarization of ultimate findings'
    }
    
    # Build performance evaluation fields for each member
    for criteria_key, criteria_desc in criteria_mapping.items():
        for member_num in range(1, min(num_members + 1, 6)):  # Max 5 members
            form_key = f"{criteria_key}_{member_num}"
            
            # Map to appropriate field name based on template type
            if template_type == "4_member":
                # For 4-member template, field names might be like: perf_1_1, perf_1_2, etc.
                field_name = f"{criteria_key}_{member_num}"
            else:  # 5_member template
                # For 5-member template, field names might be similar but support 5 columns
                field_name = f"{criteria_key}_{member_num}"
            
            if form_key in form_data:
                performance_fields[field_name] = str(form_data[form_key] or "")
    
    # Add total fields for each member
    for member_num in range(1, min(num_members + 1, 6)):
        total_key = f"total_{member_num}"
        if total_key in form_data:
            performance_fields[total_key] = str(form_data[total_key] or "")
    
    return performance_fields


def generate_3_pdf(form_data, template_dir="pdf_template"):
    """Generate PDF with filled form fields for Review III Sheet."""
    if not form_data:
        raise ValueError("form_data cannot be empty")
        
    group_id = form_data.get('group_id')
    if not group_id:
        raise ValueError("group_id is required")

    # This will raise an error if group_id is not found
    project_info = fetch_project_details(group_id)

     # Determine number of members and appropriate template
    members = project_info.get("members", [])
    num_members = len(members)
    
    if num_members == 0:
        raise ValueError(f"No members found for group_id: {group_id}")
    
    template_path, template_type = determine_template_path(num_members, template_dir)

    # Fixed date formatting logic
    date_value = form_data.get("date")
    if date_value:
        if isinstance(date_value, str):
            try:
                parsed_date = datetime.strptime(date_value, "%Y-%m-%d")
                formatted_date = parsed_date.strftime("%d/%m/%Y")
                print(f"Date formatted from {date_value} to {formatted_date}")  # Debug
            except ValueError as e:
                print(f"Date parsing error: {e}")  # Debug
                formatted_date = date_value
        else:
            # If it's a datetime object
            formatted_date = date_value.strftime("%d/%m/%Y")
            print(f"DateTime object formatted to {formatted_date}")  # Debug
    else:
        formatted_date = ""
        print("No date value provided")  # Debug
    
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

    # Debug: Print what's being set for date field
    print(f"Final date value in field_values: '{field_values['date']}'")
    # Add student information (adaptive to number of members)
    max_members = 5 if template_type == "5_member" else 4
    
    # Add student information
    members = project_info.get('members', [])
    for idx, member in enumerate(members, start=1):
        if idx > max_members:
            break
        
        if isinstance(member, (list, tuple)) and len(member) >= 3:
            field_values[f'roll_{idx}'] = str(member[0] or '')
            field_values[f'student_{idx}'] = str(member[1] or '')
            field_values[f'contact_{idx}'] = str(member[2] or '')

    # Map form responses for Review III questions
    que_to_pdf_field_map = {
        # Section 3.1 questions (ID fields for checkboxes/radio buttons)
        'que_1.1': '3.1.1id', 'que_1.2': '3.1.2id', 'que_1.3': '3.1.3id',
        'que_1.4': '3.1.4id', 'que_1.5': '3.1.5id', 'que_2.1': '3.1.6id',
        'que_2.2': '3.1.7id', 
        'ds1':'3.1.1','ds2':'3.1.2','ds3':'3.1.3','ds4':'3.1.4','ds5':'3.1.5',
        'cd1':'3.2.1','cd2':'3.2.2','cd3':'3.2.3','cd4':'3.2.4','cd5':'3.2.5',
        'f31':'3.3.1','f32':'3.3.2','f33':'3.3.3','f34':'3.3.4','f35':'3.3.5',
        'f41':'3.4.1','f42':'3.4.2','f43':'3.4.3','f44':'3.4.4','f45':'3.4.5',
        'f51':'3.5.1','f52':'3.5.2','f53':'3.5.3','f54':'3.5.4','f55':'3.5.5',
        'f61':'3.6.1','f62':'3.6.2','f63':'3.6.3','f64':'3.6.4','f65':'3.6.5',
        'sum1':'3.7.1','sum2':'3.7.2','sum3':'3.7.3','sum4':'3.7.4','sum5':'3.7.5',
        'f81':'3.8.1','f82':'3.8.2','f83':'3.8.3','f84':'3.8.4','f85':'3.8.5',
       
        # Comments
        'c3': '3.c'
    }
    
        # Add performance evaluation fields
    performance_fields = build_performance_evaluation_fields(form_data, num_members, template_type)
    field_values.update(performance_fields)

    for key, val in form_data.items():
        # Skip date field to prevent overwriting formatted date
        if key == "date":
            continue
            
        val_str = str(val or '')
        pdf_key = que_to_pdf_field_map.get(key, key)
        field_values[pdf_key] = val_str

    # Debug: Check if date field is being overwritten
    print(f"Final field_values before PDF processing:")
    for k, v in field_values.items():
        if 'date' in k.lower():
            print(f"  {k}: '{v}'")

    # Process PDF
    doc = fitz.open(template_path)
    filled_count = process_fields(doc, field_values)

    # Save PDF
    out_dir = "generated_pdfs"
    os.makedirs(out_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"Review_3_{group_id}.pdf"
    output_path = os.path.join(out_dir, output_file)

    doc.save(output_path, garbage=4, deflate=True)
    doc.close()

    if not os.path.isfile(output_path):
        raise IOError(f"PDF generation failed: output file missing: {output_path}")

    logger.info(f"PDF generated: {output_path} with {filled_count} fields filled")
    return output_path

def save_attendance_data(group_id, attendance_data):
    """Save attendance data for Review-III."""
    if not group_id or not attendance_data:
        return
    
    conn = connect_db()
    cursor = conn.cursor()
    
    try:
        for field_name, is_present in attendance_data.items():
            if field_name.startswith('attendance_'):
                roll_no = field_name.replace('attendance_', '')
                attendance_bool = is_present in ['1', 'true', True, 1]
                
                cursor.execute("""
                    UPDATE members 
                    SET review3_attendance = %s 
                    WHERE group_id = %s AND roll_no = %s
                """, (attendance_bool, group_id, roll_no))
        
        conn.commit()
        logger.info(f"Attendance saved for Review-III group {group_id}")
        
    except mysql.connector.Error as e:
        logger.error(f"Error saving attendance (Review-III): {e}")
        raise
    finally:
        cursor.close()
        conn.close()


def fetch_attendance_data(group_id):
    """Fetch Review-III attendance data for a group."""
    conn = connect_db()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT roll_no, student_name, review3_attendance
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
        logger.error(f"Error fetching Review-III attendance: {e}")
        return {}
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    sample_data = {
        'group_id': 'BIA-01',  # Must exist in database
        'date': '2025-08-06',
        
        # Section 3.1 - ID questions (Yes/No/NA for checkboxes)
        'que_3.1.1': 'Y', 'que_3.1.2': 'N', 'que_3.1.3': 'Y',
        'que_3.1.4': 'Y', 'que_3.1.5': 'N', 'que_3.1.6': 'Y', 'que_3.1.7': 'Y',
        
        # Section 3.1 - Marks (numeric values)
        'marks_3.1.1': '8', 'marks_3.1.2': '7', 'marks_3.1.3': '9', 'marks_3.1.4': '8',
        
        # Section 3.2 - Marks
        'marks_3.2.1': '9', 'marks_3.2.2': '8', 'marks_3.2.3': '7',
        
        # Section 3.3 - Marks (0-10 each)
        'que_3.3.1': '8', 'que_3.3.2': '7', 'que_3.3.3': '9', 'que_3.3.4': '8',
        
        # Section 3.4 - Marks (0-10 each)
        'que_3.4.1': '9', 'que_3.4.2': '8', 'que_3.4.3': '7', 'que_3.4.4': '8',
        
        # Section 3.5 - Marks (0-10 each)
        'que_3.5.1': '8', 'que_3.5.2': '9', 'que_3.5.3': '7', 'que_3.5.4': '8',
        
        # Section 3.6 - Marks (0-10 each)
        'que_3.6.1': '7', 'que_3.6.2': '8', 'que_3.6.3': '9', 'que_3.6.4': '8',
        
        # Section 3.7 - Marks (0-10 each)
        'que_3.7.1': '8', 'que_3.7.2': '9', 'que_3.7.3': '7', 'que_3.7.4': '8',
        
        # Section 3.8 - Marks (0-10 each)
        'que_3.8.1': '9', 'que_3.8.2': '8', 'que_3.8.3': '8', 'que_3.8.4': '9',
        
        # Comments
        'comments': 'Excellent final project presentation with comprehensive implementation and good documentation.',
    }

    try:
        pdf_path = generate_3_pdf(sample_data)
        print(f"PDF generated: {pdf_path}")
    except Exception as e:
        print(f"Error: {e}")
