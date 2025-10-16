# backend/test/test_parser.py

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.services.enhanced_parser import receipt_parser

# Test data (your actual OCR result)
test_text = """โอนเงินสำเร็จ 1d ส.ค. 68 15:33 น. i+ ด.ช. ฺพงศพัศฺต ธ.กสิกรไทย xxx-x-x9745-x จรรยา เมาประชา ธ.กรุงไทย xxx-x-x6008-x เลขที่ รายการ: 01522215334830r00498 จำนวน: loo.0o บาท ค่าธรรมเนียม: o.0d บาท สแกนตรวจสอบสลิป"""

def test_transaction_type():
    """Test transaction type detection"""
    print("=" * 50)
    print("Test 1: Transaction Type Detection")
    print("=" * 50)
    
    test_cases = [
        ("โอนเงินสำเร็จ", "transfer"),
        ("เติมเงิน", "topup"),
        ("ชำระเงิน", "payment"),
        ("จ่ายบิล", "bill_payment"),
    ]
    
    for text, expected in test_cases:
        result = receipt_parser._detect_transaction_type(text)
        status = "✅" if result['code'] == expected else "❌"
        print(f"{status} '{text}' → {result['category']} ({result['code']})")

def test_amount_extraction():
    """Test amount extraction"""
    print("\n" + "=" * 50)
    print("Test 2: Amount Extraction")
    print("=" * 50)
    
    test_cases = [
        ("จำนวน: 100.00 บาท", 100.00),
        ("จำนวน: loo.0o บาท", 100.00),  # OCR error
        ("จำนวน 5000 บาท", 5000.00),
        ("1,234.56 บาท", 1234.56),
    ]
    
    for text, expected in test_cases:
        result = receipt_parser._extract_amount(text)
        status = "✅" if result == expected else "⚠️"
        print(f"{status} '{text}' → {result} (expected: {expected})")

def test_date_extraction():
    """Test date extraction"""
    print("\n" + "=" * 50)
    print("Test 3: Date Extraction")
    print("=" * 50)
    
    test_cases = [
        ("1d ส.ค. 68", "2025-08-01"),
        ("15 ก.ย. 67", "2024-09-15"),
        ("01/08/2568", "2025-08-01"),
    ]
    
    for text, expected in test_cases:
        result = receipt_parser._extract_date(text)
        status = "✅" if result == expected else "⚠️"
        print(f"{status} '{text}' → {result} (expected: {expected})")

def test_full_parsing():
    """Test full receipt parsing"""
    print("\n" + "=" * 50)
    print("Test 4: Full Receipt Parsing")
    print("=" * 50)
    print(f"Input text:\n{test_text}\n")
    
    result = receipt_parser.parse_receipt(test_text)
    
    print("Results:")
    print("-" * 50)
    print(f"Transaction Type: {result['transaction_type']['category']}")
    print(f"Amount: ฿{result['amount']}")
    print(f"Fee: ฿{result['fee']}")
    print(f"Total: ฿{result['total_amount']}")
    print(f"Reference: {result['reference_number']}")
    print(f"From: {result['from_account']}")
    print(f"To: {result['to_account']}")
    print(f"Date: {result['date']}")
    print(f"Time: {result['time']}")
    print(f"Bank: {result['bank']}")

def main():
    print("\n🧪 Receipt Parser Test Suite")
    print("=" * 50)
    
    test_transaction_type()
    test_amount_extraction()
    test_date_extraction()
    test_full_parsing()
    
    print("\n" + "=" * 50)
    print("✅ All tests completed!")
    print("=" * 50)

if __name__ == "__main__":
    main()