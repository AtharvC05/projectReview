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
            "SELECT roll_no, student_name, contact_details FROM members WHERE group_id=%s ORDER BY roll_no", (group_id,)
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
        "student_count": len(members)
    }

def fetch_review_totals(group_id):
    """Fetch review totals from the responses table for all 4 reviews with dynamic student support."""
    conn = connect_db()
    cursor = conn.cursor()
    
    try:
        # First get student count
        cursor.execute("SELECT COUNT(*) FROM members WHERE group_id = %s", (group_id,))
        student_count = cursor.fetchone()[0]
        
        if student_count == 0:
            raise ValueError(f"No students found for group {group_id}")
        
        cursor.execute("""
            SELECT field_name, field_value
            FROM responses
            WHERE group_id = %s
            AND (
                -- Review 1 totals (field names from review1.html)
                field_name LIKE '1.%.s1' OR
                -- Review 2 totals (field names from review2.html)
                field_name LIKE '2.%.s1' OR
                -- Review 3 totals (field names from review3.html)
                field_name LIKE 'f8%' OR
                -- Review 4 totals (field names from review4.html)
                field_name LIKE 'f4.%.s1'
            )
        """, (group_id,))
        
        rows = cursor.fetchall()
        
        # Initialize dynamic structure
        review_totals = {
            'review1': {},
            'review2': {},
            'review3': {},
            'review4': {}
        }
        
        # Initialize all student positions with 0
        for i in range(1, student_count + 1):
            review_totals['review1'][str(i)] = 0
            review_totals['review2'][str(i)] = 0
            review_totals['review3'][str(i)] = 0
            review_totals['review4'][str(i)] = 0
        
        # Process the rows
        for field_name, field_value in rows:
            try:
                value = float(field_value or 0)
            except (ValueError, TypeError):
                value = 0
                
            # Parse field name to determine review and student
            if field_name.startswith('1.') and field_name.endswith('.s1'):  # Review 1
                student_num = field_name.split('.')[1]
                if student_num in review_totals['review1']:
                    review_totals['review1'][student_num] = value
                    
            elif field_name.startswith('2.') and field_name.endswith('.s1'):  # Review 2
                student_num = field_name.split('.')[1]
                if student_num in review_totals['review2']:
                    review_totals['review2'][student_num] = value
                    
            elif field_name.startswith('f8'):  # Review 3
                # Extract student number from f81, f82, f83, f84, f85 etc
                student_num = field_name[2:]  # Remove 'f8' prefix
                if student_num.isdigit() and student_num in review_totals['review3']:
                    review_totals['review3'][student_num] = value
                    
            elif field_name.startswith('f4.') and field_name.endswith('.s1'):  # Review 4
                student_num = field_name.split('.')[1]
                if student_num in review_totals['review4']:
                    review_totals['review4'][student_num] = value
        
        logger.info(f"Fetched review totals for group {group_id} ({student_count} students): {review_totals}")
        return review_totals
        
    except mysql.connector.Error as e:
        logger.error(f"Database error fetching review totals: {e}")
        raise
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
                    
                elif field_type == 3:  # Button field (not used since no radio buttons)
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

def generate_5_pdf(form_data, template_path=None):
    """Generate PDF with filled form fields for Sheet 5 with dynamic template selection."""
    if not form_data:
        raise ValueError("form_data cannot be empty")
        
    group_id = form_data.get('group_id')
    if not group_id:
        raise ValueError("group_id is required")

    # Fetch project details from database to get student count
    project_info = fetch_project_details(group_id)
    student_count = project_info.get('student_count', 4)
    
    # Dynamic template selection if not provided
    if template_path is None:
        if student_count == 5:
            template_path = "pdf_template/Review-5-Sheet-5.pdf"
        else:
            template_path = "pdf_template/Review-5-Sheet.pdf"  # Default for 4 or fewer students
    
    logger.info(f"Using template: {template_path} for {student_count} students")

    if not os.path.isfile(template_path):
        raise FileNotFoundError(f"PDF template not found: {template_path}")

    # Fetch review totals from database
    review_totals = fetch_review_totals(group_id)

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
        # Use current date if no date provided, but format it properly
        formatted_date = datetime.now().strftime("%d/%m/%Y")
        print(f"Using current date: {formatted_date}")  # Debug
    
    # Build field values dictionary with all the placeholders
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

    # Add student information dynamically based on actual student count
    members = project_info.get('members', [])
    for idx, member in enumerate(members, start=1):
        if isinstance(member, (list, tuple)) and len(member) >= 2:
            field_values[f'roll_{idx}'] = str(member[0] or '')
            field_values[f'student_{idx}'] = str(member[1] or '')

    # Add review scores from database to PDF fields dynamically
    for student_num in range(1, student_count + 1):
        student_key = str(student_num)
        
        # Review I scores (PDF fields 1.1, 1.2, 1.3, 1.4, 1.5)
        field_values[f'1.{student_num}'] = str(review_totals['review1'].get(student_key, 0))
        
        # Review II scores (PDF fields 2.1, 2.2, 2.3, 2.4, 2.5)
        field_values[f'2.{student_num}'] = str(review_totals['review2'].get(student_key, 0))
        
        # Review III scores (PDF fields 3.1, 3.2, 3.3, 3.4, 3.5)
        field_values[f'3.{student_num}'] = str(review_totals['review3'].get(student_key, 0))
        
        # Review IV scores (PDF fields 4.1, 4.2, 4.3, 4.4, 4.5)
        field_values[f'4.{student_num}'] = str(review_totals['review4'].get(student_key, 0))
    
    # Calculate and add final totals dynamically (PDF fields 5.1, 5.2, 5.3, 5.4, 5.5)
    for i in range(1, student_count + 1):
        student_key = str(i)
        total = (review_totals['review1'].get(student_key, 0) + 
                review_totals['review2'].get(student_key, 0) + 
                review_totals['review3'].get(student_key, 0) + 
                review_totals['review4'].get(student_key, 0))
        field_values[f'5.{i}'] = str(total)
    
    # Add final comments from form data
    field_values['5.c'] = str(form_data.get('c5', ''))

    # Debug: Check final field values
    print(f"Final field_values before PDF processing:")
    for k, v in field_values.items():
        if 'date' in k.lower():
            print(f"  {k}: '{v}'")

    logger.info(f"Field values for PDF generation: {field_values}")

    # Process PDF
    doc = fitz.open(template_path)
    filled_count = process_fields(doc, field_values)

    # Save PDF
    out_dir = "generated_pdfs"
    os.makedirs(out_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"Sheet5_{group_id}_{student_count}students.pdf"
    output_path = os.path.join(out_dir, output_file)

    doc.save(output_path, garbage=4, deflate=True)
    doc.close()

    if not os.path.isfile(output_path):
        raise IOError(f"PDF generation failed: output file missing: {output_path}")

    logger.info(f"PDF generated: {output_path} with {filled_count} fields filled for {student_count} students")
    return output_path

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Test with minimal data - most data will come from database
    sample_data = {
        'group_id': 'BIA-01',  # Must exist in database
        'c5': 'All students have performed consistently well across all review phases. The project demonstrates strong technical implementation and good presentation skills.',
    }

    try:
        pdf_path = generate_5_pdf(sample_data)
        print(f"PDF generated: {pdf_path}")
    except Exception as e:
        print(f"Error: {e}")