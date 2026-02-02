from flask import Flask
from models import db
import os

def create_app(config_class):
    """Application factory pattern"""
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Initialize extensions
    db.init_app(app)
    
    # Create tables
    with app.app_context():
        db.create_all()
    
    return app, db

class DatabaseManager:
    """CRUD operations for OCR results"""
    
    def __init__(self, db):
        self.db = db
    
    def create(self, ocr_result):
        """Create new OCR result"""
        try:
            self.db.session.add(ocr_result)
            self.db.session.commit()
            return ocr_result
        except Exception as e:
            self.db.session.rollback()
            raise e
    
    def read(self, result_id):
        """Read OCR result by ID"""
        return OCRResult.query.get(result_id)
    
    def read_all(self):
        """Read all OCR results"""
        return OCRResult.query.order_by(OCRResult.upload_date.desc()).all()
    
    def read_by_filename(self, filename):
        """Read OCR result by filename"""
        return OCRResult.query.filter_by(filename=filename).first()
    
    def update(self, result_id, update_data):
        """Update OCR result"""
        try:
            result = self.read(result_id)
            if result:
                for key, value in update_data.items():
                    if hasattr(result, key):
                        setattr(result, key, value)
                self.db.session.commit()
            return result
        except Exception as e:
            self.db.session.rollback()
            raise e
    
    def delete(self, result_id):
        """Delete OCR result"""
        try:
            result = self.read(result_id)
            if result:
                # Delete associated file
                if os.path.exists(result.file_path):
                    os.remove(result.file_path)
                
                self.db.session.delete(result)
                self.db.session.commit()
                return True
            return False
        except Exception as e:
            self.db.session.rollback()
            raise e
    
    def search(self, query):
        """Search OCR results by filename or content"""
        results = OCRResult.query.filter(
            OCRResult.filename.ilike(f'%{query}%') |
            OCRResult.tesseract_raw.ilike(f'%{query}%') |
            OCRResult.easyocr_raw.ilike(f'%{query}%')
        ).all()
        return results