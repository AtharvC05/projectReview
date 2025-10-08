import fitz  # PyMuPDF
import os
import mysql.connector
import logging
from datetime import datetime
from backend.db import connect_db

logger = logging.getLogger(__name__)

def _db():
    """Shared DB connection for this sheet (default via env)."""
    return connect_db()

def fetch_project_details(group_id):
    """Fetch project and members info from DB; raise error if not found."""
    conn = _db()
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
        
        # Format contact details to remove .0
        formatted_members = []
        for member in members:
            roll_no, student_name, contact = member
            # Remove .0 from contact if it's a number
            if isinstance(contact, (int, float)):
                contact = str(int(contact))
            elif contact:
                contact = str(contact).replace('.0', '')
            else:
                contact = ""
            formatted_members.append((roll_no, student_name, contact))
        
        members = formatted_members
        
    except mysql.connector.Error as e:
        logger.error(f"Database error: {e}")
        raise
    finally:
        cursor.close()
        conn.close()

    # Format mentor mobile if it exists
    mentor_mobile = project.get("mentor_mobile", "")
    if isinstance(mentor_mobile, (int, float)):
        mentor_mobile = str(int(mentor_mobile))
    elif mentor_mobile:
        mentor_mobile = str(mentor_mobile).replace('.0', '')

    return {
        "group_id": project.get("group_id", group_id),
        "project_title": project.get("project_title", ""),
        "guide_name": project.get("guide_name", ""),
        "mentor_name": project.get("mentor_name", ""),
        "mentor_email": project.get("mentor_email", ""),
        "mentor_mobile": mentor_mobile,
        "r1_name": project.get("evaluator1_name", ""),
        "r2_name": project.get("evaluator2_name", ""), 
        "members": members,
    }

def determine_template_path(num_members, base_template_dir="pdf_template"):
    """Determine which template to use based on number of members."""
    if num_members <= 4:
        template_path = os.path.join(base_template_dir, "Review-II-Sheet.pdf")
        template_type = "4_member"
    elif num_members == 5:
        template_path = os.path.join(base_template_dir, "Review-II-Sheet-5.pdf")
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
        
        # Try both methods for compatibility with different PyMuPDF versions
        try:
            wgets = list(page.widgets())  # Newer versions (1.18+)
        except AttributeError:
            try:
                # Fallback for older versions
                wgets = []
                for annot in page.annots():
                    if annot.type[0] == fitz.PDF_ANNOT_WIDGET:
                        wgets.append(annot)
            except Exception as e:
                logger.warning(f"Could not access form fields on page {page_num}: {e}")
                continue
        
        if not wgets:
            logger.warning(f"No form fields found on page {page_num}")
            continue
        
        for wget in wgets:
            field_name = getattr(wget, "field_name", None)
            if not field_name:
                continue

            # Make transparent
            try:
                wget.border_width = 0
                wget.fill_color = None
                wget.border_color = None
            except:
                pass
            
            val = data.get(field_name, "")
            val = "" if val is None else str(val)

            if val.strip():
                field_type = getattr(wget, 'field_type', 0)
                
                if field_type == fitz.PDF_WIDGET_TYPE_TEXT:  # Text field
                    wget.field_value = val.strip()
                    filled_count += 1
                    
                elif field_type in (fitz.PDF_WIDGET_TYPE_CHECKBOX, fitz.PDF_WIDGET_TYPE_RADIOBUTTON):
                    try:
                        val_upper = val.strip().upper()
                        if val_upper in ("Y", "YES", "TRUE", "1"):
                            wget.field_value = True
                        elif val_upper in ("N", "NO", "FALSE", "0"):
                            wget.field_value = False
                        else:
                            wget.field_value = val.strip()
                        filled_count += 1
                    except:
                        wget.field_value = val.strip()
                        filled_count += 1
                else:
                    # Unknown field type - try as text
                    try:
                        wget.field_value = val.strip()
                        filled_count += 1
                    except:
                        pass

            # Make read-only
            try:
                wget.field_flags |= fitz.PDF_FIELD_IS_READ_ONLY
            except:
                pass
                
            try:
                wget.update()
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
                field_name = f"{criteria_key}_{member_num}"
            else:  # 5_member template
                field_name = f"{criteria_key}_{member_num}"
            
            if form_key in form_data:
                performance_fields[field_name] = str(form_data[form_key] or "")
    
    # Add total fields for each member
    for member_num in range(1, min(num_members + 1, 6)):
        total_key = f"total_{member_num}"
        if total_key in form_data:
            performance_fields[total_key] = str(form_data[total_key] or "")
    
    return performance_fields

def generate_2_pdf(form_data, base_template_dir="pdf_template"):
    """Generate PDF with filled form fields for Review II Sheet - adaptive to 4 or 5 members."""
    if not form_data:
        raise ValueError("form_data cannot be empty")
        
    group_id = form_data.get("group_id")
    if not group_id:
        raise ValueError("group_id is required")

    # This will raise an error if group_id is not found
    project_info = fetch_project_details(group_id)
    
    # Determine number of members and appropriate template
    members = project_info.get("members", [])
    num_members = len(members)
    
    if num_members == 0:
        raise ValueError(f"No members found for group_id: {group_id}")
    
    template_path, template_type = determine_template_path(num_members, base_template_dir)

    # Fixed date formatting logic
    date_value = form_data.get("date")
    if date_value:
        if isinstance(date_value, str):
            try:
                parsed_date = datetime.strptime(date_value, "%Y-%m-%d")
                formatted_date = parsed_date.strftime("%d/%m/%Y")
                logger.debug(f"Date formatted from {date_value} to {formatted_date}")
            except ValueError as e:
                logger.debug(f"Date parsing error: {e}")
                formatted_date = date_value
        else:
            # If it's a datetime object
            formatted_date = date_value.strftime("%d/%m/%Y")
            logger.debug(f"DateTime object formatted to {formatted_date}")
    else:
        formatted_date = ""
        logger.debug("No date value provided")
    
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

    logger.debug(f"Final date value in field_values: '{field_values['date']}'")

    # Add student information (adaptive to number of members)
    max_members = 5 if template_type == "5_member" else 4
    
    for x, member in enumerate(members, start=1):
        if x > max_members:
            logger.warning(f"Member {x} skipped - template supports max {max_members} members")
            break
        
        if isinstance(member, (list, tuple)) and len(member) >= 3:
            field_values[f"roll_{x}"] = str(member[0] or "")
            field_values[f"student_{x}"] = str(member[1] or "")
            field_values[f"contact_{x}"] = str(member[2] or "")

    # Map form responses for Review II questions
    que_to_pdf_field_map = {
        # Section 2.1 questions ( fields for checkboxes/radio buttons)
        'que_2.1.1': '2.1.1id', 'que_2.1.2': '2.1.2id', 'que_2.1.3': '2.1.3id',
        'que_2.1.4': '2.1.4id', 'que_2.1.5': '2.1.5id', 'que_2.1.6': '2.1.6id',
        'que_2.1.7': '2.1.7id', 'que_2.1.8': '2.1.8id', 'que_2.1.9': '2.1.9id',
        'que_2.1.10': '2.1.10id', 'que_2.1.11': '2.1.11id', 'que_2.1.12': 'q2.1.12id',
        'que_2.1.13': '2.1.13id', 'que_2.1.14': '2.1.14id', 'que_2.1.15': '2.1.15id',
        'que_2.1.16': '2.1.16id',
        
        # Summary fields
        'sum_2.1': 'que_2.1.s1', 'sum_2.2': '2.2.s1', 'sum_2.3': '2.3.s1', 'sum_2.4': '2.4.s1',
        
        # Comments
        'c2': '2.c',
        'comments': '2.c',  # Alternative key for comments
    }
    # Add performance evaluation fields
    performance_fields = build_performance_evaluation_fields(form_data, num_members, template_type)
    field_values.update(performance_fields)
    
    # Map general form responses
    for key, val in form_data.items():
        if key == "date":
            continue
            
        val_str = str(val or "")
        pdf_key = que_to_pdf_field_map.get(key, key)
        
        if pdf_key not in field_values or not field_values[pdf_key]:
            field_values[pdf_key] = val_str

    logger.debug(f"Using template: {template_path}")
    logger.debug(f"Template type: {template_type}")
    logger.debug(f"Number of members: {num_members}")

    # Process PDF
    doc = fitz.open(template_path)
    filled_count = process_fields(doc, field_values)

    # Save PDF
    out_dir = "generated_pdfs"
    os.makedirs(out_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"Review_2_{group_id}_{template_type}.pdf"
    output_path = os.path.join(out_dir, output_file)

    doc.save(output_path, garbage=4, deflate=True)
    doc.close()

    if not os.path.isfile(output_path):
        raise IOError(f"PDF generation failed: output file missing: {output_path}")

    logger.info(f"PDF generated: {output_path} with {filled_count} fields filled using {template_type} template")
    return output_path

def save_attendance_data(group_id, attendance_data):
    """Save attendance data to database."""
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
                    SET review2_attendance = %s 
                    WHERE group_id = %s AND roll_no = %s
                """, (attendance_bool, group_id, roll_no))
        
        conn.commit()
        logger.info(f"Attendance saved for group {group_id}")
        
    except mysql.connector.Error as e:
        logger.error(f"Error saving attendance: {e}")
        raise
    finally:
        cursor.close()
        conn.close()

def fetch_attendance_data(group_id):
    """Fetch attendance data for a group."""
    conn = connect_db()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT roll_no, student_name, review2_attendance
            FROM members 
            WHERE group_id = %s
            ORDER BY roll_no
        """, (group_id,))
        
        results = cursor.fetchall()
        attendance_data = {}
        
        for roll_no, student_name, is_present in results:
            # Format roll_no to remove .0 if it's numeric
            if isinstance(roll_no, (int, float)):
                roll_no = str(int(roll_no))
            else:
                roll_no = str(roll_no).replace('.0', '')
            
            attendance_data[f"attendance_{roll_no}"] = "1" if is_present else "0"
            
        return attendance_data
        
    except mysql.connector.Error as e:
        logger.error(f"Error fetching attendance: {e}")
        return {}
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    sample_data_4_members = {
        "group_id": "BIA-01",
        "date": "2025-08-06",
        "que_2.1.1": "Y", "que_2.1.2": "N", "que_2.1.3": "Y",
        "que_2.1.4": "Y", "que_2.1.5": "N", "que_2.1.6": "Y",
        "que_2.1.7": "Y", "que_2.1.8": "N", "que_2.1.9": "Y",
        "que_2.1.10": "Y", "que_2.1.11": "N", "que_2.1.12": "Y",
        "que_2.1.13": "Y", "que_2.1.14": "N", "que_2.1.15": "Y",
        "que_2.1.16": "Y",
        "que_2.2.1": "8", "que_2.2.2": "7", "que_2.2.3": "9",
        "que_2.2.4": "8", "que_2.2.5": "7", "que_2.2.6": "8",
        "que_2.2.7": "9", "que_2.2.8": "8",
        "sum_2.1": "15", "sum_2.2": "64", "sum_2.3": "63", "sum_2.4": "64",
        "comments": "Excellent progress in Review II."
    }

    try:
        print("Testing PDF generation...")
        pdf_path = generate_2_pdf(sample_data_4_members)
        print(f"PDF generated: {pdf_path}")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()