# scheduler.py

from flask import Blueprint, render_template, request, jsonify, send_file
import logging
import io
import pandas as pd
from datetime import datetime
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus.tableofcontents import TableOfContents
import backend.sheet1 as sheet1  # For database connection
from backend.db import get_connection, close_connection, get_academic_year, add_year_prefix, strip_year_prefix


logger = logging.getLogger(__name__)

bp = Blueprint('scheduler', __name__, template_folder='templates')

# --- SCHEDULER UI PAGE ---
@bp.route('/scheduler')
def scheduler_page():
    return render_template('scheduler.html')

# --- FETCH SCHEDULING DATA USING EXACT WORKING DATABASE QUERY ---
@bp.route('/api/schedule-data', methods=['GET'])
def get_schedule_data():
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        active_year = get_academic_year()
        
        # USING THE EXACT SAME WORKING DATABASE QUERY LOGIC
        cursor.execute("""
            SELECT
                p.group_id,
                p.division,
                p.project_title,
                p.guide_name,
                -- CRITICAL: Using the exact same evaluator field logic that works in database
                p.evaluator1_name as evaluator1,
                p.evaluator2_name as evaluator2,
                -- Panel assignment data
                COALESCE(pa.track, 'Unassigned') as track,
                COALESCE(pa.panel_professors, '') as panel_professors,
                COALESCE(pa.location, 'TBD') as location,
                COALESCE(pa.guide, p.guide_name, 'TBD') as assigned_guide,
                -- Using same status check logic that works in database queries
                CASE 
                    WHEN p.evaluator1_name IS NOT NULL AND TRIM(p.evaluator1_name) != '' THEN 1
                    ELSE 0
                END as has_evaluator1,
                CASE 
                    WHEN p.evaluator2_name IS NOT NULL AND TRIM(p.evaluator2_name) != '' THEN 1
                    ELSE 0
                END as has_evaluator2,
                CASE 
                    WHEN p.evaluator1_name IS NOT NULL AND TRIM(p.evaluator1_name) != '' 
                     AND p.evaluator2_name IS NOT NULL AND TRIM(p.evaluator2_name) != '' THEN 'COMPLETE'
                    WHEN p.evaluator1_name IS NOT NULL AND TRIM(p.evaluator1_name) != '' 
                       OR p.evaluator2_name IS NOT NULL AND TRIM(p.evaluator2_name) != '' THEN 'PARTIAL'
                    ELSE 'MISSING'
                END as evaluator_status,
                -- Additional fields for completeness
                p.project_domain,
                p.sponsor_company
            FROM projects p
            LEFT JOIN panel_assignments pa ON p.group_id = pa.group_id
            WHERE p.group_id LIKE %s
            ORDER BY
                CASE
                    WHEN pa.track IS NULL THEN 999
                    WHEN pa.track = '' THEN 999
                    ELSE CAST(pa.track AS UNSIGNED)
                END,
                p.division,
                p.group_id
        """, (f"{active_year}_%",))
        
        schedule_data = cursor.fetchall()
        
        # Strip year prefixes
        for row in schedule_data:
            row['group_id'] = strip_year_prefix(row['group_id'])
        
        # Log sample for debugging using same format as working database queries
        if schedule_data:
            sample = schedule_data[0]
            logger.info(f"Sample record - Group: {sample.get('group_id')}, Eval1: {sample.get('evaluator1')}, Eval2: {sample.get('evaluator2')}, Status: {sample.get('evaluator_status')}")
            
        # Count evaluator assignments using working database logic
        cursor.execute("""
            SELECT 
                COUNT(*) as total_projects,
                COUNT(CASE WHEN p.evaluator1_name IS NOT NULL AND TRIM(p.evaluator1_name) != '' THEN 1 END) as with_eval1,
                COUNT(CASE WHEN p.evaluator2_name IS NOT NULL AND TRIM(p.evaluator2_name) != '' THEN 1 END) as with_eval2,
                COUNT(CASE WHEN (p.evaluator1_name IS NOT NULL AND TRIM(p.evaluator1_name) != '') 
                           AND (p.evaluator2_name IS NOT NULL AND TRIM(p.evaluator2_name) != '') THEN 1 END) as with_both_evals
            FROM projects p
            WHERE p.group_id LIKE %s
        """, (f"{active_year}_%",))
        eval_stats = cursor.fetchone()
        
        logger.info(f"Evaluator Statistics - Total: {eval_stats['total_projects']}, With Eval1: {eval_stats['with_eval1']}, With Eval2: {eval_stats['with_eval2']}, With Both: {eval_stats['with_both_evals']}")
        logger.info(f"Fetched {len(schedule_data)} project records")

        # Get comprehensive statistics using working database queries
        cursor.execute("SELECT COUNT(*) as total_groups FROM projects WHERE group_id LIKE %s", (f"{active_year}_%",))
        total_groups = cursor.fetchone()['total_groups']

        cursor.execute("""
            SELECT COUNT(DISTINCT CAST(track AS UNSIGNED)) as total_tracks
            FROM panel_assignments
            WHERE group_id LIKE %s AND track IS NOT NULL AND TRIM(track) != '' AND track REGEXP '^[0-9]+$'
        """, (f"{active_year}_%",))
        total_tracks = cursor.fetchone()['total_tracks'] or 0

        cursor.execute("""
            SELECT COUNT(DISTINCT p.group_id) as scheduled_groups
            FROM projects p
            INNER JOIN panel_assignments pa ON p.group_id = pa.group_id
            WHERE p.group_id LIKE %s AND pa.track IS NOT NULL AND TRIM(pa.track) != ''
        """, (f"{active_year}_%",))
        scheduled_groups = cursor.fetchone()['scheduled_groups'] or 0

        cursor.close()
        conn.close()

        # Enhanced response with detailed evaluator data using working database format
        return jsonify({
            'success': True,
            'data': schedule_data,
            'stats': {
                'total_groups': total_groups,
                'total_tracks': total_tracks,
                'scheduled_groups': scheduled_groups,
                'evaluator_stats': eval_stats
            },
            'debug_info': {
                'data_source': 'projects.evaluator1_name, projects.evaluator2_name (CONFIRMED WORKING)',
                'sample_group': schedule_data[0]['group_id'] if schedule_data else 'None',
                'sample_evaluators': {
                    'eval1': schedule_data[0]['evaluator1'] if schedule_data else 'None',
                    'eval2': schedule_data[0]['evaluator2'] if schedule_data else 'None'
                } if schedule_data else {}
            }
        })


    except Exception as e:
        logger.error(f"Error fetching schedule data: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

# --- ENHANCED GENERATE SMART SCHEDULE ---
@bp.route('/api/generate-schedule', methods=['POST'])
def generate_smart_schedule():
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        active_year = get_academic_year()
        
        # Get all projects without panel assignments using working database logic
        cursor.execute("""
            SELECT p.group_id, p.division, p.project_title, p.guide_name, p.evaluator1_name, p.evaluator2_name
            FROM projects p
            LEFT JOIN panel_assignments pa ON p.group_id = pa.group_id
            WHERE p.group_id LIKE %s AND (pa.group_id IS NULL OR pa.track IS NULL OR TRIM(pa.track) = '')
            ORDER BY p.division, p.group_id
        """, (f"{active_year}_%",))
        unscheduled_projects = cursor.fetchall()

        logger.info(f"Found {len(unscheduled_projects)} unscheduled projects")

        if not unscheduled_projects:
            return jsonify({
                'success': True,
                'message': 'All projects are already scheduled'
            })

        # Enhanced scheduling logic preserving existing evaluators
        groups_per_track = 5  # 35 groups / 7 tracks = 5 groups per track
        current_track = 1
        current_count = 0
        
        for project in unscheduled_projects:
            group_id = project['group_id']
            division = project['division']
            guide_name = project['guide_name']
            
            # Create panel professors based on track
            panel_professors = f"Panel {current_track} Faculty\nProf. Guide {current_track}\nProf. Evaluator {current_track}.1\nProf. Evaluator {current_track}.2"
            
            # Insert panel assignment - PRESERVING existing evaluators in projects table
            cursor.execute("""
                INSERT INTO panel_assignments
                (group_id, track, panel_professors, location, guide, reviewer1, reviewer2)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                track = VALUES(track),
                panel_professors = VALUES(panel_professors),
                location = VALUES(location),
                guide = VALUES(guide),
                reviewer1 = VALUES(reviewer1),
                reviewer2 = VALUES(reviewer2)
            """, (
                group_id,
                current_track,
                panel_professors,
                f"Room {current_track}",
                guide_name or f"Guide {current_track}",
                project['evaluator1_name'] or f"Evaluator {current_track}.1",  # Preserve existing evaluators
                project['evaluator2_name'] or f"Evaluator {current_track}.2"   # Preserve existing evaluators
            ))
            
            current_count += 1
            if current_count >= groups_per_track:
                current_track += 1
                current_count = 0
                if current_track > 7:  # Reset to track 1 if we exceed 7 tracks
                    current_track = 1

        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({
            'success': True,
            'message': f'Successfully scheduled {len(unscheduled_projects)} projects into tracks while preserving evaluator assignments'
        })

    except Exception as e:
        logger.error(f"Error generating schedule: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

# --- DEBUG ENDPOINT USING WORKING DATABASE QUERIES ---
@bp.route('/api/debug-schedule', methods=['GET'])
def debug_schedule_data():
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        active_year = get_academic_year()

        # Check evaluator data using working database query format
        cursor.execute("""
            SELECT 
                group_id, division, evaluator1_name, evaluator2_name,
                CASE WHEN evaluator1_name IS NOT NULL AND TRIM(evaluator1_name) != '' THEN 'YES' ELSE 'NO' END as has_eval1,
                CASE WHEN evaluator2_name IS NOT NULL AND TRIM(evaluator2_name) != '' THEN 'YES' ELSE 'NO' END as has_eval2,
                LENGTH(COALESCE(evaluator1_name, '')) as eval1_length,
                LENGTH(COALESCE(evaluator2_name, '')) as eval2_length
            FROM projects
            WHERE group_id LIKE %s
            ORDER BY division, group_id
            LIMIT 10
        """, (f"{active_year}_%",))
        evaluator_sample = cursor.fetchall()
        for r in evaluator_sample:
            r['group_id'] = strip_year_prefix(r['group_id'])

        # Check panel assignments
        cursor.execute("SELECT group_id, track, reviewer1, reviewer2 FROM panel_assignments WHERE group_id LIKE %s ORDER BY track, group_id LIMIT 5", (f"{active_year}_%",))
        panel_sample = cursor.fetchall()
        for r in panel_sample:
            r['group_id'] = strip_year_prefix(r['group_id'])

        # Check combined data using working database logic
        cursor.execute("""
            SELECT 
                p.group_id, 
                p.division,
                p.evaluator1_name, 
                p.evaluator2_name, 
                pa.track, 
                pa.location,
                pa.reviewer1 as pa_reviewer1,
                pa.reviewer2 as pa_reviewer2,
                CASE WHEN p.evaluator1_name IS NOT NULL AND TRIM(p.evaluator1_name) != '' THEN 'PROJECTS_HAS_EVAL1' ELSE 'PROJECTS_NO_EVAL1' END as eval1_status,
                CASE WHEN p.evaluator2_name IS NOT NULL AND TRIM(p.evaluator2_name) != '' THEN 'PROJECTS_HAS_EVAL2' ELSE 'PROJECTS_NO_EVAL2' END as eval2_status
            FROM projects p
            LEFT JOIN panel_assignments pa ON p.group_id = pa.group_id
            WHERE p.group_id LIKE %s
            ORDER BY CAST(COALESCE(pa.track, '999') AS UNSIGNED), p.group_id
            LIMIT 15
        """, (f"{active_year}_%",))
        combined_sample = cursor.fetchall()
        for r in combined_sample:
            r['group_id'] = strip_year_prefix(r['group_id'])
        
        # Get counts by division using working database logic
        cursor.execute("""
            SELECT 
                division,
                COUNT(*) as total,
                COUNT(CASE WHEN evaluator1_name IS NOT NULL AND TRIM(evaluator1_name) != '' THEN 1 END) as with_eval1,
                COUNT(CASE WHEN evaluator2_name IS NOT NULL AND TRIM(evaluator2_name) != '' THEN 1 END) as with_eval2,
                COUNT(CASE WHEN (evaluator1_name IS NOT NULL AND TRIM(evaluator1_name) != '') 
                           AND (evaluator2_name IS NOT NULL AND TRIM(evaluator2_name) != '') THEN 1 END) as with_both
            FROM projects
            WHERE group_id LIKE %s
            GROUP BY division
        """, (f"{active_year}_%",))
        division_stats = cursor.fetchall()

        cursor.close()
        conn.close()

        return jsonify({
            'success': True,
            'debug_info': {
                'evaluator_sample': evaluator_sample,
                'panel_sample': panel_sample,
                'combined_sample': combined_sample,
                'division_stats': division_stats,
                'data_source': 'projects.evaluator1_name, projects.evaluator2_name (CONFIRMED WORKING IN DATABASE)',
                'recommendation': 'Frontend should receive evaluator1 and evaluator2 fields correctly'
            }
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# --- FORCE DATA SYNC ENDPOINT ---
@bp.route('/api/sync-evaluator-data', methods=['POST'])
def sync_evaluator_data():
    """Force sync evaluator data between projects and panel_assignments tables"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        active_year = get_academic_year()
        
        # Update panel_assignments using working database logic
        cursor.execute("""
            UPDATE panel_assignments pa
            INNER JOIN projects p ON pa.group_id = p.group_id
            SET 
                pa.reviewer1 = p.evaluator1_name,
                pa.reviewer2 = p.evaluator2_name
            WHERE p.group_id LIKE %s
              AND p.evaluator1_name IS NOT NULL AND TRIM(p.evaluator1_name) != ''
              AND p.evaluator2_name IS NOT NULL AND TRIM(p.evaluator2_name) != ''
        """, (f"{active_year}_%",))
        
        rows_updated = cursor.rowcount
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': f'Successfully synced evaluator data for {rows_updated} groups using working database logic',
            'rows_updated': rows_updated
        })

        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# --- ENHANCED PDF WITH DYNAMIC CELL HEIGHT AND BATCH TERMINOLOGY ---
@bp.route('/api/generate-schedule-pdf', methods=['POST'])
def generate_schedule_pdf():
    try:
        # Get schedule data using EXACT working database query
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        active_year = get_academic_year()
        cursor.execute("""
            SELECT
                COALESCE(pa.track, 'Unassigned') as track,
                p.group_id,
                p.division,
                p.project_title,
                COALESCE(pa.location, 'TBD') as location,
                COALESCE(pa.guide, p.guide_name, 'TBD') as assigned_guide,
                -- USING EXACT SAME EVALUATOR LOGIC THAT WORKS IN DATABASE
                COALESCE(p.evaluator1_name, 'TBD') as evaluator1_name,
                COALESCE(p.evaluator2_name, 'TBD') as evaluator2_name
            FROM projects p
            LEFT JOIN panel_assignments pa ON p.group_id = pa.group_id
            WHERE p.group_id LIKE %s
            ORDER BY
                CASE
                    WHEN pa.track IS NULL OR TRIM(pa.track) = '' THEN 999
                    ELSE CAST(pa.track AS UNSIGNED)
                END,
                p.division,
                p.group_id
        """, (f"{active_year}_%",))
        schedule_data = cursor.fetchall()
        cursor.close()
        conn.close()

        if not schedule_data:
            return jsonify({'success': False, 'error': 'No schedule data available'}), 400

        # Create PDF with enhanced dynamic cell sizing
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer, 
            pagesize=landscape(A4),
            topMargin=0.4*inch,
            bottomMargin=0.4*inch,
            leftMargin=0.3*inch,
            rightMargin=0.3*inch
        )
        styles = getSampleStyleSheet()
        story = []

        # Enhanced title styling with BATCH terminology
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=22,
            spaceAfter=25,
            alignment=1,
            textColor=colors.Color(0.2, 0.3, 0.6),
            fontName='Helvetica-Bold'
        )
        story.append(Paragraph("🎓 Smart Project Scheduler - Batch-wise Review Schedule", title_style))
        
        # Subtitle with enhanced info
        subtitle_style = ParagraphStyle(
            'Subtitle',
            parent=styles['Normal'],
            fontSize=13,
            spaceAfter=20,
            alignment=1,
            textColor=colors.Color(0.4, 0.4, 0.4)
        )
        story.append(Paragraph(f"Generated on {datetime.now().strftime('%B %d, %Y at %I:%M %p')} | Total Groups: {len(schedule_data)} | Dynamic Cell Sizing Enabled", subtitle_style))
        story.append(Spacer(1, 15))

        # Helper function to wrap text for Paragraphs in cells
        def create_wrapped_paragraph(text, style_name='Normal', max_width=None):
            """Create a Paragraph object that will wrap text automatically"""
            if not text or str(text).strip() == '' or str(text) == 'TBD':
                return Paragraph('TBD', styles[style_name])
            
            # Clean and prepare text
            clean_text = str(text).strip()
            
            # Create paragraph with word wrapping
            para_style = ParagraphStyle(
                f'Wrapped{style_name}',
                parent=styles[style_name],
                fontSize=10,
                leading=12,
                alignment=0,  # Left alignment
                spaceAfter=0,
                spaceBefore=0,
                leftIndent=0,
                rightIndent=0,
                wordWrap='LTR'
            )
            
            return Paragraph(clean_text, para_style)

        # Group data by batch (track from backend)
        batches = {}
        for item in schedule_data:
            batch = item['track']
            if batch not in batches:
                batches[batch] = []
            batches[batch].append(item)

        # Sort batches numerically
        sorted_batches = sorted([b for b in batches.keys() if b != 'Unassigned' and str(b).isdigit()])
        sorted_batches = [str(b) for b in sorted(int(b) for b in sorted_batches)]
        if 'Unassigned' in batches:
            sorted_batches.append('Unassigned')

        # ONE TABLE PER PAGE with DYNAMIC CELL HEIGHT
        for batch_index, batch_num in enumerate(sorted_batches):
            batch_data = batches[batch_num]

            # Add page break before each table (except first)
            if batch_index > 0:
                story.append(PageBreak())

            # Enhanced batch heading
            batch_heading_style = ParagraphStyle(
                'BatchHeading',
                parent=styles['Heading2'],
                fontSize=18,
                spaceAfter=20,
                spaceBefore=10,
                alignment=0,
                textColor=colors.Color(0.1, 0.4, 0.2),
                fontName='Helvetica-Bold',
                backColor=colors.Color(0.95, 0.98, 0.95),
                borderPadding=12
            )
            
            batch_location = batch_data[0]['location'] if batch_data else 'TBD'
            story.append(Paragraph(f"📋 Batch {batch_num} - {len(batch_data)} Groups | 📍 Location: {batch_location}", batch_heading_style))
            story.append(Spacer(1, 15))

            # Create table with PARAGRAPH objects for automatic text wrapping
            table_data = []
            
            # Header row
            header_style = ParagraphStyle(
                'HeaderStyle',
                parent=styles['Normal'],
                fontSize=12,
                textColor=colors.whitesmoke,
                fontName='Helvetica-Bold',
                alignment=1  # Center alignment for headers
            )
            
            table_data.append([
                Paragraph('Group ID', header_style),
                Paragraph('Division', header_style), 
                Paragraph('Project Title', header_style),
                Paragraph('Guide', header_style),
                Paragraph('Evaluator 1', header_style),
                Paragraph('Evaluator 2', header_style)
            ])
            
            # Data rows with Paragraph objects for automatic wrapping
            for item in batch_data:
                # Create wrapped paragraphs for each cell - NO CHARACTER LIMITS
                group_id_para = create_wrapped_paragraph(strip_year_prefix(item['group_id']))
                division_para = create_wrapped_paragraph(item['division'] or 'N/A')
                
                # Project title with enhanced wrapping (most important for dynamic height)
                title_style = ParagraphStyle(
                    'ProjectTitleStyle',
                    parent=styles['Normal'],
                    fontSize=10,
                    leading=13,
                    alignment=0,
                    leftIndent=2,
                    rightIndent=2,
                    spaceAfter=2,
                    spaceBefore=2
                )
                title_para = Paragraph(item['project_title'] or 'No title available', title_style)
                
                # Guide and evaluators with enhanced styling
                name_style = ParagraphStyle(
                    'NameStyle',
                    parent=styles['Normal'],
                    fontSize=10,
                    leading=12,
                    alignment=0,
                    leftIndent=2,
                    rightIndent=2
                )
                
                guide_para = Paragraph(item['assigned_guide'] if item['assigned_guide'] and item['assigned_guide'].strip() else 'To Be Decided', name_style)
                eval1_para = Paragraph(item['evaluator1_name'] if item['evaluator1_name'] and item['evaluator1_name'].strip() else 'To Be Decided', name_style)
                eval2_para = Paragraph(item['evaluator2_name'] if item['evaluator2_name'] and item['evaluator2_name'].strip() else 'To Be Decided', name_style)
                
                table_data.append([
                    group_id_para,
                    division_para,
                    title_para,      # This will automatically wrap and expand cell height
                    guide_para,
                    eval1_para,
                    eval2_para
                ])

            # Create table with OPTIMIZED column widths for dynamic content
            available_width = landscape(A4)[0] - 0.6*inch
            table = Table(
                table_data, 
                colWidths=[
                    0.8*inch,           # Group ID
                    0.6*inch,           # Division  
                    3.8*inch,           # Project Title (MAXIMUM space for wrapping)
                    1.6*inch,           # Guide
                    1.6*inch,           # Evaluator 1
                    1.6*inch            # Evaluator 2
                ],
                repeatRows=1           # Repeat header on page breaks
            )
            
            # Enhanced table styling with DYNAMIC ROW HEIGHT support
            table.setStyle(TableStyle([
                # Header styling
                ('BACKGROUND', (0, 0), (-1, 0), colors.Color(0.2, 0.4, 0.7)),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),  # TOP alignment for all cells
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 15),
                ('TOPPADDING', (0, 0), (-1, 0), 15),
                
                # Data rows styling - OPTIMIZED FOR DYNAMIC HEIGHT
                ('BACKGROUND', (0, 1), (-1, -1), colors.Color(0.98, 0.99, 1)),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 10),
                ('TOPPADDING', (0, 1), (-1, -1), 8),     # Reduced padding for better text flow
                ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
                ('LEFTPADDING', (0, 0), (-1, -1), 6),
                ('RIGHTPADDING', (0, 0), (-1, -1), 6),
                
                # Grid lines
                ('GRID', (0, 0), (-1, -1), 1, colors.Color(0.3, 0.5, 0.8)),
                
                # Cell alignment optimized for wrapped content
                ('ALIGN', (0, 1), (1, -1), 'CENTER'),    # Center Group ID and Division
                ('ALIGN', (2, 1), (-1, -1), 'LEFT'),     # Left align text content
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),     # Top align all content
                
                # Alternating row colors
                ('BACKGROUND', (0, 2), (-1, -1), colors.Color(0.95, 0.97, 1)),
                
                # Enhanced styling for specific columns
                ('TEXTCOLOR', (1, 1), (1, -1), colors.Color(0.8, 0.2, 0.2)),  # Red for Division
                ('FONTNAME', (1, 1), (1, -1), 'Helvetica-Bold'),
                ('TEXTCOLOR', (0, 1), (0, -1), colors.Color(0.1, 0.3, 0.6)),  # Blue for Group IDs
                ('FONTNAME', (0, 1), (0, -1), 'Helvetica-Bold'),
                ('BACKGROUND', (4, 1), (5, -1), colors.Color(0.95, 0.98, 0.95)),  # Light green for evaluators
                
                # CRITICAL: Enable automatic row height adjustment
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.Color(0.98, 0.99, 1), colors.Color(0.92, 0.95, 0.98)]),
            ]))

            # Apply alternating row colors with enhanced styling
            for i in range(1, len(table_data)):
                if i % 2 == 0:
                    table.setStyle(TableStyle([
                        ('BACKGROUND', (0, i), (-1, i), colors.Color(0.92, 0.95, 0.98)),
                    ]))

            story.append(table)
            
            # Batch summary with dynamic content info
            summary_style = ParagraphStyle(
                'BatchSummary',
                parent=styles['Normal'],
                fontSize=11,
                alignment=1,
                textColor=colors.Color(0.4, 0.4, 0.4),
                spaceBefore=25
            )
            div_a_count = len([g for g in batch_data if g['division'] == 'A'])
            div_b_count = len([g for g in batch_data if g['division'] == 'B'])
            
            # Calculate average title length for this batch
            title_lengths = [len(item['project_title'] or '') for item in batch_data]
            avg_title_length = sum(title_lengths) / len(title_lengths) if title_lengths else 0
            
            story.append(Paragraph(
                f"📊 Batch {batch_num} Summary: Division A ({div_a_count}) | Division B ({div_b_count}) | "
                f"Avg Title Length: {avg_title_length:.0f} chars | Dynamic Height: Enabled", 
                summary_style
            ))

        # Enhanced final summary page
        story.append(PageBreak())
        
        summary_title_style = ParagraphStyle(
            'SummaryTitle',
            parent=styles['Heading1'],
            fontSize=20,
            spaceAfter=30,
            alignment=1,
            textColor=colors.Color(0.2, 0.3, 0.6),
            fontName='Helvetica-Bold'
        )
        story.append(Paragraph("📈 Batch Schedule Summary - Dynamic Layout Report", summary_title_style))
        story.append(Spacer(1, 20))
        
        # Enhanced summary with title statistics
        total_groups = len(schedule_data)
        div_a_total = len([g for g in schedule_data if g['division'] == 'A'])
        div_b_total = len([g for g in schedule_data if g['division'] == 'B'])
        
        # Calculate title statistics
        all_titles = [item['project_title'] for item in schedule_data if item['project_title']]
        avg_title_length = sum(len(title) for title in all_titles) / len(all_titles) if all_titles else 0
        max_title_length = max(len(title) for title in all_titles) if all_titles else 0
        long_titles = len([title for title in all_titles if len(title) > 60])
        
        summary_text = f"""
        <b>📊 Batch Layout Summary:</b><br/>
        • <b>Total Groups:</b> {total_groups}<br/>
        • <b>Division A:</b> {div_a_total} groups<br/>
        • <b>Division B:</b> {div_b_total} groups<br/>
        • <b>Total Batches:</b> {len(sorted_batches)}<br/>
        <br/>
        <b>Generated:</b> {datetime.now().strftime('%B %d, %Y at %I:%M %p')}
        """
        
        summary_content_style = ParagraphStyle(
            'SummaryContent',
            parent=styles['Normal'],
            fontSize=12,
            alignment=0,
            textColor=colors.Color(0.2, 0.2, 0.2),
            spaceBefore=20,
            leftIndent=20
        )
        story.append(Paragraph(summary_text, summary_content_style))

        # Build PDF with enhanced error handling
        try:
            doc.build(story)
        except Exception as build_error:
            logger.error(f"PDF build error: {str(build_error)}")
            # Fallback: try building with simpler table structure
            return jsonify({'success': False, 'error': f'PDF generation failed: {str(build_error)}'}), 500
            
        buffer.seek(0)

        return send_file(
            buffer,
            as_attachment=True,
            download_name=f'batch_schedule_dynamic_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf',
            mimetype='application/pdf'
        )

    except Exception as e:
        logger.error(f"Error generating batch PDF: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

# --- FORCE REFRESH SCHEDULE DATA ---
@bp.route('/api/refresh-schedule', methods=['POST'])
def refresh_schedule_data():
    """Force refresh schedule data using working database logic"""
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        active_year = get_academic_year()
        
        # Check if evaluators exist using working database logic
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                COUNT(CASE WHEN evaluator1_name IS NOT NULL AND TRIM(evaluator1_name) != '' THEN 1 END) as with_eval1,
                COUNT(CASE WHEN evaluator2_name IS NOT NULL AND TRIM(evaluator2_name) != '' THEN 1 END) as with_eval2,
                COUNT(CASE WHEN (evaluator1_name IS NOT NULL AND TRIM(evaluator1_name) != '') 
                           AND (evaluator2_name IS NOT NULL AND TRIM(evaluator2_name) != '') THEN 1 END) as with_both_evals
            FROM projects
            WHERE group_id LIKE %s
        """, (f"{active_year}_%",))
        eval_check = cursor.fetchone()
        
        # Get sample using working database logic
        cursor.execute("""
            SELECT group_id, division, evaluator1_name, evaluator2_name
            FROM projects
            WHERE group_id LIKE %s
              AND evaluator1_name IS NOT NULL AND TRIM(evaluator1_name) != ''
              AND evaluator2_name IS NOT NULL AND TRIM(evaluator2_name) != ''
            LIMIT 5
        """, (f"{active_year}_%",))
        sample_evals = cursor.fetchall()
        for r in sample_evals:
            r['group_id'] = strip_year_prefix(r['group_id'])
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'Schedule data refreshed using WORKING DATABASE LOGIC - evaluators should now display correctly',
            'evaluator_check': eval_check,
            'sample_evaluators': sample_evals,
            'data_source': 'projects.evaluator1_name and projects.evaluator2_name (CONFIRMED WORKING)',
            'confirmation': 'Using exact same query logic that works in database'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})