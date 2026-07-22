// frontend/static/js/review2.js

const REVIEW_CONFIG = {
    reviewNumber: 0,
    criteria: [
        { name: "arch_literature", label: "1. System Architecture & Literature Survey (Review-I)", max: 0, type: "text" },
        { name: "project_design", label: "2. Project Design (5M)", max: 5, type: "number" },
        { name: "methodology_algorithms", label: "3. Methodology/Algorithms and Project Features (5M)", max: 5, type: "number" },
        { name: "project_planning", label: "4. Project Planning (2M)", max: 2, type: "number" },
        { name: "implementation_details", label: "5. Basic details of Implementation (5M)", max: 5, type: "number" },
        { name: "presentation_skills", label: "6. Presentation Skills (4M)", max: 4, type: "number" },
        { name: "question_answer", label: "7. Question and Answer (4M)", max: 4, type: "number" },
        { name: "project_summary", label: "8. Summarization of ultimate findings of the Project", max: 0, type: "text" }
    ],
    totalMarks: 25,
    previousReview: '/review2',
    nextReview: '/review3'
};

// DOM ready - Initialize with config
document.addEventListener("DOMContentLoaded", () => {
    initializeReviewPage(REVIEW_CONFIG);
});