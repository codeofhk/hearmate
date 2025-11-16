# server/app/asr.py
import os
import tempfile
import asyncio
from typing import List, Dict
from pydub import AudioSegment
from io import BytesIO
import logging
import numpy as np
import whisper
import wave
from io import BytesIO
import ssl

# Disable SSL verification for model download
ssl._create_default_https_context = ssl._create_unverified_context

logger = logging.getLogger(__name__)

class ASRProcessor:
    def __init__(self):
        logger.info("Loading Whisper model...")
        self.model = whisper.load_model("base")
        self.audio_buffer = np.array([], dtype=np.float32)
        self.chunk_count = 0
        self.sample_rate = 16000
        logger.info("Whisper model loaded")
    
    async def push_audio_chunk_and_get_events(self, audio_bytes):
        """
        Process audio chunks and return ASR events
        Expects raw audio or WebM, converts to proper format for Whisper
        """
        try:
            if not audio_bytes or len(audio_bytes) == 0:
                logger.warning("Empty audio chunk")
                return []
            
            self.chunk_count += 1
            logger.info(f"Chunk #{self.chunk_count}: {len(audio_bytes)} bytes")
            
            # Try to decode as WebM first
            audio_array = await self._decode_audio(audio_bytes)
            
            if audio_array is not None:
                # Append to buffer
                self.audio_buffer = np.concatenate([self.audio_buffer, audio_array])
                
                logger.info(f"Audio buffer: {len(self.audio_buffer)} samples (~{len(self.audio_buffer)/self.sample_rate:.1f}s)")
                
                # Process every 5 sec.onds of audio
                if len(self.audio_buffer) >= self.sample_rate * 5:
                    return await self._transcribe_buffer()
                else:
                    return [{"type": "interim", "text": f"Listening... ({self.chunk_count} chunks)"}]
            else:
                return [{"type": "interim", "text": "Processing audio..."}]
            
        except Exception as e:
            logger.error(f"ASR error: {e}", exc_info=True)
            return [{"type": "interim", "text": f"Error: {str(e)[:100]}"}]
    
    async def _decode_audio(self, audio_bytes):
        """Decode audio from WebM or raw bytes"""
        try:
            # Save to temp file
            temp_path = "/tmp/audio_chunk.webm"
            with open(temp_path, 'wb') as f:
                f.write(audio_bytes)
            
            # Use ffmpeg to convert WebM to WAV
            import subprocess
            wav_path = "/tmp/audio_chunk.wav"
            
            result = subprocess.run([
                'ffmpeg',
                '-i', temp_path,
                '-acodec', 'pcm_s16le',
                '-ar', '16000',
                '-ac', '1',
                '-y',
                wav_path
            ], capture_output=True, timeout=10)
            
            if result.returncode != 0:
                logger.warning(f"FFmpeg error: {result.stderr.decode()}")
                return None
            
            # Read WAV file
            with open(wav_path, 'rb') as f:
                wav_data = f.read()
            
            # Parse WAV header and extract audio
            audio_array = self._parse_wav(wav_data)
            return audio_array
            
        except Exception as e:
            logger.warning(f"Failed to decode audio: {e}")
            return None
    
    def _parse_wav(self, wav_data):
        """Parse WAV file and return audio array"""
        try:
            wav_file = BytesIO(wav_data)
            with wave.open(wav_file, 'rb') as wav:
                n_channels = wav.getnchannels()
                sample_width = wav.getsampwidth()
                frame_rate = wav.getframerate()
                n_frames = wav.getnframes()
                
                logger.info(f"WAV: {n_channels}ch, {sample_width}B, {frame_rate}Hz, {n_frames} frames")
                
                # Read audio data
                audio_data = wav.readframes(n_frames)
                audio_array = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32768.0
                
                # Resample if necessary
                if frame_rate != self.sample_rate:
                    logger.info(f"Resampling from {frame_rate}Hz to {self.sample_rate}Hz")
                    import librosa
                    audio_array = librosa.resample(audio_array, orig_sr=frame_rate, target_sr=self.sample_rate)
                
                return audio_array
        except Exception as e:
            logger.error(f"WAV parsing error: {e}")
            return None
    
    async def _transcribe_buffer(self):
        """Transcribe accumulated audio buffer"""
        try:
            if len(self.audio_buffer) == 0:
                return []
            
            logger.info(f"Transcribing {len(self.audio_buffer)} samples...")
            
            # Transcribe
            result = self.model.transcribe(
                self.audio_buffer,
                language="en",
                fp16=False,
                task="transcribe"
            )
            
            text = result.get("text", "").strip()
            
            if text:
                logger.info(f"✅ Transcribed: {text}")
                self.audio_buffer = np.array([], dtype=np.float32)
                return [{"type": "final", "text": text}]
            else:
                logger.info("No speech detected")
                self.audio_buffer = np.array([], dtype=np.float32)
                return [{"type": "interim", "text": "No speech detected"}]
                
        except Exception as e:
            logger.error(f"Transcription error: {e}", exc_info=True)
            return [{"type": "interim", "text": f"Transcription error: {str(e)[:50]}"}]
