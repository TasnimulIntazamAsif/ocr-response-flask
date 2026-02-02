import cv2
import numpy as np
from PIL import Image
import pytesseract
import easyocr
import os
import re
import json
from typing import Dict, List, Tuple, Optional
import uuid

class BaseOCREngine:
    """Base class for all OCR engines"""
    
    def __init__(self, engine_name: str):
        self.engine_name = engine_name
    
    def preprocess_image(self, image_path: str) -> np.ndarray:
        """Preprocess image for better OCR results"""
        try:
            # Read image
            img = cv2.imread(image_path)
            
            if img is None:
                raise ValueError(f"Could not read image from {image_path}")
            
            # Convert to grayscale
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            
            # Apply thresholding
            _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            # Denoise
            denoised = cv2.medianBlur(thresh, 3)
            
            return denoised
        except Exception as e:
            print(f"Preprocessing error: {e}")
            return cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    
    def extract_text(self, image_path: str) -> str:
        """Extract text from image - to be implemented by subclasses"""
        raise NotImplementedError
    
    def extract_with_confidence(self, image_path: str) -> Tuple[str, float]:
        """Extract text with confidence score"""
        text = self.extract_text(image_path)
        # Simple confidence calculation based on text length and content
        confidence = min(1.0, len(text.strip()) / 1000)  # Normalize
        return text, confidence
    
    def parse_id_card_fields(self, text: str) -> Dict[str, str]:
        """Parse common ID card fields from extracted text"""
        fields = {
            'ID': '',
            'FullName': '',
            'University': '',
            'Department': '',
            'Enrollment': '',
            'BloodGroup': '',
            'Validity': ''
        }
        
        # ID Patterns
        id_patterns = [
            r'[A-Za-z]\d{7}',  # C2010074 pattern
            r'ID[:\s]*([A-Za-z0-9]{6,10})',
            r'ID\s*No[:\s]*([A-Za-z0-9]{6,10})'
        ]
        
        for pattern in id_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                fields['ID'] = match.group(1) if len(match.groups()) > 0 else match.group(0)
                break
        
        # Name Patterns
        name_patterns = [
            r'Name[:\s]*([A-Z][a-z]+\s+[A-Z][a-z]+\s+[A-Z][a-z]+)',
            r'Full Name[:\s]*([A-Z][a-z]+\s+[A-Z][a-z]+\s+[A-Z][a-z]+)'
        ]
        
        for pattern in name_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match and len(match.group(1).split()) >= 2:
                fields['FullName'] = match.group(1)
                break
        
        # University Patterns
        uni_keywords = ['university', 'institute', 'college']
        for line in text.split('\n'):
            line_lower = line.lower()
            if any(keyword in line_lower for keyword in uni_keywords) and len(line.strip()) > 10:
                fields['University'] = line.strip()
                break
        
        # Department Patterns
        dept_patterns = [
            r'Department[:\s]*([A-Za-z\s&(),.-]+)',
            r'Dept[:\s]*([A-Za-z\s&(),.-]+)'
        ]
        
        for pattern in dept_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                fields['Department'] = match.group(1).strip()
                break
        
        # Enrollment/Year Patterns
        year_patterns = [
            r'Enrollment[:\s]*([A-Za-z]+\s+\d{4})',
            r'Session[:\s]*([A-Za-z]+\s+\d{4})',
            r'(Spring|Fall|Autumn|Summer|Winter)\s+\d{4}'
        ]
        
        for pattern in year_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                fields['Enrollment'] = match.group(0)
                break
        
        # Blood Group Patterns
        blood_patterns = [
            r'Blood[:\s]*([A|B|AB|O][+-])',
            r'Blood Group[:\s]*([A|B|AB|O][+-])'
        ]
        
        for pattern in blood_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                fields['BloodGroup'] = match.group(1).upper()
                break
        
        # Validity Patterns
        validity_patterns = [
            r'Valid[:\s]*([A-Za-z]+\s+\d{4})',
            r'Validity[:\s]*([A-Za-z]+\s+\d{4})'
        ]
        
        for pattern in validity_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                fields['Validity'] = match.group(0)
                break
        
        return fields
    
    def process_image(self, image_path: str) -> Dict:
        """Process image and return structured results"""
        try:
            raw_text, confidence = self.extract_with_confidence(image_path)
            structured_data = self.parse_id_card_fields(raw_text)
            
            return {
                'raw_text': raw_text,
                'structured_data': structured_data,
                'confidence': confidence,
                'engine': self.engine_name
            }
        except Exception as e:
            print(f"{self.engine_name} error: {e}")
            return {
                'raw_text': f"Error: {str(e)}",
                'structured_data': {},
                'confidence': 0.0,
                'engine': self.engine_name
            }


class TesseractEngine(BaseOCREngine):
    """Tesseract OCR Engine"""
    
    def __init__(self):
        super().__init__('tesseract')
    
    def extract_text(self, image_path: str) -> str:
        """Extract text using Tesseract"""
        try:
            # Preprocess image
            processed_img = self.preprocess_image(image_path)
            
            # Convert numpy array to PIL Image
            pil_img = Image.fromarray(processed_img)
            
            # Extract text
            text = pytesseract.image_to_string(pil_img, config='--oem 3 --psm 6')
            
            return text
        except Exception as e:
            raise Exception(f"Tesseract extraction failed: {str(e)}")


class EasyOCREngine(BaseOCREngine):
    """EasyOCR Engine"""
    
    def __init__(self):
        super().__init__('easy_ocr')
        # Initialize EasyOCR reader
        self.reader = easyocr.Reader(['en'], gpu=False)
    
    def extract_text(self, image_path: str) -> str:
        """Extract text using EasyOCR"""
        try:
            # Read image
            img = cv2.imread(image_path)
            
            if img is None:
                raise ValueError("Could not read image")
            
            # Extract text
            results = self.reader.readtext(img, paragraph=True)
            
            # Combine all text
            text = ' '.join([result[1] for result in results])
            
            return text
        except Exception as e:
            raise Exception(f"EasyOCR extraction failed: {str(e)}")


class OCRProcessor:
    """Main OCR processor that uses working engines"""
    
    def __init__(self):
        self.engines = {}
        
        # Initialize Tesseract
        try:
            self.engines['tesseract'] = TesseractEngine()
            print("Tesseract engine initialized successfully")
        except Exception as e:
            print(f"Tesseract initialization failed: {e}")
        
        # Initialize EasyOCR
        try:
            self.engines['easy_ocr'] = EasyOCREngine()
            print("EasyOCR engine initialized successfully")
        except Exception as e:
            print(f"EasyOCR initialization failed: {e}")
        
        # Add dummy engines for compatibility
        self.engines['paddle_ocr'] = self._create_dummy_engine('paddle_ocr', "PaddleOCR disabled (requires paddlepaddle)")
        self.engines['ocropus'] = self._create_dummy_engine('ocropus', "Using Tesseract as fallback")
    
    def _create_dummy_engine(self, engine_name: str, message: str):
        """Create a dummy engine"""
        class DummyEngine(BaseOCREngine):
            def __init__(self, name, msg):
                super().__init__(name)
                self.msg = msg
            
            def extract_text(self, image_path):
                return self.msg
            
            def extract_with_confidence(self, image_path):
                return self.msg, 0.0
            
            def process_image(self, image_path):
                return {
                    'raw_text': self.msg,
                    'structured_data': {},
                    'confidence': 0.0,
                    'engine': self.engine_name
                }
        
        return DummyEngine(engine_name, message)
    
    def process_all(self, image_path: str) -> Dict:
        """Process image with all OCR engines"""
        results = {}
        
        for engine_name, engine in self.engines.items():
            print(f"Processing with {engine_name}...")
            try:
                result = engine.process_image(image_path)
                results[engine_name] = result
            except Exception as e:
                print(f"Error with {engine_name}: {e}")
                results[engine_name] = {
                    'raw_text': f"Error: {str(e)}",
                    'structured_data': {},
                    'confidence': 0.0,
                    'engine': engine_name
                }
        
        # Determine best guess
        best_guess = self._determine_best_guess(results)
        
        return {
            'best_guess': best_guess,
            'results_by_engine': results
        }
    
    def _determine_best_guess(self, results: Dict) -> Dict[str, str]:
        """Determine best guess by voting across engines"""
        fields = [
            'ID', 'FullName', 'University', 'Department', 
            'Enrollment', 'BloodGroup', 'Validity'
        ]
        
        best_guess = {}
        
        for field in fields:
            values = {}
            for engine_name, result in results.items():
                value = result['structured_data'].get(field, '').strip()
                if value and value.lower() not in ['not found', 'net found', '']:
                    values[value] = values.get(value, 0) + 1
            
            if values:
                # Get the most common value
                best_value = max(values.items(), key=lambda x: x[1])[0]
                best_guess[field] = best_value
            else:
                best_guess[field] = 'Not Found'
        
        return best_guess
    
    def process_single(self, image_path: str, engine_name: str) -> Dict:
        """Process image with a specific engine"""
        if engine_name not in self.engines:
            raise ValueError(f"Unknown engine: {engine_name}")
        
        engine = self.engines[engine_name]
        return engine.process_image(image_path)