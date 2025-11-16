# server/app/main.py
import asyncio
import json
import logging
import os
import tempfile
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from app.asr import ASRProcessor
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ASR = ASRProcessor()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    logger.info("WebSocket client connected")
    
    try:
        while True:
            # Receive audio data from extension
            data = await websocket.receive_bytes()
            #print(data)
            
            if not data:
                continue
            
            logger.info(f"Received {len(data)} bytes")
            
            # Just accumulate, don't transcribe yet
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

@app.post("/transcribe")
async def transcribe():
    """Transcribe accumulated audio and return text"""
    logger.info("Transcribe request received")
    text = await ASR.transcribe_all()
    return {"text": text}

@app.get("/health")
async def health():
    return {"status": "ok"}
