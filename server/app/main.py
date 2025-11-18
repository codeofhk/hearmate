# server/app/main.py
import asyncio
import json
import logging
import os
import tempfile
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, Request
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.asr import ASRProcessor
from app.letter_sign_gif_generator import LetterSignGifGenerator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Sign Language Translator", version="1.0.0")

# Create static directory
static_dir = os.path.join(os.path.dirname(__file__), "../static")
os.makedirs(static_dir, exist_ok=True)
os.makedirs(os.path.join(static_dir, "letter_signs"), exist_ok=True)

# Mount static files
app.mount("/static", StaticFiles(directory=static_dir), name="static")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ASR = ASRProcessor()
GIF_GENERATOR = LetterSignGifGenerator(letters_dir=os.path.join(static_dir, "letter_signs"))

# ==================== WebSocket ====================
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for streaming audio from browser"""
    await websocket.accept()
    logger.info("WebSocket client connected")
    
    try:
        while True:
            data = await websocket.receive_bytes()
            
            if not data:
                continue
            
            logger.info(f"Received {len(data)} bytes")
            
            # Accumulate audio chunks
            events = await ASR.push_audio_chunk_and_get_events(data)
            
            # Send back status
            for event in events:
                await websocket.send_json(event)
            
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
    except Exception as e:
        logger.exception(f"WebSocket error: {e}")
        try:
            await websocket.close(code=1011, reason=str(e))
        except:
            pass

# ==================== Audio & Transcription Endpoints ====================

@app.post("/transcribe")
async def transcribe(request: Request):
    """
    Transcribe audio from either:
    1. WebSocket accumulated buffer (ASR.audio_buffer)
    2. POST request body (blob from file upload)
    
    Returns: {"text": "...", "gif": {...}}
    """
    logger.info("Transcribe request received")
    
    try:
        text = None
        # Check if body contains audio data
        body = await request.body()
        #print(f"Body type: {type(body)}, length: {len(body)}")
        
        if body and len(body) > 0:
            logger.info(f"Received audio blob: {len(body)} bytes")
            
            # Get content type from headers
            content_type = request.headers.get("content-type", "audio/webm")
            logger.info(f"Content-Type: {content_type}")
            
            # Decode the audio blob
            audio_float32 = await ASR._decode_audio(body)
            
            # if audio_float32 is None or len(audio_float32) == 0:
            #     logger.warning("Failed to decode audio blob")
            #     return {"text": "Failed to decode audio", "gif": None}
            
            # Set the audio buffer
            # ASR.audio_buffer = audio_float32
            # logger.info(f"Audio buffer set: {len(audio_float32)} samples")
        
        
        # Transcribe the accumulated audio
        text = await ASR.push_audio_chunk_and_get_events(body)
        #print(text)
        logger.info(f"Transcribed: {text}")
        
        # Generate GIF if text is valid
        gif_result = None
            
        
        return {
            "text": text,
        }
        
    except Exception as e:
        logger.error(f"Transcribe error: {e}", exc_info=True)
        return {
            "error": str(e),
            "text": None,
            "gif": None
        }, 400

@app.post("/upload-audio")
async def upload_audio(file: UploadFile = File(...)):
    """
    Upload and transcribe audio file
    Accepts: MP3, WAV, WebM, OGG, FLAC, etc.
    Returns: {"text": "...", "gif": {...}}
    """
    try:
        logger.info(f"Uploading audio file: {file.filename}")
        
        # Read file
        content = await file.read()
        
        if not content:
            return {"error": "File is empty"}, 400
        
        logger.info(f"File size: {len(content)} bytes")
        
        # Decode audio
        audio_float32 = await ASR._decode_audio_chunk(content)
        
        if audio_float32 is None or len(audio_float32) == 0:
            return {"error": "Failed to decode audio file"}, 400
        
        # Set buffer and transcribe
        ASR.audio_buffer = audio_float32
        text = await ASR.transcribe_all()
        
        # Generate GIF
        gif_result = None
        if text and text != "No audio recorded" and not text.startswith("Error"):
            try:
                gif_result = await GIF_GENERATOR.text_to_gif(text)
            except Exception as e:
                logger.error(f"GIF generation error: {e}")
                gif_result = {"error": str(e)}
        
        return {
            "filename": file.filename,
            "text": text,
            "gif": gif_result
        }
        
    except Exception as e:
        logger.error(f"Upload error: {e}", exc_info=True)
        return {"error": str(e)}, 400

# ==================== Text to GIF Endpoints ====================

@app.post("/text-to-gif")
async def text_to_gif(text: str, duration: float = 0.5):
    """
    Convert text to sign language GIF
    Only uses available letter images, skips missing ones
    
    Query Parameters:
        text (str): Text to convert
        duration (float): Duration per letter in seconds (default: 0.5)
    
    Returns: GIF file directly (image/gif) or error JSON
    """
    logger.info(f"GIF generation request: {text}")
    
    if not text or text.strip() == "":
        return {"success": False, "error": "Text is required"}, 400
    
    try:
        # Filter text to only include available letters
        available_letters = GIF_GENERATOR.available_letters
        
        if not available_letters:
            return {"success": False, "error": "No letter images available"}, 400
        
        # Convert text to uppercase and filter
        text_upper = text.upper()
        filtered_text = "".join([char for char in text_upper if char in available_letters or char == " "])
        
        if not filtered_text or filtered_text.strip() == "":
            missing_letters = set(text_upper) - set(available_letters) - {" "}
            return {
                "success": False, 
                "error": f"No matching letters found. Missing: {', '.join(sorted(missing_letters))}. Available: {', '.join(sorted(available_letters.keys()))}"
            }, 400
        
        logger.info(f"Filtered text: '{filtered_text}' (original: '{text}')")
        
        # Generate GIF with filtered text
        result = await GIF_GENERATOR.text_to_gif(filtered_text, duration_per_letter=duration)
        
        if "error" in result:
            return {"success": False, "error": result.get("error")}, 400
        
        # Get the GIF file path
        gif_path = result.get("gif_path")
        
        if not gif_path or not os.path.exists(gif_path):
            return {"success": False, "error": "GIF file not generated"}, 400
        
        logger.info(f"Serving GIF directly: {gif_path}")
        
        # Return the GIF file directly
        return FileResponse(
            gif_path,
            media_type="image/gif",
            filename=result.get("filename", "sign_language.gif")
        )
        
    except Exception as e:
        logger.error(f"GIF generation error: {e}", exc_info=True)
        return {"success": False, "error": str(e)}, 400

@app.get("/gif/{filename}")
async def get_gif(filename: str):
    """
    Serve generated GIF file
    
    Path Parameters:
        filename (str): Name of the GIF file
    
    Returns: GIF file with media type image/gif
    """
    file_path = os.path.join("/tmp", filename)
    
    if not os.path.exists(file_path):
        logger.warning(f"GIF not found: {file_path}")
        return {"error": "GIF not found"}, 404
    
    logger.info(f"Serving GIF: {file_path}")
    return FileResponse(file_path, media_type="image/gif", filename=filename)

# ==================== Letter Images Endpoints ====================

@app.get("/available-letters")
async def get_available_letters():
    """
    Get list of available letter images
    
    Returns:
        {
            "available": ["A", "B", "C", ...],
            "count": 26,
            "directory": "..."
        }
    """
    try:
        return GIF_GENERATOR.get_available_letters()
    except Exception as e:
        logger.error(f"Error getting available letters: {e}")
        return {"error": str(e)}, 400

@app.post("/upload-letters")
async def upload_letters(files: list[UploadFile] = File(...)):
    """
    Upload letter sign images
    
    File naming convention: A.png, B.png, C.png, etc.
    Supported formats: PNG, JPG, JPEG, GIF, BMP
    
    Returns:
        {
            "success": true,
            "uploaded": ["A.png", "B.png, ...],
            "total_available": 26
        }
    """
    try:
        letters_dir = os.path.join(static_dir, "letter_signs")
        os.makedirs(letters_dir, exist_ok=True)
        
        uploaded = []
        for file in files:
            if file.filename:
                file_path = os.path.join(letters_dir, file.filename)
                content = await file.read()
                
                with open(file_path, "wb") as f:
                    f.write(content)
                
                uploaded.append(file.filename)
                logger.info(f"Uploaded: {file.filename}")
        
        # Rescan letters
        GIF_GENERATOR.available_letters = GIF_GENERATOR._scan_letter_images()
        
        return {
            "success": True,
            "uploaded": uploaded,
            "total_available": len(GIF_GENERATOR.available_letters),
            "available": sorted(GIF_GENERATOR.available_letters.keys())
        }
        
    except Exception as e:
        logger.error(f"Upload error: {e}", exc_info=True)
        return {"error": str(e)}, 400

@app.delete("/delete-letter/{letter}")
async def delete_letter(letter: str):
    """
    Delete a letter image
    
    Path Parameters:
        letter (str): Letter to delete (e.g., "A")
    
    Returns: {"success": true, "deleted": "A", "remaining": 25}
    """
    try:
        letter = letter.upper()
        
        if letter not in GIF_GENERATOR.available_letters:
            return {"error": f"Letter {letter} not found"}, 404
        
        file_path = GIF_GENERATOR.available_letters[letter]
        os.remove(file_path)
        
        # Rescan
        GIF_GENERATOR.available_letters = GIF_GENERATOR._scan_letter_images()
        
        logger.info(f"Deleted letter: {letter}")
        
        return {
            "success": True,
            "deleted": letter,
            "remaining": len(GIF_GENERATOR.available_letters),
            "available": sorted(GIF_GENERATOR.available_letters.keys())
        }
        
    except Exception as e:
        logger.error(f"Delete error: {e}")
        return {"error": str(e)}, 400

# ==================== Batch Operations ====================

@app.post("/batch-text-to-gif")
async def batch_text_to_gif(request_body: dict):
    """
    Convert multiple texts to GIFs
    
    Body:
        {
            "texts": ["hello", "goodbye", "thank you"],
            "duration": 0.5
        }
    
    Returns:
        {
            "success": true,
            "results": [
                {"text": "hello", "gif_path": "...", "filename": "..."},
                ...
            ]
        }
    """
    try:
        texts = request_body.get("texts", [])
        duration = request_body.get("duration", 0.5)
        
        logger.info(f"Batch GIF generation: {len(texts)} texts")
        
        if not texts or len(texts) == 0:
            return {"error": "No texts provided"}, 400
        
        results = []
        
        for text in texts:
            result = await GIF_GENERATOR.text_to_gif(text, duration_per_letter=duration)
            results.append({
                "text": text,
                **result
            })
        
        return {
            "success": True,
            "count": len(results),
            "results": results
        }
        
    except Exception as e:
        logger.error(f"Batch error: {e}", exc_info=True)
        return {"error": str(e)}, 400

# ==================== Statistics ====================

@app.get("/stats")
async def get_stats():
    """
    Get system statistics
    
    Returns:
        {
            "available_letters": 26,
            "total_gifs_generated": 42,
            "server_version": "1.0"
        }
    """
    try:
        letters_count = len(GIF_GENERATOR.available_letters)
        
        # Count GIFs in temp directory
        gifs_count = 0
        if os.path.exists("/tmp"):
            gifs_count = len([f for f in os.listdir("/tmp") if f.startswith("sign_") and f.endswith(".gif")])
        
        return {
            "available_letters": letters_count,
            "available_letters_list": sorted(GIF_GENERATOR.available_letters.keys()),
            "total_gifs_generated": gifs_count,
            "server_status": "running",
            "storage_dir": "/tmp",
            "letters_dir": os.path.join(static_dir, "letter_signs"),
            "version": "1.0.0"
        }
        
    except Exception as e:
        logger.error(f"Stats error: {e}")
        return {"error": str(e)}, 400

@app.get("/list-gifs")
async def list_gifs(limit: int = 10):
    """
    List recently generated GIFs
    
    Query Parameters:
        limit (int): Maximum number of GIFs to return (default: 10)
    
    Returns:
        {
            "gifs": [
                {"filename": "...", "size": 12345, "created": "2024-01-15T10:30:00"},
                ...
            ]
        }
    """
    try:
        gifs = []
        
        if os.path.exists("/tmp"):
            files = [
                f for f in os.listdir("/tmp") 
                if f.startswith("sign_") and f.endswith(".gif")
            ]
            
            # Sort by modification time (newest first)
            files.sort(
                key=lambda f: os.path.getmtime(os.path.join("/tmp", f)),
                reverse=True
            )
            
            for filename in files[:limit]:
                file_path = os.path.join("/tmp", filename)
                stat = os.stat(file_path)
                
                gifs.append({
                    "filename": filename,
                    "size": stat.st_size,
                    "created": stat.st_mtime,
                    "url": f"/gif/{filename}"
                })
        
        return {
            "count": len(gifs),
            "gifs": gifs
        }
        
    except Exception as e:
        logger.error(f"List error: {e}")
        return {"error": str(e)}, 400

# ==================== Utility Endpoints ====================

@app.get("/health")
async def health():
    """
    Health check endpoint
    
    Returns: {"status": "ok", "service": "Sign Language Translator"}
    """
    try:
        letters = len(GIF_GENERATOR.available_letters)
        return {
            "status": "ok",
            "service": "Sign Language Translator",
            "asr": "ready",
            "gif_generator": "ready",
            "available_letters": letters,
            "version": "1.0.0"
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }, 500

@app.get("/test")
async def test_page():
    """Serve interactive test page"""
    try:
        with open("test_audio.html", "r") as f:
            return HTMLResponse(f.read())
    except FileNotFoundError:
        logger.error("test_audio.html not found")
        return HTMLResponse("""
        <html>
        <body style="font-family: sans-serif; max-width: 800px; margin: 50px auto;">
            <h1>❌ Test Page Not Found</h1>
            <p>Place <code>test_audio.html</code> in the server root directory:</p>
            <code>/Users/hk/hci/server/test_audio.html</code>
            <hr>
            <h2>Available Endpoints:</h2>
            <ul>
                <li><a href="/docs">📚 Swagger API Docs</a></li>
                <li><a href="/redoc">📖 ReDoc Docs</a></li>
                <li><a href="/health">💚 Health Check</a></li>
                <li><a href="/stats">📊 Statistics</a></li>
            </ul>
        </body>
        </html>
        """, status_code=404)

@app.get("/")
async def root():
    """Root endpoint with API documentation"""
    docs = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Sign Language Translator API</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body { 
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; 
                max-width: 1200px; 
                margin: 0 auto; 
                padding: 40px 20px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
            }
            .container {
                background: white;
                border-radius: 12px;
                padding: 40px;
                box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            }
            h1 { color: #667eea; margin-bottom: 10px; font-size: 2.5em; }
            .subtitle { color: #999; margin-bottom: 30px; }
            h2 { color: #764ba2; margin-top: 40px; margin-bottom: 20px; border-bottom: 2px solid #667eea; padding-bottom: 10px; }
            .quick-links { display: flex; gap: 10px; margin-bottom: 40px; flex-wrap: wrap; }
            .quick-links a { 
                padding: 12px 24px; 
                background: #667eea; 
                color: white; 
                text-decoration: none; 
                border-radius: 6px;
                transition: all 0.3s;
            }
            .quick-links a:hover { background: #764ba2; transform: translateY(-2px); }
            .endpoint { 
                background: #f9f9f9; 
                padding: 15px; 
                margin: 10px 0; 
                border-left: 4px solid #667eea;
                border-radius: 4px;
            }
            .method { 
                color: #667eea; 
                font-weight: bold; 
                display: inline-block;
                min-width: 60px;
            }
            code { 
                background: #e8eef7; 
                padding: 4px 8px; 
                border-radius: 3px;
                font-family: 'Courier New', monospace;
            }
            .endpoint p { color: #666; margin-top: 8px; font-size: 14px; }
            .category { margin-top: 30px; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🤟 Sign Language Translator API</h1>
            <p class="subtitle">Convert speech and text to sign language GIFs</p>
            
            <div class="quick-links">
                <a href="/docs">📚 Swagger Docs</a>
                <a href="/redoc">📖 ReDoc</a>
                <a href="/test">🧪 Test Page</a>
                <a href="/health">💚 Health</a>
                <a href="/stats">📊 Stats</a>
            </div>
            
            <h2>🎯 Core Endpoints</h2>
            
            <div class="endpoint">
                <span class="method">POST</span> <code>/transcribe</code>
                <p>Transcribe audio from WebSocket buffer and generate GIF</p>
            </div>
            
            <div class="endpoint">
                <span class="method">POST</span> <code>/text-to-gif?text=hello&duration=0.5</code>
                <p>Convert text to sign language GIF</p>
            </div>
            
            <div class="endpoint">
                <span class="method">POST</span> <code>/upload-audio</code>
                <p>Upload and transcribe audio file (MP3, WAV, WebM, OGG, FLAC)</p>
            </div>
            
            <div class="endpoint">
                <span class="method">GET</span> <code>/gif/{filename}</code>
                <p>Serve generated GIF file</p>
            </div>
            
            <h2>📁 Letter Management</h2>
            
            <div class="endpoint">
                <span class="method">GET</span> <code>/available-letters</code>
                <p>List all available letter images</p>
            </div>
            
            <div class="endpoint">
                <span class="method">POST</span> <code>/upload-letters</code>
                <p>Upload letter sign images (A.png, B.png, etc.)</p>
            </div>
            
            <div class="endpoint">
                <span class="method">DELETE</span> <code>/delete-letter/{letter}</code>
                <p>Delete a letter image</p>
            </div>
            
            <h2>⚙️ Batch Operations</h2>
            
            <div class="endpoint">
                <span class="method">POST</span> <code>/batch-text-to-gif</code>
                <p>Convert multiple texts to GIFs</p>
            </div>
            
            <h2>📊 Information</h2>
            
            <div class="endpoint">
                <span class="method">GET</span> <code>/stats</code>
                <p>Get system statistics</p>
            </div>
            
            <div class="endpoint">
                <span class="method">GET</span> <code>/list-gifs</code>
                <p>List recently generated GIFs</p>
            </div>
            
            <div class="endpoint">
                <span class="method">GET</span> <code>/health</code>
                <p>Health check</p>
            </div>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(docs)

# ==================== 404 Handler ====================
@app.get("/.well-known/appspecific/com.chrome.devtools.json")
async def chrome_devtools():
    """Chrome DevTools discovery endpoint"""
    return {"status": "ok"}