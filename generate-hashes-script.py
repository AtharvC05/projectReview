#!/usr/bin/env python3
"""
Script to generate bcrypt password hashes for the database
Run this to get the correct hashes for your SQL inserts
"""

import bcrypt
import mysql.connector

def generate_hash(password):
    """Generate bcrypt hash for a password"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def connect_db():
    """Connect to MySQL database"""
    try:
        return mysql.connector.connect(
            host='localhost',
            user='root',
            password='1234',
            database='project_review',
            autocommit=True,
        )
    except mysql.connector.Error as e:
        print(f"Database connection error: {e}")
        return None

def setup_default_users():
    """Setup default users with correct password hashes"""
    conn = connect_db()
    if not conn:
        print("Failed to connect to database")
        return
    
    cursor = conn.cursor()
    
    try:
        # Generate hashes
        admin_hash = generate_hash('admin123')
        user_hash = generate_hash('user123')
        answer_hash = generate_hash('answer')
        
        print("\n=== Generated Password Hashes ===")
        print(f"Admin hash for 'admin123': {admin_hash}")
        print(f"User hash for 'user123': {user_hash}")
        print(f"Answer hash for 'answer': {answer_hash}")
        
        # Clear existing users
        cursor.execute("DELETE FROM user_security_answers")
        cursor.execute("DELETE FROM users")
        
        # Insert users with correct hashes
        cursor.execute("""
            INSERT INTO users (username, password_hash, role) VALUES 
            ('admin', %s, 'admin')
        """, (admin_hash,))
        admin_id = cursor.lastrowid
        
        cursor.execute("""
            INSERT INTO users (username, password_hash, role) VALUES 
            ('evaluator1', %s, 'user')
        """, (user_hash,))
        
        cursor.execute("""
            INSERT INTO users (username, password_hash, role) VALUES 
            ('evaluator2', %s, 'user')
        """, (user_hash,))
        
        # Add security answers for admin (for testing forgot password)
        for question_id in [1, 2, 3]:
            cursor.execute("""
                INSERT INTO user_security_answers (user_id, question_id, answer_hash) 
                VALUES (%s, %s, %s)
            """, (admin_id, question_id, answer_hash))
        
        conn.commit()
        print("\n✅ Users created successfully!")
        print("\nDefault Credentials:")
        print("  Admin: admin / admin123")
        print("  User: evaluator1 / user123")
        print("  User: evaluator2 / user123")
        print("\nSecurity answers for admin password recovery: 'answer' (for all questions)")
        
    except Exception as e:
        print(f"Error: {e}")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    print("Setting up default users with correct password hashes...")
    setup_default_users()