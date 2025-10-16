# backend/app/services/enhanced_parser.py
import re
from typing import Dict, Optional, List

class ReceiptParser:
    """
    Parse Thai bank receipt text and extract structured information
    """
    
    # Transaction type patterns
    TRANSACTION_TYPES = { # Topic E-Slip
        'topup': {
            'keywords': ['เติมเงิน', 'เติม เงิน', 'top up', 'topup'],
            'category': 'เติมเงิน',
            'description': 'โอนเงินเข้าบัญชีอื่น'
        },
        'payment': {
            'keywords': ['ชำระเงิน', 'ชำระ เงิน', 'payment', 'จ่ายเงิน'],
            'category': 'ชำระเงิน',
            'description': 'โอนเงินหรือจ่ายเงินค่าสินค้าและบริการ'
        },
        'bill_payment': {
            'keywords': ['จ่ายบิล', 'จ่าย บิล', 'pay bill', 'bill payment', 'ชำระค่า'],
            'category': 'จ่ายบิล',
            'description': 'ชำระค่าสินค้าและบริการ เช่น ค่าไฟฟ้า น้ำ โทรศัพท์'
        },
        'transfer': {
            'keywords': ['โอนเงิน', 'โอน เงิน', 'transfer', 'โอนเงินสำเร็จ'],
            'category': 'โอนเงิน',
            'description': 'โอนเงินจากบัญชีของคุณไปยังบัญชีอื่น'
        }
    }
    
    def parse_receipt(self, raw_text: str, ocr_results: List = None) -> Dict:
        """
        Main parsing function
        """
        result = {
            'transaction_type': self._detect_transaction_type(raw_text),
            'amount': self._extract_amount(raw_text),
            'fee': self._extract_fee(raw_text),
            'total_amount': None,  # amount + fee
            'reference_number': self._extract_reference(raw_text),
            'from_account': self._extract_sender(raw_text),
            'to_account': self._extract_recipient(raw_text),
            'date': self._extract_date(raw_text),
            'time': self._extract_time(raw_text),
            'bank': self._detect_bank(raw_text),
            'raw_text': raw_text
        }
        
        # Calculate total
        if result['amount'] and result['fee']:
            result['total_amount'] = result['amount'] + result['fee']
        
        return result
    
    def _detect_transaction_type(self, text: str) -> Dict:
        """
        Detect transaction type from text
        Returns: {type_code, category, description}
        """
        text_lower = text.lower()
        
        # Check each type (order matters - most specific first)
        for type_code, config in self.TRANSACTION_TYPES.items():
            for keyword in config['keywords']:
                if keyword.lower() in text_lower:
                    return {
                        'code': type_code,
                        'category': config['category'],
                        'description': config['description']
                    }
        
        # Default
        return {
            'code': 'unknown',
            'category': 'ไม่ระบุ',
            'description': 'ไม่สามารถระบุประเภทธุรกรรมได้'
        }
    
    def _extract_amount(self, text: str) -> Optional[float]:
        """
        Extract transaction amount
        """
        # Pattern 1: "จำนวน: XXX.XX บาท"
        pattern1 = r'จำนวน\s*:?\s*([0-9,]+\.?[0-9]*)\s*บาท'
        match = re.search(pattern1, text, re.IGNORECASE)
        if match:
            amount_str = match.group(1).replace(',', '')
            try:
                return float(amount_str)
            except:
                pass
        
        # Pattern 2: "XXX.XX บาท" (large number)
        pattern2 = r'\b([1-9][0-9]{1,}\.?[0-9]{0,2})\s*บาท'
        matches = re.findall(pattern2, text)
        if matches:
            # Return largest number (likely the amount)
            amounts = [float(m.replace(',', '')) for m in matches]
            return max(amounts)
        
        # Pattern 3: "จำนวน XXX" without บาท
        pattern3 = r'จำนวน\s*:?\s*([0-9,]+\.?[0-9]*)'
        match = re.search(pattern3, text, re.IGNORECASE)
        if match:
            amount_str = match.group(1).replace(',', '')
            try:
                amount = float(amount_str)
                if 1 <= amount <= 1000000:
                    return amount
            except:
                pass
        
        return None
    
    def _extract_fee(self, text: str) -> Optional[float]:
        """
        Extract transaction fee
        """
        patterns = [
            r'ค่าธรรมเนียม\s*:?\s*([0-9,]+\.?[0-9]*)',
            r'fee\s*:?\s*([0-9,]+\.?[0-9]*)',
            r'ธรรมเนียม\s*:?\s*([0-9,]+\.?[0-9]*)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    fee = float(match.group(1).replace(',', ''))
                    return fee
                except:
                    pass
        
        return 0.0
    
    def _extract_reference(self, text: str) -> Optional[str]:
        """
        Extract reference/transaction number
        """
        patterns = [
            r'เลขที่\s*รายการ\s*:?\s*([0-9]+)',
            r'รายการ\s*:?\s*([0-9]+)',
            r'reference\s*:?\s*([0-9]+)',
            r'ref\s*:?\s*([0-9]+)',
            r'\b([0-9]{10,})\b'  # Long number sequence
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return None
    
    def _extract_sender(self, text: str) -> Optional[Dict]:
        """
        Extract sender information (ผู้โอน)
        """
        # Pattern: "ชื่อ [bank] xxx-x-xXXXX-x"
        # Example: "ด.ช. พงศพัศ ธ.กสิกรไทย xxx-x-x9745-x"
        
        patterns = [
            r'((?:นาย|นาง|น\.ส\.|ด\.ช\.|ด\.ญ\.)[^\n]+?)(?:ธ\.[^\n]+?)?(xxx-x-x[0-9]+)',
            r'จาก\s*[:：]?\s*([^\n]+)',
            r'from\s*[:：]?\s*([^\n]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                name = match.group(1).strip()
                account = match.group(2) if len(match.groups()) > 1 else None
                
                return {
                    'name': name,
                    'account': account
                }
        
        return None
    
    def _extract_recipient(self, text: str) -> Optional[Dict]:
        """
        Extract recipient information (ผู้รับ)
        """
        # Look for name after sender or before "ธ.กรุงไทย" etc.
        patterns = [
            r'(?:ธ\.กสิกรไทย[^\n]+?\n)([^\n]+?)(?:ธ\.[^\n]+)?(xxx-x-x[0-9]+)',
            r'ถึง\s*[:：]?\s*([^\n]+)',
            r'to\s*[:：]?\s*([^\n]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                name = match.group(1).strip()
                account = match.group(2) if len(match.groups()) > 1 else None
                
                return {
                    'name': name,
                    'account': account
                }
        
        return None
    
    def _extract_date(self, text: str) -> Optional[str]:
        """
        Extract date from text
        """
        # Thai month abbreviations
        thai_months = {
            'ม.ค.': '01', 'ก.พ.': '02', 'มี.ค.': '03', 'เม.ย.': '04',
            'พ.ค.': '05', 'มิ.ย.': '06', 'ก.ค.': '07', 'ส.ค.': '08',
            'ก.ย.': '09', 'ต.ค.': '10', 'พ.ย.': '11', 'ธ.ค.': '12'
        }
        
        # Pattern: "1 ส.ค. 68" or "1d ส.ค. 68"
        for month_thai, month_num in thai_months.items():
            pattern = rf'(\d{{1,2}})[^\d]*{re.escape(month_thai)}\s*(\d{{2,4}})'
            match = re.search(pattern, text)
            if match:
                day = match.group(1).replace('d', '')
                year = match.group(2)
                
                # Convert Buddhist year to Christian year
                if len(year) == 2:
                    year_int = int(year)
                    # If year is 00-99, assume it's 25xx BE (Buddhist Era)
                    year = str(2500 + year_int - 543)
                elif len(year) == 4 and int(year) > 2500:
                    year = str(int(year) - 543)
                
                return f"{year}-{month_num}-{day.zfill(2)}"
        
        # Standard date patterns
        date_patterns = [
            r'(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})',
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, text)
            if match:
                day, month, year = match.groups()
                if len(year) == 2:
                    year = '20' + year
                return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
        
        return None
    
    def _extract_time(self, text: str) -> Optional[str]:
        """
        Extract time from text
        """
        # Pattern: "15:33" or "15:33 น."
        pattern = r'(\d{1,2}):(\d{2})'
        match = re.search(pattern, text)
        if match:
            hour = match.group(1).zfill(2)
            minute = match.group(2)
            return f"{hour}:{minute}"
        
        return None
    
    def _detect_bank(self, text: str) -> str:
        """
        Detect bank from text
        """
        text_lower = text.lower()
        
        banks = {
            'kbank': ['กสิกร', 'kbank', 'kasikorn'],
            'ktb': ['กรุงไทย', 'ktb', 'krungthai'],
            'scb': ['ไทยพาณิชย์', 'scb'],
            'bbl': ['กรุงเทพ', 'bbl'],
            'bay': ['กรุงศรี', 'bay'],
            'ttb': ['ทหารไทย', 'ttb'],
        }
        
        for bank_code, keywords in banks.items():
            for keyword in keywords:
                if keyword.lower() in text_lower:
                    return bank_code
        
        return 'unknown'

# Create singleton
receipt_parser = ReceiptParser()
