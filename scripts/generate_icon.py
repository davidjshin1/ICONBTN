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

# Setup - get API key (don't fail on import, fail on usage)
API_KEY = os.getenv("GOOGLE_API_KEY")

# Use the model ID specified by the user
MODEL_ID = "gemini-3-pro-image-preview"

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS_DIR = os.path.join(BASE_DIR, "assets", "iconbtnref")
OUTPUT_DIR = os.path.join(BASE_DIR, "output", "icon")

def load_image(filename):
    path = os.path.join(ASSETS_DIR, filename)
    if not os.path.exists(path):
        print(f"Skipping missing asset: {path}")
        return None
    return Image.open(path)

def generate_icon(icon_name):
    """Generate an icon and return the saved file path."""
    print(f"--- Generating: {icon_name} ---")
    
    if not API_KEY:
        raise ValueError("GOOGLE_API_KEY not set in environment")
    
    # Initialize Client
    client = genai.Client(api_key=API_KEY)

    # Load Visual References
    frame_img = load_image("frame.png")
    style_files = ["ref_chest.png", "ref_grid.png", "ref_eye.png", "ref_heart.png"]
    
    # Construct Content List
    contents = []
    
    prompt = (
        f"Generate a highly detailed 2D UI button featuring a {icon_name}. "
        "VISUAL REFERENCES: "
        "The first image provided is the 'Frame Structure'. You must replicate this circular button frame exactly (dark blue, sparkly background, border style). "
        "The subsequent images are 'Style References'. The icon inside the button must match their white, distressed art style. "
        "DETAILS: "
        f"The {icon_name} symbol should be centered, white, and textured with the same weathered details as the style references. "
        "The texture consists of organic chipping and irregular flaking, simulating a cohesive material that is wearing thin rather than a printed pattern. The surface wear resembles random abrasion and smooth fading. "
        "The icon should be 2D and flat, with no depth or perspective. "
        "The icon should blend seamlessly with the dark button surface. "
        "The background must be transparent. "
    )
    contents.append(prompt)

    if frame_img:
        contents.append(frame_img)

    for sf in style_files:
        img = load_image(sf)
        if img:
            contents.append(img)

    print(f"Sending request with {len(contents)-1} reference images...")
    
    response = client.models.generate_content(
        model=MODEL_ID,
        contents=contents,
        config=types.GenerateContentConfig(
            response_modalities=['TEXT', 'IMAGE'],
            system_instruction="You are an expert UI artist. You replicate existing asset styles perfectly.",
            image_config=types.ImageConfig(
                aspect_ratio="1:1",
            ),
        )
    )
    
    # Save Output
    if response.parts:
        for part in response.parts:
            if part.text:
                print(f"Model Response: {part.text}")
            
            try:
                image = part.as_image()
                if image:
                    os.makedirs(OUTPUT_DIR, exist_ok=True)
                    filename = f"ICONBTN_{icon_name.replace(' ', '_').upper()}.png"
                    save_path = os.path.join(OUTPUT_DIR, filename)
                    image.save(save_path)
                    print(f"SUCCESS: Saved to {save_path}")
                    return save_path
            except AttributeError:
                pass

    print("FAILED: No image returned from API.")
    return None

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", required=True, help="Icon name")
    args = parser.parse_args()
    generate_icon(args.name)
