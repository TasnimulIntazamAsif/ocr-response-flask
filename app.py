from flask import Flask, request, jsonify, render_template, send_file
from flask_cors import CORS
import os
import uuid
import json
from datetime import datetime
from werkzeug.utils import secure_filename
# Add this at the very top of app.py (after other imports)
from typing import Dict, List, Tuple, Optional
from config import Config
from models import db, OCRResult
from database import create_app, DatabaseManager
from ocr_engine import OCRProcessor

# Initialize Flask app
app, db_instance = create_app(Config)
CORS(app)

# Initialize managers
db_manager = DatabaseManager(db_instance)
ocr_processor = OCRProcessor()

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in Config.ALLOWED_EXTENSIONS

def save_uploaded_file(file):
    """Save uploaded file and return file path"""
    if file and allowed_file(file.filename):
        # Generate unique filename
        filename = secure_filename(file.filename)
        unique_filename = f"{uuid.uuid4().hex}_{filename}"
        file_path = os.path.join(Config.UPLOAD_FOLDER, unique_filename)
        
        # Save file
        file.save(file_path)
        
        return file_path, unique_filename
    return None, None

class OCRService:
    """Service class for OCR operations"""
    
    @staticmethod
    def process_image_ocr(file_path: str, filename: str) -> Dict:
        """Process image with all OCR engines and save results"""
        try:
            # Process with all OCR engines
            ocr_results = ocr_processor.process_all(file_path)
            
            # Prepare data for database
            result_data = {
                'id': str(uuid.uuid4()),
                'filename': filename,
                'file_path': file_path,
                'upload_date': datetime.utcnow(),
                'tesseract_raw': ocr_results['results_by_engine']['tesseract']['raw_text'],
                'easyocr_raw': ocr_results['results_by_engine']['easy_ocr']['raw_text'],
                'paddleocr_raw': ocr_results['results_by_engine']['paddle_ocr']['raw_text'],
                'ocropus_raw': ocr_results['results_by_engine']['ocropus']['raw_text'],
                'tesseract_structured': ocr_results['results_by_engine']['tesseract']['structured_data'],
                'easyocr_structured': ocr_results['results_by_engine']['easy_ocr']['structured_data'],
                'paddleocr_structured': ocr_results['results_by_engine']['paddle_ocr']['structured_data'],
                'ocropus_structured': ocr_results['results_by_engine']['ocropus']['structured_data'],
                'best_guess': ocr_results['best_guess'],
                'tesseract_confidence': ocr_results['results_by_engine']['tesseract']['confidence'],
                'easyocr_confidence': ocr_results['results_by_engine']['easy_ocr']['confidence'],
                'paddleocr_confidence': ocr_results['results_by_engine']['paddle_ocr']['confidence'],
                'ocropus_confidence': ocr_results['results_by_engine']['ocropus']['confidence']
            }
            
            # Create database record
            ocr_result = OCRResult.from_dict(result_data)
            db_manager.create(ocr_result)
            
            # Prepare response
            response = {
                'id': result_data['id'],
                'filename': filename,
                'upload_date': result_data['upload_date'].isoformat(),
                'best_guess': ocr_results['best_guess'],
                'results_by_engine': {
                    'tesseract': ocr_results['results_by_engine']['tesseract']['structured_data'],
                    'easy_ocr': ocr_results['results_by_engine']['easy_ocr']['structured_data'],
                    'paddle_ocr': ocr_results['results_by_engine']['paddle_ocr']['structured_data'],
                    'ocropus': ocr_results['results_by_engine']['ocropus']['structured_data']
                },
                'confidence_scores': {
                    'tesseract': ocr_results['results_by_engine']['tesseract']['confidence'],
                    'easy_ocr': ocr_results['results_by_engine']['easy_ocr']['confidence'],
                    'paddle_ocr': ocr_results['results_by_engine']['paddle_ocr']['confidence'],
                    'ocropus': ocr_results['results_by_engine']['ocropus']['confidence']
                },
                'raw_text_samples': {
                    'tesseract': ocr_results['results_by_engine']['tesseract']['raw_text'][:200] + '...',
                    'easy_ocr': ocr_results['results_by_engine']['easy_ocr']['raw_text'][:200] + '...',
                    'paddle_ocr': ocr_results['results_by_engine']['paddle_ocr']['raw_text'][:200] + '...',
                    'ocropus': ocr_results['results_by_engine']['ocropus']['raw_text'][:200] + '...'
                }
            }
            
            return response
            
        except Exception as e:
            raise Exception(f"OCR processing failed: {str(e)}")

# Routes
@app.route('/')
def index():
    """Home page"""
    return render_template('index.html')

@app.route('/api/ocr/all', methods=['POST'])
def process_ocr_all():
    """Process image with all OCR engines"""
    try:
        # Check if file is in request
        if 'image' not in request.files:
            return jsonify({
                'error': 'No image file provided',
                'code': 400
            }), 400
        
        file = request.files['image']
        
        # Check if file is empty
        if file.filename == '':
            return jsonify({
                'error': 'No selected file',
                'code': 400
            }), 400
        
        # Save uploaded file
        file_path, filename = save_uploaded_file(file)
        if not file_path:
            return jsonify({
                'error': 'File type not allowed',
                'code': 400
            }), 400
        
        # Process OCR
        result = OCRService.process_image_ocr(file_path, filename)
        
        return jsonify({
            'success': True,
            'message': 'OCR processing completed',
            'data': result,
            'code': 200
        }), 200
        
    except Exception as e:
        return jsonify({
            'error': str(e),
            'code': 500
        }), 500

@app.route('/api/ocr/<engine_name>', methods=['POST'])
def process_ocr_single(engine_name):
    """Process image with specific OCR engine"""
    try:
        if 'image' not in request.files:
            return jsonify({'error': 'No image file provided'}), 400
        
        file = request.files['image']
        
        if file.filename == '':
            return jsonify({'error': 'No selected file'}), 400
        
        file_path, filename = save_uploaded_file(file)
        if not file_path:
            return jsonify({'error': 'File type not allowed'}), 400
        
        # Process with specific engine
        result = ocr_processor.process_single(file_path, engine_name)
        
        # Generate ID for the result
        result_id = str(uuid.uuid4())
        
        return jsonify({
            'id': result_id,
            'filename': filename,
            'engine': engine_name,
            'result': result,
            'timestamp': datetime.utcnow().isoformat()
        }), 200
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# CRUD Operations
@app.route('/api/results', methods=['GET'])
def get_all_results():
    """Get all OCR results"""
    try:
        results = db_manager.read_all()
        return jsonify({
            'success': True,
            'count': len(results),
            'data': [result.to_dict() for result in results],
            'code': 200
        }), 200
    except Exception as e:
        return jsonify({
            'error': str(e),
            'code': 500
        }), 500

@app.route('/api/results/<result_id>', methods=['GET'])
def get_result(result_id):
    """Get specific OCR result by ID"""
    try:
        result = db_manager.read(result_id)
        if result:
            return jsonify({
                'success': True,
                'data': result.to_dict(),
                'code': 200
            }), 200
        else:
            return jsonify({
                'error': 'Result not found',
                'code': 404
            }), 404
    except Exception as e:
        return jsonify({
            'error': str(e),
            'code': 500
        }), 500

@app.route('/api/results/<result_id>', methods=['PUT'])
def update_result(result_id):
    """Update OCR result"""
    try:
        data = request.json
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        result = db_manager.update(result_id, data)
        if result:
            return jsonify({
                'success': True,
                'message': 'Result updated successfully',
                'data': result.to_dict(),
                'code': 200
            }), 200
        else:
            return jsonify({
                'error': 'Result not found',
                'code': 404
            }), 404
    except Exception as e:
        return jsonify({
            'error': str(e),
            'code': 500
        }), 500

@app.route('/api/results/<result_id>', methods=['DELETE'])
def delete_result(result_id):
    """Delete OCR result"""
    try:
        success = db_manager.delete(result_id)
        if success:
            return jsonify({
                'success': True,
                'message': 'Result deleted successfully',
                'code': 200
            }), 200
        else:
            return jsonify({
                'error': 'Result not found',
                'code': 404
            }), 404
    except Exception as e:
        return jsonify({
            'error': str(e),
            'code': 500
        }), 500

@app.route('/api/search', methods=['GET'])
def search_results():
    """Search OCR results"""
    try:
        query = request.args.get('q', '')
        if not query:
            return jsonify({'error': 'No search query provided'}), 400
        
        results = db_manager.search(query)
        return jsonify({
            'success': True,
            'count': len(results),
            'data': [result.to_dict() for result in results],
            'code': 200
        }), 200
    except Exception as e:
        return jsonify({
            'error': str(e),
            'code': 500
        }), 500

@app.route('/history')
def history_page():
    """History page showing all OCR results"""
    return render_template('history.html')

@app.route('/compare')
def compare_page():
    """Page for comparing OCR results"""
    return render_template('results.html')

# Health check endpoint
@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'engines': list(ocr_processor.engines.keys())
    }), 200

# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    return jsonify({'error': 'Resource not found', 'code': 404}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error', 'code': 500}), 500

if __name__ == '__main__':
    # Create upload directory if it doesn't exist
    if not os.path.exists(Config.UPLOAD_FOLDER):
        os.makedirs(Config.UPLOAD_FOLDER)
    
    # Run Flask app
    app.run(host='0.0.0.0', port=5000, debug=True)