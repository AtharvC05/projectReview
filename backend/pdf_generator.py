# backend/pdf_generator.py
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from datetime import datetime
import os
from backend.db import get_connection, close_connection, add_year_prefix, strip_year_prefix, get_academic_year

# Roman numeral mapping for review numbers
REVIEW_ROMAN = {1: 'I', 2: 'II', 3: 'III', 4: 'IV', 0: 'SEM-I Mock', 5: 'V', 6: 'SEM-II Mock'}

class GenericReviewPDFGenerator:
    def __init__(self, output_path, review_number):
        self.output_path = output_path
        self.review_number = review_number
        self.review_roman = REVIEW_ROMAN.get(review_number, str(review_number))
        
        self.doc = SimpleDocTemplate(output_path, pagesize=A4,
                                     rightMargin=0.5*inch, leftMargin=0.5*inch,
                                     topMargin=0.5*inch, bottomMargin=0.5*inch)
        self.elements = []
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
    
    def _setup_custom_styles(self):
        """Create custom paragraph styles"""
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=11,
            textColor=colors.black,
            spaceAfter=2,
            spaceBefore=0,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold',
            leading=13
        ))
        
        self.styles.add(ParagraphStyle(
            name='CustomSubtitle',
            parent=self.styles['Heading2'],
            fontSize=11,
            textColor=colors.black,
            spaceAfter=2,
            spaceBefore=0,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold',
            leading=13
        ))
        
        self.styles.add(ParagraphStyle(
            name='CustomSubtitle2',
            parent=self.styles['Heading2'],
            fontSize=10,
            textColor=colors.black,
            spaceAfter=0,
            spaceBefore=0,
            alignment=TA_CENTER,
            fontName='Helvetica',
            leading=12
        ))
        
        self.styles.add(ParagraphStyle(
            name='SectionHeader',
            parent=self.styles['Heading2'],
            fontSize=10,
            textColor=colors.black,
            spaceAfter=8,
            spaceBefore=10,
            fontName='Helvetica-Bold',
            alignment=TA_CENTER,
            leftIndent=70
        ))
        
        self.styles.add(ParagraphStyle(
            name='QuestionText',
            parent=self.styles['Normal'],
            fontSize=8.5,
            leading=10,
            fontName='Helvetica',
            alignment=TA_LEFT,
            leftIndent=0,
            rightIndent=0
        ))
        
        self.styles.add(ParagraphStyle(
            name='CustomNormal',
            parent=self.styles['Normal'],
            fontSize=9,
            leading=11,
            fontName='Helvetica',
            leftIndent=20,
        ))
        
        self.styles.add(ParagraphStyle(
            name='CenteredNormal',
            parent=self.styles['Normal'],
            alignment=TA_CENTER
        ))
        self.styles.add(ParagraphStyle(
            name='TableTextSmall',
            parent=self.styles['Normal'],
            fontSize=8.5,
            leading=9,
            fontName='Helvetica',
            alignment=TA_LEFT
        ))
    
    def calculate_academic_year(self, submission_date):
        """Calculate academic year based on submission date"""
        if isinstance(submission_date, str):
            date_obj = datetime.strptime(submission_date, '%d-%m-%Y')
        else:
            date_obj = submission_date
        
        year = date_obj.year
        month = date_obj.month
        
        if month < 7:
            return f"{year-1}-{str(year)[2:]}"
        else:
            return f"{year}-{str(year+1)[2:]}"
    
    def add_header(self, academic_year, logo_path=None):
        """Add institute header with logo"""
        if logo_path is None:
            # Construct absolute path to the logo
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            logo_path = os.path.join(base_dir, 'frontend', 'static', 'images', 'logo.png')

        logo_img = None
        try:
            if os.path.exists(logo_path):
                logo_img = Image(logo_path, width=0.8*inch, height=0.8*inch)
            else:
                print(f"Logo not found at path: {logo_path}")
        except Exception as e:
            print(f"Error loading logo: {e}")
        
        title1 = Paragraph("<b>Hope Foundation's</b>", self.styles['CustomTitle'])
        title2 = Paragraph("<b>International Institute of Information Technology, Pune</b>", 
                          self.styles['CustomTitle'])
        subtitle1 = Paragraph(f"<b>PROJECT REVIEW – {self.review_roman}</b>", self.styles['CustomSubtitle'])
        subtitle2 = Paragraph(f"(Academic Year: {academic_year})", self.styles['CustomSubtitle2'])
        
        if logo_img:
            header_data = [[logo_img, [title1, title2, subtitle1, subtitle2]]]
            header_table = Table(header_data, colWidths=[1*inch, 5.5*inch])
            header_table.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('ALIGN', (0, 0), (0, 0), 'LEFT'),
                ('ALIGN', (1, 0), (1, 0), 'CENTER'),
                ('LEFTPADDING', (0, 0), (-1, -1), 0),
                ('RIGHTPADDING', (0, 0), (-1, -1), 0),
                ('TOPPADDING', (0, 0), (-1, -1), 0),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
            ]))
            self.elements.append(header_table)
        else:
            self.elements.append(title1)
            self.elements.append(title2)
            self.elements.append(subtitle1)
            self.elements.append(subtitle2)
        
        self.elements.append(Spacer(1, 0.15*inch))
    
    def add_project_info(self, group_data, submission_date, guide_name=None):
        """Add group and project information"""
        project_title = str(group_data.get('project_title', '') or '')
        project_domain = str(group_data.get('project_domain', '') or '')
        sponsor_company = str(group_data.get('sponsor_company', '') or '')
        if not guide_name:
            guide_name = str(group_data.get('guide_name', '') or '')

        title_para = Paragraph(project_title, self.styles['TableTextSmall'])
        domain_para = Paragraph(project_domain, self.styles['TableTextSmall'])
        sponsor_para = Paragraph(sponsor_company, self.styles['TableTextSmall'])
        guide_para = Paragraph(guide_name, self.styles['TableTextSmall'])

        info_data = [
            ['Group ID', group_data.get('group_id', ''), 'DATE', str(submission_date)],
            ['Project Domain', domain_para, 'Guide Name', guide_para],
            ['Project Title', title_para, '', ''],
            ['Sponsor Company', sponsor_para, '', '']
        ]
        
        col_widths = [1.35*inch, 2.15*inch, 1.0*inch, 2.0*inch]
        info_table = Table(info_data, colWidths=col_widths)
        info_table.setStyle(TableStyle([
            ('FONT', (0, 0), (-1, -1), 'Helvetica', 9),
            ('FONT', (0, 0), (0, -1), 'Helvetica-Bold', 9),
            ('FONT', (2, 0), (2, 1), 'Helvetica-Bold', 9),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('SPAN', (1, 2), (3, 2)),
            ('SPAN', (1, 3), (3, 3)),
            ('LEFTPADDING', (0, 0), (-1, -1), 5),
            ('RIGHTPADDING', (0, 0), (-1, -1), 5),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        
        self.elements.append(info_table)
        self.elements.append(Spacer(1, 0.12*inch))
    
    def add_members_table(self, members, guide_info=None):
        """Add team members table"""
        header = [
            'Sr.No.', 
            'Roll No.', 
            'Student Name'
        ]
        data = [header]
        
        for idx, member in enumerate(members, 1):
            data.append([
                str(idx),
                member.get('roll_no', ''),
                member.get('student_name', '')
            ])
        
        col_widths = [0.8*inch, 1.7*inch, 4.0*inch]
        members_table = Table(data, colWidths=col_widths)
        
        style_commands = [
            ('FONT', (0, 0), (-1, 0), 'Helvetica-Bold', 9),
            ('FONT', (0, 1), (-1, -1), 'Helvetica', 9),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ALIGN', (0, 0), (1, -1), 'CENTER'),
            ('ALIGN', (2, 0), (2, -1), 'LEFT'),
            ('LEFTPADDING', (2, 0), (2, -1), 60),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('LEFTPADDING', (0, 0), (1, -1), 5),
            ('RIGHTPADDING', (0, 0), (-1, -1), 5),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]
        
        members_table.setStyle(TableStyle(style_commands))
        self.elements.append(members_table)
        self.elements.append(Spacer(1, 0.15*inch))
    
    def add_checklist_section(self, section_title, questions_by_section, responses):
        """Add checklist questions with responses grouped by section"""
        data = []
        
        header_left = Paragraph(f'<b>{section_title}</b>', 
                     ParagraphStyle(name='HeaderLeft', parent=self.styles['Normal'], 
                                  fontSize=10, textColor=colors.white, 
                                  fontName='Helvetica-Bold', alignment=TA_CENTER))
        header_right = Paragraph('<b>25 MARKS</b>', 
                     ParagraphStyle(name='HeaderRight', parent=self.styles['Normal'], 
                                  fontSize=10, textColor=colors.white, 
                                  fontName='Helvetica-Bold', alignment=TA_CENTER))
        
        header_row = [header_left, header_right]
        data.append(header_row)
        
        question_number = 1
        
        for section_name, questions in questions_by_section.items():
            section_row = [
                Paragraph(f'<b>{section_name.upper()}</b>', 
                         ParagraphStyle(name='SectionStyle', parent=self.styles['Normal'],
                                      fontSize=9, textColor=colors.white,
                                      fontName='Helvetica-Bold', alignment=TA_CENTER)),
                ''
            ]
            data.append(section_row)
            
            for question in questions:
                q_id = question['question_id']
                q_text = question['question_text']
                
                formatted_text = f"{question_number}. {q_text}"
                q_para = Paragraph(formatted_text, 
                                 ParagraphStyle(name='QuestionStyle', parent=self.styles['Normal'],
                                              fontSize=9, fontName='Helvetica',
                                              alignment=TA_LEFT, leading=11))
                
                db_key = q_id.replace('.', '_')
                response = responses.get(db_key, '')
                
                q_row = [q_para, response if response else '']
                data.append(q_row)
                question_number += 1
        
        col_widths = [5.8*inch, 0.7*inch]
        checklist_table = Table(data, colWidths=col_widths, repeatRows=1)
        
        style_commands = [
            ('BACKGROUND', (0, 0), (1, 0), colors.HexColor("#272727")),
            ('FONT', (0, 0), (1, 0), 'Helvetica-Bold', 10),
            ('TEXTCOLOR', (0, 0), (1, 0), colors.white),
            ('ALIGN', (0, 0), (0, 0), 'LEFT'),
            ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
            ('LEFTPADDING', (0, 0), (1, 0), 6),
            ('RIGHTPADDING', (0, 0), (1, 0), 6),
            ('TOPPADDING', (0, 0), (1, 0), 6),
            ('BOTTOMPADDING', (0, 0), (1, 0), 6),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONT', (0, 1), (0, -1), 'Helvetica', 9),
            ('FONT', (1, 1), (1, -1), 'Helvetica-Bold', 9),
            ('VALIGN', (0, 1), (-1, -1), 'MIDDLE'),
            ('ALIGN', (0, 1), (0, -1), 'LEFT'),
            ('ALIGN', (1, 1), (1, -1), 'CENTER'),
            ('LEFTPADDING', (0, 1), (-1, -1), 6),
            ('RIGHTPADDING', (0, 1), (-1, -1), 6),
            ('TOPPADDING', (0, 1), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 4),
        ]
        
        current_row = 1
        for section_name, questions in questions_by_section.items():
            style_commands.extend([
                ('BACKGROUND', (0, current_row), (-1, current_row), colors.HexColor("#7A7979")),
                ('SPAN', (0, current_row), (-1, current_row)),
                ('FONT', (0, current_row), (-1, current_row), 'Helvetica-Bold', 9),
                ('TEXTCOLOR', (0, current_row), (-1, current_row), colors.white),
                ('ALIGN', (0, current_row), (-1, current_row), 'LEFT'),
            ])
            current_row += 1
            current_row += len(questions)
        
        checklist_table.setStyle(TableStyle(style_commands))
        self.elements.append(checklist_table)
        self.elements.append(Spacer(1, 0.15*inch))
    
    def add_page_break(self, academic_year):
        """Add page break with header on new page"""
        self.elements.append(PageBreak())
        self.add_header(academic_year)
    
    def add_performance_table(self, members, marks_data, criteria_list):
        """Add student performance evaluation table"""
        section_header = Paragraph("<b>STUDENT PERFORMANCE EVALUATION</b>", self.styles['SectionHeader'])
        self.elements.append(section_header)
        self.elements.append(Spacer(1, 0.08*inch))
        
        num_members = len(members)
        
        header_row1 = [
            Paragraph('<b>Students\' Contribution and Performance</b>', 
                     ParagraphStyle(name='TableHeaderBold', parent=self.styles['Normal'],
                                  fontSize=9, fontName='Helvetica-Bold', alignment=TA_LEFT)),
            ''
        ] + [''] * num_members
        
        header_row2 = [
            '', '',
            Paragraph('<b>Marks(25M)</b>', 
                     ParagraphStyle(name='MarksBold', parent=self.styles['Normal'],
                                  fontSize=9, fontName='Helvetica-Bold', alignment=TA_CENTER))
        ] + [''] * (num_members - 1)
        
        header_row3 = [
            '', ''
        ] + [Paragraph('<b>Group Members</b>', 
                      ParagraphStyle(name='GroupMembersBold', parent=self.styles['Normal'],
                                   fontSize=9, fontName='Helvetica-Bold', alignment=TA_CENTER))] + [''] * (num_members - 1)
        
        header_row4 = [
            Paragraph('<b>Particulars</b>', 
                     ParagraphStyle(name='ParticularsBold', parent=self.styles['Normal'],
                                  fontSize=9, fontName='Helvetica-Bold', alignment=TA_CENTER)),
            ''
        ] + [Paragraph(f'<b>{i+1}</b>', 
                      ParagraphStyle(name='ColNum', parent=self.styles['Normal'],
                                   fontSize=9, fontName='Helvetica-Bold', alignment=TA_CENTER)) 
             for i in range(num_members)]
        
        data = [header_row1, header_row2, header_row3, header_row4]
        
        for idx, criterion in enumerate(criteria_list, 1):
            criteria_id = criterion['criteria_id']
            criteria_text = criterion['criteria_text']
            max_marks = criterion['max_marks']
            
            criteria_para = Paragraph(f"{criteria_text}", 
                                    ParagraphStyle(name='CriteriaText', parent=self.styles['Normal'],
                                                 fontSize=9, fontName='Helvetica', alignment=TA_LEFT))
            
            if max_marks > 0:
                marks_label = Paragraph(f"({int(max_marks)}M)", 
                                      ParagraphStyle(name='MarksLabel', parent=self.styles['Normal'],
                                                   fontSize=9, fontName='Helvetica', alignment=TA_CENTER))
            else:
                marks_label = ''
            
            row = [criteria_para, marks_label]
            
            for member in members:
                member_marks = next((m for m in marks_data if m['roll_no'] == member['roll_no']), None)
                if member_marks and member_marks.get(criteria_id) is not None:
                    mark_value = member_marks[criteria_id]
                    if isinstance(mark_value, str):
                        row.append(mark_value)
                    elif mark_value == int(mark_value):
                        row.append(str(int(mark_value)))
                    else:
                        row.append(str(mark_value))
                else:
                    row.append('')
            data.append(row)
        
        total_row = [
            Paragraph('<b>Total(25M)</b>', 
                     ParagraphStyle(name='TotalBold', parent=self.styles['Normal'],
                                  fontSize=9, fontName='Helvetica-Bold', alignment=TA_LEFT)),
            ''
        ]
        for member in members:
            member_marks = next((m for m in marks_data if m['roll_no'] == member['roll_no']), None)
            if member_marks and member_marks.get('total') is not None:
                total = member_marks['total']
                total_str = str(int(total)) if total == int(total) else str(total)
                total_row.append(Paragraph(f'<b>{total_str}</b>', 
                                          ParagraphStyle(name='TotalValue', parent=self.styles['Normal'],
                                                       fontSize=9, fontName='Helvetica-Bold', alignment=TA_CENTER)))
            else:
                total_row.append(Paragraph('<b>0</b>', 
                                          ParagraphStyle(name='TotalZero', parent=self.styles['Normal'],
                                                       fontSize=9, fontName='Helvetica-Bold', alignment=TA_CENTER)))
        data.append(total_row)
        
        particulars_col1 = 3.0*inch
        particulars_col2 = 0.7*inch
        remaining_width = 6.5*inch - particulars_col1 - particulars_col2
        member_width = remaining_width / num_members
        
        col_widths = [particulars_col1, particulars_col2] + [member_width] * num_members
        perf_table = Table(data, colWidths=col_widths)
        
        style_commands = [
            ('FONT', (0, 0), (-1, -1), 'Helvetica', 9),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ALIGN', (2, 4), (-1, -1), 'CENTER'),
            ('ALIGN', (0, 0), (-1, 3), 'CENTER'),
            ('ALIGN', (0, 4), (0, -1), 'LEFT'),
            ('ALIGN', (1, 4), (1, -1), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('SPAN', (0, 0), (num_members + 1, 0)),
            ('SPAN', (2, 1), (num_members + 1, 1)),
            ('SPAN', (2, 2), (num_members + 1, 2)),
            ('SPAN', (0, 3), (1, 3)),
            ('SPAN', (0, 1), (1, 2)),
        ]
        
        for i in range(4, len(data)):
            style_commands.append(('SPAN', (0, i), (1, i)))
        
        perf_table.setStyle(TableStyle(style_commands))
        self.elements.append(perf_table)
        self.elements.append(Spacer(1, 0.12*inch))
    
    def add_comments_section(self, comments):
        """Add comments section"""
        comments_header = Paragraph("<b>Comments (if any) :</b>", self.styles['CustomNormal'])
        self.elements.append(comments_header)
        
        comments_text = comments if comments else ''
        if comments_text:
            self.elements.append(Spacer(1, 0.05*inch))
            comments_para = Paragraph(comments_text, self.styles['CustomNormal'])
            self.elements.append(comments_para)
        
        self.elements.append(Spacer(1, 0.15*inch))
        
        note_style = ParagraphStyle(
            name='NoteStyle',
            parent=self.styles['Normal'],
            fontSize=8,
            fontName='Helvetica',
            alignment=TA_LEFT,
            leftIndent=20
        )
        
        notes = [
            "# To be filled by internal guide &amp; reviewer(s) only.",
            "* Whether the presentation / evaluation schedule. : YES / NO (If NO mention the reasons for same.)"
        ]
        
        for note in notes:
            note_para = Paragraph(note, note_style)
            self.elements.append(note_para)
            self.elements.append(Spacer(1, 0.03*inch))
        
        self.elements.append(Spacer(1, 0.12*inch))
    
    def add_deliverables_section(self, deliverables):
        """Add review deliverables list"""
        deliverables_title = Paragraph(f"<b>Review – {self.review_roman}: Deliverables</b>", 
                                       ParagraphStyle(name='DeliverableTitle', 
                                                    parent=self.styles['Normal'],
                                                    fontSize=10,
                                                    fontName='Helvetica-Bold',
                                                    textColor=colors.HexColor('#CC0000'),
                                                    alignment=TA_LEFT,
                                                    spaceAfter=6,leftIndent=20))
        self.elements.append(deliverables_title)
        self.elements.append(Spacer(1, 0.05*inch))
        
        deliverable_style = ParagraphStyle(
            name='DeliverableItem',
            parent=self.styles['Normal'],
            fontSize=9,
            fontName='Helvetica',
            alignment=TA_LEFT,
            leftIndent=22,
            bulletIndent=5
        )
        
        for item in deliverables:
            item_para = Paragraph(f"• {item['deliverable_text']}", deliverable_style)
            self.elements.append(item_para)
            self.elements.append(Spacer(1, 0.02*inch))
        
        self.elements.append(Spacer(1, 0.15*inch))
    
    def add_signatures(self, guide_name=None, reviewer1_name=None, reviewer2_name=None):
        """Add signature section"""
        sig_header = Paragraph("<b>Name &amp; Signature of evaluation committee -</b>", 
                              self.styles['CustomNormal'])
        self.elements.append(sig_header)
        self.elements.append(Spacer(1, 0.4*inch))
        
        # Row 1: Labels
        label_row = ['Name of Reviewer 1', 'Name of Reviewer 2', 'Name of Internal Guide']
        
        # Row 2: Actual names (or empty if not provided)
        name_row = [
            reviewer1_name if reviewer1_name else '',
            reviewer2_name if reviewer2_name else '',
            guide_name if guide_name else ''
        ]
        
        sig_data = [label_row, name_row]
        
        sig_table = Table(sig_data, colWidths=[2.17*inch, 2.17*inch, 2.17*inch])
        sig_table.setStyle(TableStyle([
            ('FONT', (0, 0), (-1, -1), 'Helvetica', 9),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('TOPPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ]))
        
        self.elements.append(sig_table)
           
    def build(self):
        """Build the PDF"""
        self.doc.build(self.elements)
        print(f"PDF generated: {self.output_path}")


def generate_review_pdf(review_number, group_id, output_filename=None):
    """Generic function to generate PDF for any review"""
    conn = get_connection()
    if not conn:
        return {'success': False, 'error': 'Database connection failed'}
    
    try:
        cursor = conn.cursor(dictionary=True)
        
        db_group_id = add_year_prefix(group_id)
        
        # Fetch project info
        cursor.execute("SELECT * FROM projects WHERE group_id = %s", (db_group_id,))
        project_data = cursor.fetchone()
        
        if not project_data:
            return {'success': False, 'error': f'No project found for group {group_id}'}
        
        # Strip year prefix
        project_data['group_id'] = strip_year_prefix(project_data['group_id'])
        
        # Fetch members
        cursor.execute("""
            SELECT roll_no, student_name 
            FROM members 
            WHERE group_id = %s 
            ORDER BY roll_no
        """, (db_group_id,))
        members = cursor.fetchall()
        
        if not members:
            return {'success': False, 'error': f'No members found for group {group_id}'}
            
        # Strip roll no prefix
        for m in members:
            m['roll_no'] = strip_year_prefix(m['roll_no'])
        
        # Fetch marks
        cursor.execute(f"""
            SELECT * FROM review{review_number}_marks 
            WHERE group_id = %s 
            ORDER BY roll_no
        """, (db_group_id,))
        marks_data = cursor.fetchall()
        
        # Strip roll no prefix in marks
        for m in marks_data:
            m['roll_no'] = strip_year_prefix(m['roll_no'])
        
        # Fetch questionnaire responses
        cursor.execute(f"""
            SELECT * FROM review{review_number}_group_responses 
            WHERE group_id = %s
        """, (db_group_id,))
        responses_data = cursor.fetchone()
        
        if not responses_data:
            return {'success': False, 'error': f'No review responses found for group {group_id}'}
        
        # Strip prefix if key exists
        if responses_data and 'group_id' in responses_data:
            responses_data['group_id'] = strip_year_prefix(responses_data['group_id'])
            
        # Calculate academic year
        submission_date = responses_data['submission_date']
        if isinstance(submission_date, str):
            date_obj = datetime.strptime(submission_date, '%Y-%m-%d')
            formatted_date = date_obj.strftime('%d/%m/%Y')
        else:
            # If it's already a date object
            formatted_date = submission_date.strftime('%d/%m/%Y')
        # Fetch questions
        cursor.execute(f"""
            SELECT question_id, section, question_text, display_order 
            FROM review{review_number}_questions 
            ORDER BY display_order
        """)
        questions = cursor.fetchall()
        
        # Group questions by section
        questions_by_section = {}
        section_order = []
        for q in questions:
            section = q['section']
            if section not in questions_by_section:
                questions_by_section[section] = []
                section_order.append(section)
            questions_by_section[section].append(q)
        
        ordered_questions = {section: questions_by_section[section] for section in section_order}
        
        # Fetch performance criteria
        cursor.execute(f"""
            SELECT criteria_id, criteria_text, max_marks, display_order 
            FROM review{review_number}_performance_criteria 
            ORDER BY display_order
        """)
        criteria_list = cursor.fetchall()
        
        # Fetch deliverables
        cursor.execute(f"""
            SELECT deliverable_text 
            FROM review{review_number}_deliverables 
            ORDER BY display_order
        """)
        deliverables = cursor.fetchall()
        
        # ADD THIS CODE HERE - Fetch panel assignments for reviewer names
        cursor.execute("""
            SELECT reviewer1, reviewer2, guide 
            FROM panel_assignments 
            WHERE group_id = %s
        """, (db_group_id,))
        panel_data = cursor.fetchone()

        reviewer1_name = None
        reviewer2_name = None
        guide_from_panel = None

        if panel_data:
            reviewer1_name = panel_data.get('reviewer1')
            reviewer2_name = panel_data.get('reviewer2')
            guide_from_panel = panel_data.get('guide')

        # Use guide from panel_assignments if available, otherwise use from projects table
        final_guide_name = guide_from_panel if guide_from_panel else project_data.get('guide_name', 'N/A')

        # Prepare output filename
        if not output_filename:
            output_filename = f"Review{review_number}_{group_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        
        output_path = os.path.join('frontend', 'static', 'pdfs', output_filename)
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Generate PDF
        pdf = GenericReviewPDFGenerator(output_path, review_number)
        # Use admin-set academic year from DB (persisted in system_settings)
        # This ensures the PDF always shows the year the admin has configured,
        # not a year derived from the submission date.
        academic_year = get_academic_year()
        
        # Determine section title for checklist
        review_roman = REVIEW_ROMAN.get(review_number, str(review_number))
        if review_number == 1:
            section_title = f"REVIEW – {review_roman} CHECKLIST : FINALIZATION OF SCOPE"
        elif review_number == 2:
            section_title = f"REVIEW – {review_roman} CHECKLIST : DESIGN"
        elif review_number == 0:
            section_title = f"REVIEW – SEM-I MOCK CHECKLIST : DESIGN"
        elif review_number == 3:
            section_title = f"REVIEW – {review_roman} CHECKLIST : IMPLEMENTATION"
        elif review_number == 4:
            section_title = f"REVIEW – {review_roman} CHECKLIST : TESTING"
        elif review_number == 6:
            section_title = f"REVIEW – SEM-II MOCK CHECKLIST : IMPLEMENTATION AND TESTING"
        else:
            section_title = f"REVIEW – {review_roman} CHECKLIST"
        
        # Page 1
        pdf.add_header(academic_year)
        pdf.add_project_info(project_data, formatted_date, final_guide_name)
        pdf.add_members_table(members)
        pdf.add_checklist_section(section_title, ordered_questions, responses_data)
        
        # Page 2
        pdf.add_page_break(academic_year)
        pdf.add_performance_table(members, marks_data, criteria_list)
        pdf.add_comments_section(responses_data.get('comments'))
        pdf.add_deliverables_section(deliverables)
        pdf.add_signatures(final_guide_name, reviewer1_name, reviewer2_name)
        
        pdf.build()
        
        return {
            'success': True,
            'filename': output_filename,
            'path': output_path
        }
    
    except Exception as e:
        print(f"Error generating PDF: {e}")
        import traceback
        traceback.print_exc()
        return {'success': False, 'error': str(e)}
    
    finally:
        close_connection(conn)
        


# Convenience functions for backward compatibility
def generate_review1_pdf(group_id, output_filename=None):
    """Generate Review 1 PDF"""
    return generate_review_pdf(1, group_id, output_filename)

def generate_review0_pdf(group_id, output_filename=None):
    """Generate MOCK PDF"""
    return generate_review_pdf(0, group_id, output_filename)

def generate_review2_pdf(group_id, output_filename=None):
    """Generate Review 2 PDF"""
    return generate_review_pdf(2, group_id, output_filename)

def generate_review3_pdf(group_id, output_filename=None):
    """Generate Review 3 PDF"""
    return generate_review_pdf(3, group_id, output_filename)

def generate_review4_pdf(group_id, output_filename=None):
    """Generate Review 4 PDF"""
    return generate_review_pdf(4, group_id, output_filename)

def generate_review6_pdf(group_id, output_filename=None):
    """Generate Review 6 (SEM-II MOCK) PDF"""
    return generate_review_pdf(6, group_id, output_filename)


def generate_review5_pdf(group_id, output_filename=None):
    """
    Generate the final summary PDF (Review 5) for a given group.
    """
    from backend.finalSheet import get_final_summary_data, get_overall_comments

    # 1. Fetch all necessary data
    summary_data = get_final_summary_data(group_id)
    
    if not summary_data:
        return {'success': False, 'error': f'No summary data found for group {group_id}'}

    overall_comments = get_overall_comments(group_id) or ''

    group_info = summary_data['group_info']
    members = summary_data['members']
    review_marks = summary_data['review_marks']

    # 2. Prepare output filename and path
    if not output_filename:
        output_filename = f"Review5_Final_Summary_{group_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    
    output_path = os.path.join('frontend', 'static', 'pdfs', output_filename)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # 3. Setup PDF generator
    # We can reuse the GenericReviewPDFGenerator for its setup and some basic styles
    pdf = GenericReviewPDFGenerator(output_path, 5) 
    pdf.review_roman = "I to IV" # Override for the title
    
    # Manually calculate academic year as there is no submission date for review 5
    academic_year = get_academic_year()

    # 4. Build PDF content
    # Header
    pdf.add_header(academic_year)
    pdf.elements.append(Paragraph("Summary of Project Work Evaluation Sheet", pdf.styles['CustomSubtitle']))
    pdf.elements.append(Spacer(1, 0.2 * inch))

    # Summary Table
    table_header = ['Sr.No.', 'Roll No.', 'Name of the Student', 'I', 'II', 'III', 'IV', 'Total', 'Student Signature']
    table_data = [table_header]
    
    for i, member in enumerate(members, 1):
        roll_no = member['roll_no']
        
        r1_att = bool(member.get('review1_attendance'))
        r2_att = bool(member.get('review2_attendance'))
        r3_att = bool(member.get('review3_attendance'))
        r4_att = bool(member.get('review4_attendance'))

        r1_val = float(review_marks.get('review1', {}).get(roll_no, 0) or 0)
        r2_val = float(review_marks.get('review2', {}).get(roll_no, 0) or 0)
        r3_val = float(review_marks.get('review3', {}).get(roll_no, 0) or 0)
        r4_val = float(review_marks.get('review4', {}).get(roll_no, 0) or 0)
        
        r1_str = f"{r1_val:.1f}" if r1_att else "Absent"
        r2_str = f"{r2_val:.1f}" if r2_att else "Absent"
        r3_str = f"{r3_val:.1f}" if r3_att else "Absent"
        r4_str = f"{r4_val:.1f}" if r4_att else "Absent"

        total_marks = (r1_val if r1_att else 0) + (r2_val if r2_att else 0) + (r3_val if r3_att else 0) + (r4_val if r4_att else 0)
        total_str = f"{total_marks:.0f}" if total_marks == int(total_marks) else f"{total_marks:.1f}"

        row = [
            str(i),
            roll_no,
            member['student_name'],
            r1_str,
            r2_str,
            r3_str,
            r4_str,
            Paragraph(f"<b>{total_str}</b>", pdf.styles['CenteredNormal']),
            '' # Placeholder for signature
        ]
        table_data.append(row)

    col_widths = [0.5*inch, 0.8*inch, 1.7*inch, 0.5*inch, 0.5*inch, 0.5*inch, 0.5*inch, 0.7*inch, 1.3*inch]
    summary_table = Table(table_data, colWidths=col_widths)
    summary_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (2, 1), (2, -1), 'LEFT'), # Align student names to the left
    ]))
    pdf.elements.append(summary_table)
    pdf.elements.append(Spacer(1, 0.2 * inch))

    # Overall Remarks
    total_table_width = sum(col_widths)
    comments_data = [
        [Paragraph('<b>Overall Remarks or Comments(if any):</b>', pdf.styles['Normal'])],
        [Paragraph(overall_comments.replace('\n', '<br/>\n'), pdf.styles['Normal'])]
    ]
    comments_table = Table(comments_data, colWidths=[total_table_width], rowHeights=[0.3*inch, 1.5*inch])
    comments_table.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
    ]))
    pdf.elements.append(comments_table)
    pdf.elements.append(Spacer(1, 0.5 * inch))

    # Signatures
    guide_name = group_info.get('guide_name', 'N/A')
    reviewer1_name = group_info.get('reviewer1_name', 'N/A')
    reviewer2_name = group_info.get('reviewer2_name', 'N/A')
    pdf.add_signatures(guide_name, reviewer1_name, reviewer2_name)
    
    # 5. Build the PDF
    try:
        pdf.build()
        return {'success': True, 'filename': output_filename, 'path': output_path}
    except Exception as e:
        print(f"Error building Review 5 PDF: {e}")
        import traceback
        traceback.print_exc()
        return {'success': False, 'error': str(e)}