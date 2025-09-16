from flask import Blueprint, jsonify

user_bp = Blueprint('user', __name__)

@user_bp.route('/info', methods=['GET'])
def get_user_info():
    return jsonify({
        "success": True,
        "data": {
            "username": "default_user",
            "role": "admin"
        }
    })
