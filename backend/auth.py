# backend/auth.py
"""
Authentication module with Email OTP verification
- Registration with email OTP
- Login with username/password
- Forgot password with email OTP
- No security questions required
"""

from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for
import bcrypt
import logging
from functools import wraps
from datetime import datetime
import secrets
from backend.db import get_connection, close_connection
from backend.email_service import email_service
from backend.otp_storage import otp_storage

logger = logging.getLogger(__name__)
bp = Blueprint('auth', __name__, template_folder='templates')


# ============================================
# Password Hashing Utilities
# ============================================

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


# ============================================
# Route Protection Decorators
# ============================================

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


# ============================================
# Login Route
# ============================================

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        data = request.get_json() or {}
        email = data.get('email', '').strip().lower()
        password = data.get('password', '')

        if not email or not password:
            return jsonify({'error': 'Email and password required'}), 400

        try:
            conn = get_connection()
            if not conn:
                return jsonify({'error': 'Database connection failed'}), 500
                
            cursor = conn.cursor(dictionary=True)

            cursor.execute("""
                SELECT id, username, email, password_hash, role, active, email_verified 
                FROM users WHERE email = %s AND active = TRUE
            """, (email,))

            user = cursor.fetchone()
            cursor.close()
            close_connection(conn)

            if user and verify_password(password, user['password_hash']):
                # Check if email is verified
                if not user.get('email_verified', False):
                    return jsonify({
                        'error': 'Email not verified. Please verify your email first.'
                    }), 403
                
                # Update last login timestamp
                conn = get_connection()
                if conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = %s
                    """, (user['id'],))
                    conn.commit()
                    cursor.close()
                    close_connection(conn)

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


# ============================================
# Registration Routes
# ============================================

@bp.route('/register', methods=['GET', 'POST'])
def register():
    """Registration page and initial submission"""
    if request.method == 'GET':
        return render_template('register.html')
    
    # POST - Process registration request
    try:
        data = request.get_json()
        email = data.get('email', '').strip().lower()
        password = data.get('password', '')
        confirm_password = data.get('confirm_password', '')
        
        # Validation
        if not email or not password:
            return jsonify({'error': 'Email and password are required'}), 400
        
        if password != confirm_password:
            return jsonify({'error': 'Passwords do not match'}), 400
        
        # Email validation
        if '@' not in email or '.' not in email:
            return jsonify({'error': 'Invalid email format'}), 400
        
        # Password strength validation
        if len(password) < 8:
            return jsonify({'error': 'Password must be at least 8 characters'}), 400
        if not any(c.isupper() for c in password):
            return jsonify({'error': 'Password must contain uppercase letter'}), 400
        if not any(c.islower() for c in password):
            return jsonify({'error': 'Password must contain lowercase letter'}), 400
        if not any(c.isdigit() for c in password):
            return jsonify({'error': 'Password must contain a number'}), 400
        
        # Check if email already exists
        conn = get_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
        
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("SELECT email FROM users WHERE email = %s", (email,))
        
        existing = cursor.fetchone()
        cursor.close()
        close_connection(conn)
        
        if existing:
            return jsonify({'error': 'Email already registered'}), 400
        
        # Generate and send OTP
        success, message, otp = email_service.send_registration_otp(email)
        
        if not success:
            return jsonify({'error': 'Failed to send OTP'}), 500
        
        # Store registration data temporarily in session
        session['pending_registration'] = {
            'email': email,
            'password_hash': hash_password(password),
            'timestamp': datetime.now().isoformat()
        }
        
        return jsonify({
            'success': True,
            'message': 'OTP sent to your email',
            'email': email
        })
        
    except Exception as e:
        logger.error(f"Registration error: {e}")
        return jsonify({'error': 'Registration failed'}), 500


@bp.route('/verify-registration-otp', methods=['POST'])
def verify_registration_otp():
    """Verify OTP and complete registration"""
    try:
        data = request.get_json()
        otp = data.get('otp', '').strip()
        
        if not otp:
            return jsonify({'error': 'OTP is required'}), 400
        
        # Get pending registration data from session
        pending = session.get('pending_registration')
        if not pending:
            return jsonify({'error': 'No pending registration found'}), 400
        
        email = pending['email']
        
        # Verify OTP
        success, message = email_service.verify_otp(email, otp, purpose='registration')
        
        if not success:
            return jsonify({'error': message}), 400
        
        # Create user account
        conn = get_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
        
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO users (username, email, password_hash, role, email_verified)
            VALUES (%s, %s, %s, 'user', TRUE)
        """, (pending['email'], pending['email'], pending['password_hash']))
        
        conn.commit()
        cursor.close()
        close_connection(conn)
        
        # Clean up
        session.pop('pending_registration', None)
        otp_storage.delete_otp(email, purpose='registration')
        
        return jsonify({
            'success': True,
            'message': 'Registration successful! You can now login.'
        })
        
    except Exception as e:
        logger.error(f"OTP verification error: {e}")
        return jsonify({'error': 'Verification failed'}), 500


@bp.route('/resend-registration-otp', methods=['POST'])
def resend_registration_otp():
    """Resend OTP for registration"""
    try:
        pending = session.get('pending_registration')
        if not pending:
            return jsonify({'error': 'No pending registration found'}), 400
        
        email = pending['email']
        
        # Generate and send new OTP
        success, message, otp = email_service.send_registration_otp(email)
        
        if not success:
            return jsonify({'error': 'Failed to resend OTP'}), 500
        
        return jsonify({
            'success': True,
            'message': 'OTP resent successfully'
        })
        
    except Exception as e:
        logger.error(f"Resend OTP error: {e}")
        return jsonify({'error': 'Failed to resend OTP'}), 500


# ============================================
# Forgot Password Routes
# ============================================

@bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    """Forgot password page and request handler"""
    if request.method == 'GET':
        return render_template('forgot_password.html')
    
    # POST - Send password reset OTP
    try:
        data = request.get_json()
        email = data.get('email', '').strip().lower()
        
        if not email:
            return jsonify({'error': 'Email is required'}), 400
        
        # Check if user exists
        conn = get_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
        
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT id, username, email FROM users 
            WHERE email = %s AND active = TRUE
        """, (email,))
        
        user = cursor.fetchone()
        cursor.close()
        close_connection(conn)
        
        if not user:
            # Don't reveal if email exists for security
            return jsonify({
                'success': True,
                'message': 'If the email exists, an OTP has been sent'
            })
        
        # Generate and send OTP
        success, message, otp = email_service.send_password_reset_otp(email)
        
        if not success:
            return jsonify({'error': 'Failed to send OTP'}), 500
        
        # Store user_id in session for later use
        session['password_reset_email'] = email
        session['password_reset_user_id'] = user['id']
        
        return jsonify({
            'success': True,
            'message': 'OTP sent to your email'
        })
        
    except Exception as e:
        logger.error(f"Forgot password error: {e}")
        return jsonify({'error': 'Request failed'}), 500


@bp.route('/verify-reset-otp', methods=['POST'])
def verify_reset_otp():
    """Verify OTP for password reset"""
    try:
        data = request.get_json()
        otp = data.get('otp', '').strip()
        
        if not otp:
            return jsonify({'error': 'OTP is required'}), 400
        
        email = session.get('password_reset_email')
        if not email:
            return jsonify({'error': 'No password reset request found', 'redirect': url_for('auth.login')}), 400
        
        # Initialize attempts counter
        if 'otp_attempts' not in session:
            session['otp_attempts'] = 0

        # Verify OTP
        success, message = email_service.verify_otp(email, otp, purpose='password_reset')
        
        if not success:
            session['otp_attempts'] += 1
            if session['otp_attempts'] >= 3:
                # Clear session and redirect
                session.pop('password_reset_email', None)
                session.pop('password_reset_user_id', None)
                session.pop('otp_attempts', None)
                return jsonify({'error': 'Too many failed attempts. Please try again.', 'redirect': url_for('auth.login')}), 400
            
            return jsonify({'error': f'{message}. You have {3 - session["otp_attempts"]} attempts remaining.'}), 400
        
        # Mark as verified and reset attempts
        session['otp_verified'] = True
        session.pop('otp_attempts', None)
        
        return jsonify({
            'success': True,
            'message': 'OTP verified. You can now reset your password.'
        })
        
    except Exception as e:
        logger.error(f"OTP verification error: {e}")
        return jsonify({'error': 'Verification failed'}), 500


@bp.route('/reset-password', methods=['POST'])
def reset_password():
    """Reset password after OTP verification"""
    try:
        data = request.get_json()
        new_password = data.get('new_password', '')
        confirm_password = data.get('confirm_password', '')
        
        if not new_password or not confirm_password:
            return jsonify({'error': 'All fields are required'}), 400
        
        if new_password != confirm_password:
            return jsonify({'error': 'Passwords do not match'}), 400
        
        # Password strength validation
        if len(new_password) < 8:
            return jsonify({'error': 'Password must be at least 8 characters'}), 400
        if not any(c.isupper() for c in new_password):
            return jsonify({'error': 'Password must contain uppercase letter'}), 400
        if not any(c.islower() for c in new_password):
            return jsonify({'error': 'Password must contain lowercase letter'}), 400
        if not any(c.isdigit() for c in new_password):
            return jsonify({'error': 'Password must contain a number'}), 400
        
        # Check if OTP was verified
        if not session.get('otp_verified'):
            return jsonify({'error': 'OTP verification required'}), 400
        
        user_id = session.get('password_reset_user_id')
        email = session.get('password_reset_email')
        
        if not user_id or not email:
            return jsonify({'error': 'Invalid session'}), 400
        
        # Update password
        conn = get_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
        
        cursor = conn.cursor()
        password_hash = hash_password(new_password)
        
        cursor.execute("""
            UPDATE users SET password_hash = %s WHERE id = %s
        """, (password_hash, user_id))
        
        conn.commit()
        cursor.close()
        close_connection(conn)
        
        # Clean up session and OTP
        session.pop('password_reset_email', None)
        session.pop('password_reset_user_id', None)
        session.pop('otp_verified', None)
        otp_storage.delete_otp(email, purpose='password_reset')
        
        return jsonify({
            'success': True,
            'message': 'Password reset successfully!'
        })
        
    except Exception as e:
        logger.error(f"Password reset error: {e}")
        return jsonify({'error': 'Password reset failed'}), 500


@bp.route('/resend-reset-otp', methods=['POST'])
def resend_reset_otp():
    """Resend OTP for password reset"""
    try:
        email = session.get('password_reset_email')
        if not email:
            return jsonify({'error': 'No password reset request found'}), 400
        
        # Generate and send new OTP
        success, message, otp = email_service.send_password_reset_otp(email)
        
        if not success:
            return jsonify({'error': 'Failed to resend OTP'}), 500
        
        return jsonify({
            'success': True,
            'message': 'OTP resent successfully'
        })
        
    except Exception as e:
        logger.error(f"Resend OTP error: {e}")
        return jsonify({'error': 'Failed to resend OTP'}), 500


# ============================================
# Development/Debug Routes
# ============================================

@bp.route('/dev/view-otps', methods=['GET'])
def view_otps():
    """View all active OTPs (for development only)"""
    # Only enable in development
    if os.getenv('FLASK_ENV') != 'production':
        otps = otp_storage.get_all_otps()
        return jsonify({
            'otps': otps,
            'count': len(otps)
        })
    return jsonify({'error': 'Not available in production'}), 403


# ============================================
# User Management (Admin)
# ============================================

@bp.route('/api/users', methods=['GET'])
@admin_required
def get_users():
    """Get all users (admin only)"""
    try:
        conn = get_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
            
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT id, username, email, role, email_verified, 
                   created_at, last_login, active
            FROM users ORDER BY created_at DESC
        """)
        users = cursor.fetchall()
        cursor.close()
        close_connection(conn)
        return jsonify({'users': users})
    except Exception as e:
        logger.error(f"Get users error: {e}")
        return jsonify({'error': 'Failed to fetch users'}), 500


@bp.route('/api/users/<int:user_id>', methods=['DELETE'])
@admin_required
def delete_user(user_id):
    """Deactivate user (admin only)"""
    try:
        conn = get_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
            
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET active = FALSE WHERE id = %s", (user_id,))
        row_count = cursor.rowcount
        conn.commit()
        cursor.close()
        close_connection(conn)
        
        if row_count == 0:
            return jsonify({'error': 'User not found'}), 404
        return jsonify({'success': True, 'message': 'User deactivated'})
    except Exception as e:
        logger.error(f"Delete user error: {e}")
        return jsonify({'error': 'Failed to deactivate user'}), 500


@bp.route('/api/admin-reset-password', methods=['POST'])
@admin_required
def admin_reset_password():
    """Reset user password (admin only)"""
    data = request.get_json()
    user_id = data.get('user_id')
    new_password = data.get('new_password')
    
    if not user_id or not new_password:
        return jsonify({'error': 'User ID and password required'}), 400
        
    try:
        conn = get_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
            
        cursor = conn.cursor()
        password_hash = hash_password(new_password)
        cursor.execute(
            "UPDATE users SET password_hash = %s WHERE id = %s", 
            (password_hash, user_id)
        )
        row_count = cursor.rowcount
        conn.commit()
        cursor.close()
        close_connection(conn)
        
        if row_count == 0:
            return jsonify({'error': 'User not found'}), 404
        return jsonify({'success': True, 'message': 'Password reset successfully'})
    except Exception as e:
        logger.error(f"Admin reset password error: {e}")
        return jsonify({'error': 'Password reset failed'}), 500


# ============================================
# Initialization
# ============================================

def initialize_default_users():
    """Create default admin user if doesn't exist"""
    try:
        conn = get_connection()
        if not conn:
            logger.error("Cannot initialize users - database connection failed")
            return
            
        cursor = conn.cursor()
        
        # Check if admin exists
        cursor.execute("SELECT id FROM users WHERE username = 'admin'")
        if not cursor.fetchone():
            # Create admin user
            admin_hash = hash_password('Admin@789')
            cursor.execute("""
                INSERT INTO users (username, email, password_hash, role, email_verified) 
                VALUES ('admin', 'admin@i2it.edu', %s, 'admin', TRUE)
            """, (admin_hash,))
            logger.info("Created default admin user")
            conn.commit()
        
        cursor.close()
        close_connection(conn)
        
    except Exception as e:
        logger.error(f"Error initializing default users: {e}")


# Import os for environment check
import os