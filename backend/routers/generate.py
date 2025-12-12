"""
Generation API endpoints.
Routes requests to appropriate generation services based on parsed intent.
"""
import os
import sys
import uuid
import asyncio
import traceback
from pathlib import Path
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from backend.services.parser import IntentParser, ParsedIntent

router = APIRouter()

class GenerateRequest(BaseModel):
    message: str

class GenerateResponse(BaseModel):
    status: str
    asset_type: str
    message: str
    download_url: Optional[str] = None
    details: Optional[dict] = None

@router.post("/generate", response_model=GenerateResponse)
async def generate_asset(request: GenerateRequest):
    """
    Generate a UI asset based on natural language input.
    Parses the message to determine asset type and parameters,
    then routes to the appropriate generation service.
    """
    print(f"[API] Received request: {request.message}")
    
    parser = IntentParser()
    intent = parser.parse(request.message)
    print(f"[API] Parsed intent: {intent.asset_type} with params {intent.params}")
    
    try:
        result = await run_generation(intent)
        print(f"[API] Generation successful: {result}")
        return GenerateResponse(
            status="success",
            asset_type=intent.asset_type,
            message=result["message"],
            download_url=result.get("download_url"),
            details=result.get("details")
        )
    except Exception as e:
        print(f"[API] Generation error: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

async def run_generation(intent: ParsedIntent) -> dict:
    """Route to appropriate generation service based on intent."""
    
    if intent.asset_type == "icon":
        return await generate_icon(intent.params)
    elif intent.asset_type == "cta":
        return await generate_cta(intent.params)
    elif intent.asset_type == "card":
        return await generate_card(intent.params)
    elif intent.asset_type == "boon":
        return await generate_boon(intent.params)
    elif intent.asset_type == "gacha":
        return await generate_gacha(intent.params)
    else:
        raise ValueError(f"Unknown asset type: {intent.asset_type}")

async def generate_icon(params: dict) -> dict:
    """Generate an icon using the icon script."""
    from generate_icon import generate_icon as gen_icon
    
    name = params.get("name", "button")
    
    # Run in thread pool to avoid blocking
    loop = asyncio.get_event_loop()
    result_path = await loop.run_in_executor(None, gen_icon, name)
    
    if result_path:
        filename = Path(result_path).name
        return {
            "message": f"Generated icon: {name}",
            "download_url": f"/downloads/icon/{filename}",
            "details": {"name": name}
        }
    else:
        raise Exception("Icon generation failed - no image returned")

async def generate_cta(params: dict) -> dict:
    """Generate a CTA button using the CTA script."""
    from generate_cta import CTAGenerator
    
    cta_type = params.get("type", "primary")
    text = params.get("text", "BUTTON")
    color = params.get("color")
    
    api_key = os.getenv("GOOGLE_API_KEY")
    generator = CTAGenerator(api_key=api_key)
    
    loop = asyncio.get_event_loop()
    result_path = await loop.run_in_executor(
        None, 
        lambda: generator.generate(button_type=cta_type, text=text, color=color)
    )
    
    if result_path:
        filename = Path(result_path).name
        return {
            "message": f"Generated {cta_type} CTA: {text}",
            "download_url": f"/downloads/cta/{filename}",
            "details": {"type": cta_type, "text": text, "color": color}
        }
    else:
        raise Exception("CTA generation failed")

async def generate_card(params: dict) -> dict:
    """Generate a card using the card script."""
    from generate_card import SorceryCardGenerator
    
    character = params.get("character", "")
    rarity = params.get("rarity", "3star")
    calling = params.get("calling", "Cunning")
    
    if not character:
        raise ValueError("Character name is required for card generation")
    if not calling:
        raise ValueError("Calling type is required for card generation")
    
    generator = SorceryCardGenerator()
    
    loop = asyncio.get_event_loop()
    result_path = await loop.run_in_executor(
        None,
        lambda: generator.generate(character=character, rarity=rarity, calling=calling)
    )
    
    if result_path:
        filename = Path(result_path).name
        return {
            "message": f"Generated {rarity} card for {character} ({calling})",
            "download_url": f"/downloads/card/{filename}",
            "details": {"character": character, "rarity": rarity, "calling": calling}
        }
    else:
        raise Exception("Card generation failed")

async def generate_boon(params: dict) -> dict:
    """Generate a boon icon using the boon script."""
    from generate_boon import generate_boon as gen_boon
    
    boon = params.get("boon", "fire")
    subicon = params.get("subicon", "up")
    
    loop = asyncio.get_event_loop()
    result_path = await loop.run_in_executor(None, gen_boon, boon, subicon, None)
    
    if result_path:
        filename = Path(result_path).name
        return {
            "message": f"Generated {boon} boon with {subicon} modifier",
            "download_url": f"/downloads/boon/{filename}",
            "details": {"boon": boon, "subicon": subicon}
        }
    else:
        raise Exception("Boon generation failed")

async def generate_gacha(params: dict) -> dict:
    """Generate a gacha screen using the gacha script."""
    from generate_gacha import UnifiedGachaGenerator
    
    pull = params.get("pull", "1 5star primal, 9 3star sorcery")
    
    generator = UnifiedGachaGenerator()
    
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        None,
        lambda: generator.generate(pull_spec=pull)
    )
    
    if result:
        if result.get('png'):
            # Return PNG if available
            png_path = result['png']
            rel_path = png_path.relative_to(PROJECT_ROOT / "output")
            return {
                "message": "Generated gacha screen",
                "download_url": f"/downloads/{rel_path}",
                "details": params
            }
        elif result.get('html'):
            # Fall back to HTML if PNG failed
            html_path = result['html']
            rel_path = html_path.relative_to(PROJECT_ROOT / "output")
            return {
                "message": "Generated gacha screen (HTML only - PNG rendering unavailable)",
                "download_url": f"/downloads/{rel_path}",
                "details": params
            }
    
    raise Exception("Gacha generation failed")

@router.get("/health")
async def health():
    return {"status": "ok"}
