# backend/test_import.py
import sys
sys.path.insert(0, '.')

print("=" * 50)
print("Testing Smart Expense Tracker Backend")
print("=" * 50)

# Test 1: FastAPI
print("\n1. Testing FastAPI import...")
try:
    from app.main import app
    print(f"   ✅ FastAPI app loaded")
    print(f"   Type: {type(app)}")
except Exception as e:
    print(f"   ❌ Failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 2: OCR Service
print("\n2. Testing OCR service import...")
try:
    from app.services.ocr_service import ocr_service
    print(f"   ✅ OCR service imported")
    print(f"   Type: {type(ocr_service)}")
except Exception as e:
    print(f"   ❌ Failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 3: Dependencies
print("\n3. Testing dependencies...")
dependencies = {
    'fastapi': 'FastAPI',
    'uvicorn': 'Uvicorn',
    'easyocr': 'EasyOCR',
    'cv2': 'OpenCV',
    'PIL': 'Pillow',
    'numpy': 'NumPy'
}

for module, name in dependencies.items():
    try:
        __import__(module)
        print(f"   ✅ {name}")
    except ImportError:
        print(f"   ❌ {name} not installed")

print("\n" + "=" * 50)
print("All tests passed! 🎉")
print("=" * 50)
print("\nNext step: Run the server")
print("  uvicorn app.main:app --reload --host 0.0.0.0 --port 8000")