import os
import argparse
from PIL import Image
from google import genai
from google.genai import types

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Setup - get API key (don't fail on import)
API_KEY = os.getenv("GOOGLE_API_KEY")

MODEL_ID = "gemini-3-pro-image-preview"

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS_DIR = os.path.join(BASE_DIR, "assets", "boonsref")
OUTPUT_DIR = os.path.join(BASE_DIR, "output", "boon")

# =============================================================================
# REGISTRY: Add new boons and sub-icons here
# =============================================================================

MAIN_BOONS = {
    "fire": "BOON_FIRE.png",
    "ice": "BOON_ICE.png",
    "celestial": "BOON_CELESTIAL.png",
    "earth": "BOON_EARTH.png",
    "outer_dark": "BOON_OUTER_DARK.png",
    "outer dark": "BOON_OUTER_DARK.png",
    "storm": "BOON_STORM.png",
}

SUB_ICONS = {
    "down": "SUBICON_DOWN.png",
    "downward": "SUBICON_DOWN.png",
    "decrease": "SUBICON_DOWN.png",
    "decreased": "SUBICON_DOWN.png",
    "up": "SUBICON_UP.png",
    "upward": "SUBICON_UP.png",
    "increase": "SUBICON_UP.png",
    "increased": "SUBICON_UP.png",
}

# =============================================================================
# Core Functions
# =============================================================================

def load_image(filename):
    """Load an image from the assets directory."""
    path = os.path.join(ASSETS_DIR, filename)
    if not os.path.exists(path):
        raise FileNotFoundError(f"Asset not found: {path}")
    return Image.open(path)


def get_boon_filename(boon_key: str) -> str:
    """Get the filename for a main boon."""
    key = boon_key.lower().strip()
    if key not in MAIN_BOONS:
        available = ", ".join(MAIN_BOONS.keys())
        raise ValueError(f"Unknown boon '{boon_key}'. Available: {available}")
    return MAIN_BOONS[key]


def get_subicon_filename(subicon_key: str) -> str:
    """Get the filename for a sub-icon."""
    key = subicon_key.lower().strip()
    if key not in SUB_ICONS:
        available = ", ".join(set(SUB_ICONS.keys()))
        raise ValueError(f"Unknown sub-icon '{subicon_key}'. Available: {available}")
    return SUB_ICONS[key]


def generate_composite_prompt(boon_name: str, subicon_name: str) -> str:
    """Generate the prompt for compositing images."""
    return (
        f"You are compositing two UI icons into a single game asset. "
        f"IMAGE 1 is the main boon icon representing '{boon_name}'. "
        f"IMAGE 2 is the sub-icon (a '{subicon_name}' arrow). "
        f"\n\n"
        f"INSTRUCTIONS:\n"
        f"1. Place the sub-icon (IMAGE 2) in the bottom-right corner of the main boon (IMAGE 1).\n"
        f"2. The sub-icon should overlap the main boon slightly.\n"
        f"3. Create a transparent cutout/outline around the arrow so it stands out visually against the primary icon.\n"
        f"4. Keep ALL features of both images completely unchanged - same style, texture, and details.\n"
        f"5. The background must be solid gray (#4A4A4A).\n"
        f"6. Maintain the weathered, distressed white texture style of both icons.\n"
        f"7. The final image should look like a professional game UI element.\n"
        f"8. Create a A flat 2D asset sheet containing 30 different variations of the composite. The assets are arranged in a neat grid with spacing between them. No overlapping items. Against a gray background.\n"
        f"9. For each of the 30 variations, vary the size of the sub-icon (arrow) and the thickness/style of the transparent cutout around it (how it cuts into the main boon). No two variations should be exactly the same.\n"
    )


def generate_boon(boon: str, subicon: str, output_name: str = None):
    """
    Generate a composite boon image.
    
    Args:
        boon: The main boon type (fire, ice, celestial, earth, outer_dark, storm)
        subicon: The sub-icon type (up/increase, down/decrease)
        output_name: Optional custom output filename (without extension)
    """
    print(f"--- Generating Composite Boon ---")
    print(f"Main Boon: {boon}")
    print(f"Sub-Icon: {subicon}")
    
    if not API_KEY:
        raise ValueError("GOOGLE_API_KEY not set in environment")
    
    # Resolve filenames
    boon_file = get_boon_filename(boon)
    subicon_file = get_subicon_filename(subicon)
    
    print(f"Boon File: {boon_file}")
    print(f"Sub-Icon File: {subicon_file}")
    
    # Load images
    boon_img = load_image(boon_file)
    subicon_img = load_image(subicon_file)
    
    # Initialize client
    client = genai.Client(api_key=API_KEY)
    
    # Build prompt
    prompt = generate_composite_prompt(boon, subicon)
    
    # Build content list
    contents = [
        prompt,
        boon_img,      # IMAGE 1: Main boon
        subicon_img,   # IMAGE 2: Sub-icon
    ]
    
    print(f"Sending request to {MODEL_ID}...")
    
    try:
        response = client.models.generate_content(
            model=MODEL_ID,
            contents=contents,
            config=types.GenerateContentConfig(
                response_modalities=['TEXT', 'IMAGE'],
                system_instruction=(
                    "You are an expert UI artist specializing in game asset compositing. "
                    "You combine icons precisely while maintaining their original art style."
                ),
                image_config=types.ImageConfig(
                    aspect_ratio="1:1",
                ),
            )
        )
        
        # Process response
        image_saved = False
        if response.parts:
            for part in response.parts:
                if part.text:
                    print(f"Model Response: {part.text}")
                
                try:
                    image = part.as_image()
                    if image:
                        os.makedirs(OUTPUT_DIR, exist_ok=True)
                        
                        # Generate filename
                        if output_name:
                            filename = f"{output_name}.png"
                        else:
                            boon_clean = boon.upper().replace(" ", "_")
                            subicon_clean = "DOWN" if any(x in subicon.lower() for x in ["down", "decrease"]) else "UP"
                            filename = f"BOON_{boon_clean}_{subicon_clean}.png"
                        
                        save_path = os.path.join(OUTPUT_DIR, filename)
                        image.save(save_path)
                        print(f"SUCCESS: Saved to {save_path}")
                        image_saved = True
                        return save_path
                        
                except AttributeError:
                    if hasattr(part, 'inline_data') and part.inline_data:
                        # Fallback for different SDK versions
                        import io
                        image_data = part.inline_data.data
                        image = Image.open(io.BytesIO(image_data))
                        
                        os.makedirs(OUTPUT_DIR, exist_ok=True)
                        
                        if output_name:
                            filename = f"{output_name}.png"
                        else:
                            boon_clean = boon.upper().replace(" ", "_")
                            subicon_clean = "DOWN" if any(x in subicon.lower() for x in ["down", "decrease"]) else "UP"
                            filename = f"BOON_{boon_clean}_{subicon_clean}.png"
                        
                        save_path = os.path.join(OUTPUT_DIR, filename)
                        image.save(save_path)
                        print(f"SUCCESS: Saved to {save_path}")
                        image_saved = True
                        return save_path

        if not image_saved:
            print("FAILED: No image returned from API.")
            return None

    except Exception as e:
        print(f"ERROR: {e}")
        raise


def list_available():
    """Print available boons and sub-icons."""
    print("\n=== Available Main Boons ===")
    seen_boons = set()
    for key, filename in MAIN_BOONS.items():
        if filename not in seen_boons:
            print(f"  - {key}: {filename}")
            seen_boons.add(filename)
    
    print("\n=== Available Sub-Icons ===")
    seen_icons = set()
    for key, filename in SUB_ICONS.items():
        if filename not in seen_icons:
            print(f"  - {key}: {filename}")
            seen_icons.add(filename)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate composite boon icons by combining a main boon with a sub-icon."
    )
    parser.add_argument(
        "--boon", 
        required=True, 
        help="Main boon type (fire, ice, celestial, earth, outer_dark, storm)"
    )
    parser.add_argument(
        "--subicon", 
        required=True, 
        help="Sub-icon type (up/increase, down/decrease)"
    )
    parser.add_argument(
        "--output", 
        required=False, 
        help="Custom output filename (without extension)"
    )
    parser.add_argument(
        "--list", 
        action="store_true", 
        help="List available boons and sub-icons"
    )
    
    args = parser.parse_args()
    
    if args.list:
        list_available()
    else:
        generate_boon(args.boon, args.subicon, args.output)