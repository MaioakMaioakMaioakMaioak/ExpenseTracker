# backend/app/services/ocr_service.py
import easyocr
import cv2
import numpy as np
import re
from typing import Dict, List, Optional
from pathlib import Path

class OCRService:
    def __init__(self):
        print("🔧 Loading OCR model (this may take a moment)...")
        try:
            # Load Thai + English reader
            self.reader = easyocr.Reader(['th', 'en'], gpu=False, verbose=False)
            print("✅ OCR model loaded successfully!")
            
            # Import parser
            try:
                from app.services.enhanced_parser import receipt_parser
                self.parser = receipt_parser
                print("✅ Receipt parser loaded!")
            except ImportError:
                print("⚠️ Receipt parser not found, using basic parsing")
                self.parser = None
        except Exception as e:
            print(f"❌ Failed to load OCR model: {e}")
            raise
    
    def process_receipt(self, image_path: str) -> Dict:
        """
        Main function: Extract info from receipt image
        """
        try:
            # Check if file exists
            if not Path(image_path).exists():
                return {
                    'success': False,
                    'error': f'Image file not found: {image_path}'
                }
            
            # 1. Preprocess image
            processed_image = self._preprocess_image(image_path)
            
            # 2. Extract text with OCR
            print("🔍 Reading text from image...")
            results = self.reader.readtext(processed_image)
            
            if not results:
                return {
                    'success': False,
                    'error': 'No text found in image',
                    'raw_text': '',
                    'all_numbers': []
                }
            
            # 3. Parse the text
            parsed_data = self._parse_receipt_text(results)
            
            return {
                'success': True,
                'amount': parsed_data['amount'],
                'bank': parsed_data['bank'],
                'date': parsed_data['date'],
                'raw_text': parsed_data['raw_text'],
                'all_numbers': parsed_data['all_numbers'],
                'confidence': parsed_data['confidence']
            }
        except Exception as e:
            import traceback
            return {
                'success': False,
                'error': str(e),
                'traceback': traceback.format_exc()
            }
    
    def _preprocess_image(self, image_path: str) -> np.ndarray:
        """
        Improve image quality before OCR
        """
        try:
            # Read image
            img = cv2.imread(image_path)
            
            if img is None:
                raise ValueError(f"Cannot read image: {image_path}")
            
            # Convert to grayscale
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            
            # Increase contrast
            gray = cv2.convertScaleAbs(gray, alpha=1.5, beta=0)
            
            # Denoise
            denoised = cv2.fastNlMeansDenoising(gray)
            
            # Sharpen
            kernel = np.array([[-1,-1,-1],
                              [-1, 9,-1],
                              [-1,-1,-1]])
            sharpened = cv2.filter2D(denoised, -1, kernel)
            
            return sharpened
        except Exception as e:
            print(f"⚠️ Image preprocessing failed: {e}")
            # Return original image if preprocessing fails
            return cv2.imread(image_path)
    
    def _parse_receipt_text(self, ocr_results: List) -> Dict:
        """
        Extract structured data from OCR results
        """
        # Combine all text
        all_text = ' '.join([text[1] for text in ocr_results])

        # Get confidence scores
        confidences = [text[2] for text in ocr_results]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0

        # Find all numbers (for debugging & fallback)
        all_numbers = re.findall(r'\d+[,.]?\d*', all_text)

        # Extract amount
        amount = self._extract_amount(all_text)

        # Detect bank
        bank = self._detect_bank(all_text)

        # Extract date (pass all_numbers as fallback)
        date = self._extract_date(all_text, all_numbers)

        return {
            'amount': amount,
            'bank': bank,
            'date': date,
            'raw_text': all_text,
            'all_numbers': all_numbers,
            'confidence': round(avg_confidence, 2)
        }
    
    def _extract_amount(self, text: str) -> Optional[float]:
        """
        Extract monetary amount from text
        """
        # Normalize common OCR mistakes

        cleaned = (
            text.replace(',', '')
                .replace(' ', '')
                .replace('O', '0')
                .replace('o', '0')
                .replace('l', '1')
                .replace('I', '1')
                .replace('|', '1')
                .replace('฿', '')
                .replace('B', '')
        )
        
        # Patterns to detect amount (more flexible)
        patterns = [
            r'(?:จำนวน|ยอด|Amount|Total|รวม|โอน)\s*:?\s*([0-9]+\.?[0-9]{0,2})',
            r'([0-9]+\.?[0-9]{0,2})\s*(?:บาท|THB|฿)',
            r'\b([0-9]+\.[0-9]{2})\b',
            r'\b([0-9]{2,6})\b'
        ]

        for pattern in patterns:
            matches = re.findall(pattern, cleaned)
            if matches:
                for m in matches:
                    try:
                        amount = float(m)
                        # sanity check (amount between 1 and 1,000,000)
                        if 1 <= amount <= 1_000_000:
                            return amount
                    except ValueError:
                        continue
        return None
    
    def _detect_bank(self, text: str) -> str:
        """
        Detect bank from text
        """
        text_lower = text.lower()
        
        banks = {
            'kbank': ['กสิกร', 'kbank', 'kasikorn', 'k-bank', 'k bank'],
            'ktb': ['กรุงไทย', 'ktb', 'krungthai', 'krung thai'],
            'scb': ['ไทยพาณิชย์', 'scb', 'siam commercial'],
            'bbl': ['กรุงเทพ', 'bbl', 'bangkok bank'],
            'bay': ['กรุงศรี', 'bay', 'krungsri'],
            'ttb': ['ทหารไทย', 'ttb', 'tmb', 'thanachart'],
        }
        
        for bank_code, keywords in banks.items():
            for keyword in keywords:
                if keyword.lower() in text_lower:
                    return bank_code
        
        return 'unknown'
    
    def _extract_date(self, text: str, all_numbers: Optional[list] = None) -> Optional[str]:
        """
        Extract date and time from OCR text or all_numbers fallback
        """
        # แผนที่เดือนภาษาไทยเป็นตัวเลข
        thai_months = [
            'ม.ค.', 'ก.พ.', 'มี.ค.', 'เม.ย.', 'พ.ค.', 'มิ.ย.',
            'ก.ค.', 'ส.ค.', 'ก.ย.', 'ต.ค.', 'พ.ย.', 'ธ.ค.'
        ]

        # 1) ลองหาวันที่จาก text โดยตรง
        date_pattern = r'(\d{1,2})\s*(ม\.ค\.|ก\.พ\.|มี\.ค\.|เม\.ย\.|พ\.ค\.|มิ\.ย\.|ก\.ค\.|ส\.ค\.|ก\.ย\.|ต\.ค\.|พ\.ย\.|ธ\.ค\.)\s*(\d{2,4})'
        match = re.search(date_pattern, text)
        if match:
            day, month, year = match.groups()
            if len(year) == 4:
                year = year[-2:]  # เหลือแค่สองหลัก เช่น 2568 -> 68

            # ลองหาด้วยว่าในข้อความมีเวลาไหม
            time_match = re.search(r'(\d{1,2}):(\d{2})', text)
            if time_match:
                hour, minute = time_match.groups()
                return f"{int(day)} {month} {year} {hour}:{minute}"
            else:
                return f"{int(day)} {month} {year}"

        # fallback ถ้า OCR อ่านไม่ครบ ใช้ all_numbers ช่วย
        if all_numbers and len(all_numbers) >= 4:
            try:
                day = int(all_numbers[0])
                year = int(all_numbers[1]) % 100  # ตัดเหลือ 2 หลัก เช่น 68
                hour = all_numbers[2]
                minute = all_numbers[3]

                # หาเดือนจาก text
                month_match = re.search(r'(ม\.ค\.|ก\.พ\.|มี\.ค\.|เม\.ย\.|พ\.ค\.|มิ\.ย\.|ก\.ค\.|ส\.ค\.|ก\.ย\.|ต\.ค\.|พ\.ย\.|ธ\.ค\.)', text)
                month = month_match.group(1) if month_match else 'ม.ค.'

                return f"{day} {month} {year} {hour}:{minute}"
            except:
                pass

        return None


# Create singleton instance
print("📦 Initializing OCR Service...")
ocr_service = OCRService()
print("🎉 OCR Service ready!")