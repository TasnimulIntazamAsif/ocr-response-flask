from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import json

db = SQLAlchemy()

class OCRResult(db.Model):
    __tablename__ = 'ocr_results'
    
    id = db.Column(db.String(36), primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    upload_date = db.Column(db.DateTime, default=datetime.utcnow)
    
    # OCR Results
    tesseract_raw = db.Column(db.Text, nullable=True)
    easyocr_raw = db.Column(db.Text, nullable=True)
    paddleocr_raw = db.Column(db.Text, nullable=True)
    ocropus_raw = db.Column(db.Text, nullable=True)
    
    # Structured Results
    tesseract_structured = db.Column(db.Text, nullable=True)
    easyocr_structured = db.Column(db.Text, nullable=True)
    paddleocr_structured = db.Column(db.Text, nullable=True)
    ocropus_structured = db.Column(db.Text, nullable=True)
    
    # Best Guess
    best_guess = db.Column(db.Text, nullable=True)
    
    # Confidence Scores
    tesseract_confidence = db.Column(db.Float, default=0.0)
    easyocr_confidence = db.Column(db.Float, default=0.0)
    paddleocr_confidence = db.Column(db.Float, default=0.0)
    ocropus_confidence = db.Column(db.Float, default=0.0)
    
    def __repr__(self):
        return f'<OCRResult {self.filename}>'
    
    def to_dict(self):
        """Convert model to dictionary"""
        return {
            'id': self.id,
            'filename': self.filename,
            'upload_date': self.upload_date.isoformat(),
            'results_by_engine': {
                'tesseract': json.loads(self.tesseract_structured) if self.tesseract_structured else {},
                'easy_ocr': json.loads(self.easyocr_structured) if self.easyocr_structured else {},
                'paddle_ocr': json.loads(self.paddleocr_structured) if self.paddleocr_structured else {},
                'ocropus': json.loads(self.ocropus_structured) if self.ocropus_structured else {}
            },
            'best_guess': json.loads(self.best_guess) if self.best_guess else {},
            'confidence_scores': {
                'tesseract': self.tesseract_confidence,
                'easy_ocr': self.easyocr_confidence,
                'paddle_ocr': self.paddleocr_confidence,
                'ocropus': self.ocropus_confidence
            }
        }
    
    @classmethod
    def from_dict(cls, data):
        """Create model from dictionary"""
        result = cls(
            id=data.get('id'),
            filename=data.get('filename'),
            file_path=data.get('file_path'),
            tesseract_raw=data.get('tesseract_raw'),
            easyocr_raw=data.get('easyocr_raw'),
            paddleocr_raw=data.get('paddleocr_raw'),
            ocropus_raw=data.get('ocropus_raw'),
            tesseract_structured=json.dumps(data.get('tesseract_structured', {})),
            easyocr_structured=json.dumps(data.get('easyocr_structured', {})),
            paddleocr_structured=json.dumps(data.get('paddleocr_structured', {})),
            ocropus_structured=json.dumps(data.get('ocropus_structured', {})),
            best_guess=json.dumps(data.get('best_guess', {})),
            tesseract_confidence=data.get('tesseract_confidence', 0.0),
            easyocr_confidence=data.get('easyocr_confidence', 0.0),
            paddleocr_confidence=data.get('paddleocr_confidence', 0.0),
            ocropus_confidence=data.get('ocropus_confidence', 0.0)
        )
        return result