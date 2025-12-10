#!/usr/bin/env python3
"""
CTA Button Generator
====================
Generates Primary and Secondary CTA buttons using Google's Gemini 
image generation API with extreme consistency.

Called by the CTA Button Droid (see droids/cta-button-droid.md)

Usage:
    python generate_cta.py --type primary --text "LEVEL UP"
    python generate_cta.py --type secondary --text "CANCEL" --color purple
    python generate_cta.py --list
"""

import os
import argparse
from PIL import Image
from google import genai
from google.genai import types
from dotenv import load_dotenv

# =============================================================================
# SETUP
# =============================================================================

load_dotenv()
API_KEY = os.getenv("GOOGLE_API_KEY")
if not API_KEY:
    raise ValueError("GOOGLE_API_KEY not found in .env file")

MODEL_ID = "gemini-3-pro-image-preview"

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS_DIR = os.path.join(BASE_DIR, "assets", "ctaref")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")

# =============================================================================
# REGISTRY: CTA Button Types
# =============================================================================

CTA_TYPES = {
    "primary": {
        "filename": "PrimaryCTA.png",
        "description": "Blue button with inner border embellishments and diamond accents",
        "default_color": "deep royal blue (#1a237e to #283593 gradient appearance)",
        "has_embellishments": True,
    },
    "secondary": {
        "filename": "SecondaryCTA.png",
        "description": "Dark gray/charcoal button with simple border",
        "default_color": "dark charcoal gray (#2d2d3a to #1a1a24)",
        "has_embellishments": False,
    },
}

FONT_REFERENCE = "ButtonFontRef.png"


# =============================================================================
# PROMPT ENGINEERING
# =============================================================================

def build_generation_prompt(button_type: str, text: str, width: int, height: int, color: str = None) -> str:
    """
    Build an extremely explicit prompt for consistent CTA button generation.
    
    This prompt is engineered for maximum consistency by:
    1. Defining exact typography specifications
    2. Specifying precise alignment rules
    3. Referencing the gold standard images explicitly
    4. Detailing texture preservation requirements
    """
    
    config = CTA_TYPES[button_type]
    
    # Determine color to use
    if color:
        color_instruction = f"""
COLOR OVERRIDE:
- Replace the original button color with: {color}
- Maintain the same texture, gradients, and lighting as the original
- The color change should only affect the main button surface, NOT the border/frame
- Keep the weathered, textured appearance - just shift the hue to {color}
"""
    else:
        color_instruction = f"""
COLOR REQUIREMENT:
- Use EXACTLY the original color from the reference: {config['default_color']}
- Do NOT alter, brighten, darken, or shift the color in any way
- The final button must be indistinguishable in color from the reference
"""
    
    # Embellishment instructions based on button type
    if config["has_embellishments"]:
        embellishment_instruction = """
EMBELLISHMENTS (CRITICAL - PRIMARY CTA ONLY):
- The inner decorative border lines MUST be preserved exactly
- The small diamond accents at the corners and center MUST be included
- The thin inner border that follows the button shape MUST be present
- These embellishments are part of the brand identity - do not omit them
"""
    else:
        embellishment_instruction = """
SIMPLICITY (SECONDARY CTA):
- This button has NO inner embellishments - keep it clean
- Only the outer weathered border/frame should be visible
- Do not add any decorative elements not present in the reference
"""
    
    prompt = f"""
=== CTA BUTTON GENERATION TASK ===

You are generating a {button_type.upper()} CTA button for a game UI.
You will receive THREE reference images:
1. IMAGE 1: The button frame template (use this EXACTLY)
2. IMAGE 2: Font style reference showing "CANCEL" and "LEVEL UP" examples
3. IMAGE 3: The same button frame (backup reference)

=== ABSOLUTE REQUIREMENTS ===

BUTTON TEXT: "{text}"

TYPOGRAPHY SPECIFICATIONS (MATCH THE FONT REFERENCE EXACTLY):
- Font Family: Cinzel (elegant serif font with classical proportions)
- Font Weight: Semi Bold
- Font Color: Pure white (#FFFFFF)
- Text Style: ALL UPPERCASE
- Letter Spacing: Slightly expanded tracking (approximately 5-10% of character width)

TEXT POSITIONING (CRITICAL FOR CONSISTENCY):
- Horizontal Alignment: PERFECTLY CENTERED on the button's horizontal axis
- Vertical Alignment: PERFECTLY CENTERED on the button's vertical axis
- The text baseline should sit at exactly 50% of the button height
- Equal padding on left and right sides
- The text should occupy approximately 60-70% of the button's inner width
- The text height should be approximately 35-45% of the button's inner height

TEXT SIZING RULES:
- For short text (1-6 characters): Use larger font size (45% of button height)
- For medium text (7-12 characters): Use standard font size (40% of button height)  
- For long text (13+ characters): Use smaller font size (32% of button height)
- The text must NEVER touch or overflow the button edges
- Minimum padding from edges: 15% of button width on each side

{color_instruction}

FRAME/STRUCTURE PRESERVATION (CRITICAL):
- The button shape is a horizontally-oriented hexagon (elongated with angled ends)
- The weathered stone/metal texture MUST be preserved exactly
- The cracked, aged appearance of the border MUST remain intact
- The subtle surface variations and imperfections MUST be maintained
- Do NOT smooth out, clean up, or modernize the texture

{embellishment_instruction}

TEXTURE DETAILS TO PRESERVE:
- The granular, slightly rough surface texture
- The subtle color variations within the button surface
- The worn edges and slight imperfections
- Any cracks, chips, or weathering marks
- The border's metallic/stone appearance with patina

OUTPUT SPECIFICATIONS:
- The final image should show ONLY the button with text
- Background: Transparent (or solid gray #808080 if transparency not possible)
- The button should be centered in the output image
- Output should match the aspect ratio of the input button frame
- High resolution, sharp text edges (no blur or anti-aliasing artifacts)
- Target Resolution: {width}x{height} pixels
- Aspect Ratio: {width/height:.2f}:1 (Must match input frame exactly)

=== QUALITY CHECKLIST ===
Before finalizing, verify:
✓ Text is perfectly horizontally centered
✓ Text is perfectly vertically centered  
✓ Text uses Cinzel font style matching the reference
✓ Text is white with subtle texture
✓ Button frame is identical to reference (shape, texture, weathering)
✓ All embellishments present (if primary CTA)
✓ Color matches specification exactly
✓ No unwanted artifacts or modifications

Generate the button now with "{text}" as the text content.
The background must be white.
"""
    
    return prompt.strip()


# =============================================================================
# CORE GENERATION FUNCTION
# =============================================================================

def load_image(filename: str) -> Image.Image:
    """Load an image from the assets directory."""
    path = os.path.join(ASSETS_DIR, filename)
    if not os.path.exists(path):
        raise FileNotFoundError(f"Asset not found: {path}")
    return Image.open(path)


def generate_cta(button_type: str, text: str, color: str = None, output_name: str = None) -> str:
    """
    Generate a CTA button with the specified parameters.
    
    Args:
        button_type: "primary" or "secondary"
        text: The text to display on the button
        color: Optional color override
        output_name: Optional custom output filename (without extension)
    
    Returns:
        Path to the generated image, or None if generation failed
    """
    print(f"{'='*60}")
    print(f"GENERATING {button_type.upper()} CTA BUTTON")
    print(f"{'='*60}")
    print(f"Text: {text}")
    print(f"Color: {color if color else 'Default'}")
    
    # Validate button type
    if button_type.lower() not in CTA_TYPES:
        available = ", ".join(CTA_TYPES.keys())
        raise ValueError(f"Unknown button type '{button_type}'. Available: {available}")
    
    config = CTA_TYPES[button_type.lower()]
    
    # Load reference images
    print(f"\nLoading reference images...")
    
    try:
        button_frame = load_image(config["filename"])
        print(f"  ✓ Button frame: {config['filename']}")
    except FileNotFoundError as e:
        print(f"  ✗ {e}")
        raise
    
    # Get dimensions from the button frame
    width, height = button_frame.size
    print(f"  ✓ Reference dimensions: {width}x{height} (Aspect Ratio: {width/height:.2f}:1)")
    
    try:
        font_ref = load_image(FONT_REFERENCE)
        print(f"  ✓ Font reference: {FONT_REFERENCE}")
    except FileNotFoundError as e:
        print(f"  ✗ {e}")
        raise
    
    # Initialize client
    client = genai.Client(api_key=API_KEY)
    
    # Build the prompt
    # Build the prompt
    prompt = build_generation_prompt(button_type, text, width, height, color)
    
    # Build content list
    contents = [
        prompt,
        button_frame,   # IMAGE 1: Button frame template
        font_ref,       # IMAGE 2: Font style reference
        button_frame,   # IMAGE 3: Backup reference for emphasis
    ]
    
    print(f"\nSending request to {MODEL_ID}...")
    print(f"Prompt length: {len(prompt)} characters")
    
    try:
        response = client.models.generate_content(
            model=MODEL_ID,
            contents=contents,
            config=types.GenerateContentConfig(
                response_modalities=['TEXT', 'IMAGE'],
                system_instruction=(
                    "You are an expert UI artist specializing in game interface design. "
                    "You have perfect typography skills and can match font styles exactly. "
                    "You never deviate from reference materials - consistency is your top priority. "
                    "You understand that CTA buttons must have perfectly centered, readable text. "
                    "You preserve textures and weathered effects while adding new elements."
                ),
                image_config=types.ImageConfig(
                ),
            )
        )
        
        # Process response
        image_saved = False
        output_path = None
        
        if response.parts:
            for part in response.parts:
                if part.text:
                    print(f"\nModel Response: {part.text[:200]}...")
                
                # Try to extract image
                try:
                    image = part.as_image()
                    if image:
                        os.makedirs(OUTPUT_DIR, exist_ok=True)
                        
                        # Generate filename
                        if output_name:
                            filename = f"{output_name}.png"
                        else:
                            text_clean = text.upper().replace(" ", "_")
                            type_prefix = "PRIMARY" if button_type == "primary" else "SECONDARY"
                            color_suffix = f"_{color.upper()}" if color else ""
                            filename = f"CTA_{type_prefix}_{text_clean}{color_suffix}.png"
                        
                        output_path = os.path.join(OUTPUT_DIR, filename)
                        image.save(output_path)
                        print(f"\n{'='*60}")
                        print(f"SUCCESS: Saved to {output_path}")
                        print(f"{'='*60}")
                        image_saved = True
                        return output_path
                        
                except AttributeError:
                    # Fallback for different SDK versions
                    if hasattr(part, 'inline_data') and part.inline_data:
                        import io
                        image_data = part.inline_data.data
                        image = Image.open(io.BytesIO(image_data))
                        
                        os.makedirs(OUTPUT_DIR, exist_ok=True)
                        
                        if output_name:
                            filename = f"{output_name}.png"
                        else:
                            text_clean = text.upper().replace(" ", "_")
                            type_prefix = "PRIMARY" if button_type == "primary" else "SECONDARY"
                            color_suffix = f"_{color.upper()}" if color else ""
                            filename = f"CTA_{type_prefix}_{text_clean}{color_suffix}.png"
                        
                        output_path = os.path.join(OUTPUT_DIR, filename)
                        image.save(output_path)
                        print(f"\n{'='*60}")
                        print(f"SUCCESS: Saved to {output_path}")
                        print(f"{'='*60}")
                        image_saved = True
                        return output_path
        
        if not image_saved:
            print("\nFAILED: No image returned from API.")
            return None
            
    except Exception as e:
        print(f"\nERROR: {e}")
        raise


def list_available():
    """Print available button types and options."""
    print("\n" + "=" * 60)
    print("AVAILABLE CTA BUTTON TYPES")
    print("=" * 60)
    
    for type_name, config in CTA_TYPES.items():
        print(f"\n{type_name.upper()}:")
        print(f"  Description: {config['description']}")
        print(f"  Default Color: {config['default_color']}")
        print(f"  Has Embellishments: {'Yes' if config['has_embellishments'] else 'No'}")
    
    print("\n" + "-" * 60)
    print("SUPPORTED COLORS (override with --color):")
    print("  red, green, blue, purple, orange, yellow, pink, teal,")
    print("  cyan, gold, silver, bronze, crimson, emerald, sapphire,")
    print("  ruby, amber, or any descriptive color name")
    print("=" * 60 + "\n")


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate CTA buttons for game UI with consistent styling.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python generate_cta.py --type primary --text "LEVEL UP"
      Generate a primary CTA button with "LEVEL UP" text
      
  python generate_cta.py --type secondary --text "CANCEL" --color purple
      Generate a purple secondary CTA button with "CANCEL" text
      
  python generate_cta.py --list
      Show available button types and colors

Note: This script is designed to be called by the CTA Button Droid.
      See droids/cta-button-droid.md for natural language interface.
        """
    )
    
    parser.add_argument(
        "--type", "-t",
        choices=["primary", "secondary"],
        help="Button type: 'primary' (blue with embellishments) or 'secondary' (gray, simple)"
    )
    parser.add_argument(
        "--text", "-x",
        help="Text to display on the button (will be uppercased)"
    )
    parser.add_argument(
        "--color", "-c",
        help="Optional color override (e.g., 'red', 'purple', 'gold')"
    )
    parser.add_argument(
        "--output", "-o",
        help="Custom output filename (without extension)"
    )
    parser.add_argument(
        "--list", "-l",
        action="store_true",
        help="List available button types and options"
    )
    
    args = parser.parse_args()
    
    if args.list:
        list_available()
    elif args.type and args.text:
        generate_cta(
            button_type=args.type,
            text=args.text.upper(),
            color=args.color,
            output_name=args.output
        )
    else:
        parser.print_help()