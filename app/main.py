# backend/app/main.py
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import shutil
from pathlib import Path
import uuid
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Try to import OCR service
try:
    from app.services.ocr_service import ocr_service
    OCR_AVAILABLE = True
    print("✅ OCR Service imported successfully!")
except ImportError as e:
    print(f"⚠️ OCR Service not available: {e}")
    OCR_AVAILABLE = False
    ocr_service = None

# Create FastAPI app
app = FastAPI(
    title="Smart Expense Tracker API",
    description="OCR-powered expense tracking API",
    version="1.0.0"
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create temp directory (relative to this file)
TEMP_DIR = Path(__file__).parent.parent / "temp"
TEMP_DIR.mkdir(exist_ok=True)

@app.get("/")
async def root():
    """
    Root endpoint - Health check
    """
    return {
        "status": "running",
        "message": "🚀 Smart Expense Tracker API is running!",
        "ocr_available": OCR_AVAILABLE,
        "version": "1.0.0",
        "endpoints": {
            "docs": "/docs",
            "health": "/health",
            "scan_receipt": "/scan-receipt"
        }
    }

@app.get("/health")
async def health_check():
    """
    Health check endpoint
    """
    return {
        "status": "healthy",
        "ocr_loaded": OCR_AVAILABLE,
        "temp_dir": str(TEMP_DIR),
        "temp_dir_exists": TEMP_DIR.exists()
    }

@app.post("/scan-receipt")
async def scan_receipt(file: UploadFile = File(...)):
    """
    Upload receipt image and extract information
    
    Parameters:
    - file: Image file (JPG, PNG, etc.)
    
    Returns:
    - JSON with extracted data (amount, bank, date, etc.)
    """
    
    # Check if OCR is available
    if not OCR_AVAILABLE or ocr_service is None:
        raise HTTPException(
            status_code=503,
            detail="OCR service not available. Please check server logs."
        )
    
    # Validate file
    if not file:
        raise HTTPException(status_code=400, detail="No file provided")
    
    if not file.content_type:
        raise HTTPException(status_code=400, detail="Invalid file type")
    
    if not file.content_type.startswith('image/'):
        raise HTTPException(
            status_code=400,
            detail=f"File must be an image. Got: {file.content_type}"
        )
    
    # Generate unique filename
    file_id = str(uuid.uuid4())
    file_extension = Path(file.filename).suffix if file.filename else '.jpg'
    temp_path = TEMP_DIR / f"{file_id}{file_extension}"
    
    try:
        # Save uploaded file
        print(f"📥 Saving uploaded file to: {temp_path}")
        with temp_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        print(f"📸 Processing image: {temp_path}")
        
        # Process with OCR
        result = ocr_service.process_receipt(str(temp_path))
        
        if result.get('success'):
            print(f"✅ OCR Success - Amount: {result.get('amount')}, Bank: {result.get('bank')}")
        else:
            print(f"⚠️ OCR Warning: {result.get('error')}")
        
        return JSONResponse(content=result)
        
    except Exception as e:
        print(f"❌ Error processing receipt: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Error processing receipt: {str(e)}"
        )
    
    finally:
        # Clean up: delete temporary file
        if temp_path.exists():
            try:
                temp_path.unlink()
                print(f"🗑️ Cleaned up temp file: {temp_path}")
            except Exception as e:
                print(f"⚠️ Failed to delete temp file: {e}")

@app.post("/scan-receipt-debug")
async def scan_receipt_debug(file: UploadFile = File(...)):
    """
    Debug version: Keeps the image file for inspection
    """
    if not OCR_AVAILABLE or ocr_service is None:
        raise HTTPException(
            status_code=503,
            detail="OCR service not available"
        )
    
    file_id = str(uuid.uuid4())
    file_extension = Path(file.filename).suffix if file.filename else '.jpg'
    temp_path = TEMP_DIR / f"debug_{file_id}{file_extension}"
    
    try:
        with temp_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        result = ocr_service.process_receipt(str(temp_path))
        
        # Add file path to result for debugging
        result['saved_image'] = str(temp_path)
        result['note'] = 'Image saved for debugging. Check temp/ folder.'
        
        return JSONResponse(content=result)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/test")
async def test_endpoint():
    """
    Simple test endpoint
    """
    return {
        "message": "Test endpoint is working!",
        "status": "ok"
    }

# Startup event
@app.on_event("startup")
async def startup_event():
    print("=" * 50)
    print("🚀 Smart Expense Tracker API Starting...")
    print("=" * 50)
    print(f"OCR Available: {OCR_AVAILABLE}")
    print(f"Temp Directory: {TEMP_DIR}")
    print(f"Temp Dir Exists: {TEMP_DIR.exists()}")
    print("=" * 50)

# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    print("👋 Shutting down...")

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting server directly...")
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)