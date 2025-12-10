#!/usr/bin/env python3
"""
Exact Card Layer System - Based on Figma Design Specs
======================================================
Pixel-perfect layer compositing derived from Figma source of truth.

Figma Source Frame: "Form" (node 9024:246)
- Canvas: 1464 × 2605 px
- BaseShape: (0, 1) @ 1464 × 2604
- Border: (25, 0) @ 1414 × 2605

This module provides a formula-based system that scales these exact
relationships to any target resolution while maintaining pixel accuracy.
"""

from dataclasses import dataclass, field
from typing import Tuple, Optional, Dict, List, Callable
from pathlib import Path
from PIL import Image, ImageChops, ImageOps
from enum import Enum, auto


# =============================================================================
# FIGMA SOURCE OF TRUTH
# =============================================================================

@dataclass(frozen=True)
class FigmaSpec:
    """
    Immutable Figma design specifications.
    These values are the SINGLE SOURCE OF TRUTH extracted from Figma.
    """
    # Frame dimensions (Form node 9024:246)
    FRAME_WIDTH: int = 1464
    FRAME_HEIGHT: int = 2605
    
    # Layer: SorceryCard_Front_BaseShape 1 (node 9024:243)
    BASE_SHAPE_X: int = 0
    BASE_SHAPE_Y: int = 1
    BASE_SHAPE_WIDTH: int = 1464
    BASE_SHAPE_HEIGHT: int = 2604
    
    # Layer: SorceryCard_Front_Border_3star 1 (node 9024:242)
    BORDER_X: int = 25
    BORDER_Y: int = 0
    BORDER_WIDTH: int = 1414
    BORDER_HEIGHT: int = 2605
    
    # Derived relationships (computed once, used for scaling)
    @property
    def border_inset_left(self) -> int:
        """Border inset from left edge."""
        return self.BORDER_X  # 25px
    
    @property
    def border_inset_right(self) -> int:
        """Border inset from right edge."""
        return self.FRAME_WIDTH - self.BORDER_X - self.BORDER_WIDTH  # 25px
    
    @property
    def base_shape_top_offset(self) -> int:
        """Base shape offset from top."""
        return self.BASE_SHAPE_Y  # 1px
    
    @property
    def aspect_ratio(self) -> float:
        """Frame aspect ratio (height / width)."""
        return self.FRAME_HEIGHT / self.FRAME_WIDTH  # ~1.779


# Global Figma spec instance
FIGMA = FigmaSpec()


# =============================================================================
# LAYER FORMULA SYSTEM
# =============================================================================

@dataclass
class LayerPosition:
    """Calculated layer position with integer pixel coordinates."""
    x: int
    y: int
    width: int
    height: int
    
    @property
    def origin(self) -> Tuple[int, int]:
        return (self.x, self.y)
    
    @property
    def size(self) -> Tuple[int, int]:
        return (self.width, self.height)
    
    def __repr__(self) -> str:
        return f"LayerPosition(x={self.x}, y={self.y}, w={self.width}, h={self.height})"


class LayerType(Enum):
    """Enumeration of all layer types in z-order (bottom to top)."""
    BLACK_BORDER = auto()    # 1. Outer stroke (background)
    BASE_SHAPE = auto()      # 2. Card shape mask
    CHARACTER = auto()       # 3. Character artwork (masked)
    BORDER = auto()          # 4. Decorative border frame
    PIP = auto()             # 5. Rarity stars (bottom)
    CALLING = auto()         # 6. Class icon (top)


@dataclass
class LayerFormula:
    """
    Formula for calculating a layer's position at any scale.
    
    Each formula is expressed as ratios of the Figma source dimensions,
    allowing exact scaling to any target resolution.
    """
    # Position ratios (0.0 to 1.0 relative to canvas)
    x_ratio: float
    y_ratio: float
    
    # Size ratios (relative to canvas dimensions)
    width_ratio: float
    height_ratio: float
    
    # Optional fixed pixel offsets (applied after scaling)
    x_offset: int = 0
    y_offset: int = 0
    
    # Alignment helpers
    center_x: bool = False  # If True, x_ratio is ignored and layer is centered
    center_y: bool = False  # If True, y_ratio is ignored and layer is centered
    anchor_bottom: bool = False  # If True, y is calculated from bottom edge
    
    def calculate(self, canvas_width: int, canvas_height: int,
                  content_width: Optional[int] = None,
                  content_height: Optional[int] = None) -> LayerPosition:
        """
        Calculate exact pixel position for a given canvas size.
        
        Args:
            canvas_width: Target canvas width in pixels
            canvas_height: Target canvas height in pixels
            content_width: Actual content width (for centering)
            content_height: Actual content height (for bottom anchoring)
        """
        # Calculate size
        width = int(canvas_width * self.width_ratio) if self.width_ratio > 0 else content_width or 0
        height = int(canvas_height * self.height_ratio) if self.height_ratio > 0 else content_height or 0
        
        # Use content dimensions if provided and size ratios are 0
        if content_width and self.width_ratio == 0:
            width = content_width
        if content_height and self.height_ratio == 0:
            height = content_height
        
        # Calculate X position
        if self.center_x and content_width:
            x = (canvas_width - content_width) // 2
        else:
            x = int(canvas_width * self.x_ratio) + self.x_offset
        
        # Calculate Y position
        if self.anchor_bottom and content_height:
            y = canvas_height - content_height + int(canvas_height * self.y_ratio) + self.y_offset
        elif self.center_y and content_height:
            y = (canvas_height - content_height) // 2
        else:
            y = int(canvas_height * self.y_ratio) + self.y_offset
        
        return LayerPosition(x=x, y=y, width=width, height=height)


# =============================================================================
# LAYER FORMULA DEFINITIONS (Derived from Figma)
# =============================================================================

class CardLayerFormulas:
    """
    Pre-computed layer formulas based on Figma specifications.
    
    All ratios are calculated from FIGMA constants to ensure
    exact proportional relationships at any scale.
    """
    
    # Base shape formula
    # Figma: (0, 1) @ 1464×2604 on 1464×2605 canvas
    BASE_SHAPE = LayerFormula(
        x_ratio=FIGMA.BASE_SHAPE_X / FIGMA.FRAME_WIDTH,      # 0.0
        y_ratio=FIGMA.BASE_SHAPE_Y / FIGMA.FRAME_HEIGHT,     # 0.000384
        width_ratio=FIGMA.BASE_SHAPE_WIDTH / FIGMA.FRAME_WIDTH,   # 1.0
        height_ratio=FIGMA.BASE_SHAPE_HEIGHT / FIGMA.FRAME_HEIGHT, # 0.9996
    )
    
    # Border formula
    # Figma: (25, 0) @ 1414×2605 on 1464×2605 canvas
    BORDER = LayerFormula(
        x_ratio=FIGMA.BORDER_X / FIGMA.FRAME_WIDTH,          # 0.01708
        y_ratio=FIGMA.BORDER_Y / FIGMA.FRAME_HEIGHT,         # 0.0
        width_ratio=FIGMA.BORDER_WIDTH / FIGMA.FRAME_WIDTH,  # 0.9658
        height_ratio=FIGMA.BORDER_HEIGHT / FIGMA.FRAME_HEIGHT, # 1.0
    )
    
    # Character layer (same as base shape, will be masked)
    CHARACTER = LayerFormula(
        x_ratio=0.0,
        y_ratio=0.0,
        width_ratio=1.0,
        height_ratio=1.0,
    )
    
    # Black border (full canvas, behind everything)
    BLACK_BORDER = LayerFormula(
        x_ratio=0.0,
        y_ratio=0.0,
        width_ratio=1.0,
        height_ratio=1.0,
        center_x=True,
        center_y=True,
    )
    
    # Pip (rarity stars) - centered horizontally, anchored to bottom
    # These ratios can be adjusted based on your Figma specs for pips
    PIP = LayerFormula(
        x_ratio=0.0,  # Ignored due to center_x
        y_ratio=0.0,  # Offset from bottom
        width_ratio=0.0,  # Use actual content size
        height_ratio=0.0,
        center_x=True,
        anchor_bottom=True,
    )
    
    # Calling icon - centered horizontally, fixed from top
    # Adjust top margin ratio based on your Figma specs
    CALLING = LayerFormula(
        x_ratio=0.0,  # Ignored due to center_x
        y_ratio=22 / FIGMA.FRAME_HEIGHT,  # Top margin as ratio
        width_ratio=0.0,  # Use actual content size
        height_ratio=0.0,
        center_x=True,
    )


# =============================================================================
# EXACT IMAGE LOADER
# =============================================================================

class ExactImageLoader:
    """
    Loads and normalizes images for consistent processing.
    """
    
    @staticmethod
    def load(path: Path, mode: str = 'RGBA') -> Image.Image:
        """
        Load image with exact, consistent settings.
        
        - Applies EXIF orientation
        - Converts to specified mode
        - Strips color profiles
        """
        img = Image.open(path)
        
        # Apply EXIF rotation to pixels
        img = ImageOps.exif_transpose(img)
        
        # Convert mode
        if img.mode != mode:
            if img.mode == 'P':
                # Handle palette images
                img = img.convert('RGBA' if 'transparency' in img.info else 'RGB')
            img = img.convert(mode)
        
        # Strip ICC profile for cross-platform consistency
        if 'icc_profile' in img.info:
            del img.info['icc_profile']
        
        return img
    
    @staticmethod
    def resize_exact(img: Image.Image, size: Tuple[int, int]) -> Image.Image:
        """Resize with LANCZOS for consistent high-quality output."""
        return img.resize(size, Image.Resampling.LANCZOS)


# =============================================================================
# EXACT MASK APPLICATION
# =============================================================================

class ExactMask:
    """
    Pixel-perfect mask operations.
    """
    
    @staticmethod
    def apply(image: Image.Image, mask: Image.Image) -> Image.Image:
        """
        Apply mask's alpha channel to image.
        
        Uses alpha multiplication for proper semi-transparent edge handling.
        """
        if image.size != mask.size:
            raise ValueError(f"Size mismatch: image={image.size}, mask={mask.size}")
        
        image = image.convert('RGBA')
        mask = mask.convert('RGBA')
        
        # Extract channels
        r, g, b, img_alpha = image.split()
        mask_alpha = mask.split()[3]
        
        # Multiply alphas: result = img_alpha * mask_alpha / 255
        combined_alpha = ImageChops.multiply(img_alpha, mask_alpha)
        
        return Image.merge('RGBA', (r, g, b, combined_alpha))
    
    @staticmethod
    def extract_alpha(image: Image.Image) -> Image.Image:
        """Extract alpha channel as grayscale image."""
        return image.convert('RGBA').split()[3]


# =============================================================================
# EXACT CARD COMPOSITOR
# =============================================================================

@dataclass
class LayerSpec:
    """Specification for a single layer to composite."""
    layer_type: LayerType
    image: Image.Image
    formula: LayerFormula
    apply_mask: bool = False
    mask_image: Optional[Image.Image] = None


class ExactCardCompositor:
    """
    Pixel-perfect card compositor using formula-based positioning.
    
    All positions are calculated from Figma-derived formulas,
    ensuring exact proportional relationships at any scale.
    """
    
    def __init__(self, canvas_width: int, canvas_height: int):
        """
        Initialize compositor with target canvas dimensions.
        
        Args:
            canvas_width: Target output width in pixels
            canvas_height: Target output height in pixels
        """
        self.canvas_width = canvas_width
        self.canvas_height = canvas_height
        self.canvas_size = (canvas_width, canvas_height)
        
        # Pre-calculate all layer positions
        self._positions: Dict[LayerType, LayerPosition] = {}
        self._precalculate_positions()
    
    def _precalculate_positions(self) -> None:
        """Pre-calculate fixed layer positions."""
        formulas = CardLayerFormulas
        
        self._positions[LayerType.BASE_SHAPE] = formulas.BASE_SHAPE.calculate(
            self.canvas_width, self.canvas_height
        )
        self._positions[LayerType.BORDER] = formulas.BORDER.calculate(
            self.canvas_width, self.canvas_height
        )
        self._positions[LayerType.CHARACTER] = formulas.CHARACTER.calculate(
            self.canvas_width, self.canvas_height
        )
    
    def get_position(self, layer_type: LayerType, 
                     content_size: Optional[Tuple[int, int]] = None) -> LayerPosition:
        """
        Get the exact position for a layer type.
        
        Args:
            layer_type: The type of layer
            content_size: (width, height) for dynamically-sized layers
        """
        # Return pre-calculated if available
        if layer_type in self._positions and content_size is None:
            return self._positions[layer_type]
        
        # Calculate dynamic positions
        formula_map = {
            LayerType.BLACK_BORDER: CardLayerFormulas.BLACK_BORDER,
            LayerType.BASE_SHAPE: CardLayerFormulas.BASE_SHAPE,
            LayerType.CHARACTER: CardLayerFormulas.CHARACTER,
            LayerType.BORDER: CardLayerFormulas.BORDER,
            LayerType.PIP: CardLayerFormulas.PIP,
            LayerType.CALLING: CardLayerFormulas.CALLING,
        }
        
        formula = formula_map.get(layer_type)
        if not formula:
            raise ValueError(f"Unknown layer type: {layer_type}")
        
        content_w, content_h = content_size if content_size else (None, None)
        return formula.calculate(
            self.canvas_width, self.canvas_height,
            content_width=content_w, content_height=content_h
        )
    
    def composite_layer(self, canvas: Image.Image, layer_image: Image.Image,
                        position: LayerPosition) -> Image.Image:
        """
        Composite a single layer onto the canvas.
        
        Args:
            canvas: Current canvas state
            layer_image: Image to composite
            position: Exact pixel position
            
        Returns:
            New canvas with layer composited
        """
        # Validate integer coordinates
        assert isinstance(position.x, int), f"Non-integer x: {position.x}"
        assert isinstance(position.y, int), f"Non-integer y: {position.y}"
        
        # Create temporary layer at full canvas size
        temp = Image.new('RGBA', self.canvas_size, (0, 0, 0, 0))
        temp.paste(layer_image, position.origin, layer_image)
        
        # Alpha composite
        return Image.alpha_composite(canvas, temp)
    
    def composite_card(self, layers: List[LayerSpec]) -> Image.Image:
        """
        Composite all layers into final card image.
        
        Args:
            layers: List of LayerSpec in z-order (bottom to top)
            
        Returns:
            Final composited card image
        """
        # Sort by z-order
        sorted_layers = sorted(layers, key=lambda l: l.layer_type.value)
        
        # Start with transparent canvas
        canvas = Image.new('RGBA', self.canvas_size, (0, 0, 0, 0))
        
        for spec in sorted_layers:
            # Apply mask if needed
            image = spec.image
            if spec.apply_mask and spec.mask_image:
                image = ExactMask.apply(image, spec.mask_image)
            
            # Get position
            position = self.get_position(spec.layer_type, image.size)
            
            # Resize if needed to match position dimensions
            if position.width > 0 and position.height > 0:
                if image.size != position.size:
                    image = ExactImageLoader.resize_exact(image, position.size)
            
            # Composite
            canvas = self.composite_layer(canvas, image, position)
        
        return canvas


# =============================================================================
# HIGH-LEVEL CARD BUILDER
# =============================================================================

class ExactCardBuilder:
    """
    High-level interface for building cards with exact positioning.
    
    Usage:
        builder = ExactCardBuilder(width=1123, height=2000)
        card = builder.build(
            character_path=Path("character.png"),
            border_path=Path("border.png"),
            base_shape_path=Path("base_shape.png"),
        )
    """
    
    def __init__(self, width: int = 1123, height: int = 2000):
        """
        Initialize builder with target dimensions.
        
        Default dimensions maintain the Figma aspect ratio.
        """
        self.width = width
        self.height = height
        self.compositor = ExactCardCompositor(width, height)
        self.loader = ExactImageLoader()
    
    def build(self,
              character_path: Path,
              border_path: Path,
              base_shape_path: Path,
              black_border_path: Optional[Path] = None,
              pip_path: Optional[Path] = None,
              calling_path: Optional[Path] = None) -> Image.Image:
        """
        Build a complete card with all layers.
        
        Args:
            character_path: Path to character artwork
            border_path: Path to decorative border
            base_shape_path: Path to base shape (mask)
            black_border_path: Optional outer stroke
            pip_path: Optional rarity stars
            calling_path: Optional class icon
            
        Returns:
            Final composited card image
        """
        layers: List[LayerSpec] = []
        
        # Load base shape (used as mask for character)
        base_shape = self.loader.load(base_shape_path)
        base_shape = ExactImageLoader.resize_exact(base_shape, (self.width, self.height))
        
        # Layer 1: Black border (if provided)
        if black_border_path and black_border_path.exists():
            black_border = self.loader.load(black_border_path)
            layers.append(LayerSpec(
                layer_type=LayerType.BLACK_BORDER,
                image=black_border,
                formula=CardLayerFormulas.BLACK_BORDER,
            ))
        
        # Layer 2: Character (masked to base shape)
        character = self.loader.load(character_path)
        character = self._fit_character(character, base_shape)
        layers.append(LayerSpec(
            layer_type=LayerType.CHARACTER,
            image=character,
            formula=CardLayerFormulas.CHARACTER,
            apply_mask=True,
            mask_image=base_shape,
        ))
        
        # Layer 3: Border
        border = self.loader.load(border_path)
        # Calculate expected border size from formula
        border_pos = self.compositor.get_position(LayerType.BORDER)
        border = ExactImageLoader.resize_exact(border, border_pos.size)
        layers.append(LayerSpec(
            layer_type=LayerType.BORDER,
            image=border,
            formula=CardLayerFormulas.BORDER,
        ))
        
        # Layer 4: Pip (if provided)
        if pip_path and pip_path.exists():
            pip = self.loader.load(pip_path)
            # Scale pip to appropriate size (25% of canvas width)
            pip_width = int(self.width * 0.25)
            pip_scale = pip_width / pip.width
            pip_height = int(pip.height * pip_scale)
            pip = ExactImageLoader.resize_exact(pip, (pip_width, pip_height))
            layers.append(LayerSpec(
                layer_type=LayerType.PIP,
                image=pip,
                formula=CardLayerFormulas.PIP,
            ))
        
        # Layer 5: Calling icon (if provided)
        if calling_path and calling_path.exists():
            calling = self.loader.load(calling_path)
            # Scale calling to appropriate size (12% of canvas width)
            calling_width = int(self.width * 0.12)
            calling_scale = calling_width / calling.width
            calling_height = int(calling.height * calling_scale)
            calling = ExactImageLoader.resize_exact(calling, (calling_width, calling_height))
            layers.append(LayerSpec(
                layer_type=LayerType.CALLING,
                image=calling,
                formula=CardLayerFormulas.CALLING,
            ))
        
        return self.compositor.composite_card(layers)
    
    def _fit_character(self, character: Image.Image, 
                       base_shape: Image.Image) -> Image.Image:
        """
        Fit character image to canvas using cover fit.
        
        Scales to cover entire canvas, crops to fit, biased toward top.
        """
        target_w, target_h = self.width, self.height
        img_w, img_h = character.size
        
        # Calculate scale to cover
        scale = max(target_w / img_w, target_h / img_h)
        
        # Scale image
        new_w = int(img_w * scale)
        new_h = int(img_h * scale)
        scaled = ExactImageLoader.resize_exact(character, (new_w, new_h))
        
        # Crop (center horizontally, bias toward top vertically)
        left = (new_w - target_w) // 2
        top = int((new_h - target_h) * 0.3)  # 30% from top for character framing
        top = max(0, min(top, new_h - target_h))
        
        return scaled.crop((left, top, left + target_w, top + target_h))


# =============================================================================
# FORMULA DOCUMENTATION & VALIDATION
# =============================================================================

def print_formula_report(target_width: int = 1123, target_height: int = 2000) -> None:
    """Print a detailed report of all layer formulas and their calculated positions."""
    
    print("=" * 70)
    print("CARD LAYER FORMULA REPORT")
    print("=" * 70)
    print(f"\nFigma Source: {FIGMA.FRAME_WIDTH} × {FIGMA.FRAME_HEIGHT} px")
    print(f"Target Output: {target_width} × {target_height} px")
    print(f"Scale Factor: {target_width / FIGMA.FRAME_WIDTH:.4f}")
    print()
    
    compositor = ExactCardCompositor(target_width, target_height)
    
    layers = [
        ("BASE_SHAPE", LayerType.BASE_SHAPE, None),
        ("BORDER", LayerType.BORDER, None),
        ("CHARACTER", LayerType.CHARACTER, None),
        ("PIP (280×100)", LayerType.PIP, (280, 100)),
        ("CALLING (135×135)", LayerType.CALLING, (135, 135)),
    ]
    
    print(f"{'Layer':<20} {'Position (x,y)':<20} {'Size (w×h)':<20}")
    print("-" * 60)
    
    for name, layer_type, content_size in layers:
        pos = compositor.get_position(layer_type, content_size)
        print(f"{name:<20} ({pos.x:>4}, {pos.y:>4})       {pos.width:>4} × {pos.height:<4}")
    
    print()
    print("Border Inset Verification:")
    border_pos = compositor.get_position(LayerType.BORDER)
    print(f"  Left inset:  {border_pos.x} px")
    print(f"  Right inset: {target_width - border_pos.x - border_pos.width} px")
    print(f"  Expected:    {int(FIGMA.BORDER_X / FIGMA.FRAME_WIDTH * target_width)} px (from Figma ratio)")
    print()


def validate_formulas() -> bool:
    """Validate that formulas produce correct positions at Figma's original size."""
    
    compositor = ExactCardCompositor(FIGMA.FRAME_WIDTH, FIGMA.FRAME_HEIGHT)
    
    # Check base shape
    base_pos = compositor.get_position(LayerType.BASE_SHAPE)
    assert base_pos.x == FIGMA.BASE_SHAPE_X, f"Base X mismatch: {base_pos.x} != {FIGMA.BASE_SHAPE_X}"
    assert base_pos.y == FIGMA.BASE_SHAPE_Y, f"Base Y mismatch: {base_pos.y} != {FIGMA.BASE_SHAPE_Y}"
    
    # Check border
    border_pos = compositor.get_position(LayerType.BORDER)
    assert border_pos.x == FIGMA.BORDER_X, f"Border X mismatch: {border_pos.x} != {FIGMA.BORDER_X}"
    assert border_pos.y == FIGMA.BORDER_Y, f"Border Y mismatch: {border_pos.y} != {FIGMA.BORDER_Y}"
    
    print("✓ All formula validations passed!")
    return True


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    # Validate formulas match Figma exactly
    validate_formulas()
    
    # Print report for default target size
    print_formula_report(1123, 2000)
    
    # Print report for Figma original size
    print_formula_report(FIGMA.FRAME_WIDTH, FIGMA.FRAME_HEIGHT)
