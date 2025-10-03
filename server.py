#change

from flask import Flask, render_template, redirect, request, jsonify, send_file, abort
from flask_cors import CORS
import os
import threading
import functools
import logging
import pandas as pd
import json
from datetime import datetime
import io
# Import blueprints only
import backend.data_manager as data_manager
import backend.scheduler as scheduler


app = Flask(__name__)
# Enhanced CORS configuration for device access
CORS(app, resources={
    r"/*": {
        "origins": "*",
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization", "Accept", "Origin", "X-Requested-With"],
        "supports_credentials": True
    }
})

# Add security headers for better device compatibility
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization,Accept,Origin,X-Requested-With')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    response.headers.add('Access-Control-Allow-Credentials', 'true')
    # Add headers for file download compatibility
    response.headers.add('Access-Control-Expose-Headers', 'Content-Disposition,Content-Length,Content-Type')
    return response

logging.basicConfig(level=logging.WARNING)  # Reduced logging level
logger = logging.getLogger(__name__)

# Register blueprints
app.register_blueprint(data_manager.bp)
app.register_blueprint(scheduler.bp)
app.secret_key = os.environ.get('SECRET_KEY', 'your-secret-key-change-this-in-production-2024')

# Import database functions
try:
    from backend.sheet1 import fetch_project_details, connect_db
    DATABASE_AVAILABLE = True
except ImportError:
    DATABASE_AVAILABLE = False

# Import PDF generation functions
try:
    from backend.sheet1 import generate_fillable_pdf as generate_review1_pdf
except ImportError:
    generate_review1_pdf = None

try:
    from backend.sheet2 import generate_2_pdf as generate_review2_pdf
except ImportError:
    generate_review2_pdf = None

try:
    from backend.sheet3 import generate_3_pdf as generate_review3_pdf
except ImportError:
    generate_review3_pdf = None

try:
    from backend.sheet4 import generate_review4_pdf
except ImportError:
    generate_review4_pdf = None

try:
    from backend.sheet5 import generate_5_pdf as generate_review5_pdf, fetch_review_totals as sheet5_fetch_review_totals
except ImportError:
    generate_review5_pdf = None
    sheet5_fetch_review_totals = None

# Define fetch_review_totals function with dynamic student support
def fetch_review_totals(group_id):
    """Fetch review totals from database for a given group_id with dynamic student support."""
    if not DATABASE_AVAILABLE:
        raise Exception("Database not available")
    
    conn = connect_db()
    cursor = conn.cursor()
    
    try:
        # First, get the actual number of students for this group
        cursor.execute("SELECT COUNT(*) FROM members WHERE group_id = %s", (group_id,))
        student_count = cursor.fetchone()[0]
        
        if student_count == 0:
            raise ValueError(f"No students found for group {group_id}")
        
        # Query to get total scores for each review for each student
        query = """
        SELECT 
            r.field_name, 
            r.field_value
        FROM responses r
        WHERE r.group_id = %s 
        AND (
            r.field_name LIKE '1.%.s1' OR  -- Review 1 totals
            r.field_name LIKE '2.%.s1' OR  -- Review 2 totals  
            r.field_name LIKE '3.%.s1' OR  -- Review 3 totals
            r.field_name LIKE 'f4.%.s1'    -- Review 4 totals
        )
        ORDER BY r.field_name
        """
        
        cursor.execute(query, (group_id,))
        rows = cursor.fetchall()
        
        # Initialize review totals structure with dynamic student count
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
        
        for field_name, field_value in rows:
            try:
                value = float(field_value) if field_value else 0
            except (ValueError, TypeError):
                value = 0
                
            # Parse field name to determine review and student
            if field_name.startswith('1.'):  # Review 1
                student_num = field_name.split('.')[1]
                if student_num in review_totals['review1']:
                    review_totals['review1'][student_num] = value
                    
            elif field_name.startswith('2.'):  # Review 2
                student_num = field_name.split('.')[1]
                if student_num in review_totals['review2']:
                    review_totals['review2'][student_num] = value
                    
            elif field_name.startswith('3.'):  # Review 3
                student_num = field_name.split('.')[1]
                if student_num in review_totals['review3']:
                    review_totals['review3'][student_num] = value
                    
            elif field_name.startswith('f4.'):  # Review 4
                student_num = field_name.split('.')[1]
                if student_num in review_totals['review4']:
                    review_totals['review4'][student_num] = value
        
        return review_totals
        
    except Exception as e:
        logger.error(f"Error fetching review totals: {e}")
        raise
    finally:
        cursor.close()
        conn.close()

class SafeThread(threading.Thread):
    def __init__(self, target, args=(), kwargs=None):
        super().__init__(target=target, args=args, kwargs=kwargs or {})
        self.result = None
        self.exception = None
    
    def run(self):
        try:
            self.result = self._target(*self._args, **self._kwargs)
        except Exception as e:
            self.exception = e

# ================== MAIN ROUTES ==================
import socket

def get_local_ip():
    """Get the local IP address of the machine"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except Exception:
        return "127.0.0.1"

@app.route('/')
def index():
    # For testing, serve attendance dashboard as base page
    return render_template('review-1.html')

@app.route('/reviews')
def reviews_home():
    return render_template('review-1.html')

@app.route('/review<int:review_num>')
def review_page(review_num):
    if 1 <= review_num <= 5:
        return render_template(f'review-{review_num}.html')
    return redirect("/")

@app.route('/data-manager')
def data_manager_page():
    return render_template('data-manager.html')

# Add this route after your existing auth routes
@app.route('/register')
def register_page():
    """Serve the registration page for new users"""
    return render_template(('register.html'))


# ================== ATTENDANCE DASHBOARD ROUTES ==================

@app.route('/attendance-dashboard')
def attendance_dashboard():
    """Serve the attendance dashboard page"""
    return render_template('attendance-dashboard.html')

# ================== API ROUTES ==================

@app.route('/api/project-details')
def api_project_details():
    group_id = request.args.get('group_id')
    if not group_id:
        return jsonify({"error": "group_id is required"}), 400
    
    try:
        if DATABASE_AVAILABLE:
            project_details = fetch_project_details(group_id)
            return jsonify(project_details)
        else:
            return jsonify({"error": "Database not available"}), 501
    except ValueError as e:
        # Handle case where group_id doesn't exist
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        logger.error(f"Project details error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/group-students')
def api_group_students():
    """Fetch students for a given group_id from members table"""
    group_id = request.args.get('group_id')
    if not group_id:
        return jsonify({"error": "group_id is required"}), 400
    
    if not DATABASE_AVAILABLE:
        return jsonify({"error": "Database not available"}), 501
    
    try:
        conn = connect_db()
        cursor = conn.cursor()
        
        # Check if group exists in projects table first
        cursor.execute("SELECT COUNT(*) FROM projects WHERE group_id = %s", (group_id,))
        if cursor.fetchone()[0] == 0:
            cursor.close()
            conn.close()
            return jsonify({"error": f"Group {group_id} not found"}), 404
        
        # Fetch students from members table
        cursor.execute("""
            SELECT roll_no, student_name, contact_details 
            FROM members 
            WHERE group_id = %s 
            ORDER BY roll_no
        """, (group_id,))
        
        students = cursor.fetchall()
        cursor.close()
        conn.close()
        
        if not students:
            return jsonify({"error": f"No students found for group {group_id}"}), 404
        
        student_list = []
        for student in students:
            student_list.append({
                'roll_no': student[0],
                'student_name': student[1],
                'contact_details': student[2]
            })
        
        return jsonify({
            'students': student_list,
            'count': len(student_list)
        })
        
    except Exception as e:
        logger.error(f"Fetch group students error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/review-totals')
def api_review_totals():
    """Fetch review totals from database for a given group_id."""
    group_id = request.args.get('group_id')
    if not group_id:
        return jsonify({"error": "group_id is required"}), 400
    
    if not DATABASE_AVAILABLE:
        return jsonify({"error": "Database not available"}), 501
        
    try:
        review_totals = fetch_review_totals(group_id)
        return jsonify({
            "group_id": group_id,
            "review_totals": review_totals
        }), 200
    except Exception as e:
        logger.error(f"Fetch review totals error: {e}")
        return jsonify({"error": str(e)}), 500

# ================== ATTENDANCE API ROUTES ==================

@app.route('/api/attendance', methods=['GET'])
def api_get_all_attendance():
    """Fetch attendance data for all students across all reviews"""
    if not DATABASE_AVAILABLE:
        return jsonify({"error": "Database not available"}), 501
    
    try:
        conn = connect_db()
        cursor = conn.cursor()
        
        # Fetch all members with their group_id and attendance across all reviews
        query = """
            SELECT 
                group_id,
                roll_no, 
                student_name,
                review1_attendance,
                review2_attendance, 
                review3_attendance,
                review4_attendance
            FROM members 
            ORDER BY group_id, roll_no
        """
        cursor.execute(query)
        members = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        attendance_data = []
        for group_id, roll_no, name, r1, r2, r3, r4 in members:
            attendance_data.append({
                'group_id': group_id,
                'roll_no': roll_no,
                'student_name': name,
                'review1_attendance': bool(r1) if r1 is not None else False,
                'review2_attendance': bool(r2) if r2 is not None else False,
                'review3_attendance': bool(r3) if r3 is not None else False,
                'review4_attendance': bool(r4) if r4 is not None else False
            })
        
        return jsonify(attendance_data), 200
        
    except Exception as e:
        logger.error(f"Fetch attendance error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/groups', methods=['GET'])
def api_get_all_groups():
    """Fetch all groups with their members and attendance data"""
    if not DATABASE_AVAILABLE:
        return jsonify({"error": "Database not available"}), 501
    
    try:
        conn = connect_db()
        cursor = conn.cursor()
        
        # Fetch all groups and their members
        query = """
            SELECT 
                group_id,
                roll_no, 
                student_name,
                review1_attendance,
                review2_attendance, 
                review3_attendance,
                review4_attendance
            FROM members 
            ORDER BY group_id, roll_no
        """
        cursor.execute(query)
        members = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        # Group data by group_id
        groups_data = {}
        for group_id, roll_no, name, r1, r2, r3, r4 in members:
            if group_id not in groups_data:
                groups_data[group_id] = {
                    'group_id': group_id,
                    'members': []
                }
            
            groups_data[group_id]['members'].append({
                'roll_no': roll_no,
                'student_name': name,
                'review1_attendance': bool(r1) if r1 is not None else False,
                'review2_attendance': bool(r2) if r2 is not None else False,
                'review3_attendance': bool(r3) if r3 is not None else False,
                'review4_attendance': bool(r4) if r4 is not None else False
            })
        
        # Convert to list format
        groups_list = list(groups_data.values())
        
        return jsonify(groups_list), 200
        
    except Exception as e:
        logger.error(f"Fetch groups error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/group/<group_id>/attendance', methods=['GET'])
def api_get_group_attendance(group_id):
    """Fetch attendance data for a specific group"""
    if not DATABASE_AVAILABLE:
        return jsonify({"error": "Database not available"}), 501
    
    try:
        conn = connect_db()
        cursor = conn.cursor()
        
        # Check if group exists
        cursor.execute("SELECT COUNT(*) FROM members WHERE group_id = %s", (group_id,))
        if cursor.fetchone()[0] == 0:
            cursor.close()
            conn.close()
            return jsonify({"error": f"Group {group_id} not found"}), 404
        
        # Fetch group members with attendance
        query = """
            SELECT 
                group_id,
                roll_no, 
                student_name,
                review1_attendance,
                review2_attendance, 
                review3_attendance,
                review4_attendance
            FROM members 
            WHERE group_id = %s
            ORDER BY roll_no
        """
        cursor.execute(query, (group_id,))
        members = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        group_data = {
            'group_id': group_id,
            'members': []
        }
        
        for group_id_db, roll_no, name, r1, r2, r3, r4 in members:
            group_data['members'].append({
                'roll_no': roll_no,
                'student_name': name,
                'review1_attendance': bool(r1) if r1 is not None else False,
                'review2_attendance': bool(r2) if r2 is not None else False,
                'review3_attendance': bool(r3) if r3 is not None else False,
                'review4_attendance': bool(r4) if r4 is not None else False
            })
        
        return jsonify(group_data), 200
        
    except Exception as e:
        logger.error(f"Fetch group attendance error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/attendance/pdf', methods=['GET', 'OPTIONS'])
def generate_attendance_pdf():
    """Generate PDF report for attendance data"""
    if request.method == 'OPTIONS':
        return '', 200
        
    if not DATABASE_AVAILABLE:
        return jsonify({"error": "Database not available"}), 501
    
    try:
        import io
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import letter, A4
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        
        # Fetch attendance data
        conn = connect_db()
        cursor = conn.cursor()
        
        query = """
            SELECT 
                group_id,
                roll_no, 
                student_name,
                review1_attendance,
                review2_attendance, 
                review3_attendance,
                review4_attendance
            FROM members 
            ORDER BY group_id
        """
        cursor.execute(query)
        members = cursor.fetchall()
        cursor.close()
        conn.close()
        
        # Create PDF
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=18)
        
        # Styles
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            spaceAfter=30,
            alignment=1  # Center alignment
        )
        
        # Build PDF content
        story = []
        
        # Title
        title = Paragraph("Student Attendance Report", title_style)
        story.append(title)
        story.append(Spacer(1, 20))
        
        # Create table data
        table_data = [['Group ID', 'Roll No', 'Student Name', 'Review 1', 'Review 2', 'Review 3', 'Review 4']]
        
        for group_id, roll_no, name, r1, r2, r3, r4 in members:
            table_data.append([
                str(group_id),
                str(roll_no),
                name,
                'P' if r1 else 'A',
                'P' if r2 else 'A', 
                'P' if r3 else 'A',
                'P' if r4 else 'A'
            ])
        
        # Create table
        table = Table(table_data, colWidths=[0.8*inch, 0.8*inch, 2*inch, 0.8*inch, 0.8*inch, 0.8*inch, 0.8*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(table)
        
        # Add generation timestamp
        story.append(Spacer(1, 20))
        timestamp = Paragraph(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", styles['Normal'])
        story.append(timestamp)
        
        # Build PDF
        doc.build(story)
        buffer.seek(0)
        
        # Create unique filename
        timestamp_str = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"Attendance_Report_{timestamp_str}.pdf"
        
        response = send_file(
            io.BytesIO(buffer.read()),
            as_attachment=True,
            download_name=filename,
            mimetype='application/pdf'
        )
        
        # Add headers for device compatibility
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        
        return response
        
    except ImportError:
        return jsonify({"error": "ReportLab library not installed. Install with: pip install reportlab"}), 501
    except Exception as e:
        logger.error(f"Generate attendance PDF error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/attendance/<group_id>/<review_num>', methods=['GET'])
def get_attendance(group_id, review_num):
    """Fetch member attendance data for a specific review"""
    if not DATABASE_AVAILABLE:
        return jsonify({"error": "Database not available"}), 501
    
    try:
        # Validate review number
        review_num_int = int(review_num)
        if not (1 <= review_num_int <= 5):
            return jsonify({"error": "Invalid review number. Must be 1-5"}), 400
    except ValueError:
        return jsonify({"error": "Review number must be an integer"}), 400
    
    try:
        conn = connect_db()
        cursor = conn.cursor()
        
        # Check if group exists first
        cursor.execute("SELECT COUNT(*) FROM members WHERE group_id = %s", (group_id,))
        if cursor.fetchone()[0] == 0:
            cursor.close()
            conn.close()
            return jsonify({"error": f"Group {group_id} not found"}), 404
        
        # Fetch members with their attendance status for the specific review
        query = f"""
            SELECT roll_no, student_name, review{review_num}_attendance 
            FROM members 
            WHERE group_id = %s 
        """
        cursor.execute(query, (group_id,))
        members = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        attendance_data = []
        for roll_no, name, attendance in members:
            attendance_data.append({
                'roll_no': roll_no,
                'name': name,
                'present': bool(attendance) if attendance is not None else False
            })
        
        return jsonify({
            "group_id": group_id,
            "review": review_num,
            "members": attendance_data
        }), 200
        
    except Exception as e:
        logger.error(f"Fetch attendance error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/attendance', methods=['POST'])
def save_attendance():
    """Save attendance data for a specific review"""
    if not DATABASE_AVAILABLE:
        return jsonify({"error": "Database not available"}), 501
    
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid JSON data"}), 400
    
    group_id = data.get('group_id')
    review_num = data.get('review_num') 
    attendance_data = data.get('attendance', {})
    
    if not all([group_id, review_num is not None, attendance_data]):
        return jsonify({"error": "Missing required fields: group_id, review_num, attendance"}), 400
    
    # Validate review number
    try:
        review_num = int(review_num)
        if not (1 <= review_num <= 5):
            return jsonify({"error": "Invalid review number. Must be 1-5"}), 400
    except ValueError:
        return jsonify({"error": "Review number must be an integer"}), 400
    
    try:
        conn = connect_db()
        cursor = conn.cursor()
        
        # Check if group exists
        cursor.execute("SELECT COUNT(*) FROM members WHERE group_id = %s", (group_id,))
        if cursor.fetchone()[0] == 0:
            cursor.close()
            conn.close()
            return jsonify({"error": f"Group {group_id} not found"}), 404
        
        # Update attendance for each member
        updated_count = 0
        for roll_no, present in attendance_data.items():
            update_query = f"""
                UPDATE members 
                SET review{review_num}_attendance = %s 
                WHERE group_id = %s AND roll_no = %s
            """
            cursor.execute(update_query, (bool(present), group_id, roll_no))
            if cursor.rowcount > 0:
                updated_count += 1
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({
            "status": "success",
            "message": f"Attendance saved for review {review_num}",
            "updated_members": updated_count
        }), 200
        
    except Exception as e:
        logger.error(f"Save attendance error: {e}")
        return jsonify({"error": str(e)}), 500

# ================== PDF GENERATION ==================

def handle_pdf_generation(generate_function):
    if request.method == 'OPTIONS':
        return '', 200

    try:
        data = request.get_json()
        if not data or not isinstance(data, dict):
            return jsonify({"error": "Invalid JSON data"}), 400

        group_id = data.get('group_id')
        if not group_id:
            return jsonify({"error": "Group ID is required"}), 400

        if generate_function == generate_review1_pdf:
            template_path = data.get('template_path', 'pdf_template/')
            thread = SafeThread(target=generate_function, args=(data, template_path))
        else:
            thread = SafeThread(target=generate_function, args=(data,))
        
        thread.start()
        thread.join()

        if thread.exception:
            return jsonify({"error": f"PDF generation failed: {str(thread.exception)}"}), 500

        if not thread.result or not os.path.exists(thread.result):
            return jsonify({"error": "PDF generation failed - no output file"}), 500

        return send_file(
            thread.result,
            as_attachment=True,
            download_name=os.path.basename(thread.result),
            mimetype='application/pdf'
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ================== PDF ROUTES ==================

pdf_functions = {
    1: generate_review1_pdf,
    2: generate_review2_pdf,
    3: generate_review3_pdf,
    4: generate_review4_pdf,
    5: generate_review5_pdf
}

for i in range(1, 6):
    pdf_function = pdf_functions.get(i)
    if pdf_function:
        app.add_url_rule(
            f'/generate-pdf-review{i}',
            f'generate_review{i}',
            functools.partial(handle_pdf_generation, pdf_function),
            methods=['POST', 'OPTIONS']
        )

@app.route('/api/export-excel-test', methods=['POST'])
def export_excel_test():
    try:
        import pandas as pd
        import io
        from datetime import datetime
        
        data = request.get_json()
        print(f"Received data: {data}")
        
        if not data or 'data' not in data:
            return jsonify({'error': 'No data provided'}), 400

        df = pd.DataFrame(data['data'])
        print(f"Created DataFrame with {len(df)} rows")
        
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, sheet_name='Project Data', index=False)
        
        output.seek(0)
        return send_file(
            output,
            as_attachment=True,
            download_name=f'test_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx',
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        
    except Exception as e:
        print(f"Export error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

# ================== RESPONSE STORAGE ROUTES ==================

@app.route('/api/save-response', methods=['POST'])
def api_save_response():
    """Save evaluator responses for a group_id."""
    if not DATABASE_AVAILABLE:
        return jsonify({"error": "Database not available"}), 501

    data = request.get_json()
    if not data or not isinstance(data, dict):
        return jsonify({"error": "Invalid JSON data"}), 400

    group_id = data.get("group_id")
    if not group_id:
        return jsonify({"error": "group_id is required"}), 400

    try:
        conn = connect_db()
        cursor = conn.cursor()

        # Use your existing table structure
        saved_count = 0
        for field_name, field_value in data.items():
            if field_name == "group_id":
                continue
                
            cursor.execute("""
                INSERT INTO responses (group_id, field_name, field_value)
                VALUES (%s, %s, %s)
                ON DUPLICATE KEY UPDATE field_value = VALUES(field_value)
            """, (group_id, field_name, str(field_value)))
            saved_count += 1

        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({
            "status": "success", 
            "message": f"Saved {saved_count} responses for group {group_id}"
        }), 200
    except Exception as e:
        logger.error(f"Save response error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/fetch-response/<group_id>', methods=['GET'])
def api_fetch_response(group_id):
    """Fetch evaluator responses for given group_id."""
    if not DATABASE_AVAILABLE:
        return jsonify({"error": "Database not available"}), 501

    try:
        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT field_name, field_value
            FROM responses
            WHERE group_id = %s
        """, (group_id,))
        rows = cursor.fetchall()
        cursor.close()
        conn.close()

        response_data = {field_name: field_value for field_name, field_value in rows}
        return jsonify({
            "group_id": group_id, 
            "responses": response_data
        }), 200

    except Exception as e:
        logger.error(f"Fetch response error: {e}")
        return jsonify({"error": str(e)}), 500

# ================== PDF VIEWER ROUTES ==================

@app.route("/pdf_viewer")
def pdf_viewer():
    """Serve the PDF viewer webpage."""
    return render_template('pdf_viewer.html')

@app.route("/list-pdfs")
def list_pdfs():
    """API endpoint to list all PDF files in generated_pdfs folder."""
    try:
        pdf_dir = "generated_pdfs"
        
        # Check if directory exists
        if not os.path.exists(pdf_dir):
            os.makedirs(pdf_dir, exist_ok=True)
            return jsonify({
                "success": True,
                "pdfs": [],
                "stats": {"count": 0, "totalSize": 0}
            })
        
        pdf_files = []
        total_size = 0
        
        # Get all PDF files
        for filename in os.listdir(pdf_dir):
            if filename.lower().endswith('.pdf'):
                file_path = os.path.join(pdf_dir, filename)
                
                # Get file stats
                stat = os.stat(file_path)
                file_size = stat.st_size
                modified_time = datetime.fromtimestamp(stat.st_mtime).isoformat()
                
                pdf_files.append({
                    "name": filename,
                    "size": file_size,
                    "modified": modified_time,
                    "path": file_path
                })
                
                total_size += file_size
        
        # Sort by modification time (newest first)
        pdf_files.sort(key=lambda x: x['modified'], reverse=True)
        
        return jsonify({
            "success": True,
            "pdfs": pdf_files,
            "stats": {
                "count": len(pdf_files),
                "totalSize": total_size
            }
        })
        
    except Exception as e:
        logger.error(f"Error listing PDFs: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route("/download-pdf/<filename>")
def download_pdf(filename):
    """Download a specific PDF file."""
    try:
        pdf_dir = "generated_pdfs"
        file_path = os.path.join(pdf_dir, filename)
        
        # Security check: ensure file exists and is in the correct directory
        if not os.path.exists(file_path) or not os.path.commonpath([pdf_dir, file_path]) == pdf_dir:
            abort(404)
        
        # Security check: ensure it's a PDF file
        if not filename.lower().endswith('.pdf'):
            abort(400)
            
        return send_file(
            file_path,
            as_attachment=True,
            download_name=filename,
            mimetype='application/pdf'
        )
        
    except Exception as e:
        logger.error(f"Error downloading PDF {filename}: {e}")
        abort(500)

@app.route("/view-pdf/<filename>")
def view_pdf(filename):
    """View a specific PDF file in browser."""
    try:
        pdf_dir = "generated_pdfs"
        file_path = os.path.join(pdf_dir, filename)
        
        # Security check: ensure file exists and is in the correct directory
        if not os.path.exists(file_path) or not os.path.commonpath([pdf_dir, file_path]) == pdf_dir:
            abort(404)
        
        # Security check: ensure it's a PDF file
        if not filename.lower().endswith('.pdf'):
            abort(400)
            
        return send_file(
            file_path,
            mimetype='application/pdf'
        )
        
    except Exception as e:
        logger.error(f"Error viewing PDF {filename}: {e}")
        abort(500)

@app.route("/delete-pdf/<filename>", methods=['DELETE'])
def delete_pdf(filename):
    """Delete a specific PDF file (optional feature)."""
    try:
        pdf_dir = "generated_pdfs"
        file_path = os.path.join(pdf_dir, filename)
        
        # Security check: ensure file exists and is in the correct directory
        if not os.path.exists(file_path) or not os.path.commonpath([pdf_dir, file_path]) == pdf_dir:
            abort(404)
        
        # Security check: ensure it's a PDF file
        if not filename.lower().endswith('.pdf'):
            abort(400)
            
        os.remove(file_path)
        logger.info(f"PDF deleted: {filename}")
        
        return jsonify({
            "success": True,
            "message": f"PDF {filename} deleted successfully"
        })
        
    except Exception as e:
        logger.error(f"Error deleting PDF {filename}: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

# ================== ERROR HANDLERS ==================

@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Resource not found"}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "Internal server error"}), 500

@app.errorhandler(400)
def bad_request(error):
    return jsonify({"error": "Bad request"}), 400

# ================== SCHEDULER ROUTES ==================

@app.route('/scheduler')
def scheduler_page():
    """Serve the scheduler page"""
    return render_template('scheduler.html')

# ================== MAIN APPLICATION STARTUP ==================

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    local_ip = get_local_ip()
    
    print("🚀 PROJECT REVIEW MANAGEMENT SYSTEM STARTED")
    print(f"📊 Server running on port {port}")
    print(f"🏠 Local access: http://localhost:{port}/")
    print(f"📱 Device access: http://{local_ip}:{port}/")
    print(f"🔗 Share this IP with other devices on the same network: {local_ip}:{port}")
    print("\n📋 Available Endpoints:")
    print(f"   - Review Pages: /review1 to /review5")
    print(f"   - Data Manager: /data-manager")
    print(f"   - Attendance Dashboard: /attendance-dashboard")
    print(f"   - PDF Viewer: /pdf_viewer")
    print(f"   - Scheduler: /scheduler")
    print("\n🔌 API Endpoints:")
    print(f"   - Project Details: /api/project-details")
    print(f"   - Group Students: /api/group-students")
    print(f"   - Review Totals: /api/review-totals")
    print(f"   - Attendance: /api/attendance")
    print(f"   - Save Response: /api/save-response")
    print(f"   - Fetch Response: /api/fetch-response/<group_id>")
    
    # Create necessary directories
    os.makedirs('generated_pdfs', exist_ok=True)
    os.makedirs('pdf_template', exist_ok=True)
    
    # Run server with device access enabled
    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)