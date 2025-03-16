from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from ..models.user import User
from ..services.analysis_service import AnalysisService

bp = Blueprint('analysis', __name__)


@bp.route('/analyze', methods=['POST'])
@jwt_required()
def perform_analysis():
    """
    Endpoint for performing drum performance analysis
    """
    try:
        # Get current user
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)

        # Check if file was uploaded
        if 'audio_file' not in request.files:
            return jsonify({'error': 'No audio file uploaded'}), 400

        audio_file = request.files['audio_file']
        analysis_type = request.form.get('analysis_type', 'general')

        # Perform analysis
        analysis_service = AnalysisService()
        result = analysis_service.create_analysis(current_user_id, analysis_type)

        return jsonify(result), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500