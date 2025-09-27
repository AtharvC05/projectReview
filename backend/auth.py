from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for
import bcrypt
import mysql.connector
import logging
from functools import wraps
from datetime import datetime
import json


logger = logging.getLogger(__name__)
bp = Blueprint('auth', __name__, template_folder='templates')


def connect_db():
    """Database connection with error handling."""
    try:
        return mysql.connector.connect(
            host='localhost',
            user='root',
            password='1234',
            database='project_review1',
            autocommit=True,
        )
    except mysql.connector.Error as e:
        logger.error(f"Database connection error: {e}")
        raise


# Password hashing utilities
def hash_password(password):
    """Hash password using bcrypt."""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def verify_password(password, hashed):
    """Verify password against hash."""
    try:
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
    except Exception as e:
        logger.error(f"Password verification error: {e}")
        return False


# Decorators for route protection
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('auth.login'))
        if session.get('role') != 'admin':
            return jsonify({'error': 'Admin access required'}), 403
        return f(*args, **kwargs)
    return decorated_function


def user_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('auth.login'))
        if session.get('role') not in ['admin', 'user']:
            return jsonify({'error': 'User access required'}), 403
        return f(*args, **kwargs)
    return decorated_function


# Routes

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        data = request.get_json() or {}
        username = data.get('username', '').strip()
        password = data.get('password', '')

        if not username or not password:
            return jsonify({'error': 'Username and password required'}), 400

        try:
            conn = connect_db()
            cursor = conn.cursor(dictionary=True)

            cursor.execute("""
                SELECT id, username, password_hash, role, active 
                FROM users WHERE username = %s AND active = TRUE
            """, (username,))

            user = cursor.fetchone()
            cursor.close()
            conn.close()

            if user and verify_password(password, user['password_hash']):
                # Update last login timestamp
                conn = connect_db()
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = %s
                """, (user['id'],))
                cursor.close()
                conn.close()

                # Set session variables
                session['user_id'] = user['id']
                session['username'] = user['username']
                session['role'] = user['role']

                return jsonify({
                    'success': True,
                    'role': user['role'],
                    'username': user['username'],
                    'redirect': '/' if user['role'] == 'admin' else '/review/1'
                })
            else:
                return jsonify({'error': 'Invalid credentials'}), 401

        except Exception as e:
            logger.error(f"Login error: {e}")
            return jsonify({'error': 'Login failed'}), 500

    # For GET request, serve login page
    return render_template('login.html')


@bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth.login'))


# Add this route for public user registration (replace existing register route)
@bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        data = request.get_json()
        username = data.get('username', '').strip()
        password = data.get('password', '')
        confirm_password = data.get('confirm_password', '')
        security_answers = data.get('security_answers', [])
        
        # Validation
        if not username or not password:
            return jsonify({'error': 'Username and password required'}), 400
            
        if password != confirm_password:
            return jsonify({'error': 'Passwords do not match'}), 400
            
        # Password constraints
        if len(password) < 8:
            return jsonify({'error': 'Password must be at least 8 characters long'}), 400
        if not any(c.isupper() for c in password):
            return jsonify({'error': 'Password must contain at least one uppercase letter'}), 400
        if not any(c.islower() for c in password):
            return jsonify({'error': 'Password must contain at least one lowercase letter'}), 400
        if not any(c.isdigit() for c in password):
            return jsonify({'error': 'Password must contain at least one number'}), 400
            
        if len(security_answers) != 3:
            return jsonify({'error': 'Exactly 3 security questions required'}), 400
            
        try:
            conn = connect_db()
            cursor = conn.cursor()
            
            # Check if username already exists
            cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
            if cursor.fetchone():
                return jsonify({'error': 'Username already exists'}), 400
                
            # Create user with default role 'user'
            password_hash = hash_password(password)
            cursor.execute("""
                INSERT INTO users (username, password_hash, role)
                VALUES (%s, %s, 'user')
            """, (username, password_hash))
            
            user_id = cursor.lastrowid
            
            # Store security answers
            for answer_data in security_answers:
                question_id = answer_data.get('question_id')
                answer = answer_data.get('answer', '').strip().lower()
                
                if question_id and answer:
                    answer_hash = hash_password(answer)
                    cursor.execute("""
                        INSERT INTO user_security_answers (user_id, question_id, answer_hash)
                        VALUES (%s, %s, %s)
                    """, (user_id, question_id, answer_hash))
                    
            cursor.close()
            conn.close()
            
            return jsonify({'success': True, 'message': 'Account created successfully'})
            
        except Exception as e:
            logger.error(f"Registration error: {e}")
            return jsonify({'error': 'Registration failed'}), 500
    
    # GET request - serve registration page
    try:
        conn = connect_db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id, question FROM security_questions WHERE active = TRUE")
        questions = cursor.fetchall()
        cursor.close()
        conn.close()
        
        return render_template('register.html', questions=questions)
        
    except Exception as e:
        logger.error(f"Error fetching security questions: {e}")
        return render_template('register.html', questions=[])

# Add route to get security questions for frontend
@bp.route('/api/security-questions', methods=['GET'])
def get_security_questions():
    try:
        conn = connect_db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id, question FROM security_questions WHERE active = TRUE")
        questions = cursor.fetchall()
        cursor.close()
        conn.close()
        
        return jsonify({'questions': questions})
        
    except Exception as e:
        logger.error(f"Error fetching security questions: {e}")
        return jsonify({'error': 'Failed to fetch security questions'}), 500

@bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        data = request.get_json()
        username = data.get('username', '').strip()

        if not username:
            return jsonify({'error': 'Username required'}), 400

        try:
            conn = connect_db()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT u.id, u.username, sq.id as question_id, sq.question
                FROM users u
                JOIN user_security_answers usa ON u.id = usa.user_id
                JOIN security_questions sq ON usa.question_id = sq.id
                WHERE u.username = %s AND u.active = TRUE AND sq.active = TRUE
            """, (username,))

            user_questions = cursor.fetchall()
            cursor.close()
            conn.close()

            if not user_questions:
                return jsonify({'error': 'User not found or no security questions set'}), 404

            questions = [{'id': q['question_id'], 'question': q['question']} for q in user_questions]

            return jsonify({
                'success': True,
                'user_id': user_questions[0]['id'],
                'questions': questions
            })

        except Exception as e:
            logger.error(f"Forgot password error: {e}")
            return jsonify({'error': 'Failed to retrieve security questions'}), 500

    return render_template('forgot_password.html')


@bp.route('/reset-password', methods=['POST'])
def reset_password():
    data = request.get_json()
    user_id = data.get('user_id')
    answers = data.get('answers', [])
    new_password = data.get('new_password', '')

    if not user_id or not answers or not new_password:
        return jsonify({'error': 'All fields required'}), 400

    if len(answers) < 3:
        return jsonify({'error': 'At least 3 security answers required'}), 400

    try:
        conn = connect_db()
        cursor = conn.cursor()

        correct_answers = 0
        for answer_data in answers:
            question_id = answer_data.get('question_id')
            answer = answer_data.get('answer', '').strip().lower()

            cursor.execute("""
                SELECT answer_hash FROM user_security_answers
                WHERE user_id = %s AND question_id = %s
            """, (user_id, question_id))

            stored = cursor.fetchone()
            if stored and verify_password(answer, stored[0]):
                correct_answers += 1

        if correct_answers < 3:
            return jsonify({'error': 'Incorrect security answers'}), 401

        password_hash = hash_password(new_password)
        cursor.execute("""
            UPDATE users SET password_hash = %s WHERE id = %s
        """, (password_hash, user_id))

        cursor.close()
        conn.close()

        return jsonify({'success': True, 'message': 'Password reset successfully'})

    except Exception as e:
        logger.error(f"Reset password error: {e}")
        return jsonify({'error': 'Password reset failed'}), 500


# Add initialization function to create default users with proper passwords
def initialize_default_users():
    """Create default users if they don't exist"""
    try:
        conn = connect_db()
        cursor = conn.cursor()
        
        # Check if admin exists
        cursor.execute("SELECT id FROM users WHERE username = 'admin'")
        if not cursor.fetchone():
            # Create admin user with password 'admin123'
            admin_hash = hash_password('admin123')
            cursor.execute("""
                INSERT INTO users (username, password_hash, role) 
                VALUES ('admin', %s, 'admin')
            """, (admin_hash,))
            logger.info("Created default admin user")
        
        # Check if evaluator1 exists
        cursor.execute("SELECT id FROM users WHERE username = 'evaluator1'")
        if not cursor.fetchone():
            # Create evaluator1 with password 'user123'
            user_hash = hash_password('user123')
            cursor.execute("""
                INSERT INTO users (username, password_hash, role) 
                VALUES ('evaluator1', %s, 'user')
            """, (user_hash,))
            logger.info("Created default evaluator1 user")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        logger.error(f"Error initializing default users: {e}")


@bp.route('/api/users', methods=['GET'])
@admin_required
def get_users():
    try:
        conn = connect_db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT id, username, role, created_at, last_login, active
            FROM users ORDER BY created_at DESC
        """)
        users = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify({'users': users})
    except Exception as e:
        logger.error(f"Get users error: {e}")
        return jsonify({'error': 'Failed to fetch users'}), 500


@bp.route('/api/users/<int:user_id>', methods=['DELETE'])
@admin_required
def delete_user(user_id):
    try:
        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET active = FALSE WHERE id = %s", (user_id,))
        if cursor.rowcount == 0:
            return jsonify({'error': 'User not found'}), 404
        cursor.close()
        conn.close()
        return jsonify({'success': True, 'message': 'User deactivated'})
    except Exception as e:
        logger.error(f"Delete user error: {e}")
        return jsonify({'error': 'Failed to deactivate user'}), 500


@bp.route('/api/admin-reset-password', methods=['POST'])
@admin_required
def admin_reset_password():
    data = request.get_json()
    user_id = data.get('user_id')
    new_password = data.get('new_password')
    if not user_id or not new_password:
        return jsonify({'error': 'User ID and new password required'}), 400
    try:
        conn = connect_db()
        cursor = conn.cursor()
        password_hash = hash_password(new_password)
        cursor.execute("UPDATE users SET password_hash = %s WHERE id = %s", (password_hash, user_id))
        if cursor.rowcount == 0:
            return jsonify({'error': 'User not found'}), 404
        cursor.close()
        conn.close()
        return jsonify({'success': True, 'message': 'Password reset successfully'})
    except Exception as e:
        logger.error(f"Admin reset password error: {e}")
        return jsonify({'error': 'Password reset failed'}), 500