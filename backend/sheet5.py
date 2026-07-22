# backend/sheet5.py
from backend.commonBackend import (
    update_review_attendance,
    get_group_members_for_review,
    save_review_marks,
    get_review_marks,
    save_review_responses,
    get_review_responses
)


def update_review6_attendance(group_id, attendance):
    """Update review6_attendance for members"""
    return update_review_attendance(6, group_id, attendance)


def get_group_members(group_id):
    """Fetch all members of a group with their details for Review 6 (SEM-II MOCK)"""
    return get_group_members_for_review(6, group_id)


def save_review6_marks(marks_list):
    """Save or update Review 6 marks for multiple students using UPSERT"""
    return save_review_marks(6, marks_list)


def get_review6_marks(group_id):
    """Fetch existing Review 6 marks for a group"""
    return get_review_marks(6, group_id)


def save_review6_responses(group_id, date, comments, responses):
    """Save or update Review 6 questionnaire responses using UPSERT"""
    return save_review_responses(6, group_id, date, comments, responses)


def get_review6_responses(group_id):
    """Fetch Review 6 questionnaire responses for a group"""
    return get_review_responses(6, group_id)
