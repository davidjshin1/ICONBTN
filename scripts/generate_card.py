#!/usr/bin/env python3
"""
Sorcery Card Generator - Hybrid PIL + AI Approach
==================================================
Generates game card assets by compositing multiple layers with pixel-perfect precision.

Architecture:
- PIL/Pillow: Handles all layer compositing for consistent positioning
- Google Gemini (optional): Smart character image fitting/cropping

Usage:
    python generate_card.py --character "frost queen" --rarity 3star --calling cunning
    python generate_card.py --parse "give me a card for frost queen 3 star calling cunning"
"""

import os
import re
import argparse
import json
from pathlib import Path
from PIL import Image, ImageOps, ImageFilter, ImageEnhance
from typing import Tuple, Optional, Dict, Any, List

# Optional AI imports
try:
    from google import genai
    from google.genai import types
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# =============================================================================
# CONFIGURATION
# =============================================================================

class CardConfig:
    """Central configuration for card generation."""
    
    # Canvas dimensions (matches base shape)
    CANVAS_WIDTH = 1123
    CANVAS_HEIGHT = 2000
    
    # ==========================================================================
    # ICON SIZING GUIDELINES (Based on reference design spec)
    # ==========================================================================
    # Reference: 1000px × 1778px card (9:16 ratio)
    # Actual canvas: 1123px × 2000px (scaled proportionally)
    # 
    # Top Icon (Class Sigil):
    #   - Flat/Vector glyph style (simplified, graphic silhouette)
    #   - Color: Pale glowing cyan (#A0E0E0) at 80-90% opacity
    #   - Container: 12-15% of card width = ~135-168px at 1123px width
    #   - Height: Approximately equal to width (square-ish container)
    #   - Generous padding within the header bar keystone/shield cutout
    #
    # Bottom Icons (Rarity/Grade Stars):
    #   - 8-pointed North Star (Octagram) style
    #   - Metallic emboss effect (polished silver/platinum)
    #   - Inverted triangle/V-formation cluster
    #   - Cluster width: 25% of card width = ~280px at 1123px width
    #   - Central star height: 5% of card height = ~100px at 2000px height
    #   - Central star is 10-15% larger than flanking stars
    # ==========================================================================
    
    # Icon sizing (as percentage of canvas dimensions)
    ICON_SIZING = {
        "calling": {
            "width_percent": 0.12,       # 12% of card width (min recommendation)
            "max_width_percent": 0.15,   # 15% max
            "maintain_aspect": True,
            "opacity": 0.85,             # 80-90% opacity for flat glyph style
            "description": "Class Sigil - flat vector glyph in keystone container"
        },
        "pip": {
            "width_percent": 0.25,       # 25% of card width for entire cluster
            "height_percent": 0.05,      # 5% of card height for central star
            "maintain_aspect": True,
            "description": "Rarity Stars - 8-pointed metallic emboss cluster"
        }
    }
    
    # Calculated target dimensions (at CANVAS_WIDTH=1123, CANVAS_HEIGHT=2000)
    # Calling icon: 12% × 1123 = ~135px width
    # Pip cluster: 25% × 1123 = ~280px width, 5% × 2000 = ~100px height
    
    # Layer configurations for each rarity
    # Format: (filename_pattern, offset_x, offset_y, z_order)
    LAYER_CONFIG = {
        "base_shape": {
            "pattern": "SorceryCard_BaseShape__1_.png",
            "offset": (0, 0),
            "z_order": 0,
            "description": "Card shape mask"
        },
        "black_border": {
            "pattern": "SorceryCard_Front_Border_Black_{rarity}.png",
            "offset": (0, 0),  # Full canvas, centered
            "z_order": 1,
            "is_outer_stroke": True,  # Ensures this is rendered as outer card stroke
            "description": "Outer black stroke - outermost layer of the card"
        },
        "character": {
            "pattern": None,  # Dynamic based on character name
            "offset": (0, 0),
            "z_order": 2,
            "description": "Character artwork"
        },
        "border": {
            "pattern": "SorceryCard_Front_Border_{rarity}.png",
            "offset": (19, 0),  # Centered: (1123-1085)//2 = 19
            "z_order": 3,
            "description": "Decorative border frame"
        },
        "pip": {
            "pattern": "SorceryCard_Front_Pip_{rarity}.png",
            "offset": "center_bottom",  # Special positioning
            "pip_bottom_margin": 0,  # Distance from bottom
            "z_order": 4,
            "resize": True,  # Enable resizing based on ICON_SIZING
            "description": "Rarity star indicator"
        },
        "calling": {
            "pattern": "icon_calling_{calling}.png",
            "offset": "center_top",  # Special positioning
            "calling_top_margin": 22,  # Distance from top
            "z_order": 5,
            "resize": True,  # Enable resizing based on ICON_SIZING
            "description": "Character type icon"
        }
    }
    
    # Supported rarities
    RARITIES = ["3star", "4star", "5star"]
    
    # Known callings (expandable)
    CALLINGS = ["Cunning", "Might", "Wisdom", "Spirit", "Shadow"]
    
    # AI Model configuration
    GEMINI_MODEL = "gemini-3-pro-image-preview"
    
    # Character fit settings
    CHARACTER_FIT_MODE = "cover"  # "cover", "contain", "smart"


class PathResolver:
    """Resolves asset paths based on the project structure."""
    
    def __init__(self, base_dir: str = None):
        if base_dir is None:
            # Default: look for assets relative to script location
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.base_dir = Path(base_dir)
        self.assets_dir = self.base_dir / "assets" / "sorcerycardref"
        self.output_dir = self.base_dir / "output" / "card"
        
    def get_rarity_dir(self, rarity: str) -> Path:
        """Get the directory for a specific rarity's assets."""
        return self.assets_dir / rarity
    
    def get_primals_dir(self) -> Path:
        """Get the directory containing character images."""
        return self.assets_dir / "primals"
    
    def get_calling_dir(self) -> Path:
        """Get the directory containing calling icons."""
        return self.assets_dir / "calling"
    
    def get_base_shape(self, rarity: str = "3star") -> Path:
        """Get the base shape file (check rarity folder first, then common)."""
        # Check in rarity folder first
        rarity_path = self.assets_dir / rarity / CardConfig.LAYER_CONFIG["base_shape"]["pattern"]
        if rarity_path.exists():
            return rarity_path
        # Fallback to 3star
        return self.assets_dir / "3star" / CardConfig.LAYER_CONFIG["base_shape"]["pattern"]
    
    def find_character(self, character_name: str) -> Optional[Path]:
        """Find a character image by name (fuzzy matching)."""
        primals_dir = self.get_primals_dir()
        if not primals_dir.exists():
            return None
            
        # Normalize search term
        search_term = character_name.lower().replace(" ", "").replace("_", "")
        
        # Search for matching files
        for file in primals_dir.iterdir():
            if file.is_file() and file.suffix.lower() in ['.png', '.jpg', '.jpeg', '.webp']:
                file_normalized = file.stem.lower().replace(" ", "").replace("_", "")
                if search_term in file_normalized or file_normalized in search_term:
                    return file
        return None
    
    def find_calling_icon(self, calling: str) -> Optional[Path]:
        """Find a calling icon by name."""
        calling_dir = self.get_calling_dir()
        
        # Try exact pattern first
        pattern = f"icon_calling_{calling}.png"
        exact_path = calling_dir / pattern
        if exact_path.exists():
            return exact_path
        
        # Case-insensitive search
        calling_lower = calling.lower()
        pattern_lower = f"icon_calling_{calling_lower}.png"
        
        if calling_dir.exists():
            for file in calling_dir.iterdir():
                if file.is_file() and file.name.lower() == pattern_lower:
                    return file
                # Also fuzzy match
                if file.is_file() and calling_lower in file.stem.lower():
                    return file
        return None
    
    def get_rarity_asset(self, rarity: str, asset_type: str) -> Optional[Path]:
        """Get a rarity-specific asset (border, pip, black_border)."""
        config = CardConfig.LAYER_CONFIG.get(asset_type)
        if not config or not config["pattern"]:
            return None
            
        pattern = config["pattern"].format(rarity=rarity)
        path = self.get_rarity_dir(rarity) / pattern
        return path if path.exists() else None


# =============================================================================
# NATURAL LANGUAGE PARSER
# =============================================================================

class CommandParser:
    """Parses natural language commands to extract card generation parameters."""
    
    # Patterns for extracting components
    RARITY_PATTERNS = [
        r'(\d)\s*star',
        r'(\d)-star',
        r'rarity[:\s]+(\d)',
    ]
    
    CALLING_PATTERNS = [
        r'calling[:\s]+(\w+)',
        r'type[:\s]+(\w+)',
        r'class[:\s]+(\w+)',
    ]
    
    def __init__(self):
        self.known_callings = [c.lower() for c in CardConfig.CALLINGS]
    
    def parse(self, command: str) -> Dict[str, Any]:
        """
        Parse a natural language command into structured parameters.
        
        Examples:
            "give me a card for frost queen 3 star calling cunning"
            "create frost queen 3star cunning"
            "frost queen, rarity: 3, calling: Cunning"
        """
        command_lower = command.lower().strip()
        result = {
            "character": None,
            "rarity": None,
            "calling": None,
            "raw_command": command
        }
        
        # Extract rarity
        for pattern in self.RARITY_PATTERNS:
            match = re.search(pattern, command_lower)
            if match:
                rarity_num = match.group(1)
                result["rarity"] = f"{rarity_num}star"
                break
        
        # Extract calling - check for known callings in the text
        for calling in self.known_callings:
            if calling in command_lower:
                result["calling"] = calling.capitalize()
                break
        
        # If not found, try patterns
        if not result["calling"]:
            for pattern in self.CALLING_PATTERNS:
                match = re.search(pattern, command_lower)
                if match:
                    result["calling"] = match.group(1).capitalize()
                    break
        
        # Extract character name (most complex)
        # Remove known components to isolate character name
        cleaned = command_lower
        
        # Remove rarity mentions
        cleaned = re.sub(r'\d\s*star', '', cleaned)
        cleaned = re.sub(r'\d-star', '', cleaned)
        
        # Remove calling mentions
        cleaned = re.sub(r'calling[:\s]+\w+', '', cleaned)
        for calling in self.known_callings:
            cleaned = cleaned.replace(calling, '')
        
        # Remove common command words
        remove_words = ['give', 'me', 'a', 'card', 'for', 'create', 'generate', 'make', 'rarity', 'type', 'class']
        for word in remove_words:
            cleaned = re.sub(rf'\b{word}\b', '', cleaned)
        
        # Clean up and get character name
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        cleaned = re.sub(r'[^\w\s]', '', cleaned).strip()
        
        if cleaned:
            result["character"] = cleaned.title()
        
        return result


# =============================================================================
# IMAGE PROCESSING
# =============================================================================

class CharacterFitter:
    """Handles fitting character artwork into the card shape."""
    
    def __init__(self, use_ai: bool = False, api_key: str = None):
        self.use_ai = use_ai and GEMINI_AVAILABLE and api_key
        self.api_key = api_key
        
    def fit_to_shape(self, character_img: Image.Image, mask_img: Image.Image, 
                     mode: str = "cover") -> Image.Image:
        """
        Fit a character image to the card shape.
        
        Args:
            character_img: The character artwork
            mask_img: The base shape mask (alpha channel defines card shape)
            mode: Fitting mode - "cover", "contain", or "smart"
        """
        target_w, target_h = mask_img.size
        
        # Convert to RGBA if needed
        if character_img.mode != 'RGBA':
            character_img = character_img.convert('RGBA')
        
        if mode == "smart" and self.use_ai:
            return self._smart_fit_ai(character_img, mask_img)
        elif mode == "cover":
            return self._cover_fit(character_img, target_w, target_h, mask_img)
        else:  # contain
            return self._contain_fit(character_img, target_w, target_h, mask_img)
    
    def _cover_fit(self, img: Image.Image, target_w: int, target_h: int,
                   mask: Image.Image) -> Image.Image:
        """Scale image to cover the entire target area, then crop to fit."""
        img_w, img_h = img.size
        
        # Calculate scale to cover
        scale_w = target_w / img_w
        scale_h = target_h / img_h
        scale = max(scale_w, scale_h)
        
        # Scale image
        new_w = int(img_w * scale)
        new_h = int(img_h * scale)
        scaled = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
        
        # Crop to target size (center crop with bias toward top for character portraits)
        left = (new_w - target_w) // 2
        # Bias crop toward top of image for better character framing
        top = int((new_h - target_h) * 0.3)  # 30% from top instead of 50%
        top = max(0, min(top, new_h - target_h))
        
        cropped = scaled.crop((left, top, left + target_w, top + target_h))
        
        # Apply mask
        return self._apply_mask(cropped, mask)
    
    def _contain_fit(self, img: Image.Image, target_w: int, target_h: int,
                     mask: Image.Image) -> Image.Image:
        """Scale image to fit within target area, maintaining aspect ratio."""
        img_w, img_h = img.size
        
        # Calculate scale to contain
        scale_w = target_w / img_w
        scale_h = target_h / img_h
        scale = min(scale_w, scale_h)
        
        # Scale image
        new_w = int(img_w * scale)
        new_h = int(img_h * scale)
        scaled = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
        
        # Create canvas and center image
        canvas = Image.new('RGBA', (target_w, target_h), (0, 0, 0, 0))
        paste_x = (target_w - new_w) // 2
        paste_y = (target_h - new_h) // 2
        canvas.paste(scaled, (paste_x, paste_y))
        
        return self._apply_mask(canvas, mask)
    
    def _apply_mask(self, img: Image.Image, mask: Image.Image) -> Image.Image:
        """Apply the base shape mask to the image."""
        # Ensure both are RGBA
        if img.mode != 'RGBA':
            img = img.convert('RGBA')
        if mask.mode != 'RGBA':
            mask = mask.convert('RGBA')
        
        # Get alpha channel from mask
        mask_alpha = mask.split()[3]
        
        # Apply mask to image alpha
        img_r, img_g, img_b, img_a = img.split()
        
        # Combine: keep image where mask is opaque
        new_alpha = Image.composite(img_a, Image.new('L', img.size, 0), mask_alpha)
        
        return Image.merge('RGBA', (img_r, img_g, img_b, new_alpha))
    
    def _smart_fit_ai(self, img: Image.Image, mask: Image.Image) -> Image.Image:
        """Use AI to intelligently crop/fit the character (requires Gemini API)."""
        # For now, fall back to cover fit
        # This could be enhanced to use Gemini's vision to detect the subject
        # and crop optimally
        return self._cover_fit(img, mask.size[0], mask.size[1], mask)


class CardCompositor:
    """
    Handles the compositing of all card layers using pure PIL.
    No external dependencies required.
    """
    
    def __init__(self, path_resolver: PathResolver):
        self.resolver = path_resolver
    
    def _resize_icon(self, icon: Image.Image, icon_type: str) -> Image.Image:
        """Resize an icon based on the ICON_SIZING configuration."""
        sizing = CardConfig.ICON_SIZING.get(icon_type)
        if not sizing:
            return icon
        
        canvas_w = CardConfig.CANVAS_WIDTH
        orig_w, orig_h = icon.size
        
        if icon_type == "calling":
            target_w = int(canvas_w * sizing["width_percent"])
            scale = target_w / orig_w
            target_h = int(orig_h * scale)
        elif icon_type == "pip":
            target_w = int(canvas_w * sizing["width_percent"])
            scale = target_w / orig_w
            target_w = int(orig_w * scale)
            target_h = int(orig_h * scale)
        else:
            return icon
        
        resized = icon.resize((target_w, target_h), Image.Resampling.LANCZOS)
        
        if "opacity" in sizing and sizing["opacity"] < 1.0:
            r, g, b, a = resized.split()
            a = a.point(lambda x: int(x * sizing["opacity"]))
            resized = Image.merge('RGBA', (r, g, b, a))
        
        return resized
    
    def _center_paste(self, canvas: Image.Image, layer: Image.Image, 
                      offset_x: int = 0, offset_y: int = 0) -> Image.Image:
        """Paste a layer centered on the canvas with optional offset."""
        canvas_w, canvas_h = canvas.size
        layer_w, layer_h = layer.size
        
        x = (canvas_w - layer_w) // 2 + offset_x
        y = (canvas_h - layer_h) // 2 + offset_y
        
        canvas.alpha_composite(layer, (x, y))
        return canvas
        
    def composite(self, character_img: Image.Image, rarity: str, calling: str,
                  base_shape: Image.Image, character_fitter: CharacterFitter) -> Image.Image:
        """
        Composite all layers into a final card image using PIL.
        
        Layer order:
        1. BLACK_BORDER - Outer stroke (background)
        2. CHARACTER    - Character artwork (masked to card shape)
        3. BORDER       - Decorative border frame
        4. PIP          - Rarity stars (bottom center)
        5. CALLING      - Class icon (top center)
        """
        canvas_w = CardConfig.CANVAS_WIDTH
        canvas_h = CardConfig.CANVAS_HEIGHT
        
        # Create transparent canvas
        canvas = Image.new('RGBA', (canvas_w, canvas_h), (0, 0, 0, 0))
        
        # Layer 1: Black border (background)
        black_border_path = self.resolver.get_rarity_asset(rarity, "black_border")
        if black_border_path and black_border_path.exists():
            black_border = Image.open(black_border_path).convert('RGBA')
            self._center_paste(canvas, black_border)
        
        # Layer 2: Character (masked to base shape)
        fitted_character = character_fitter.fit_to_shape(
            character_img, base_shape, 
            mode=CardConfig.CHARACTER_FIT_MODE
        )
        canvas.alpha_composite(fitted_character, (0, 0))
        
        # Layer 3: Decorative border
        border_path = self.resolver.get_rarity_asset(rarity, "border")
        if border_path and border_path.exists():
            border = Image.open(border_path).convert('RGBA')
            # Border offset from config: (19, 0)
            border_offset = CardConfig.LAYER_CONFIG["border"]["offset"]
            canvas.alpha_composite(border, border_offset)
        
        # Layer 4: Pip (rarity stars) - bottom center
        pip_path = self.resolver.get_rarity_asset(rarity, "pip")
        if pip_path and pip_path.exists():
            pip = Image.open(pip_path).convert('RGBA')
            pip = self._resize_icon(pip, "pip")
            pip_w, pip_h = pip.size
            pip_x = (canvas_w - pip_w) // 2
            pip_y = canvas_h - pip_h - CardConfig.LAYER_CONFIG["pip"]["pip_bottom_margin"]
            canvas.alpha_composite(pip, (pip_x, pip_y))
        
        # Layer 5: Calling icon - top center
        calling_path = self.resolver.find_calling_icon(calling)
        if calling_path and calling_path.exists():
            calling_icon = Image.open(calling_path).convert('RGBA')
            calling_icon = self._resize_icon(calling_icon, "calling")
            calling_w, calling_h = calling_icon.size
            calling_x = (canvas_w - calling_w) // 2
            calling_y = CardConfig.LAYER_CONFIG["calling"]["calling_top_margin"]
            canvas.alpha_composite(calling_icon, (calling_x, calling_y))
        
        return canvas


# =============================================================================
# MAIN CARD GENERATOR
# =============================================================================

class SorceryCardGenerator:
    """Main class for generating sorcery cards."""
    
    def __init__(self, base_dir: str = None, use_ai: bool = False):
        self.resolver = PathResolver(base_dir)
        self.parser = CommandParser()
        
        api_key = os.getenv("GOOGLE_API_KEY")
        self.character_fitter = CharacterFitter(use_ai=use_ai, api_key=api_key)
        self.compositor = CardCompositor(self.resolver)
        
    def generate_from_command(self, command: str) -> Optional[Path]:
        """Generate a card from a natural language command."""
        params = self.parser.parse(command)
        
        if not params["character"]:
            raise ValueError(f"Could not extract character name from: {command}")
        if not params["rarity"]:
            raise ValueError(f"Could not extract rarity from: {command}")
        if not params["calling"]:
            raise ValueError(f"Could not extract calling from: {command}")
        
        return self.generate(
            character=params["character"],
            rarity=params["rarity"],
            calling=params["calling"]
        )
    
    def generate(self, character: str, rarity: str, calling: str) -> Optional[Path]:
        """
        Generate a card with the specified parameters.
        
        Args:
            character: Character name (will be fuzzy matched to find image)
            rarity: Card rarity ("3star", "4star", "5star")
            calling: Character calling/class type
            
        Returns:
            Path to the generated card image
        """
        print(f"\n{'='*60}")
        print(f"Generating Card")
        print(f"{'='*60}")
        print(f"  Character: {character}")
        print(f"  Rarity:    {rarity}")
        print(f"  Calling:   {calling}")
        print(f"{'='*60}\n")
        
        # Validate rarity
        if rarity not in CardConfig.RARITIES:
            raise ValueError(f"Invalid rarity: {rarity}. Must be one of {CardConfig.RARITIES}")
        
        # Find character image
        character_path = self.resolver.find_character(character)
        if not character_path:
            raise FileNotFoundError(f"Could not find character image for: {character}")
        print(f"[✓] Found character: {character_path.name}")
        
        # Load base shape
        base_shape_path = self.resolver.get_base_shape(rarity)
        if not base_shape_path.exists():
            raise FileNotFoundError(f"Base shape not found: {base_shape_path}")
        base_shape = Image.open(base_shape_path).convert('RGBA')
        print(f"[✓] Loaded base shape: {base_shape_path.name}")
        
        # Verify rarity assets exist
        border_path = self.resolver.get_rarity_asset(rarity, "border")
        if not border_path or not border_path.exists():
            print(f"[!] Warning: Border not found for {rarity}")
        else:
            print(f"[✓] Found border: {border_path.name}")
        
        pip_path = self.resolver.get_rarity_asset(rarity, "pip")
        if not pip_path or not pip_path.exists():
            print(f"[!] Warning: Pip not found for {rarity}")
        else:
            print(f"[✓] Found pip: {pip_path.name}")
        
        calling_path = self.resolver.find_calling_icon(calling)
        if not calling_path:
            print(f"[!] Warning: Calling icon not found for: {calling}")
        else:
            print(f"[✓] Found calling icon: {calling_path.name}")
        
        # Load character image
        character_img = Image.open(character_path).convert('RGBA')
        print(f"[✓] Loaded character image: {character_img.size}")
        
        # Composite the card
        print("\n[...] Compositing layers...")
        card = self.compositor.composite(
            character_img=character_img,
            rarity=rarity,
            calling=calling,
            base_shape=base_shape,
            character_fitter=self.character_fitter
        )
        
        # Save output
        self.resolver.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate filename
        char_clean = character.lower().replace(" ", "_")
        output_filename = f"{char_clean}_front_merge.png"
        output_path = self.resolver.output_dir / output_filename
        
        card.save(output_path, "PNG")
        print(f"\n[✓] SUCCESS: Saved to {output_path}")
        
        return output_path
    
    def list_available_assets(self) -> Dict[str, Any]:
        """List all available assets for card generation."""
        assets = {
            "characters": [],
            "callings": [],
            "rarities": {}
        }
        
        # Find characters
        primals_dir = self.resolver.get_primals_dir()
        if primals_dir.exists():
            for f in primals_dir.iterdir():
                if f.is_file() and f.suffix.lower() in ['.png', '.jpg', '.jpeg', '.webp']:
                    assets["characters"].append(f.stem)
        
        # Find callings
        calling_dir = self.resolver.get_calling_dir()
        if calling_dir.exists():
            for f in calling_dir.iterdir():
                if f.is_file() and "calling" in f.stem.lower():
                    # Extract calling name from filename
                    name = f.stem.replace("icon_calling_", "").replace("icon_", "")
                    assets["callings"].append(name)
        
        # Check rarities
        for rarity in CardConfig.RARITIES:
            rarity_dir = self.resolver.get_rarity_dir(rarity)
            assets["rarities"][rarity] = {
                "available": rarity_dir.exists(),
                "has_border": self.resolver.get_rarity_asset(rarity, "border") is not None,
                "has_pip": self.resolver.get_rarity_asset(rarity, "pip") is not None,
                "has_black_border": self.resolver.get_rarity_asset(rarity, "black_border") is not None
            }
        
        return assets


# =============================================================================
# BATCH PROCESSING (for parallel/subagent use)
# =============================================================================

class BatchCardGenerator:
    """Handles batch generation of multiple cards."""
    
    def __init__(self, generator: SorceryCardGenerator):
        self.generator = generator
        
    def generate_batch(self, requests: List[Dict[str, str]]) -> List[Dict[str, Any]]:
        """
        Generate multiple cards from a list of requests.
        
        Args:
            requests: List of dicts with keys: character, rarity, calling
            
        Returns:
            List of results with status and output path
        """
        results = []
        
        for i, req in enumerate(requests, 1):
            print(f"\n[{i}/{len(requests)}] Processing: {req}")
            try:
                output = self.generator.generate(
                    character=req["character"],
                    rarity=req["rarity"],
                    calling=req["calling"]
                )
                results.append({
                    "request": req,
                    "status": "success",
                    "output": str(output)
                })
            except Exception as e:
                results.append({
                    "request": req,
                    "status": "error",
                    "error": str(e)
                })
        
        return results
    
    def generate_all_variants(self, character: str, calling: str = None) -> List[Dict[str, Any]]:
        """Generate all rarity variants for a character."""
        assets = self.generator.list_available_assets()
        requests = []
        
        callings = [calling] if calling else (assets["callings"] if assets["callings"] else ["Cunning"])
        
        for rarity in CardConfig.RARITIES:
            for c in callings:
                requests.append({
                    "character": character,
                    "rarity": rarity,
                    "calling": c
                })
        
        return self.generate_batch(requests)


# =============================================================================
# CLI INTERFACE
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Sorcery Card Generator - Create game card assets",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Direct parameters:
  python generate_card.py --character "frost queen" --rarity 3star --calling Cunning
  
  # Natural language:
  python generate_card.py --parse "give me a card for frost queen 3 star calling cunning"
  
  # List available assets:
  python generate_card.py --list
  
  # Batch mode (JSON input):
  python generate_card.py --batch '[{"character": "frost queen", "rarity": "3star", "calling": "Cunning"}]'
        """
    )
    
    parser.add_argument("--character", "-c", help="Character name")
    parser.add_argument("--rarity", "-r", choices=CardConfig.RARITIES, help="Card rarity")
    parser.add_argument("--calling", "-l", help="Character calling/class")
    parser.add_argument("--parse", "-p", help="Natural language command to parse")
    parser.add_argument("--list", action="store_true", help="List available assets")
    parser.add_argument("--batch", help="Batch process JSON array of requests")
    parser.add_argument("--base-dir", help="Base directory for assets")
    parser.add_argument("--use-ai", action="store_true", help="Use AI for smart character fitting")
    parser.add_argument("--output", "-o", help="Output filename override")
    
    args = parser.parse_args()
    
    # Initialize generator
    generator = SorceryCardGenerator(
        base_dir=args.base_dir,
        use_ai=args.use_ai
    )
    
    try:
        if args.list:
            # List available assets
            assets = generator.list_available_assets()
            print("\n=== Available Assets ===\n")
            print(f"Characters: {', '.join(assets['characters']) or 'None found'}")
            print(f"Callings: {', '.join(assets['callings']) or 'None found'}")
            print("\nRarities:")
            for rarity, info in assets["rarities"].items():
                status = "✓" if info["available"] else "✗"
                print(f"  {status} {rarity}: border={info['has_border']}, pip={info['has_pip']}")
            return
        
        if args.batch:
            # Batch processing
            requests = json.loads(args.batch)
            batch_gen = BatchCardGenerator(generator)
            results = batch_gen.generate_batch(requests)
            print("\n=== Batch Results ===")
            for r in results:
                status = "✓" if r["status"] == "success" else "✗"
                print(f"  {status} {r['request']}: {r.get('output', r.get('error'))}")
            return
        
        if args.parse:
            # Natural language parsing
            output = generator.generate_from_command(args.parse)
        elif args.character and args.rarity and args.calling:
            # Direct parameters
            output = generator.generate(
                character=args.character,
                rarity=args.rarity,
                calling=args.calling
            )
        else:
            parser.print_help()
            return
        
        if output:
            print(f"\n✓ Card generated: {output}")
            
    except Exception as e:
        print(f"\n✗ Error: {e}")
        raise


if __name__ == "__main__":
    main()
