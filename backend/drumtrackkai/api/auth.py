from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token
from werkzeug.security import generate_password_hash, check_password_hash
from ..models.user import User, SubscriptionTier
from .. import db

bp = Blueprint('auth', __name__)


@bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()

    # Validate input
    if not data or not data.get('email') or not data.get('password'):
        return jsonify({"error": "Email and password are required"}), 400

    # Check if user already exists
    existing_user = User.query.filter_by(email=data['email']).first()
    if existing_user:
        return jsonify({"error": "Email already registered"}), 400

    # Create new user
    new_user = User(
        email=data['email'],
        password_hash=generate_password_hash(data['password']),
        subscription_tier=SubscriptionTier.FREE
    )

    try:
        db.session.add(new_user)
        db.session.commit()

        # Generate access token
        access_token = create_access_token(identity=new_user.id)

        return jsonify({
            "user_id": new_user.id,
            "email": new_user.email,
            "access_token": access_token,
            "subscription_tier": new_user.subscription_tier.value
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()

    # Validate input
    if not data or not data.get('email') or not data.get('password'):
        return jsonify({"error": "Email and password are required"}), 400

    # Find user
    user = User.query.filter_by(email=data['email']).first()

    # Validate credentials
    if not user or not check_password_hash(user.password_hash, data['password']):
        return jsonify({"error": "Invalid credentials"}), 401

    # Generate access token
    access_token = create_access_token(identity=user.id)

    return jsonify({
        "user_id": user.id,
        "email": user.email,
        "access_token": access_token,
        "subscription_tier": user.subscription_tier.value
    }), 200