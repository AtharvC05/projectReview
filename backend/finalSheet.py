# backend/finalSheet.py
from backend.db import get_connection, close_connection, add_year_prefix, strip_year_prefix
from backend.commonBackend import validate_group_id
from typing import List, Dict, Optional


def get_final_summary_data(group_id: str) -> Optional[Dict]:
    """
    Fetch complete summary data for all reviews for a given group
    Returns: {
        'group_info': {...},
        'members': [...],
        'review_marks': {
            'review1': [...],
            'review2': [...],
            'review3': [...],
            'review4': [...]
        }
    }
    """
    if not validate_group_id(group_id):
        print(f"Invalid group_id format: {group_id}")
        return None
    
    conn = get_connection()
    if not conn:
        return None
    
    try:
        cursor = conn.cursor(dictionary=True)
        db_group_id = add_year_prefix(group_id)
        
        # 1. Get project information
        cursor.execute("""
            SELECT 
                p.group_id,
                p.project_title,
                p.guide_name,
                p.division,
                p.project_domain,
                p.sponsor_company,
                p.evaluator1_name,
                p.evaluator2_name
            FROM projects p
            WHERE p.group_id = %s
        """, (db_group_id,))
        
        group_info = cursor.fetchone()
        
        if not group_info:
            print(f"No project found for group_id: {db_group_id}")
            return None
        
        # Strip prefix from returned group_id
        group_info['group_id'] = strip_year_prefix(group_info['group_id'])
        
        # 2. Get all members
        cursor.execute("""
            SELECT 
                roll_no,
                student_name,
                review1_attendance,
                review2_attendance,
                review3_attendance,
                review4_attendance
            FROM members
            WHERE group_id = %s
            ORDER BY roll_no
        """, (db_group_id,))
        
        members = cursor.fetchall()
        
        if not members:
            print(f"No members found for group_id: {db_group_id}")
            return None
        
        # Strip prefix from returned roll numbers
        for m in members:
            m['roll_no'] = strip_year_prefix(m['roll_no'])
        
        # 3. Get marks for all reviews
        review_marks = {}
        
        for review_num in range(1, 5):
            table_name = f"review{review_num}_marks"
            
            cursor.execute(f"""
                SELECT 
                    roll_no,
                    total
                FROM {table_name}
                WHERE group_id = %s
                ORDER BY roll_no
            """, (db_group_id,))
            
            marks_data = cursor.fetchall()
            
            # Convert to dict for easy lookup and strip roll_no prefixes
            marks_dict = {strip_year_prefix(row['roll_no']): row['total'] for row in marks_data}
            review_marks[f'review{review_num}'] = marks_dict
        
        # 4. Get panel assignments for reviewer names
        cursor.execute("""
            SELECT reviewer1, reviewer2, guide 
            FROM panel_assignments 
            WHERE group_id = %s
        """, (db_group_id,))
        panel_data = cursor.fetchone()
 
        if panel_data:
            group_info['reviewer1_name'] = panel_data.get('reviewer1')
            group_info['reviewer2_name'] = panel_data.get('reviewer2')
            # Override guide name if available in panel_assignments
            if panel_data.get('guide'):
                group_info['guide_name'] = panel_data.get('guide')
        
        # 5. Build final result
        result = {
            'group_info': group_info,
            'members': members,
            'review_marks': review_marks
        }
        
        print(f"Final summary data fetched for group: {group_id}")
        return result
        
    except Exception as e:
        print(f"Error fetching final summary data: {e}")
        import traceback
        traceback.print_exc()
        return None
        
    finally:
        close_connection(conn)


def get_overall_comments(group_id: str) -> Optional[str]:
    """
    Fetch overall remarks/comments for the group from final_sheet table
    """
    if not validate_group_id(group_id):
        return None
    
    conn = get_connection()
    if not conn:
        return None
    
    try:
        cursor = conn.cursor(dictionary=True)
        db_group_id = add_year_prefix(group_id)
        
        cursor.execute("""
            SELECT overall_comments
            FROM final_sheet
            WHERE group_id = %s
        """, (db_group_id,))
        
        result = cursor.fetchone()
        
        if result:
            return result['overall_comments']
        return None
        
    except Exception as e:
        print(f"Error fetching overall comments: {e}")
        return None
    
    finally:
        close_connection(conn)


def save_overall_comments(group_id: str, comments: str) -> bool:
    """
    Save or update overall remarks/comments for the group
    """
    if not validate_group_id(group_id):
        print(f"Invalid group_id format: {group_id}")
        return False
    
    conn = get_connection()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        db_group_id = add_year_prefix(group_id)
        
        # Limit comment length
        safe_comments = comments[:2000] if comments else None
        
        query = """
            INSERT INTO final_sheet (group_id, overall_comments)
            VALUES (%s, %s)
            ON DUPLICATE KEY UPDATE 
                overall_comments = VALUES(overall_comments),
                updated_at = CURRENT_TIMESTAMP
        """
        
        cursor.execute(query, (db_group_id, safe_comments))
        conn.commit()
        
        print(f"Overall comments saved for group: {group_id}")
        return True
        
    except Exception as e:
        conn.rollback()
        print(f"Error saving overall comments: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        close_connection(conn)