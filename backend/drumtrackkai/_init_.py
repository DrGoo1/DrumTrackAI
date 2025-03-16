from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager

# Initialize extensions
db = SQLAlchemy()
jwt = JWTManager()


def create_app(config_object=None):
    """
    Application factory function

    Args:
        config_object: Configuration class or object

    Returns:
        Configured Flask application
    """
    # Create Flask app instance
    app = Flask(__name__)

    # Default configuration
    app.config['SECRET_KEY'] = 'your-secret-key'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///drumtrackkai.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['JWT_SECRET_KEY'] = 'your-jwt-secret-key'

    # Override with provided config if any
    if config_object:
        app.config.from_object(config_object)

    # Initialize extensions
    db.init_app(app)
    jwt.init_app(app)

    # Import and register blueprints
    from .api import auth, analysis
    app.register_blueprint(auth.bp, url_prefix='/api/auth')
    app.register_blueprint(analysis.bp, url_prefix='/api/analysis')

    return app