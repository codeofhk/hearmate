import logging
import os
import imageio
import numpy as np
from typing import List, Dict, Optional
from datetime import datetime
import cv2
from PIL import Image

logger = logging.getLogger(__name__)

class LetterSignGifGenerator:
    """
    Generate GIF by stitching letter sign images
    Takes text input and creates GIF from individual letter images
    """
    
    def __init__(self, letters_dir: str = "static/letter_signs"):
        logger.info("Initializing Letter Sign GIF Generator...")
        
        self.letters_dir = letters_dir
        self.output_dir = "./"
        
        # Create directory if it doesn't exist
        os.makedirs(self.letters_dir, exist_ok=True)
        
        # Load available letter images
        self.available_letters = self._scan_letter_images()
        
        logger.info(f"Letter Sign Generator initialized with {len(self.available_letters)} letters")
        logger.info(f"Available letters: {sorted(self.available_letters.keys())}")
    
    def _scan_letter_images(self) -> Dict[str, str]:
        """Scan and load all letter images from directory"""
        letters = {}
        
        if not os.path.exists(self.letters_dir):
            logger.warning(f"Letters directory not found: {self.letters_dir}")
            return letters
        
        # Supported image formats
        image_extensions = ('.png', '.jpg', '.jpeg', '.gif', '.bmp')
        
        for filename in os.listdir(self.letters_dir):
            if filename.lower().endswith(image_extensions):
                # Extract letter from filename (e.g., "A.png" -> "A")
                letter = filename.split('.')[0].upper()
                
                file_path = os.path.join(self.letters_dir, filename)
                letters[letter] = file_path
                
                logger.info(f"Loaded letter image: {letter} -> {file_path}")
        
        return letters
    
    async def text_to_gif(self, text: str, duration_per_letter: float = 0.5) -> Dict:
        """
        Convert text to animated GIF by stitching letter images
        
        Args:
            text: Text to convert (e.g., "HELLO")
            duration_per_letter: How long each letter displays (seconds)
        """
        try:
            logger.info(f"Generating GIF for text: {text}")
            
            # Convert to uppercase
            text = text.upper().strip()
            
            # Validate letters
            letters = list(text)
            missing_letters = [l for l in letters if l not in self.available_letters and l != ' ']
            
            if missing_letters:
                logger.warning(f"Missing letter images: {missing_letters}")
                return {
                    "error": f"Missing letter images: {', '.join(missing_letters)}",
                    "available": sorted(self.available_letters.keys())
                }
            
            # Create GIF
            gif_path = await self._create_letter_gif(letters, duration_per_letter)
            
            if not gif_path:
                return {"error": "Failed to create GIF"}
            
            #os.system(f"open {gif_path}")
            
            return {
                "success": True,
                "gif_path": gif_path,
                "filename": os.path.basename(gif_path),
                "text": text,
                "letters": letters,
                "duration": len([l for l in letters if l != ' ']) * duration_per_letter
            }
            
        except Exception as e:
            logger.error(f"GIF generation error: {e}", exc_info=True)
            return {"error": str(e)}
    
    async def _create_letter_gif(self, letters: List[str], duration_per_letter: float = 0.5) -> Optional[str]:
        """Create GIF from letter images"""
        try:
            filename = f"sign_{datetime.now().strftime('%Y%m%d_%H%M%S')}.gif"
            output_path = os.path.join(self.output_dir, filename)
            
            frames = []
            fps = 10  # Frames per second
            frames_per_letter = int(duration_per_letter * fps)
            
            for letter_idx, letter in enumerate(letters):
                if letter == ' ':
                    # Add blank frame for spaces
                    blank_frame = np.ones((400, 600, 3), dtype=np.uint8) * 240
                    self._add_letter_info(blank_frame, letter, letter_idx, len(letters))
                    for _ in range(frames_per_letter):
                        frames.append(blank_frame)
                    continue
                
                # Load letter image
                letter_image_path = self.available_letters.get(letter)
                
                if not letter_image_path:
                    logger.warning(f"No image for letter: {letter}")
                    continue
                
                try:
                    # Load image
                    letter_img = Image.open(letter_image_path)
                    letter_img = letter_img.convert('RGB')
                    
                    # Resize to standard size
                    letter_img = self._resize_letter_image(letter_img, target_height=300)
                    
                    # Convert to numpy array
                    letter_array = np.array(letter_img)
                    
                    # Create frame with letter
                    frame = self._create_letter_frame(letter_array, letter, letter_idx, len(letters))
                    
                    # Add frame multiple times for duration
                    for _ in range(frames_per_letter):
                        frames.append(frame.copy())
                    
                    logger.info(f"Added letter {letter} ({letter_idx + 1}/{len(letters)})")
                    
                except Exception as e:
                    logger.error(f"Error loading letter image {letter}: {e}")
                    continue
            
            # Save as GIF
            if frames:
                logger.info(f"Saving GIF with {len(frames)} frames")
                imageio.mimsave(output_path, frames, fps=fps, loop=0)
                logger.info(f"GIF created: {output_path} ({len(frames)} frames)")
                return output_path
            else:
                logger.error("No frames created")
                return None
            
        except Exception as e:
            logger.error(f"GIF creation error: {e}", exc_info=True)
            return None
    
    def _resize_letter_image(self, img: Image.Image, target_height: int = 300) -> Image.Image:
        """Resize letter image maintaining aspect ratio"""
        try:
            original_width, original_height = img.size
            
            # Calculate new width maintaining aspect ratio
            aspect_ratio = original_width / original_height
            new_width = int(target_height * aspect_ratio)
            
            # Resize
            resized = img.resize((new_width, target_height), Image.Resampling.LANCZOS)
            
            return resized
            
        except Exception as e:
            logger.error(f"Resize error: {e}")
            return img
    
    def _create_letter_frame(self, letter_img: np.ndarray, letter: str, 
                            letter_idx: int, total_letters: int) -> np.ndarray:
        """Create frame with letter image"""
        try:
            frame_height, frame_width = 400, 600
            
            # Create white background
            frame = np.ones((frame_height, frame_width, 3), dtype=np.uint8) * 240
            
            # Get letter image dimensions
            img_height, img_width = letter_img.shape[:2]
            
            # Calculate position to center letter image
            x_offset = (frame_width - img_width) // 2
            y_offset = (frame_height - img_height) // 2
            
            # Ensure offsets are non-negative
            x_offset = max(0, x_offset)
            y_offset = max(0, y_offset)
            
            # Place letter image on frame
            x_end = min(frame_width, x_offset + img_width)
            y_end = min(frame_height, y_offset + img_height)
            
            img_x_end = x_end - x_offset
            img_y_end = y_end - y_offset
            
            frame[y_offset:y_end, x_offset:x_end] = letter_img[:img_y_end, :img_x_end]
            
            # Add letter info
            self._add_letter_info(frame, letter, letter_idx, total_letters)
            
            return frame
            
        except Exception as e:
            logger.error(f"Frame creation error: {e}")
            # Return blank frame on error
            return np.ones((400, 600, 3), dtype=np.uint8) * 240
    
    def _add_letter_info(self, frame: np.ndarray, letter: str, letter_idx: int, total_letters: int):
        """Add text information to frame"""
        try:
            h, w = frame.shape[:2]
            
            # Letter label
            cv2.putText(frame, f"Letter: {letter}", (20, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)
            
            # Counter
            cv2.putText(frame, f"{letter_idx + 1}/{total_letters}", (w - 150, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (100, 100, 100), 1)
            
            # Progress bar
            progress = (letter_idx + 1) / total_letters
            bar_width = int((w - 40) * progress)
            cv2.rectangle(frame, (20, h - 30), (20 + bar_width, h - 10), (0, 200, 0), -1)
            cv2.rectangle(frame, (20, h - 30), (w - 20, h - 10), (100, 100, 100), 2)
            
        except Exception as e:
            logger.error(f"Info overlay error: {e}")
    
    def get_available_letters(self) -> Dict:
        """Get list of available letter images"""
        return {
            "available": sorted(self.available_letters.keys()),
            "count": len(self.available_letters),
            "directory": self.letters_dir
        }
    
    async def upload_letter_images(self, images_dir: str) -> Dict:
        """Copy letter images from another directory"""
        try:
            if not os.path.exists(images_dir):
                return {"error": f"Directory not found: {images_dir}"}
            
            copied = []
            for filename in os.listdir(images_dir):
                if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp')):
                    source = os.path.join(images_dir, filename)
                    dest = os.path.join(self.letters_dir, filename)
                    
                    import shutil
                    shutil.copy2(source, dest)
                    copied.append(filename)
            
            # Rescan letters
            self.available_letters = self._scan_letter_images()
            
            logger.info(f"Copied {len(copied)} letter images")
            
            return {
                "success": True,
                "copied": copied,
                "total_available": len(self.available_letters)
            }
            
        except Exception as e:
            logger.error(f"Upload error: {e}")
            return {"error": str(e)}

if __name__ == "__main__":
    # Test the LetterSignGifGenerator
    import asyncio
    
    async def test():
        generator = LetterSignGifGenerator(letters_dir="/Users/hk/hci/server/static/letter_signs")
        result = await generator.text_to_gif("hello", duration_per_letter=0.5)
        print(result)
    
    asyncio.run(test())