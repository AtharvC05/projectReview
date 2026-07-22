from flask import Blueprint, request, jsonify, send_file, session
import os

from backend.commonBackend import fetch_members

from backend.sheet0 import (
    update_review0_attendance,
    get_group_members as get_review0_members,
    save_review0_marks,
    get_review0_marks,
    save_review0_responses,
    get_review0_responses,
)
from backend.sheet1 import (
    update_review1_attendance,
    get_group_members as get_review1_members,
    save_review1_marks,
    get_review1_marks,
    save_review1_responses,
    get_review1_responses,
)
from backend.sheet2 import (
    update_review2_attendance,
    get_group_members as get_review2_members,
    save_review2_marks,
    get_review2_marks,
    save_review2_responses,
    get_review2_responses,
)
from backend.sheet3 import (
    update_review3_attendance,
    get_group_members as get_review3_members,
    save_review3_marks,
    get_review3_marks,
    save_review3_responses,
    get_review3_responses,
)
from backend.sheet4 import (
    update_review4_attendance,
    get_group_members as get_review4_members,
    save_review4_marks,
    get_review4_marks,
    save_review4_responses,
    get_review4_responses,
)
from backend.sheet5 import (
    update_review6_attendance,
    get_group_members as get_review6_members,
    save_review6_marks,
    get_review6_marks,
    save_review6_responses,
    get_review6_responses,
)

# Import authentication decorators
import backend.auth as auth
login_required = auth.login_required
admin_required = auth.admin_required
user_required = auth.user_required

api_bp = Blueprint("api", __name__, url_prefix="/api")


# Healthcheck endpoint for production readiness
@api_bp.route("/health", methods=["GET"]) 
def api_healthcheck():
    return jsonify({"status": "ok"}), 200


@api_bp.route("/members", methods=["GET"])
@login_required
def api_members():
    group_id = request.args.get("group_id")
    review_number = request.args.get("review_number", 1, type=int)

    if not group_id:
        return jsonify({"error": "Missing group_id"}), 400

    members = fetch_members(group_id, review_number)
    return jsonify(members)


# ==================== REVIEW 1 ====================

@api_bp.route("/review1/attendance", methods=["POST"])
@login_required
def api_save_review1_attendance():
    data = request.get_json()
    group_id = data.get("group_id")
    attendance = data.get("attendance")

    if not group_id or attendance is None:
        return jsonify({"error": "Invalid payload"}), 400

    success = update_review1_attendance(group_id, attendance)
    if success:
        return jsonify({"message": "Attendance saved successfully"}), 200
    return jsonify({"error": "Failed to save attendance"}), 500


@api_bp.route("/review1/members", methods=["GET"])
@login_required
def api_get_review1_members():
    group_id = request.args.get("group_id")
    if not group_id:
        return jsonify({"error": "Missing group_id"}), 400
    members = get_review1_members(group_id)
    return jsonify(members)


@api_bp.route("/review1/marks", methods=["POST"])
@login_required
def api_save_review1_marks():
    data = request.get_json()
    marks_list = data.get("marks", [])

    if not marks_list:
        return jsonify({"error": "Invalid payload - marks list is empty"}), 400

    for marks in marks_list:
        if not marks.get("group_id") or not marks.get("roll_no"):
            return jsonify({"error": "Each mark entry must have group_id and roll_no"}), 400

    success = save_review1_marks(marks_list)
    if success:
        return jsonify({"success": True, "message": "Marks saved/updated successfully"}), 200
    return jsonify({"error": "Failed to save marks"}), 500


@api_bp.route("/review1/marks", methods=["GET"])
@login_required
def api_get_review1_marks():
    group_id = request.args.get("group_id")
    if not group_id:
        return jsonify({"error": "Missing group_id"}), 400
    marks = get_review1_marks(group_id)
    return jsonify(marks)


@api_bp.route("/review1/responses", methods=["POST"])
@login_required
def api_save_review1_responses():
    data = request.get_json()
    group_id = data.get("group_id")
    date = data.get("date")
    comments = data.get("comments", "")
    responses = data.get("responses", [])

    if not group_id or not date:
        return jsonify({"error": "Missing group_id or date"}), 400

    result = save_review1_responses(group_id, date, comments, responses)
    if result.get("success"):
        return (
            jsonify(
                {
                    "success": True,
                    "message": f"Responses {result['action']} successfully",
                    "action": result["action"],
                    "group_id": result["group_id"],
                }
            ),
            200,
        )
    return jsonify({"error": result.get("error", "Failed to save responses")}), 500


@api_bp.route("/review1/responses", methods=["GET"])
@login_required
def api_get_review1_responses():
    group_id = request.args.get("group_id")
    if not group_id:
        return jsonify({"error": "Missing group_id"}), 400
    submission = get_review1_responses(group_id)
    if submission:
        return jsonify(submission), 200
    return jsonify({"message": "No submission found"}), 404


@api_bp.route("/review1/generate-pdf", methods=["POST"])
@user_required  # Allow both admin and user to generate PDFs
def api_generate_review1_pdf():
    from backend.pdf_generator import generate_review1_pdf

    data = request.get_json()
    group_id = data.get("group_id")

    if not group_id:
        return jsonify({"error": "Missing group_id"}), 400

    result = generate_review1_pdf(group_id)
    if result["success"]:
        return (
            jsonify(
                {
                    "success": True,
                    "message": "PDF generated successfully",
                    "pdf_url": f"/pdf/generate/1/{group_id}",
                    "download_url": f"/pdf/download/1/{group_id}",
                }
            ),
            200,
        )
    return jsonify({"error": result["error"]}), 500


@api_bp.route("/review1/download-pdf/<filename>")
@login_required
def download_review1_pdf(filename):
    file_path = os.path.join("frontend", "static", "pdfs", filename)
    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=True)
    return jsonify({"error": "File not found"}), 404


# ==================== REVIEW 2 ====================

@api_bp.route("/review2/attendance", methods=["POST"])
@login_required
def api_save_review2_attendance():
    data = request.get_json()
    group_id = data.get("group_id")
    attendance = data.get("attendance")

    if not group_id or attendance is None:
        return jsonify({"error": "Invalid payload"}), 400

    success = update_review2_attendance(group_id, attendance)
    if success:
        return jsonify({"message": "Attendance saved successfully"}), 200
    return jsonify({"error": "Failed to save attendance"}), 500


@api_bp.route("/review2/members", methods=["GET"])
@login_required
def api_get_review2_members():
    group_id = request.args.get("group_id")
    if not group_id:
        return jsonify({"error": "Missing group_id"}), 400
    members = get_review2_members(group_id)
    return jsonify(members)


@api_bp.route("/review2/marks", methods=["POST"])
@login_required
def api_save_review2_marks():
    data = request.get_json()
    marks_list = data.get("marks", [])

    if not marks_list:
        return jsonify({"error": "Invalid payload - marks list is empty"}), 400

    for marks in marks_list:
        if not marks.get("group_id") or not marks.get("roll_no"):
            return jsonify({"error": "Each mark entry must have group_id and roll_no"}), 400

    success = save_review2_marks(marks_list)
    if success:
        return jsonify({"success": True, "message": "Marks saved/updated successfully"}), 200
    return jsonify({"error": "Failed to save marks"}), 500


@api_bp.route("/review2/marks", methods=["GET"])
@login_required
def api_get_review2_marks():
    group_id = request.args.get("group_id")
    if not group_id:
        return jsonify({"error": "Missing group_id"}), 400
    marks = get_review2_marks(group_id)
    return jsonify(marks)


@api_bp.route("/review2/responses", methods=["POST"])
@login_required
def api_save_review2_responses():
    data = request.get_json()
    group_id = data.get("group_id")
    date = data.get("date")
    comments = data.get("comments", "")
    responses = data.get("responses", [])

    if not group_id or not date:
        return jsonify({"error": "Missing group_id or date"}), 400

    result = save_review2_responses(group_id, date, comments, responses)
    if result.get("success"):
        return (
            jsonify(
                {
                    "success": True,
                    "message": f"Responses {result['action']} successfully",
                    "action": result["action"],
                    "group_id": result["group_id"],
                }
            ),
            200,
        )
    return jsonify({"error": result.get("error", "Failed to save responses")}), 500


@api_bp.route("/review2/responses", methods=["GET"])
@login_required
def api_get_review2_responses():
    group_id = request.args.get("group_id")
    if not group_id:
        return jsonify({"error": "Missing group_id"}), 400
    submission = get_review2_responses(group_id)
    if submission:
        return jsonify(submission), 200
    return jsonify({"message": "No submission found"}), 404


@api_bp.route("/review2/generate-pdf", methods=["POST"])
@user_required
def api_generate_review2_pdf():
    from backend.pdf_generator import generate_review2_pdf

    data = request.get_json()
    group_id = data.get("group_id")
    if not group_id:
        return jsonify({"error": "Missing group_id"}), 400
    result = generate_review2_pdf(group_id)
    if result["success"]:
        return (
            jsonify(
                {
                    "success": True,
                    "message": "PDF generated successfully",
                    "pdf_url": f"/pdf/generate/2/{group_id}",
                    "download_url": f"/pdf/download/2/{group_id}",
                }
            ),
            200,
        )
    return jsonify({"error": result["error"]}), 500

#MOCK

@api_bp.route("/review0/attendance", methods=["POST"])
@login_required
def api_save_review0_attendance():
    data = request.get_json()
    group_id = data.get("group_id")
    attendance = data.get("attendance")

    if not group_id or attendance is None:
        return jsonify({"error": "Invalid payload"}), 400

    success = update_review0_attendance(group_id, attendance)
    if success:
        return jsonify({"message": "Attendance saved successfully"}), 200
    return jsonify({"error": "Failed to save attendance"}), 500


@api_bp.route("/review0/members", methods=["GET"])
@login_required
def api_get_review0_members():
    group_id = request.args.get("group_id")
    if not group_id:
        return jsonify({"error": "Missing group_id"}), 400
    members = get_review0_members(group_id)
    return jsonify(members)


@api_bp.route("/review0/marks", methods=["POST"])
@login_required
def api_save_review0_marks():
    data = request.get_json()
    marks_list = data.get("marks", [])

    if not marks_list:
        return jsonify({"error": "Invalid payload - marks list is empty"}), 400

    for marks in marks_list:
        if not marks.get("group_id") or not marks.get("roll_no"):
            return jsonify({"error": "Each mark entry must have group_id and roll_no"}), 400

    success = save_review0_marks(marks_list)
    if success:
        return jsonify({"success": True, "message": "Marks saved/updated successfully"}), 200
    return jsonify({"error": "Failed to save marks"}), 500


@api_bp.route("/review0/marks", methods=["GET"])
@login_required
def api_get_review0_marks():
    group_id = request.args.get("group_id")
    if not group_id:
        return jsonify({"error": "Missing group_id"}), 400
    marks = get_review0_marks(group_id)
    return jsonify(marks)


@api_bp.route("/review0/responses", methods=["POST"])
@login_required
def api_save_review0_responses():
    data = request.get_json()
    group_id = data.get("group_id")
    date = data.get("date")
    comments = data.get("comments", "")
    responses = data.get("responses", [])

    if not group_id or not date:
        return jsonify({"error": "Missing group_id or date"}), 400

    result = save_review0_responses(group_id, date, comments, responses)
    if result.get("success"):
        return (
            jsonify(
                {
                    "success": True,
                    "message": f"Responses {result['action']} successfully",
                    "action": result["action"],
                    "group_id": result["group_id"],
                }
            ),
            200,
        )
    return jsonify({"error": result.get("error", "Failed to save responses")}), 500


@api_bp.route("/review0/responses", methods=["GET"])
@login_required
def api_get_review0_responses():
    group_id = request.args.get("group_id")
    if not group_id:
        return jsonify({"error": "Missing group_id"}), 400
    submission = get_review0_responses(group_id)
    if submission:
        return jsonify(submission), 200
    return jsonify({"message": "No submission found"}), 404


@api_bp.route("/review0/generate-pdf", methods=["POST"])
@user_required
def api_generate_review0_pdf():
    from backend.pdf_generator import generate_review0_pdf

    data = request.get_json()
    group_id = data.get("group_id")
    if not group_id:
        return jsonify({"error": "Missing group_id"}), 400
    result = generate_review0_pdf(group_id)
    if result["success"]:
        return (
            jsonify(
                {
                    "success": True,
                    "message": "PDF generated successfully",
                    "pdf_url": f"/pdf/generate/0/{group_id}",
                    "download_url": f"/pdf/download/0/{group_id}",
                }
            ),
            200,
        )
    return jsonify({"error": result["error"]}), 500

# ==================== REVIEW 3 ====================

@api_bp.route("/review3/attendance", methods=["POST"])
@login_required
def api_save_review3_attendance():
    data = request.get_json()
    group_id = data.get("group_id")
    attendance = data.get("attendance")

    if not group_id or attendance is None:
        return jsonify({"error": "Invalid payload"}), 400

    success = update_review3_attendance(group_id, attendance)
    if success:
        return jsonify({"message": "Attendance saved successfully"}), 200
    return jsonify({"error": "Failed to save attendance"}), 500


@api_bp.route("/review3/members", methods=["GET"])
@login_required
def api_get_review3_members():
    group_id = request.args.get("group_id")
    if not group_id:
        return jsonify({"error": "Missing group_id"}), 400
    members = get_review3_members(group_id)
    return jsonify(members)


@api_bp.route("/review3/marks", methods=["POST"])
@login_required
def api_save_review3_marks():
    data = request.get_json()
    marks_list = data.get("marks", [])

    if not marks_list:
        return jsonify({"error": "Invalid payload - marks list is empty"}), 400

    for marks in marks_list:
        if not marks.get("group_id") or not marks.get("roll_no"):
            return jsonify({"error": "Each mark entry must have group_id and roll_no"}), 400

    success = save_review3_marks(marks_list)
    if success:
        return jsonify({"success": True, "message": "Marks saved/updated successfully"}), 200
    return jsonify({"error": "Failed to save marks"}), 500


@api_bp.route("/review3/marks", methods=["GET"])
@login_required
def api_get_review3_marks():
    group_id = request.args.get("group_id")
    if not group_id:
        return jsonify({"error": "Missing group_id"}), 400
    marks = get_review3_marks(group_id)
    return jsonify(marks)


@api_bp.route("/review3/responses", methods=["POST"])
@login_required
def api_save_review3_responses():
    data = request.get_json()
    group_id = data.get("group_id")
    date = data.get("date")
    comments = data.get("comments", "")
    responses = data.get("responses", [])

    if not group_id or not date:
        return jsonify({"error": "Missing group_id or date"}), 400

    result = save_review3_responses(group_id, date, comments, responses)
    if result.get("success"):
        return (
            jsonify(
                {
                    "success": True,
                    "message": f"Responses {result['action']} successfully",
                    "action": result["action"],
                    "group_id": result["group_id"],
                }
            ),
            200,
        )
    return jsonify({"error": result.get("error", "Failed to save responses")}), 500


@api_bp.route("/review3/responses", methods=["GET"])
@login_required
def api_get_review3_responses():
    group_id = request.args.get("group_id")
    if not group_id:
        return jsonify({"error": "Missing group_id"}), 400
    submission = get_review3_responses(group_id)
    if submission:
        return jsonify(submission), 200
    return jsonify({"message": "No submission found"}), 404


@api_bp.route("/review3/generate-pdf", methods=["POST"])
@user_required
def api_generate_review3_pdf():
    from backend.pdf_generator import generate_review3_pdf

    data = request.get_json()
    group_id = data.get("group_id")
    if not group_id:
        return jsonify({"error": "Missing group_id"}), 400
    result = generate_review3_pdf(group_id)
    if result["success"]:
        return (
            jsonify(
                {
                    "success": True,
                    "message": "PDF generated successfully",
                    "pdf_url": f"/pdf/generate/3/{group_id}",
                    "download_url": f"/pdf/download/3/{group_id}"
                }
            ),
            200,
        )
    return jsonify({"error": result["error"]}), 500


# ==================== REVIEW 4 ====================

@api_bp.route("/review4/attendance", methods=["POST"])
@login_required
def api_save_review4_attendance():
    data = request.get_json()
    group_id = data.get("group_id")
    attendance = data.get("attendance")

    if not group_id or attendance is None:
        return jsonify({"error": "Invalid payload"}), 400

    success = update_review4_attendance(group_id, attendance)
    if success:
        return jsonify({"message": "Attendance saved successfully"}), 200
    return jsonify({"error": "Failed to save attendance"}), 500


@api_bp.route("/review4/members", methods=["GET"])
@login_required
def api_get_review4_members():
    group_id = request.args.get("group_id")
    if not group_id:
        return jsonify({"error": "Missing group_id"}), 400
    members = get_review4_members(group_id)
    return jsonify(members)


@api_bp.route("/review4/marks", methods=["POST"])
@login_required
def api_save_review4_marks():
    data = request.get_json()
    marks_list = data.get("marks", [])

    if not marks_list:
        return jsonify({"error": "Invalid payload - marks list is empty"}), 400

    for marks in marks_list:
        if not marks.get("group_id") or not marks.get("roll_no"):
            return jsonify({"error": "Each mark entry must have group_id and roll_no"}), 400

    success = save_review4_marks(marks_list)
    if success:
        return jsonify({"success": True, "message": "Marks saved/updated successfully"}), 200
    return jsonify({"error": "Failed to save marks"}), 500


@api_bp.route("/review4/marks", methods=["GET"])
@login_required
def api_get_review4_marks():
    group_id = request.args.get("group_id")
    if not group_id:
        return jsonify({"error": "Missing group_id"}), 400
    marks = get_review4_marks(group_id)
    return jsonify(marks)


@api_bp.route("/review4/responses", methods=["POST"])
@login_required
def api_save_review4_responses():
    data = request.get_json()
    group_id = data.get("group_id")
    date = data.get("date")
    comments = data.get("comments", "")
    responses = data.get("responses", [])

    if not group_id or not date:
        return jsonify({"error": "Missing group_id or date"}), 400

    result = save_review4_responses(group_id, date, comments, responses)
    if result.get("success"):
        return (
            jsonify(
                {
                    "success": True,
                    "message": f"Responses {result['action']} successfully",
                    "action": result["action"],
                    "group_id": result["group_id"],
                }
            ),
            200,
        )
    return jsonify({"error": result.get("error", "Failed to save responses")}), 500


@api_bp.route("/review4/responses", methods=["GET"])
@login_required
def api_get_review4_responses():
    group_id = request.args.get("group_id")
    if not group_id:
        return jsonify({"error": "Missing group_id"}), 400
    submission = get_review4_responses(group_id)
    if submission:
        return jsonify(submission), 200
    return jsonify({"message": "No submission found"}), 404


@api_bp.route("/review4/generate-pdf", methods=["POST"])
@user_required
def api_generate_review4_pdf():
    from backend.pdf_generator import generate_review4_pdf

    data = request.get_json()
    group_id = data.get("group_id")
    if not group_id:
        return jsonify({"error": "Missing group_id"}), 400
    result = generate_review4_pdf(group_id)
    if result["success"]:
        return (
            jsonify(
                {
                    "success": True,
                    "message": "PDF generated successfully",
                    "pdf_url": f"/pdf/generate/4/{group_id}",
                    "download_url": f"/pdf/download/4/{group_id}"
                }
            ),
            200,
        )
    return jsonify({"error": result["error"]}), 500


# ==================== REVIEW 6 ROUTES (SEM-II MOCK) ====================

@api_bp.route("/review6/attendance", methods=["POST"])
@user_required
def api_save_review6_attendance():
    data = request.get_json()
    group_id = data.get("group_id")
    attendance = data.get("attendance")
    if not group_id or not isinstance(attendance, list):
        return jsonify({"error": "Invalid payload"}), 400
    success = update_review6_attendance(group_id, attendance)
    if success:
        return jsonify({"message": "Attendance saved successfully"}), 200
    return jsonify({"error": "Failed to save attendance"}), 500


@api_bp.route("/review6/members", methods=["GET"])
@user_required
def api_get_review6_members():
    group_id = request.args.get("group_id")
    if not group_id:
        return jsonify({"error": "Missing group_id"}), 400
    members = get_review6_members(group_id)
    return jsonify(members), 200


@api_bp.route("/review6/marks", methods=["POST"])
@user_required
def api_save_review6_marks():
    data = request.get_json()
    marks_list = data.get("marks")
    if not marks_list or not isinstance(marks_list, list):
        return jsonify({"error": "Invalid payload"}), 400
    for item in marks_list:
        if "group_id" not in item or "roll_no" not in item:
            return jsonify({"error": "Each mark entry must contain group_id and roll_no"}), 400
    success = save_review6_marks(marks_list)
    if success:
        return jsonify({"message": "Marks saved successfully"}), 200
    return jsonify({"error": "Failed to save marks"}), 500


@api_bp.route("/review6/marks", methods=["GET"])
@user_required
def api_get_review6_marks():
    group_id = request.args.get("group_id")
    if not group_id:
        return jsonify({"error": "Missing group_id"}), 400
    marks = get_review6_marks(group_id)
    return jsonify(marks), 200


@api_bp.route("/review6/responses", methods=["POST"])
@user_required
def api_save_review6_responses():
    data = request.get_json()
    group_id = data.get("group_id")
    date = data.get("date")
    comments = data.get("comments")
    responses = data.get("responses")
    if not group_id or not date or not isinstance(responses, dict):
        return jsonify({"error": "Invalid payload"}), 400
    result = save_review6_responses(group_id, date, comments, responses)
    if result["success"]:
        return jsonify({"message": "Responses saved successfully"}), 200
    return jsonify({"error": result.get("error", "Failed to save responses")}), 500


@api_bp.route("/review6/responses", methods=["GET"])
@user_required
def api_get_review6_responses():
    group_id = request.args.get("group_id")
    if not group_id:
        return jsonify({"error": "Missing group_id"}), 400
    submission = get_review6_responses(group_id)
    if submission:
        return jsonify(submission), 200
    return jsonify({"message": "No submission found"}), 404


@api_bp.route("/review6/generate-pdf", methods=["POST"])
@user_required
def api_generate_review6_pdf():
    from backend.pdf_generator import generate_review6_pdf

    data = request.get_json()
    group_id = data.get("group_id")
    if not group_id:
        return jsonify({"error": "Missing group_id"}), 400
    result = generate_review6_pdf(group_id)
    if result["success"]:
        return (
            jsonify(
                {
                    "success": True,
                    "message": "PDF generated successfully",
                    "pdf_url": f"/pdf/generate/6/{group_id}",
                    "download_url": f"/pdf/download/6/{group_id}"
                }
            ),
            200,
        )
    return jsonify({"error": result["error"]}), 500


# ==================== UTILITIES ====================

@api_bp.route('/export-excel-test', methods=['POST'])
@admin_required  # Only admins can export data
def export_excel_test():
    try:
        import pandas as pd
        import io
        from datetime import datetime

        data = request.get_json()
        if not data or 'data' not in data:
            return jsonify({'error': 'No data provided'}), 400

        df = pd.DataFrame(data['data'])

        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, sheet_name='Project Data', index=False)

        output.seek(0)
        return send_file(
            output,
            as_attachment=True,
            download_name=f'test_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx',
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
# ==================== ATTENDANCE DASHBOARD ====================

@api_bp.route("/groups", methods=["GET"])
@login_required
def api_get_all_groups():
    """API endpoint to fetch all groups with members and attendance"""
    from backend.commonBackend import get_all_groups_with_attendance
    
    try:
        groups = get_all_groups_with_attendance()
        return jsonify(groups), 200
    except Exception as e:
        print(f"Error in /api/groups: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@api_bp.route("/attendance/pdf", methods=["GET"])
@login_required
def api_generate_attendance_pdf():
    """API endpoint to generate attendance PDF report"""
    from backend.commonBackend import generate_attendance_pdf_report
    from datetime import datetime
    
    try:
        result = generate_attendance_pdf_report()
        
        if not result['success']:
            return jsonify({'error': result.get('error', 'Unknown error')}), 500
        
        # Send the PDF file
        return send_file(
            result['buffer'],
            as_attachment=True,
            download_name=result['filename'],
            mimetype='application/pdf'
        )
        
    except Exception as e:
        print(f"Error in /api/attendance/pdf: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500
    
# ==================== FINAL SHEET ====================

@api_bp.route("/final-sheet/summary", methods=["GET"])
@login_required
def api_get_final_sheet_summary():
    """API endpoint to get complete summary data"""
    from backend.finalSheet import get_final_summary_data
    
    group_id = request.args.get('group_id', '').strip()
    
    if not group_id:
        return jsonify({'error': 'Group ID is required'}), 400
    
    summary_data = get_final_summary_data(group_id)
    
    if not summary_data:
        return jsonify({'error': 'No data found for this group'}), 404

    
    return jsonify(summary_data), 200


@api_bp.route("/review5/generate-pdf", methods=["POST"])
@user_required
def api_generate_review5_pdf():
    """API endpoint to generate the final summary PDF for Review 5."""
    from backend.pdf_generator import generate_review5_pdf

    data = request.get_json()
    group_id = data.get("group_id")

    if not group_id:
        return jsonify({"error": "Missing group_id"}), 400

    result = generate_review5_pdf(group_id)
    if result.get("success"):
        return jsonify({
            "success": True,
            "message": "Review 5 PDF generated successfully",
            "download_url": f"/static/pdfs/{result['filename']}"
        }), 200
    
    return jsonify({"error": result.get("error", "Failed to generate Review 5 PDF")}), 500



@api_bp.route("/final-sheet/comments", methods=["GET"])
@login_required
def api_get_final_comments():
    """Get overall comments for a group"""
    from backend.finalSheet import get_overall_comments
    
    group_id = request.args.get('group_id', '').strip()
    
    if not group_id:
        return jsonify({'error': 'Group ID is required'}), 400
    
    comments = get_overall_comments(group_id)
    
    return jsonify({
        'group_id': group_id,
        'comments': comments or ''
    }), 200


@api_bp.route("/final-sheet/comments", methods=["POST"])
@login_required
def api_save_final_comments():
    """Save overall comments for a group"""
    from backend.finalSheet import save_overall_comments
    
    data = request.get_json()
    
    group_id = data.get('group_id', '').strip()
    comments = data.get('comments', '').strip()
    
    if not group_id:
        return jsonify({'error': 'Group ID is required'}), 400
    
    success = save_overall_comments(group_id, comments)
    
    if success:
        return jsonify({
            'success': True,
            'message': 'Comments saved successfully'
        }), 200
    else:
        return jsonify({'error': 'Failed to save comments'}), 500


# ================== ACADEMIC YEAR ENDPOINTS ==================

@api_bp.route("/academic-year", methods=["GET"])
@login_required
def api_get_academic_year():
    import backend.db as db
    return jsonify({
        "success": True,
        "academic_year": db.get_academic_year(),
        "is_admin": session.get('role') == 'admin'
    }), 200


@api_bp.route("/academic-year", methods=["POST"])
@admin_required   # ← Only admins can change the year
def api_set_academic_year():
    import backend.db as db
    import re
    data = request.get_json()
    year = data.get("academic_year", "").strip()
    if not year:
        return jsonify({"error": "Academic year is required"}), 400
    # Validate strict YYYY-YY format
    if not re.match(r'^\d{4}-\d{2}$', year):
        return jsonify({"error": "Invalid format. Use YYYY-YY (e.g. 2025-26)"}), 400
    db.set_academic_year(year)
    return jsonify({
        "success": True,
        "message": f"Academic year updated to {year} server-wide",
        "academic_year": year
    }), 200