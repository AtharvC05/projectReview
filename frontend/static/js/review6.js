// frontend/static/js/review6.js

const REVIEW_CONFIG = {
    reviewNumber: 6,
    criteria: [
        { name: "implementation", label: "1. 75% Implementation completed", max: 0, type: "text" },
        { name: "testing_coverage", label: "2. Testing (Unit/Integration/System) (10M)", max: 10, type: "number" },
        { name: "test_cases", label: "3. Test cases designed and executed (7M)", max: 7, type: "number" },
        { name: "result_analysis", label: "4. Result analysis and conclusion (3M)", max: 3, type: "number" },
        { name: "presentation_skills", label: "5. Presentation skills (3M)", max: 3, type: "number" },
        { name: "question_answer", label: "6. Question and Answer (2M)", max: 2, type: "number" }
    ],
    totalMarks: 25,
    previousReview: '/review4',
    nextReview: '/review5'
};

// DOM ready - Initialize with config
document.addEventListener("DOMContentLoaded", () => {
    initializeReviewPage(REVIEW_CONFIG);
});
