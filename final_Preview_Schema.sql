create database p_review;
use p_review;
CREATE TABLE projects (
    group_id         VARCHAR(50) PRIMARY KEY,          -- unique group ID
    project_title    TEXT NOT NULL,                    -- project title
    guide_name       TEXT,                              -- faculty guide
    evaluator1_name  TEXT,
    evaluator2_name  TEXT,
    division         VARCHAR(10),                      -- e.g. A, B, C
    project_domain   TEXT,                              -- AI, IoT, etc.
    sponsor_company  TEXT                               -- optional sponsor
);

CREATE TABLE members (
    member_id           INT AUTO_INCREMENT PRIMARY KEY, -- internal ID
    group_id            VARCHAR(50) NOT NULL,           -- links to projects table
    roll_no             VARCHAR(50) NOT NULL,           -- student roll number
    student_name        TEXT NOT NULL,
    review1_attendance  BOOLEAN DEFAULT FALSE,
    review2_attendance  BOOLEAN DEFAULT FALSE,
    review3_attendance  BOOLEAN DEFAULT FALSE,
    review4_attendance  BOOLEAN DEFAULT FALSE,
	
    FOREIGN KEY (group_id) REFERENCES projects(group_id)
        ON DELETE CASCADE,
    UNIQUE KEY unique_roll (roll_no)
);

alter table members add column review0_attendance  BOOLEAN DEFAULT FALSE;

CREATE TABLE review1_marks (
    id INT AUTO_INCREMENT PRIMARY KEY,
    group_id VARCHAR(50) NOT NULL,
    roll_no VARCHAR(50) NOT NULL,
    understanding_topic FLOAT DEFAULT 0,
    project_scope FLOAT DEFAULT 0,
    literature_survey FLOAT DEFAULT 0,
    project_planning FLOAT DEFAULT 0,
    contribution FLOAT DEFAULT 0,
    presentation_skills FLOAT DEFAULT 0,
    question_answer FLOAT DEFAULT 0,
    total FLOAT GENERATED ALWAYS AS (
        understanding_topic + project_scope + literature_survey +
        project_planning + contribution + presentation_skills + question_answer
    ) STORED,
    FOREIGN KEY (group_id) REFERENCES projects(group_id) ON DELETE CASCADE,
    FOREIGN KEY (roll_no) REFERENCES members(roll_no) ON DELETE CASCADE
);


-- Step 1: Create the questions master table
CREATE TABLE review1_questions (
    question_id VARCHAR(20) PRIMARY KEY,
    section VARCHAR(50) NOT NULL,
    question_text TEXT NOT NULL,
    display_order INT NOT NULL,
    UNIQUE KEY unique_order (display_order)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Step 2: Populate the questions (one-time insert)
INSERT INTO review1_questions (question_id, section, question_text, display_order) VALUES
('que_1.1.1', 'Problem Statement', 'Is the statement short and concise (10-20 words maximum)?', 1),
('que_1.1.2', 'Problem Statement', 'Does the statement give clear indication about what your project will accomplish?', 2),
('que_1.1.3', 'Problem Statement', 'Can a person who is not familiar with the project understand scope of the project by reading the Project Problem Statement?', 3),
('que_1.2.1', 'Scope and Objectives', 'Are all aspects of the requirements document addressed in the design?', 4),
('que_1.2.2', 'Scope and Objectives', 'Is the architecture / block diagram well defined and understood?', 5),
('que_1.2.3', 'Scope and Objectives', 'The project\'s objective of study (what product, process, resource etc.) is being addressed?', 6),
('que_1.2.4', 'Scope and Objectives', 'The project\'s purpose: is the purpose of project addressed properly (why it\'s being pursued: to evaluate, reduce, increase, etc.)?', 7),
('que_1.2.5', 'Scope and Objectives', 'The project\'s viewpoint: Is the project\'s viewpoint understood? (Who is the project\'s end user)?', 8),
('que_1.2.6', 'Scope and Objectives', 'Is the project goal statement in alignment with the sponsoring organization\'s business goals and mission?', 9),
('que_1.3.1', 'Analysis', 'Is information domain analysis complete, consistent and accurate?', 10),
('que_1.3.2', 'Analysis', 'Is problem statement categorized in identified area and targeted towards specific area therein?', 11),
('que_1.3.3', 'Analysis', 'Are external and internal interfaces properly defined?', 12),
('que_1.3.4', 'Analysis', 'Does the Use Case Model properly reflect the actors and their roles and responsibilities?', 13),
('que_1.3.5', 'Analysis', 'Are all requirements traceable to system level?', 14),
('que_1.3.6', 'Analysis', 'Is similar type of methodology / model used for existing work?', 15),
('que_1.3.7', 'Analysis', 'Are requirements consistent with schedule, resources and budget?', 16);


CREATE TABLE review1_group_responses (
    group_id VARCHAR(50) PRIMARY KEY,
    submission_date DATE NOT NULL,
    comments TEXT,
    que_1_1_1 ENUM('Y', 'N', 'NA', 'NC') DEFAULT NULL,
    que_1_1_2 ENUM('Y', 'N', 'NA', 'NC') DEFAULT NULL,
    que_1_1_3 ENUM('Y', 'N', 'NA', 'NC') DEFAULT NULL,
    que_1_2_1 ENUM('Y', 'N', 'NA', 'NC') DEFAULT NULL,
    que_1_2_2 ENUM('Y', 'N', 'NA', 'NC') DEFAULT NULL,
    que_1_2_3 ENUM('Y', 'N', 'NA', 'NC') DEFAULT NULL,
    que_1_2_4 ENUM('Y', 'N', 'NA', 'NC') DEFAULT NULL,
    que_1_2_5 ENUM('Y', 'N', 'NA', 'NC') DEFAULT NULL,
    que_1_2_6 ENUM('Y', 'N', 'NA', 'NC') DEFAULT NULL,
    que_1_3_1 ENUM('Y', 'N', 'NA', 'NC') DEFAULT NULL,
    que_1_3_2 ENUM('Y', 'N', 'NA', 'NC') DEFAULT NULL,
    que_1_3_3 ENUM('Y', 'N', 'NA', 'NC') DEFAULT NULL,
    que_1_3_4 ENUM('Y', 'N', 'NA', 'NC') DEFAULT NULL,
    que_1_3_5 ENUM('Y', 'N', 'NA', 'NC') DEFAULT NULL,
    que_1_3_6 ENUM('Y', 'N', 'NA', 'NC') DEFAULT NULL,
    que_1_3_7 ENUM('Y', 'N', 'NA', 'NC') DEFAULT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (group_id) REFERENCES projects(group_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Add to your existing schema

-- Performance criteria table for Review 1
CREATE TABLE review1_performance_criteria (
    criteria_id VARCHAR(50) PRIMARY KEY,
    criteria_text TEXT NOT NULL,
    max_marks FLOAT NOT NULL,
    display_order INT NOT NULL,
    UNIQUE KEY unique_order (display_order)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Populate performance criteria
INSERT INTO review1_performance_criteria (criteria_id, criteria_text, max_marks, display_order) VALUES
('understanding_topic', 'Understanding background and Topic', 2, 1),
('project_scope', 'Specifies Project Scope and Objective', 2, 2),
('literature_survey', 'Literature Survey', 5, 3),
('project_planning', 'Project Planning', 4, 4),
('contribution', 'Contribution of the Student', 4, 5),
('presentation_skills', 'Presentation Skills', 4, 6),
('question_answer', 'Question and Answer', 4, 7);

-- Verify your existing tables are correct
-- Make sure review1_marks table has these columns matching criteria_id above:
-- understanding_topic, project_scope, literature_survey, project_planning, 
-- contribution, presentation_skills, question_answer, total


-- 2. Create review2_marks table
CREATE TABLE IF NOT EXISTS review2_marks (
    id INT AUTO_INCREMENT PRIMARY KEY,
    group_id VARCHAR(50) NOT NULL,
    roll_no VARCHAR(50) NOT NULL,

    arch_literature TEXT COMMENT '1. System Architecture & Literature Survey (Review-I)',
    project_design FLOAT DEFAULT 0 COMMENT '2. Project Design (5M)',
    methodology_algorithms FLOAT DEFAULT 0 COMMENT '3. Methodology/Algorithms and Project Features (5M)',
    project_planning FLOAT DEFAULT 0 COMMENT '4. Project Planning (2M)',
    implementation_details FLOAT DEFAULT 0 COMMENT '5. Basic details of Implementation (5M)',
    presentation_skills FLOAT DEFAULT 0 COMMENT '6. Presentation Skills (4M)',
    question_answer FLOAT DEFAULT 0 COMMENT '7. Question and Answer (4M)',
    project_summary TEXT COMMENT '8. Summarization of ultimate findings of the Project',

    -- Total only sums numeric fields
    total FLOAT GENERATED ALWAYS AS (
        project_design + methodology_algorithms +
        project_planning + implementation_details +
        presentation_skills + question_answer
    ) STORED,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    FOREIGN KEY (group_id) REFERENCES projects(group_id) ON DELETE CASCADE,
    FOREIGN KEY (roll_no) REFERENCES members(roll_no) ON DELETE CASCADE,
    UNIQUE KEY unique_group_roll (group_id, roll_no)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- 3. Create review2_questions master table
CREATE TABLE IF NOT EXISTS review2_questions (
    question_id VARCHAR(20) PRIMARY KEY,
    section VARCHAR(50) NOT NULL,
    question_text TEXT NOT NULL,
    display_order INT NOT NULL,
    UNIQUE KEY unique_order (display_order)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 4. Insert Review 2 questions
INSERT INTO review2_questions (question_id, section, question_text, display_order) VALUES
('que_2.1.1', 'Design', 'Are requirements reflected in the system architecture?', 1),
('que_2.1.2', 'Design', 'Does the design support both project (product) and project goals?', 2),
('que_2.1.3', 'Design', 'Does the design address all the issues from the requirements?', 3),
('que_2.1.4', 'Design', 'Is effective modularity achieved and modules are functionally independent?', 4),
('que_2.1.5', 'Design', 'Are structural diagrams (Class, Object, etc.) well defined and understood?', 5),
('que_2.1.6', 'Design', 'Are all class associations clearly defined and understood? (Is it clear which classes provide which services)?', 6),
('que_2.1.7', 'Design', 'Are the classes in the class diagram clear? (What they represent in the architecture design document?)', 7),
('que_2.1.8', 'Design', 'Is inheritance appropriately used?', 8),
('que_2.1.9', 'Design', 'Are the multiplicities in the use case diagram depicted in the class diagram?', 9),
('que_2.1.10', 'Design', 'Are behavioral diagrams (use case, sequence, activity, etc.) well defined and understood?', 10),
('que_2.1.11', 'Design', 'Is aggregation/containment (if used) clearly defined and understood?', 11),
('que_2.1.12', 'Design', 'Does each case have clearly defined actors and input/output?', 12),
('que_2.1.13', 'Design', 'Is all concurrent processing (if used) clearly understood and reflected in the sequence diagrams?', 13),
('que_2.1.14', 'Design', 'Are all objects used in sequence diagram?', 14),
('que_2.1.15', 'Design', 'Does the sequence diagram match class diagram?', 15),
('que_2.1.16', 'Design', 'Are the symbols used in all diagrams correspond to UML standards?', 16);

-- 5. Create review2_group_responses table
CREATE TABLE IF NOT EXISTS review2_group_responses (
    group_id VARCHAR(50) PRIMARY KEY,
    submission_date DATE NOT NULL,
    comments TEXT,
    que_2_1_1 ENUM('Y', 'N', 'NA', 'NC') DEFAULT NULL,
    que_2_1_2 ENUM('Y', 'N', 'NA', 'NC') DEFAULT NULL,
    que_2_1_3 ENUM('Y', 'N', 'NA', 'NC') DEFAULT NULL,
    que_2_1_4 ENUM('Y', 'N', 'NA', 'NC') DEFAULT NULL,
    que_2_1_5 ENUM('Y', 'N', 'NA', 'NC') DEFAULT NULL,
    que_2_1_6 ENUM('Y', 'N', 'NA', 'NC') DEFAULT NULL,
    que_2_1_7 ENUM('Y', 'N', 'NA', 'NC') DEFAULT NULL,
    que_2_1_8 ENUM('Y', 'N', 'NA', 'NC') DEFAULT NULL,
    que_2_1_9 ENUM('Y', 'N', 'NA', 'NC') DEFAULT NULL,
    que_2_1_10 ENUM('Y', 'N', 'NA', 'NC') DEFAULT NULL,
    que_2_1_11 ENUM('Y', 'N', 'NA', 'NC') DEFAULT NULL,
    que_2_1_12 ENUM('Y', 'N', 'NA', 'NC') DEFAULT NULL,
    que_2_1_13 ENUM('Y', 'N', 'NA', 'NC') DEFAULT NULL,
    que_2_1_14 ENUM('Y', 'N', 'NA', 'NC') DEFAULT NULL,
    que_2_1_15 ENUM('Y', 'N', 'NA', 'NC') DEFAULT NULL,
    que_2_1_16 ENUM('Y', 'N', 'NA', 'NC') DEFAULT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (group_id) REFERENCES projects(group_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 6. Create performance criteria table for Review 2
CREATE TABLE IF NOT EXISTS review2_performance_criteria (
    criteria_id VARCHAR(50) PRIMARY KEY,
    criteria_text TEXT NOT NULL,
    max_marks FLOAT NOT NULL,
    display_order INT NOT NULL,
    UNIQUE KEY unique_order (display_order)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 7. Insert performance criteria for Review 2
INSERT INTO review2_performance_criteria (criteria_id, criteria_text, max_marks, display_order) VALUES
('arch_literature', 'System Architecture & Literature Survey (Review-I)', 0, 1),
('project_design', 'Project Design', 5, 2),
('methodology_algorithms', 'Methodology/Algorithms and Project Features', 5, 3),
('project_planning', 'Project Planning', 2, 4),
('implementation_details', 'Basic details of Implementation', 5, 5),
('presentation_skills', 'Presentation Skills', 4, 6),
('question_answer', 'Question and Answer', 4, 7),
('project_summary', 'Summarization of ultimate findings of the Project', 0, 8);

-- 2. Create review2_marks table
CREATE TABLE IF NOT EXISTS review0_marks (
    id INT AUTO_INCREMENT PRIMARY KEY,
    group_id VARCHAR(50) NOT NULL,
    roll_no VARCHAR(50) NOT NULL,

    arch_literature TEXT COMMENT '1. System Architecture & Literature Survey (Review-I)',
    project_design FLOAT DEFAULT 0 COMMENT '2. Project Design (5M)',
    methodology_algorithms FLOAT DEFAULT 0 COMMENT '3. Methodology/Algorithms and Project Features (5M)',
    project_planning FLOAT DEFAULT 0 COMMENT '4. Project Planning (2M)',
    implementation_details FLOAT DEFAULT 0 COMMENT '5. Basic details of Implementation (5M)',
    presentation_skills FLOAT DEFAULT 0 COMMENT '6. Presentation Skills (4M)',
    question_answer FLOAT DEFAULT 0 COMMENT '7. Question and Answer (4M)',
    project_summary TEXT COMMENT '8. Summarization of ultimate findings of the Project',

    -- Total only sums numeric fields
    total FLOAT GENERATED ALWAYS AS (
        project_design + methodology_algorithms +
        project_planning + implementation_details +
        presentation_skills + question_answer
    ) STORED,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    FOREIGN KEY (group_id) REFERENCES projects(group_id) ON DELETE CASCADE,
    FOREIGN KEY (roll_no) REFERENCES members(roll_no) ON DELETE CASCADE,
    UNIQUE KEY unique_group_roll (group_id, roll_no)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- 3. Create review2_questions master table
CREATE TABLE IF NOT EXISTS review0_questions (
    question_id VARCHAR(20) PRIMARY KEY,
    section VARCHAR(50) NOT NULL,
    question_text TEXT NOT NULL,
    display_order INT NOT NULL,
    UNIQUE KEY unique_order (display_order)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 4. Insert Review 2 questions
INSERT INTO review0_questions (question_id, section, question_text, display_order) VALUES
('que_0.1.1', 'Design', 'Are requirements reflected in the system architecture?', 1),
('que_0.1.2', 'Design', 'Does the design support both project (product) and project goals?', 2),
('que_0.1.3', 'Design', 'Does the design address all the issues from the requirements?', 3),
('que_0.1.4', 'Design', 'Is effective modularity achieved and modules are functionally independent?', 4),
('que_0.1.5', 'Design', 'Are structural diagrams (Class, Object, etc.) well defined and understood?', 5),
('que_0.1.6', 'Design', 'Are all class associations clearly defined and understood? (Is it clear which classes provide which services)?', 6),
('que_0.1.7', 'Design', 'Are the classes in the class diagram clear? (What they represent in the architecture design document?)', 7),
('que_0.1.8', 'Design', 'Is inheritance appropriately used?', 8),
('que_0.1.9', 'Design', 'Are the multiplicities in the use case diagram depicted in the class diagram?', 9),
('que_0.1.10', 'Design', 'Are behavioral diagrams (use case, sequence, activity, etc.) well defined and understood?', 10),
('que_0.1.11', 'Design', 'Is aggregation/containment (if used) clearly defined and understood?', 11),
('que_0.1.12', 'Design', 'Does each case have clearly defined actors and input/output?', 12),
('que_0.1.13', 'Design', 'Is all concurrent processing (if used) clearly understood and reflected in the sequence diagrams?', 13),
('que_0.1.14', 'Design', 'Are all objects used in sequence diagram?', 14),
('que_0.1.15', 'Design', 'Does the sequence diagram match class diagram?', 15),
('que_0.1.16', 'Design', 'Are the symbols used in all diagrams correspond to UML standards?', 16);

-- 5. Create review2_group_responses table
CREATE TABLE IF NOT EXISTS review0_group_responses (
    group_id VARCHAR(50) PRIMARY KEY,
    submission_date DATE NOT NULL,
    comments TEXT,
    que_0_1_1 ENUM('Y', 'N', 'NA', 'NC') DEFAULT NULL,
    que_0_1_2 ENUM('Y', 'N', 'NA', 'NC') DEFAULT NULL,
    que_0_1_3 ENUM('Y', 'N', 'NA', 'NC') DEFAULT NULL,
    que_0_1_4 ENUM('Y', 'N', 'NA', 'NC') DEFAULT NULL,
    que_0_1_5 ENUM('Y', 'N', 'NA', 'NC') DEFAULT NULL,
    que_0_1_6 ENUM('Y', 'N', 'NA', 'NC') DEFAULT NULL,
    que_0_1_7 ENUM('Y', 'N', 'NA', 'NC') DEFAULT NULL,
    que_0_1_8 ENUM('Y', 'N', 'NA', 'NC') DEFAULT NULL,
    que_0_1_9 ENUM('Y', 'N', 'NA', 'NC') DEFAULT NULL,
    que_0_1_10 ENUM('Y', 'N', 'NA', 'NC') DEFAULT NULL,
    que_0_1_11 ENUM('Y', 'N', 'NA', 'NC') DEFAULT NULL,
    que_0_1_12 ENUM('Y', 'N', 'NA', 'NC') DEFAULT NULL,
    que_0_1_13 ENUM('Y', 'N', 'NA', 'NC') DEFAULT NULL,
    que_0_1_14 ENUM('Y', 'N', 'NA', 'NC') DEFAULT NULL,
    que_0_1_15 ENUM('Y', 'N', 'NA', 'NC') DEFAULT NULL,
    que_0_1_16 ENUM('Y', 'N', 'NA', 'NC') DEFAULT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (group_id) REFERENCES projects(group_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 6. Create performance criteria table for Review 2
CREATE TABLE IF NOT EXISTS review0_performance_criteria (
    criteria_id VARCHAR(50) PRIMARY KEY,
    criteria_text TEXT NOT NULL,
    max_marks FLOAT NOT NULL,
    display_order INT NOT NULL,
    UNIQUE KEY unique_order (display_order)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 7. Insert performance criteria for Review 2
INSERT INTO review0_performance_criteria (criteria_id, criteria_text, max_marks, display_order) VALUES
('arch_literature', 'System Architecture & Literature Survey (Review-I)', 0, 1),
('project_design', 'Project Design', 5, 2),
('methodology_algorithms', 'Methodology/Algorithms and Project Features', 5, 3),
('project_planning', 'Project Planning', 2, 4),
('implementation_details', 'Basic details of Implementation', 5, 5),
('presentation_skills', 'Presentation Skills', 4, 6),
('question_answer', 'Question and Answer', 4, 7),
('project_summary', 'Summarization of ultimate findings of the Project', 0, 8);

-- ==================== REVIEW 3 DATABASE TABLES ====================

-- 1. Performance Criteria Table
CREATE TABLE review3_performance_criteria (
    criteria_id VARCHAR(50) PRIMARY KEY,
    criteria_text TEXT NOT NULL,
    max_marks DECIMAL(4,1) NOT NULL,
    display_order INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert Review 3 criteria
INSERT INTO review3_performance_criteria (criteria_id, criteria_text, max_marks, display_order) VALUES
('algo_study', '1. Detailed study of Algorithm(s) / Model / Hardware specification (As applicable)', 0, 1),
('dataset_confirm', '2. Confirmation of Data set used (As applicable)', 0, 2),
('implementation', '3. 50% Implementation (10M)', 10, 3),
('partial_results', '4. Partial results obtained (7M)', 7, 4),
('presentation_skills', '5. Presentation skills (4M)', 4, 5),
('question_answer', '6. Question and Answer (4M)', 4, 6),
('methodology_summary', '7. Summarize the methodologies/Algorithms implemented / to be implemented', 0, 7);

-- 2. Marks Table (with triggers for auto-calculation)
CREATE TABLE review3_marks (
    id INT AUTO_INCREMENT PRIMARY KEY,
    group_id VARCHAR(20) NOT NULL,
    roll_no VARCHAR(20) NOT NULL,
    algo_study VARCHAR(1) DEFAULT NULL COMMENT 'Y/N field',
    dataset_confirm VARCHAR(1) DEFAULT NULL COMMENT 'Y/N field',
    implementation DECIMAL(4,1) DEFAULT 0,
    partial_results DECIMAL(4,1) DEFAULT 0,
    presentation_skills DECIMAL(4,1) DEFAULT 0,
    question_answer DECIMAL(4,1) DEFAULT 0,
    methodology_summary VARCHAR(1) DEFAULT NULL COMMENT 'Y/N field',
    total DECIMAL(5,1) GENERATED ALWAYS AS (
        COALESCE(implementation, 0) + 
        COALESCE(partial_results, 0) + 
        COALESCE(presentation_skills, 0) + 
        COALESCE(question_answer, 0)
    ) STORED,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY unique_group_student (group_id, roll_no),
    INDEX idx_group (group_id),
    INDEX idx_roll (roll_no)
);

-- 3. Questions Table
CREATE TABLE review3_questions (
    question_id VARCHAR(20) PRIMARY KEY,
    section VARCHAR(100) NOT NULL,
    question_text TEXT NOT NULL,
    display_order INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert Review 3 questions
INSERT INTO review3_questions (question_id, section, question_text, display_order) VALUES
('que_3.1.1', 'Implementation', 'Does the code completely and correctly implement the design?', 1),
('que_3.1.2', 'Implementation', 'Does the code comply with the Coding Standards?', 2),
('que_3.1.3', 'Implementation', 'Is the code well-structured, consistent in style, and consistently formatted?', 3),
('que_3.1.4', 'Implementation', 'Does the implementation match the design?', 4),
('que_3.1.5', 'Implementation', 'Are all functions in the design coded?', 5),
('que_2.1', 'Documentation', 'Is the code clearly and adequately documented?', 6),
('que_2.2', 'Documentation', 'Are all comments consistent with the code?', 7);

-- 4. Group Responses Table
CREATE TABLE review3_group_responses (
    id INT AUTO_INCREMENT PRIMARY KEY,
    group_id VARCHAR(20) NOT NULL UNIQUE,
    submission_date DATE NOT NULL,
    comments TEXT,
    -- Implementation section (que_3.1.x)
    que_3_1_1 VARCHAR(3) DEFAULT NULL COMMENT 'Y/N/NA/NC',
    que_3_1_2 VARCHAR(3) DEFAULT NULL COMMENT 'Y/N/NA/NC',
    que_3_1_3 VARCHAR(3) DEFAULT NULL COMMENT 'Y/N/NA/NC',
    que_3_1_4 VARCHAR(3) DEFAULT NULL COMMENT 'Y/N/NA/NC',
    que_3_1_5 VARCHAR(3) DEFAULT NULL COMMENT 'Y/N/NA/NC',
    -- Documentation section (que_2.x)
    que_2_1 VARCHAR(3) DEFAULT NULL COMMENT 'Y/N/NA/NC',
    que_2_2 VARCHAR(3) DEFAULT NULL COMMENT 'Y/N/NA/NC',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_group (group_id)
);


-- ==================== REVIEW 4 DATABASE TABLES ====================

-- 1. Performance Criteria Table
CREATE TABLE review4_performance_criteria (
    criteria_id VARCHAR(50) PRIMARY KEY,
    criteria_text TEXT NOT NULL,
    max_marks DECIMAL(4,1) NOT NULL,
    display_order INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert Review 4 criteria
INSERT INTO review4_performance_criteria (criteria_id, criteria_text, max_marks, display_order) VALUES
('implementation', '1. 75% Implementation completed', 0, 1),
('testing_coverage', '2. Testing (Unit/Integration/System) (10M)', 10, 2),
('test_cases', '3. Test cases designed and executed (7M)', 7, 3),
('result_analysis', '4. Result analysis and conclusion (3M)', 3, 4),
('presentation_skills', '5. Presentation skills (3M)', 3, 5),
('question_answer', '6. Question and Answer (2M)', 2, 6);

-- 2. Marks Table (with triggers for auto-calculation) 
CREATE TABLE review4_marks (
    id INT AUTO_INCREMENT PRIMARY KEY,
    group_id VARCHAR(20) NOT NULL,
    roll_no VARCHAR(20) NOT NULL,
    implementation VARCHAR(1) DEFAULT NULL COMMENT 'Y/N field',
    testing_coverage DECIMAL(4,1) DEFAULT 0,
    test_cases DECIMAL(4,1) DEFAULT 0,
    result_analysis DECIMAL(4,1) DEFAULT 0,
    presentation_skills DECIMAL(4,1) DEFAULT 0,
    question_answer DECIMAL(4,1) DEFAULT 0,
    total DECIMAL(5,1) GENERATED ALWAYS AS (
        COALESCE(testing_coverage, 0) + 
        COALESCE(test_cases, 0) + 
        COALESCE(result_analysis, 0) + 
        COALESCE(presentation_skills, 0) + 
        COALESCE(question_answer, 0)
    ) STORED,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY unique_group_student (group_id, roll_no),
    INDEX idx_group (group_id),
    INDEX idx_roll (roll_no)
);

-- 3. Questions Table
CREATE TABLE review4_questions (
    question_id VARCHAR(20) PRIMARY KEY,
    section VARCHAR(100) NOT NULL,
    question_text TEXT NOT NULL,
    question_type VARCHAR(20) NOT NULL COMMENT 'radio or numeric',
    display_order INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert Review 4 questions
INSERT INTO review4_questions (question_id, section, question_text, question_type, display_order) VALUES
('que_4.1.1', 'Implementation and Testing', 'Is every feature tested?', 'radio', 1),
('que_4.1.2', 'Implementation and Testing', 'Are all functions, user screens and navigation tested?', 'radio', 2),
('que_4.1.3', 'Implementation and Testing', 'Are test cases designed? (manual and automated)', 'radio', 3),
('que_4.1.4', 'Implementation and Testing', 'Is testing tool used?', 'radio', 4),
('que_4.1.5', 'Implementation and Testing', 'Is result analysis done properly and proper conclusion drawn?', 'radio', 5),
('que_4.1.6', 'Implementation and Testing', 'Implementation status (code completion in percentage)', 'numeric', 6);

-- 4. Group Responses Table
CREATE TABLE review4_group_responses (
    id INT AUTO_INCREMENT PRIMARY KEY,
    group_id VARCHAR(20) NOT NULL UNIQUE,
    submission_date DATE NOT NULL,
    comments TEXT,
    -- Implementation and Testing section (que_4.1.x)
    que_4_1_1 VARCHAR(3) DEFAULT NULL COMMENT 'Y/N/NA/NC',
    que_4_1_2 VARCHAR(3) DEFAULT NULL COMMENT 'Y/N/NA/NC',
    que_4_1_3 VARCHAR(3) DEFAULT NULL COMMENT 'Y/N/NA/NC',
    que_4_1_4 VARCHAR(3) DEFAULT NULL COMMENT 'Y/N/NA/NC',
    que_4_1_5 VARCHAR(3) DEFAULT NULL COMMENT 'Y/N/NA/NC',
    que_4_1_6 DECIMAL(5,2) DEFAULT NULL COMMENT 'Implementation percentage',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_group (group_id)
);


-- ==================== REVIEW 6 DATABASE TABLES ====================

-- 1. Performance Criteria Table
CREATE TABLE review6_performance_criteria (
    criteria_id VARCHAR(50) PRIMARY KEY,
    criteria_text TEXT NOT NULL,
    max_marks DECIMAL(4,1) NOT NULL,
    display_order INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert Review 6 criteria
INSERT INTO review6_performance_criteria (criteria_id, criteria_text, max_marks, display_order) VALUES
('implementation', '1. 75% Implementation completed', 0, 1),
('testing_coverage', '2. Testing (Unit/Integration/System) (10M)', 10, 2),
('test_cases', '3. Test cases designed and executed (7M)', 7, 3),
('result_analysis', '4. Result analysis and conclusion (3M)', 3, 4),
('presentation_skills', '5. Presentation skills (3M)', 3, 5),
('question_answer', '6. Question and Answer (2M)', 2, 6);

-- 2. Marks Table (with triggers for auto-calculation) 
CREATE TABLE review6_marks (
    id INT AUTO_INCREMENT PRIMARY KEY,
    group_id VARCHAR(20) NOT NULL,
    roll_no VARCHAR(20) NOT NULL,
    implementation VARCHAR(1) DEFAULT NULL COMMENT 'Y/N field',
    testing_coverage DECIMAL(4,1) DEFAULT 0,
    test_cases DECIMAL(4,1) DEFAULT 0,
    result_analysis DECIMAL(4,1) DEFAULT 0,
    presentation_skills DECIMAL(4,1) DEFAULT 0,
    question_answer DECIMAL(4,1) DEFAULT 0,
    total DECIMAL(5,1) GENERATED ALWAYS AS (
        COALESCE(testing_coverage, 0) + 
        COALESCE(test_cases, 0) + 
        COALESCE(result_analysis, 0) + 
        COALESCE(presentation_skills, 0) + 
        COALESCE(question_answer, 0)
    ) STORED,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY unique_group_student (group_id, roll_no),
    INDEX idx_group (group_id),
    INDEX idx_roll (roll_no)
);

-- 3. Questions Table
CREATE TABLE review6_questions (
    question_id VARCHAR(20) PRIMARY KEY,
    section VARCHAR(100) NOT NULL,
    question_text TEXT NOT NULL,
    question_type VARCHAR(20) NOT NULL COMMENT 'radio or numeric',
    display_order INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert Review 6 questions
INSERT INTO review6_questions (question_id, section, question_text, question_type, display_order) VALUES
('que_6.1.1', 'Implementation and Testing', 'Is every feature tested?', 'radio', 1),
('que_6.1.2', 'Implementation and Testing', 'Are all functions, user screens and navigation tested?', 'radio', 2),
('que_6.1.3', 'Implementation and Testing', 'Are test cases designed? (manual and automated)', 'radio', 3),
('que_6.1.4', 'Implementation and Testing', 'Is testing tool used?', 'radio', 4),
('que_6.1.5', 'Implementation and Testing', 'Is result analysis done properly and proper conclusion drawn?', 'radio', 5),
('que_6.1.6', 'Implementation and Testing', 'Implementation status (code completion in percentage)', 'numeric', 6);

-- 4. Group Responses Table
CREATE TABLE review6_group_responses (
    id INT AUTO_INCREMENT PRIMARY KEY,
    group_id VARCHAR(20) NOT NULL UNIQUE,
    submission_date DATE NOT NULL,
    comments TEXT,
    -- Implementation and Testing section (que_6.1.x)
    que_6_1_1 VARCHAR(3) DEFAULT NULL COMMENT 'Y/N/NA/NC',
    que_6_1_2 VARCHAR(3) DEFAULT NULL COMMENT 'Y/N/NA/NC',
    que_6_1_3 VARCHAR(3) DEFAULT NULL COMMENT 'Y/N/NA/NC',
    que_6_1_4 VARCHAR(3) DEFAULT NULL COMMENT 'Y/N/NA/NC',
    que_6_1_5 VARCHAR(3) DEFAULT NULL COMMENT 'Y/N/NA/NC',
    que_6_1_6 DECIMAL(5,2) DEFAULT NULL COMMENT 'Implementation percentage',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_group (group_id)
);

-- Review 6 Deliverables
CREATE TABLE IF NOT EXISTS review6_deliverables (
    id INT AUTO_INCREMENT PRIMARY KEY,
    deliverable_text TEXT NOT NULL,
    display_order INT NOT NULL,
    UNIQUE KEY unique_order (display_order),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

INSERT INTO review6_deliverables (deliverable_text, display_order) VALUES
('Detailed Design', 1),
('100% of code implementation', 2),
('Experimental Results', 3),
('Result Evaluation', 4),
('Test Cases', 5),
('Result Analysis and Conclusion', 6),
('Project Report', 7);





-- Review 1 Deliverables
CREATE TABLE review1_deliverables (
    id INT AUTO_INCREMENT PRIMARY KEY,
    deliverable_text TEXT NOT NULL,
    display_order INT NOT NULL,
    UNIQUE KEY unique_order (display_order)
);

INSERT INTO review1_deliverables (deliverable_text, display_order) VALUES
('Problem Statement / Title', 1),
('Purpose, Scope, Objectives', 2),
('Abstract (System Overview)', 3),
('Introduction (Architecture and High-level Design)', 4),
('Literature Survey', 5),
('References', 6),
('Project Plan 1.0', 7);

-- Review 2 Deliverables
CREATE TABLE review2_deliverables (
    id INT AUTO_INCREMENT PRIMARY KEY,
    deliverable_text TEXT NOT NULL,
    display_order INT NOT NULL,
    UNIQUE KEY unique_order (display_order)
);

INSERT INTO review2_deliverables (deliverable_text, display_order) VALUES
('Modules Split-up', 1),
('Proposed System', 2),
('Software Tools / Technologies to be used', 3),
('Proposed Outcomes', 4),
('Partial Report (Semester – I)', 5),
('Project Plan 2.0', 6),
('Problem Statement / Title', 7),
('Abstract', 8),
('Introduction', 9),
('Literature Survey', 10),
('Methodology', 11),
('Design / algorithms / techniques used', 12);

CREATE TABLE review0_deliverables (
    id INT AUTO_INCREMENT PRIMARY KEY,
    deliverable_text TEXT NOT NULL,
    display_order INT NOT NULL,
    UNIQUE KEY unique_order (display_order)
);
INSERT INTO review0_deliverables (deliverable_text, display_order) VALUES
('Modules Split-up', 1),
('Proposed System', 2),
('Software Tools / Technologies to be used', 3),
('Proposed Outcomes', 4),
('Partial Report (Semester – I)', 5),
('Project Plan 2.0', 6),
('Problem Statement / Title', 7),
('Abstract', 8),
('Introduction', 9),
('Literature Survey', 10),
('Methodology', 11),
('Design / algorithms / techniques used', 12);
-- Review 3 Deliverables
CREATE TABLE IF NOT EXISTS review3_deliverables (
    id INT AUTO_INCREMENT PRIMARY KEY,
    deliverable_text TEXT NOT NULL,
    display_order INT NOT NULL,
    UNIQUE KEY unique_order (display_order),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

INSERT INTO review3_deliverables (deliverable_text, display_order) VALUES
('Detailed Study (System deviation)', 1),
('50% of code implementation', 2),
('Some Experimental Results', 3),
('Project Plan 3.0', 4);

-- Review 4 Deliverables
CREATE TABLE IF NOT EXISTS review4_deliverables (
    id INT AUTO_INCREMENT PRIMARY KEY,
    deliverable_text TEXT NOT NULL,
    display_order INT NOT NULL,
    UNIQUE KEY unique_order (display_order),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

INSERT INTO review4_deliverables (deliverable_text, display_order) VALUES
('Detailed Design', 1),
('100% of code implementation', 2),
('Experimental Results', 3),
('Result Evaluation', 4),
('Test Cases', 5),
('Result Analysis and Conclusion', 6),
('Project Report', 7);

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
-- Users Table (Authentication)
-- =====================================================

-- Create PDF generation logs table
CREATE TABLE IF NOT EXISTS pdf_generation_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    review_number INT NOT NULL,
    group_id VARCHAR(50) NOT NULL,
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    generated_by VARCHAR(100),
    ip_address VARCHAR(45),
    user_agent TEXT,
    INDEX idx_group_review (group_id, review_number),
    INDEX idx_generated_at (generated_at),
    FOREIGN KEY (group_id) REFERENCES projects(group_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- System settings table (persists server-wide configuration across restarts)
CREATE TABLE IF NOT EXISTS system_settings (
    setting_key VARCHAR(100) PRIMARY KEY,
    setting_value VARCHAR(255) NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Seed the default active academic year (adjust as needed)
INSERT INTO system_settings (setting_key, setting_value)
VALUES ('active_academic_year', '2025-26')
ON DUPLICATE KEY UPDATE setting_value = setting_value;



-- Add this to your database schema
CREATE TABLE IF NOT EXISTS final_sheet (
    id INT AUTO_INCREMENT PRIMARY KEY,
    group_id VARCHAR(50) NOT NULL UNIQUE,
    overall_comments TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (group_id) REFERENCES projects(group_id) ON DELETE CASCADE,
    INDEX idx_group (group_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role ENUM('admin','user') DEFAULT 'user',
    email_verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP NULL,
    active BOOLEAN DEFAULT TRUE
);
select * from members; 
delete from users where id=1;
show tables;