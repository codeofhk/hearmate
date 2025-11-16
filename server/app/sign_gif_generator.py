import logging
import os
import imageio
import numpy as np
from typing import List, Dict, Optional
from datetime import datetime
import cv2

logger = logging.getLogger(__name__)

class SignLanguageGifGenerator:
    """
    Generate animated GIF of sign language from text
    Creates hand sign animations and saves as GIF
    """
    
    def __init__(self):
        logger.info("Initializing Sign Language GIF Generator...")
        
        # Sign database with keyframe positions
        self.sign_database = self._load_sign_poses()
        self.output_dir = "/tmp"
        
        logger.info("Sign Language GIF Generator initialized")
    
    def _load_sign_poses(self) -> Dict[str, Dict]:
        """Load sign-to-hand-pose mappings"""
        return {
            "hello": {
                "frames": 15,
                "hand_positions": self._generate_wave_positions(),
                "description": "Wave hand"
            },
            "hi": {
                "frames": 12,
                "hand_positions": self._generate_wave_positions(),
                "description": "Quick wave"
            },
            "how": {
                "frames": 15,
                "hand_positions": self._generate_circle_positions(),
                "description": "Circular motion"
            },
            "are": {
                "frames": 10,
                "hand_positions": self._generate_point_positions(),
                "description": "Point outward"
            },
            "you": {
                "frames": 10,
                "hand_positions": self._generate_point_positions(),
                "description": "Point to you"
            },
            "thank": {
                "frames": 12,
                "hand_positions": self._generate_thank_positions(),
                "description": "Hand to chest"
            },
            "thanks": {
                "frames": 12,
                "hand_positions": self._generate_thank_positions(),
                "description": "Hand to chest"
            },
            "good": {
                "frames": 10,
                "hand_positions": self._generate_thumbs_up_positions(),
                "description": "Thumbs up"
            },
            "yes": {
                "frames": 10,
                "hand_positions": self._generate_nod_positions(),
                "description": "Nod motion"
            },
            "no": {
                "frames": 12,
                "hand_positions": self._generate_shake_positions(),
                "description": "Shake motion"
            },
            "water": {
                "frames": 12,
                "hand_positions": self._generate_down_positions(),
                "description": "Move downward"
            },
            "help": {
                "frames": 12,
                "hand_positions": self._generate_lift_positions(),
                "description": "Hands lifting"
            },
            "love": {
                "frames": 12,
                "hand_positions": self._generate_heart_positions(),
                "description": "Heart shape"
            },
            "name": {
                "frames": 10,
                "hand_positions": self._generate_cross_positions(),
                "description": "Crossing motion"
            },
            "what": {
                "frames": 12,
                "hand_positions": self._generate_shrug_positions(),
                "description": "Shrug motion"
            },
        }
    
    # Position generators for different hand movements
    def _generate_wave_positions(self) -> List[tuple]:
        """Generate positions for waving gesture"""
        positions = []
        for i in range(15):
            x = 300 + int(30 * np.sin(i * np.pi / 7.5))
            y = 200 - int(20 * np.cos(i * np.pi / 7.5))
            positions.append((x, y))
        return positions
    
    def _generate_circle_positions(self) -> List[tuple]:
        """Generate positions for circular motion"""
        positions = []
        for i in range(15):
            angle = i * (2 * np.pi / 15)
            x = 300 + int(40 * np.cos(angle))
            y = 250 + int(40 * np.sin(angle))
            positions.append((x, y))
        return positions
    
    def _generate_point_positions(self) -> List[tuple]:
        """Generate positions for pointing"""
        positions = []
        for i in range(10):
            x = 300 + int(60 * (i / 10))
            y = 250 - int(30 * (i / 10))
            positions.append((x, y))
        return positions
    
    def _generate_thank_positions(self) -> List[tuple]:
        """Generate positions for thank you"""
        positions = []
        for i in range(12):
            x = 300
            y = 250 - int(40 * np.sin(i * np.pi / 12))
            positions.append((x, y))
        return positions
    
    def _generate_thumbs_up_positions(self) -> List[tuple]:
        """Generate positions for thumbs up"""
        positions = []
        for i in range(10):
            x = 300
            y = 300 - int(50 * (i / 10))
            positions.append((x, y))
        return positions
    
    def _generate_nod_positions(self) -> List[tuple]:
        """Generate positions for nodding"""
        positions = []
        for i in range(10):
            x = 300
            y = 250 + int(30 * np.sin(i * np.pi / 5))
            positions.append((x, y))
        return positions
    
    def _generate_shake_positions(self) -> List[tuple]:
        """Generate positions for shaking"""
        positions = []
        for i in range(12):
            x = 300 + int(40 * np.cos(i * np.pi / 6))
            y = 250
            positions.append((x, y))
        return positions
    
    def _generate_down_positions(self) -> List[tuple]:
        """Generate positions for moving down"""
        positions = []
        for i in range(12):
            x = 300
            y = 200 + int(100 * (i / 12))
            positions.append((x, y))
        return positions
    
    def _generate_lift_positions(self) -> List[tuple]:
        """Generate positions for lifting"""
        positions = []
        for i in range(12):
            x = 300
            y = 350 - int(100 * (i / 12))
            positions.append((x, y))
        return positions
    
    def _generate_heart_positions(self) -> List[tuple]:
        """Generate positions for heart shape"""
        positions = []
        for i in range(12):
            angle = i * (2 * np.pi / 12)
            x = 300 + int(50 * np.cos(angle))
            y = 250 + int(50 * np.sin(angle))
            positions.append((x, y))
        return positions
    
    def _generate_cross_positions(self) -> List[tuple]:
        """Generate positions for crossing"""
        positions = []
        for i in range(10):
            x = 250 + int(100 * (i / 10))
            y = 200 + int(100 * (i / 10))
            positions.append((x, y))
        return positions
    
    def _generate_shrug_positions(self) -> List[tuple]:
        """Generate positions for shrugging"""
        positions = []
        for i in range(12):
            x = 280 + int(40 * np.sin(i * np.pi / 6))
            y = 250 - int(30 * np.cos(i * np.pi / 6))
            positions.append((x, y))
        return positions
    
    async def text_to_gif(self, text: str) -> Dict:
        """
        Convert text to animated sign language GIF
        """
        try:
            logger.info(f"Generating GIF for text: {text}")
            
            # Convert text to signs
            signs = self._text_to_signs(text)
            
            if not signs:
                return {"error": "No signs found for text"}
            
            logger.info(f"Sign sequence: {signs}")
            
            # Generate GIF
            gif_path = await self._create_gif(signs)
            
            if not gif_path:
                return {"error": "Failed to create GIF"}
            
            return {
                "success": True,
                "gif_path": gif_path,
                "filename": os.path.basename(gif_path),
                "text": text,
                "signs": signs,
                "duration": len(signs) * 1.0
            }
            
        except Exception as e:
            logger.error(f"GIF generation error: {e}", exc_info=True)
            return {"error": str(e)}
    
    def _text_to_signs(self, text: str) -> List[str]:
        """Convert text to sign sequence"""
        try:
            words = text.lower().split()
            signs = []
            
            for word in words:
                clean_word = word.strip('.,!?;:\'"')
                
                if clean_word in self.sign_database:
                    signs.append(clean_word)
                else:
                    logger.warning(f"No sign for '{clean_word}'")
                    # Try to use as-is or skip
                    if clean_word in ["the", "a", "an", "is", "and", "or", "in", "on", "at"]:
                        # Skip common words
                        continue
                    signs.append(clean_word)
            
            return signs
            
        except Exception as e:
            logger.error(f"Text to signs error: {e}")
            return []
    
    async def _create_gif(self, signs: List[str]) -> Optional[str]:
        """Create animated GIF from signs"""
        try:
            filename = f"sign_{datetime.now().strftime('%Y%m%d_%H%M%S')}.gif"
            output_path = os.path.join(self.output_dir, filename)
            
            # Video properties
            width, height = 600, 500
            fps = 10
            
            frames = []
            
            for sign_idx, sign in enumerate(signs):
                sign_info = self.sign_database.get(sign, {
                    "frames": 10,
                    "hand_positions": [(300, 250)] * 10,
                    "description": sign
                })
                
                positions = sign_info["hand_positions"]
                
                # Create frames for this sign
                for frame_idx, (hand_x, hand_y) in enumerate(positions):
                    frame = np.ones((height, width, 3), dtype=np.uint8) * 240
                    
                    # Draw background
                    cv2.rectangle(frame, (0, 0), (width, height), (245, 245, 245), -1)
                    
                    # Draw body
                    self._draw_body(frame, 300, 300)
                    
                    # Draw animated hand
                    self._draw_hand(frame, hand_x, hand_y, sign)
                    
                    # Draw sign info
                    cv2.putText(frame, f"Sign: {sign.upper()}", (20, 40),
                               cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)
                    cv2.putText(frame, sign_info["description"], (20, 70),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (100, 100, 100), 1)
                    
                    # Draw counter
                    cv2.putText(frame, f"{sign_idx + 1}/{len(signs)}", 
                               (width - 120, 40),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.8, (100, 100, 100), 1)
                    
                    frames.append(frame)
            
            # Save as GIF
            if frames:
                imageio.mimsave(output_path, frames, fps=fps, loop=0)
                logger.info(f"GIF created: {output_path} ({len(frames)} frames)")
                return output_path
            
            return None
            
        except Exception as e:
            logger.error(f"GIF creation error: {e}", exc_info=True)
            return None
    
    def _draw_body(self, frame: np.ndarray, center_x: int, center_y: int):
        """Draw avatar body"""
        # Head
        cv2.circle(frame, (center_x, center_y - 100), 30, (220, 180, 160), -1)
        cv2.circle(frame, (center_x, center_y - 100), 30, (100, 100, 100), 2)
        
        # Eyes
        cv2.circle(frame, (center_x - 10, center_y - 105), 4, (0, 0, 0), -1)
        cv2.circle(frame, (center_x + 10, center_y - 105), 4, (0, 0, 0), -1)
        
        # Mouth (smile)
        cv2.ellipse(frame, (center_x, center_y - 95), (10, 6), 0, 0, 180, (0, 0, 0), 2)
        
        # Torso
        cv2.line(frame, (center_x, center_y - 70), (center_x, center_y + 30), (0, 0, 255), 4)
        
        # Shoulders/arms anchor
        cv2.line(frame, (center_x - 40, center_y - 50), (center_x + 40, center_y - 50), (100, 100, 100), 3)
        
        # Legs
        cv2.line(frame, (center_x - 15, center_y + 30), (center_x - 20, center_y + 80), (100, 100, 100), 3)
        cv2.line(frame, (center_x + 15, center_y + 30), (center_x + 20, center_y + 80), (100, 100, 100), 3)
    
    def _draw_hand(self, frame: np.ndarray, hand_x: int, hand_y: int, sign: str):
        """Draw animated hand"""
        # Hand shape circle
        hand_radius = 20
        cv2.circle(frame, (hand_x, hand_y), hand_radius, (220, 180, 160), -1)
        cv2.circle(frame, (hand_x, hand_y), hand_radius, (100, 100, 100), 2)
        
        # Fingers (simplified)
        finger_length = 15
        finger_angles = [0, 72, 144, 216, 288]  # 5 fingers equally spaced
        
        for angle in finger_angles:
            rad = np.radians(angle)
            end_x = int(hand_x + (hand_radius + finger_length) * np.cos(rad))
            end_y = int(hand_y + (hand_radius + finger_length) * np.sin(rad))
            cv2.line(frame, (hand_x, hand_y), (end_x, end_y), (100, 100, 100), 2)
            cv2.circle(frame, (end_x, end_y), 3, (100, 100, 100), -1)
        
        # Palm details
        cv2.circle(frame, (hand_x, hand_y), 8, (200, 150, 120), -1)


if __name__ == "__main__":
    # Test the SignLanguageGifGenerator
    import asyncio

    async def test_gif_generator():
        generator = SignLanguageGifGenerator()
        test_text = "Hello"
        result = await generator.text_to_gif(test_text)
        
        if "gif_path" in result:
            print(f"GIF generated at: {result['gif_path']}")
            os.system(f"open {result['gif_path']}")       
        else:
            print(f"Error: {result.get('error', 'Unknown error')}")

    asyncio.run(test_gif_generator())