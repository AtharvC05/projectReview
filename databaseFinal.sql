-- =====================================================
-- Database Schema for Project Review System
-- =====================================================

-- Use or create database
CREATE DATABASE IF NOT EXISTS project_review1;
USE project_review1;

-- =====================================================
-- Projects Table
-- =====================================================
CREATE TABLE IF NOT EXISTS projects (
    group_id VARCHAR(50) PRIMARY KEY,
    project_title TEXT,
    guide_name TEXT,
    mentor_name TEXT,
    mentor_email TEXT,
    mentor_mobile TEXT,
    evaluator1_name TEXT,
    evaluator2_name TEXT,
    division VARCHAR(10),
    project_domain TEXT,
    sponsor_company TEXT
);

-- =====================================================
-- Members Table
-- =====================================================
CREATE TABLE IF NOT EXISTS members (
    group_id VARCHAR(50),
    roll_no VARCHAR(50),
    student_name TEXT,
    contact_details TEXT,
    review1_attendance BOOLEAN DEFAULT FALSE,
    review2_attendance BOOLEAN DEFAULT FALSE,
    review3_attendance BOOLEAN DEFAULT FALSE,
    review4_attendance BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (group_id) REFERENCES projects(group_id) ON DELETE CASCADE,
    UNIQUE KEY unique_roll (roll_no)
);

-- =====================================================
-- Panel Assignments
-- =====================================================
CREATE TABLE IF NOT EXISTS panel_assignments (
    group_id VARCHAR(50) PRIMARY KEY,
    track INT,
    panel_professors TEXT,
    location VARCHAR(255),
    guide VARCHAR(255),
    reviewer1 VARCHAR(255),
    reviewer2 VARCHAR(255),
    reviewer3 VARCHAR(255),
    FOREIGN KEY (group_id) REFERENCES projects(group_id) ON DELETE CASCADE
);

-- =====================================================
-- Responses Table
-- =====================================================
CREATE TABLE IF NOT EXISTS responses (
    id INT NOT NULL AUTO_INCREMENT,
    group_id VARCHAR(50) NOT NULL,
    review_num INT NOT NULL DEFAULT 1,
    field_name VARCHAR(100) NOT NULL,
    field_value TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY unique_group_review_field (group_id, review_num, field_name),
    INDEX idx_group_id (group_id),
    INDEX idx_group_review (group_id, review_num)
);

-- =====================================================
-- Users Table (Authentication)
-- =====================================================
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role ENUM('admin', 'user') DEFAULT 'user',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP NULL,
    active BOOLEAN DEFAULT TRUE,
    INDEX idx_username (username),
    INDEX idx_role (role)
);

-- =====================================================
-- Security Questions Table
-- =====================================================
CREATE TABLE IF NOT EXISTS security_questions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    question VARCHAR(255) NOT NULL,
    active BOOLEAN DEFAULT TRUE
);

-- Default security questions
INSERT INTO security_questions (question, active) VALUES
('What was the name of your first pet?', TRUE),
('In what city were you born?', TRUE),
('What is your mother''s maiden name?', TRUE),
('What was the name of your elementary school?', TRUE),
('What is the name of your favorite teacher?', TRUE),
('What was your first car model?', TRUE),
('What is your favorite book?', TRUE),
('What was the name of your childhood best friend?', TRUE),
('In what city did you meet your spouse?', TRUE),
('What is your favorite food?', TRUE),
('What is your favorite color?', TRUE),
('What is your favorite sport?', TRUE),
('What is your favorite movie?', TRUE),
('What is your favorite song?', TRUE),
('What is your favorite holiday destination?', TRUE),
('What is your favorite fruit?', TRUE),
('What was your favorite subject?', TRUE),
('What is your favorite festival?', TRUE),
('Who is your favorite cartoon character?', TRUE),
('What is your favorite animal?', TRUE);

-- =====================================================
-- User Security Answers
-- =====================================================
CREATE TABLE IF NOT EXISTS user_security_answers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    question_id INT NOT NULL,
    answer_hash VARCHAR(255) NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (question_id) REFERENCES security_questions(id) ON DELETE CASCADE,
    UNIQUE KEY unique_user_question (user_id, question_id)
);
