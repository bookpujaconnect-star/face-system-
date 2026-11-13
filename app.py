"""
AI-Based Student Identification and Campus Entry Monitoring System
Application Factory & Server Entry Point
"""

import os
import logging
from flask import Flask, render_template, jsonify, send_from_directory
from flask_cors import CORS
from config import Config
from database import Database
from models.settings import SettingsModel

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("campus_ai")

def create_app():
    app = Flask(
        __name__,
        static_folder="static",
        template_folder="templates"
    )
    app.config.from_object(Config)

    # Enable CORS for frontend API communications
    CORS(app, resources={r"/api/*": {"origins": "*"}}, supports_credentials=True)

    # Initialize Database Connection
    with app.app_context():
        try:
            Database.get_client()
            logger.info("MongoDB Atlas connected & verified.")
        except Exception as e:
            logger.error(f"Database connection initialization warning: {e}")

    # Register Blueprints
    from routes import (
        auth_bp,
        student_bp,
        biometric_bp,
        camera_bp,
        entry_bp,
        unknown_bp,
        analytics_bp,
        settings_bp,
        evaluation_bp
    )

    app.register_blueprint(auth_bp)
    app.register_blueprint(student_bp)
    app.register_blueprint(biometric_bp)
    app.register_blueprint(camera_bp)
    app.register_blueprint(entry_bp)
    app.register_blueprint(unknown_bp)
    app.register_blueprint(analytics_bp)
    app.register_blueprint(settings_bp)
    app.register_blueprint(evaluation_bp)

    # Public institution info endpoint (accessible before login)
    @app.route("/api/public/info", methods=["GET"])
    def get_public_info():
        try:
            settings = SettingsModel.get_settings()
            return jsonify({
                "status": "success",
                "institution_name": settings.get("institution_name", Config.DEFAULT_INSTITUTION_NAME),
                "campus_location": settings.get("campus_location", Config.DEFAULT_CAMPUS_LOCATION)
            })
        except Exception:
            return jsonify({
                "status": "success",
                "institution_name": Config.DEFAULT_INSTITUTION_NAME,
                "campus_location": Config.DEFAULT_CAMPUS_LOCATION
            })

    # Health check endpoint
    @app.route("/api/health", methods=["GET"])
    def health_check():
        db_latency = Database.ping_latency_ms()
        return jsonify({
            "status": "healthy" if db_latency >= 0 else "degraded",
            "database_connected": db_latency >= 0,
            "database_latency_ms": db_latency,
            "ai_models_loaded": True
        })

    # Serve Main Application UI
    @app.route("/")
    def index():
        return render_template("index.html")

    # Global error handlers
    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"status": "error", "message": "Resource not found."}), 404

    @app.errorhandler(500)
    def server_error(e):
        return jsonify({"status": "error", "message": "Internal server error occurred."}), 500

    return app

app = create_app()

if __name__ == "__main__":
    logger.info(f"Starting Campus Entry AI Server on http://{Config.HOST}:{Config.PORT}")
    app.run(host=Config.HOST, port=Config.PORT, debug=Config.DEBUG)
