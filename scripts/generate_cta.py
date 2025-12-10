#!/usr/bin/env python3
"""
CTA Button Generator (PIL-Based)
=================================
Generates Primary and Secondary CTA buttons using PIL for text rendering
and optional Google Gemini API for color variations.

Based on Figma Design Specs:
- Frame: "Secondary CTA" (node 9048:232)
- Font: Cinzel SemiBold, 100px
- Text Color: White (#FFFFFF)
- Alignment: Centered (px-220, py-34)

Usage:
    python generate_cta_pil.py --type primary --text "LEVEL UP"
    python generate_cta_pil.py --type secondary --text "CANCEL"
    python generate_cta_pil.py --type primary --text "START" --color gold
"""

import os
import argparse
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, Tuple
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance

# =============================================================================
# FIGMA SOURCE OF TRUTH
# =============================================================================

@dataclass(frozen=True)
class FigmaSpec:
    """
    Immutable Figma design specifications for CTA buttons.
    Extracted from Figma node 9048:232 (Secondary CTA).
    """
    # Typography
    FONT_FAMILY: str = "Cinzel"
    FONT_WEIGHT: str = "SemiBold"
    FONT_SIZE: int = 100  # pixels
    TEXT_COLOR: Tuple[int, int, int, int] = (255, 255, 255, 255)  # White RGBA
    
    # Text styling
    LETTER_SPACING: float = 0.05  # 5% of character width (tracking)
    TEXT_TRANSFORM: str = "uppercase"
    
    # Padding specifications
    PADDING_X_MAX: int = 125  # max horizontal padding
    PADDING_Y: int = 36       # fixed vertical padding
    
    # Frame dimensions
    SECONDARY_WIDTH: int = 871
    SECONDARY_HEIGHT: int = 204
    PRIMARY_WIDTH: int = 940
    PRIMARY_HEIGHT: int = 207


FIGMA = FigmaSpec()


# =============================================================================
# CONFIGURATION
# =============================================================================

@dataclass
class CTAConfig:
    """Configuration for a CTA button type."""
    name: str
    filename: str
    width: int
    height: int
    description: str
    default_color: str
    has_embellishments: bool
    
    # Calculated text area
    @property
    def text_area_width(self) -> int:
        return self.width - (2 * FIGMA.PADDING_X_MAX)
    
    @property
    def text_area_height(self) -> int:
        return self.height - (2 * FIGMA.PADDING_Y)


CTA_TYPES = {
    "primary": CTAConfig(
        name="primary",
        filename="PrimaryCTA.png",
        width=FIGMA.PRIMARY_WIDTH,
        height=FIGMA.PRIMARY_HEIGHT,
        description="Blue button with inner border embellishments and diamond accents",
        default_color="deep royal blue (#1a237e to #283593)",
        has_embellishments=True,
    ),
    "secondary": CTAConfig(
        name="secondary",
        filename="SecondaryCTA.png",
        width=FIGMA.SECONDARY_WIDTH,
        height=FIGMA.SECONDARY_HEIGHT,
        description="Dark gray/charcoal button with simple border",
        default_color="dark charcoal gray (#2d2d3a to #1a1a24)",
        has_embellishments=False,
    ),
}


# =============================================================================
# PATH RESOLVER
# =============================================================================

class PathResolver:
    """Resolves asset and output paths."""
    
    def __init__(self, base_dir: Optional[str] = None):
        if base_dir is None:
            # Go up one level from scripts/ to project root
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.base_dir = Path(base_dir)
        self.assets_dir = self.base_dir / "assets" / "ctaref"
        self.fonts_dir = self.base_dir / "fonts"
        self.output_dir = self.base_dir / "output" / "cta"
        
    def get_button_frame(self, config: CTAConfig) -> Path:
        """Get path to button frame image."""
        return self.assets_dir / config.filename
    
    def get_font(self, weight: str = "SemiBold") -> Path:
        """Get path to Cinzel font file, with fallback to system fonts."""
        # Try Cinzel first
        cinzel_path = self.fonts_dir / f"Cinzel-{weight}.ttf"
        if cinzel_path.exists():
            return cinzel_path
        
        # Fallback to system serif fonts (similar aesthetic)
        fallbacks = [
            Path("/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"),
            Path("/usr/share/fonts/truetype/freefont/FreeSerifBold.ttf"),
            Path("/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf"),
        ]
        
        for font_path in fallbacks:
            if font_path.exists():
                return font_path
        
        # Last resort - any available font
        import subprocess
        result = subprocess.run(['fc-match', '-f', '%{file}', 'serif:bold'], 
                                capture_output=True, text=True)
        if result.returncode == 0 and result.stdout.strip():
            return Path(result.stdout.strip())
        
        raise FileNotFoundError("No suitable font found")
    
    def get_output_path(self, button_type: str, text: str, color: Optional[str] = None) -> Path:
        """Generate output path for the CTA button."""
        text_clean = text.upper().replace(" ", "_")
        type_prefix = button_type.upper()
        color_suffix = f"_{color.upper()}" if color else ""
        filename = f"CTA_{type_prefix}_{text_clean}{color_suffix}.png"
        return self.output_dir / filename


# =============================================================================
# EXACT IMAGE LOADER
# =============================================================================

class ExactImageLoader:
    """Loads images with consistent settings."""
    
    @staticmethod
    def load(path: Path, mode: str = 'RGBA') -> Image.Image:
        """Load image ensuring consistent mode."""
        if not path.exists():
            raise FileNotFoundError(f"Asset not found: {path}")
        img = Image.open(path)
        if img.mode != mode:
            img = img.convert(mode)
        return img


# =============================================================================
# TEXT RENDERER (PIL-Based)
# =============================================================================

class CTATextRenderer:
    """
    Renders text onto CTA buttons using PIL with exact CSS specifications:
    - font-family: Cinzel
    - font-size: 100px
    - font-weight: 600 (SemiBold)
    - color: #FFF
    - line-height: normal (no custom spacing)
    """
    
    def __init__(self, font_path: Path):
        self.font_path = font_path
        if not font_path.exists():
            print(f"  ⚠ Primary font not found: {font_path}")
            print(f"    Using fallback font")
        print(f"  ✓ Font: {font_path}")
    
    def get_fixed_font_size(self) -> int:
        """
        Return the fixed font size - no scaling.
        Font size is always 100px as per CSS spec.
        """
        return FIGMA.FONT_SIZE  # Always 100px
    
    def render_text_layer(self, text: str, canvas_size: Tuple[int, int], 
                          font_size: int) -> Image.Image:
        """
        Render text as a transparent layer with exact centering.
        
        Uses PIL's anchor-based centering for clean, simple text rendering
        matching the CSS specs (no custom letter spacing, normal line-height).
        """
        width, height = canvas_size
        
        # Create transparent layer
        layer = Image.new('RGBA', canvas_size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(layer)
        
        # Load font at specified size
        font = ImageFont.truetype(str(self.font_path), font_size)
        
        # Calculate center position
        center_x = width // 2
        center_y = height // 2
        
        # Draw text centered using anchor (mm = middle-middle)
        # This uses PIL's built-in centering which matches CSS text-align: center
        draw.text(
            (center_x, center_y), 
            text, 
            font=font, 
            fill=FIGMA.TEXT_COLOR,
            anchor="mm"  # middle-middle anchor for perfect centering
        )
        
        return layer
    
    def add_text_effects(self, text_layer: Image.Image) -> Image.Image:
        """
        No effects - clean text per CSS spec.
        """
        return text_layer


# =============================================================================
# CTA BUTTON COMPOSITOR
# =============================================================================

class CTACompositor:
    """
    Composites CTA button layers using exact positioning.
    
    Layer stack (bottom to top):
    1. Button frame (background texture)
    2. Text layer (centered white text)
    """
    
    def __init__(self, resolver: PathResolver):
        self.resolver = resolver
        self.loader = ExactImageLoader()
        self.text_renderer = CTATextRenderer(resolver.get_font())
    
    def composite(self, config: CTAConfig, text: str) -> Image.Image:
        """
        Composite a complete CTA button with text.
        
        Args:
            config: CTA button configuration
            text: Text to display (will be uppercased)
            
        Returns:
            Final composited button image
        """
        # Uppercase the text per Figma spec
        text = text.upper()
        
        # Load button frame
        frame_path = self.resolver.get_button_frame(config)
        frame = self.loader.load(frame_path)
        
        print(f"  ✓ Loaded frame: {frame_path.name} ({frame.size[0]}x{frame.size[1]})")
        
        # Fixed padding values
        print(f"  ✓ Padding: H={FIGMA.PADDING_X_MAX}px (max), V={FIGMA.PADDING_Y}px (fixed)")
        
        # Use FIXED font size - no scaling
        font_size = self.text_renderer.get_fixed_font_size()
        print(f"  ✓ Font size: {font_size}px (FIXED)")
        
        # Render text layer at full canvas size
        text_layer = self.text_renderer.render_text_layer(
            text, 
            frame.size, 
            font_size
        )
        
        # Apply any text effects
        text_layer = self.text_renderer.add_text_effects(text_layer)
        
        # Composite: frame + text
        result = Image.alpha_composite(frame, text_layer)
        
        return result


# =============================================================================
# COLOR RECOLORIZER (AI-Based, Optional)
# =============================================================================

class ColorRecolorizer:
    """
    Handles color changes using Google Gemini API.
    Only used when --color flag is specified.
    """
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self._client = None
    
    @property
    def client(self):
        if self._client is None:
            from google import genai
            self._client = genai.Client(api_key=self.api_key)
        return self._client
    
    def recolor(self, image: Image.Image, target_color: str, 
                button_type: str) -> Image.Image:
        """
        Recolor a button using AI while preserving texture.
        """
        from google.genai import types
        
        prompt = f"""
Recolor this {button_type} CTA button to {target_color}.

CRITICAL REQUIREMENTS:
1. ONLY change the main button surface color to {target_color}
2. PRESERVE the exact texture, grain, and weathered appearance
3. PRESERVE all edge details, borders, and frame elements
4. PRESERVE the text exactly as it appears (white color, same position)
5. PRESERVE any embellishments or decorative elements
6. The lighting and shadows should adjust naturally to the new color
7. Do NOT smooth, clean, or modernize any textures
8. The output should have a TRANSPARENT or WHITE background

The result should look like the same button, just with a different color scheme.
"""
        
        print(f"  → Sending recolor request to Gemini API...")
        
        response = self.client.models.generate_content(
            model="gemini-3-pro-image-preview",
            contents=[prompt, image],
            config=types.GenerateContentConfig(
                response_modalities=['TEXT', 'IMAGE'],  # Need BOTH modalities
            )
        )
        
        # Extract image from response
        for part in response.parts:
            try:
                result_image = part.as_image()
                if result_image:
                    print(f"  ✓ Recolor complete")
                    return result_image
            except:
                pass
        
        print(f"  ⚠ Recolor failed, returning original")
        return image


# =============================================================================
# MAIN CTA GENERATOR
# =============================================================================

class CTAGenerator:
    """
    Main CTA button generator.
    
    Uses PIL for text rendering (fast, consistent)
    Uses AI only for color changes (optional)
    """
    
    def __init__(self, base_dir: Optional[str] = None, api_key: Optional[str] = None):
        self.resolver = PathResolver(base_dir)
        self.compositor = CTACompositor(self.resolver)
        self.recolorizer = ColorRecolorizer(api_key) if api_key else None
    
    def generate(self, button_type: str, text: str, 
                 color: Optional[str] = None,
                 output_name: Optional[str] = None) -> Optional[Path]:
        """
        Generate a CTA button.
        
        Args:
            button_type: "primary" or "secondary"
            text: Button text
            color: Optional color override (triggers AI recoloring)
            output_name: Optional custom output filename
            
        Returns:
            Path to generated button image
        """
        print(f"\n{'='*60}")
        print(f"CTA BUTTON GENERATOR (PIL)")
        print(f"{'='*60}")
        print(f"  Type: {button_type.upper()}")
        print(f"  Text: \"{text.upper()}\"")
        if color:
            print(f"  Color: {color}")
        print(f"{'='*60}\n")
        
        # Validate button type
        if button_type.lower() not in CTA_TYPES:
            available = ", ".join(CTA_TYPES.keys())
            raise ValueError(f"Unknown button type '{button_type}'. Available: {available}")
        
        config = CTA_TYPES[button_type.lower()]
        
        # Step 1: Composite button with text (PIL)
        print("Step 1: Compositing button with text...")
        result = self.compositor.composite(config, text)
        
        # Step 2: Recolor if requested (AI)
        if color:
            print(f"\nStep 2: Recoloring to {color}...")
            if self.recolorizer:
                result = self.recolorizer.recolor(result, color, button_type)
            else:
                print("  ⚠ No API key provided, skipping recolor")
        
        # Step 3: Save output
        print("\nStep 3: Saving output...")
        self.resolver.output_dir.mkdir(parents=True, exist_ok=True)
        
        if output_name:
            output_path = self.resolver.output_dir / f"{output_name}.png"
        else:
            output_path = self.resolver.get_output_path(button_type, text, color)
        # Handle different image types (PIL vs Gemini SDK)
        if hasattr(result, 'save') and callable(result.save):
            try:
                # Try PIL-style save first
                result.save(output_path, "PNG")
            except TypeError:
                # Fall back to Gemini SDK style save (takes only path)
                result.save(str(output_path))
        
        print(f"\n{'='*60}")
        print(f"✓ SUCCESS: {output_path}")
        # Handle different image types for size info
        try:
            print(f"  Size: {result.size[0]}x{result.size[1]}px")
        except (AttributeError, TypeError):
            print(f"  (Image saved)")
        print(f"{'='*60}\n")
        
        return output_path
    
    def list_available(self):
        """Print available button types."""
        print("\n" + "=" * 60)
        print("AVAILABLE CTA BUTTON TYPES")
        print("=" * 60)
        
        for type_name, config in CTA_TYPES.items():
            print(f"\n{type_name.upper()}:")
            print(f"  Dimensions: {config.width}x{config.height}px")
            print(f"  Text Area: {config.text_area_width}x{config.text_area_height}px")
            print(f"  Description: {config.description}")
            print(f"  Embellishments: {'Yes' if config.has_embellishments else 'No'}")
        
        print("\n" + "-" * 60)
        print("TYPOGRAPHY (from Figma):")
        print(f"  Font: {FIGMA.FONT_FAMILY} {FIGMA.FONT_WEIGHT}")
        print(f"  Base Size: {FIGMA.FONT_SIZE}px")
        print(f"  Color: White (#FFFFFF)")
        print(f"  Letter Spacing: {FIGMA.LETTER_SPACING * 100}%")
        print("=" * 60 + "\n")


# =============================================================================
# CLI
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Generate CTA buttons using PIL with optional AI recoloring.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python generate_cta_pil.py --type primary --text "LEVEL UP"
  python generate_cta_pil.py --type secondary --text "CANCEL"
  python generate_cta_pil.py --type primary --text "START" --color gold
  python generate_cta_pil.py --list
        """
    )
    
    parser.add_argument("--type", "-t", choices=["primary", "secondary"],
                        help="Button type")
    parser.add_argument("--text", "-x", help="Button text")
    parser.add_argument("--color", "-c", help="Color override (uses AI)")
    parser.add_argument("--output", "-o", help="Custom output filename")
    parser.add_argument("--list", "-l", action="store_true", 
                        help="List available options")
    
    args = parser.parse_args()
    
    # Get API key for recoloring (optional)
    api_key = os.getenv("GOOGLE_API_KEY")
    
    generator = CTAGenerator(api_key=api_key)
    
    if args.list:
        generator.list_available()
    elif args.type and args.text:
        generator.generate(
            button_type=args.type,
            text=args.text,
            color=args.color,
            output_name=args.output
        )
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
