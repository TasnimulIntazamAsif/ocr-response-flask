import os
from datetime import datetime

class Config:
    # Flask Configuration
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'ocr-comparison-secret-key'
    UPLOAD_FOLDER = 'uploads'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'bmp', 'tiff', 'pdf'}
    
    # Database Configuration
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///ocr_results.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # OCR Configuration
    EASYOCR_LANGUAGES = ['en', 'bn']  # English and Bengali
    TESSERACT_CONFIG = '--oem 3 --psm 6'
    
    @staticmethod
    def init_app(app):
        # Create upload directory if not exists
        if not os.path.exists(Config.UPLOAD_FOLDER):
            os.makedirs(Config.UPLOAD_FOLDER)
            
        # Create templates directory if not exists
        templates_dir = 'templates'
        if not os.path.exists(templates_dir):
            os.makedirs(templates_dir)