-- Create the main database
CREATE DATABASE IF NOT EXISTS project_review;
USE project_review;

-- ================== MAIN PROJECT TABLES ==================

-- Projects table
CREATE TABLE projects (
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

-- Members table
CREATE TABLE members (
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

-- Panel assignments
CREATE TABLE panel_assignments (
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

-- ================== FACULTY + BATCH TABLES ==================

-- Faculty
CREATE TABLE faculty (
    faculty_id INT PRIMARY KEY AUTO_INCREMENT,
    faculty_name VARCHAR(100) NOT NULL UNIQUE,
    email VARCHAR(100),
    seniority_level ENUM('junior', 'senior') DEFAULT 'junior',
    max_groups_as_guide INT DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Review batches
CREATE TABLE review_batches (
    batch_id INT PRIMARY KEY AUTO_INCREMENT,
    batch_name VARCHAR(50),
    review_date DATE,
    review_time TIME,
    location VARCHAR(100),
    room_no VARCHAR(20),
    track_id INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Batch assignments
CREATE TABLE batch_assignments (
    assignment_id INT PRIMARY KEY AUTO_INCREMENT,
    batch_id INT,
    group_id VARCHAR(50),
    guide_faculty_id INT,
    evaluator1_faculty_id INT,
    evaluator2_faculty_id INT,
    row_position INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (batch_id) REFERENCES review_batches(batch_id) ON DELETE CASCADE,
    FOREIGN KEY (group_id) REFERENCES projects(group_id) ON DELETE CASCADE,
    FOREIGN KEY (guide_faculty_id) REFERENCES faculty(faculty_id) ON DELETE SET NULL,
    FOREIGN KEY (evaluator1_faculty_id) REFERENCES faculty(faculty_id) ON DELETE SET NULL,
    FOREIGN KEY (evaluator2_faculty_id) REFERENCES faculty(faculty_id) ON DELETE SET NULL,
    UNIQUE KEY unique_group_batch (batch_id, group_id)
);

-- Faculty workload
CREATE TABLE faculty_workload (
    faculty_id INT PRIMARY KEY,
    total_guide_assignments INT DEFAULT 0,
    total_evaluator_assignments INT DEFAULT 0,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (faculty_id) REFERENCES faculty(faculty_id) ON DELETE CASCADE
);

-- ================== REVIEWS ==================

-- Review responses
CREATE TABLE reviews (
  id INT AUTO_INCREMENT PRIMARY KEY,
  group_id VARCHAR(255) NOT NULL,
  review_number INT NOT NULL,
  question_id VARCHAR(255) NOT NULL,
  answer VARCHAR(255),
  marks DECIMAL(5,2),
  comments TEXT,
  last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY unique_review (group_id, review_number, question_id)
);

-- ================== USEFUL VIEWS ==================

-- Complete schedule view
CREATE VIEW schedule_overview AS
SELECT 
    rb.batch_name,
    rb.location,
    rb.room_no,
    rb.review_date,
    rb.review_time,
    ba.group_id,
    ba.row_position,
    p.project_title,
    g.faculty_name as guide_name,
    e1.faculty_name as evaluator1_name,
    e2.faculty_name as evaluator2_name
FROM review_batches rb
JOIN batch_assignments ba ON rb.batch_id = ba.batch_id
JOIN projects p ON ba.group_id = p.group_id
LEFT JOIN faculty g ON ba.guide_faculty_id = g.faculty_id
LEFT JOIN faculty e1 ON ba.evaluator1_faculty_id = e1.faculty_id
LEFT JOIN faculty e2 ON ba.evaluator2_faculty_id = e2.faculty_id
ORDER BY rb.batch_name, ba.row_position;

-- Faculty workload view
CREATE VIEW faculty_workload_summary AS
SELECT 
    f.faculty_name,
    f.email,
    fw.total_guide_assignments,
    fw.total_evaluator_assignments,
    (fw.total_guide_assignments + fw.total_evaluator_assignments) as total_assignments
FROM faculty f
LEFT JOIN faculty_workload fw ON f.faculty_id = fw.faculty_id
ORDER BY total_assignments DESC, f.faculty_name;
