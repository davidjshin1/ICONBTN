#!/usr/bin/env python3
"""
Gacha Screen Generator (PIL-Based)
===================================
Generates gacha pull screens by compositing card assets onto a background
using exact positions derived from Figma.

Based on Figma Frame: "Gacha" (node 9064:2061)
Canvas: 852 × 393 px

Usage:
    python generate_gacha.py --primals 1 --sorcery 9
    python generate_gacha.py --pull "1 5star primal, 9 3star sorcery"
    python generate_gacha.py --preset standard

Called by the Gacha Droid (see droids/gacha-droid.md)
"""

import os
import argparse
import re
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Dict
from PIL import Image, ImageOps
from enum import Enum, auto


# =============================================================================
# FIGMA SOURCE OF TRUTH
# =============================================================================

@dataclass(frozen=True)
class FigmaGachaSpec:
    """
    Immutable Figma design specifications for the Gacha screen.
    Extracted from Figma node 9064:2061.
    """
    # Canvas dimensions
    CANVAS_WIDTH: int = 852
    CANVAS_HEIGHT: int = 393
    
    # Background positioning (extends beyond frame)
    BG_OFFSET_X: int = 0
    BG_OFFSET_Y: int = -83
    BG_WIDTH: int = 852
    BG_HEIGHT: int = 476  # Rounded from 475.53
    
    # Layout frame offset (card positions are relative to this)
    LAYOUT_OFFSET_X: int = 185
    LAYOUT_OFFSET_Y: int = 32
    
    # Primal card (5-star) specs
    PRIMAL_WIDTH: int = 106
    PRIMAL_HEIGHT: int = 159
    PRIMAL_OFFSET_X: int = -2  # Relative to layout
    PRIMAL_OFFSET_Y: int = 34
    
    # Sorcery card (3-star) specs
    SORCERY_WIDTH: int = 89  # Rounded from 88.6
    SORCERY_HEIGHT: int = 145  # Rounded from 144.72
    
    # Awaken button specs
    BUTTON_X: int = 668
    BUTTON_Y: int = 349
    BUTTON_WIDTH: int = 114  # Rounded from 113.53
    BUTTON_HEIGHT: int = 25


FIGMA = FigmaGachaSpec()


# =============================================================================
# CARD SLOT POSITIONS (Derived from Figma)
# =============================================================================

@dataclass
class CardSlot:
    """A slot where a card can be placed."""
    index: int
    x: int  # Absolute X position on canvas
    y: int  # Absolute Y position on canvas
    width: int
    height: int
    is_primal_slot: bool = False


def calculate_card_slots() -> List[CardSlot]:
    """
    Calculate all 10 card slot positions based on Figma layout.
    
    Slot 0: Primal card position (larger, top-left)
    Slots 1-4: Top row sorcery cards (cascading right-to-left diagonal)
    Slots 5-9: Bottom row sorcery cards (cascading right-to-left diagonal)
    """
    slots = []
    
    # Figma positions relative to layout frame (185, 32)
    # These create a cascading diagonal effect
    
    # Slot 0: Primal card
    slots.append(CardSlot(
        index=0,
        x=FIGMA.LAYOUT_OFFSET_X + FIGMA.PRIMAL_OFFSET_X,  # 183
        y=FIGMA.LAYOUT_OFFSET_Y + FIGMA.PRIMAL_OFFSET_Y,  # 66
        width=FIGMA.PRIMAL_WIDTH,
        height=FIGMA.PRIMAL_HEIGHT,
        is_primal_slot=True,
    ))
    
    # Sorcery card positions (from Figma metadata)
    # Row 1: Positions 1-4 (top row, cascading up-right)
    sorcery_positions_row1 = [
        (103, 26),   # Slot 1
        (199, 16),   # Slot 2
        (295, 10),   # Slot 3
        (390, 4),    # Slot 4
    ]
    
    # Row 2: Positions 5-9 (bottom row, cascading up-right)
    sorcery_positions_row2 = [
        (11, 190),   # Slot 5
        (107, 183),  # Slot 6
        (203, 173),  # Slot 7
        (299, 167),  # Slot 8
        (394, 161),  # Slot 9
    ]
    
    # Add row 1 slots
    for i, (rel_x, rel_y) in enumerate(sorcery_positions_row1, start=1):
        slots.append(CardSlot(
            index=i,
            x=FIGMA.LAYOUT_OFFSET_X + rel_x,
            y=FIGMA.LAYOUT_OFFSET_Y + rel_y,
            width=FIGMA.SORCERY_WIDTH,
            height=FIGMA.SORCERY_HEIGHT,
            is_primal_slot=False,
        ))
    
    # Add row 2 slots
    for i, (rel_x, rel_y) in enumerate(sorcery_positions_row2, start=5):
        slots.append(CardSlot(
            index=i,
            x=FIGMA.LAYOUT_OFFSET_X + rel_x,
            y=FIGMA.LAYOUT_OFFSET_Y + rel_y,
            width=FIGMA.SORCERY_WIDTH,
            height=FIGMA.SORCERY_HEIGHT,
            is_primal_slot=False,
        ))
    
    return slots


# Pre-calculate slots
CARD_SLOTS = calculate_card_slots()


# =============================================================================
# CARD TYPES
# =============================================================================

class CardType(Enum):
    PRIMAL_5STAR = auto()
    PRIMAL_4STAR = auto()
    PRIMAL_3STAR = auto()
    SORCERY_5STAR = auto()
    SORCERY_4STAR = auto()
    SORCERY_3STAR = auto()


@dataclass
class CardAsset:
    """Configuration for a card asset."""
    card_type: CardType
    filename: str
    is_primal: bool
    rarity: int  # 3, 4, or 5


CARD_ASSETS = {
    CardType.PRIMAL_5STAR: CardAsset(
        card_type=CardType.PRIMAL_5STAR,
        filename="PrimalCard_Back_5star-merge.png",
        is_primal=True,
        rarity=5,
    ),
    CardType.PRIMAL_4STAR: CardAsset(
        card_type=CardType.PRIMAL_4STAR,
        filename="PrimalCard_Back_4star-merge.png",
        is_primal=True,
        rarity=4,
    ),
    CardType.PRIMAL_3STAR: CardAsset(
        card_type=CardType.PRIMAL_3STAR,
        filename="PrimalCard_Back_3star-merge.png",
        is_primal=True,
        rarity=3,
    ),
    CardType.SORCERY_5STAR: CardAsset(
        card_type=CardType.SORCERY_5STAR,
        filename="SorceryCard_Back_5star-merge.png",
        is_primal=False,
        rarity=5,
    ),
    CardType.SORCERY_4STAR: CardAsset(
        card_type=CardType.SORCERY_4STAR,
        filename="SorceryCard_Back_4star-merge.png",
        is_primal=False,
        rarity=4,
    ),
    CardType.SORCERY_3STAR: CardAsset(
        card_type=CardType.SORCERY_3STAR,
        filename="SorceryCard_Back_3star-merge.png",
        is_primal=False,
        rarity=3,
    ),
}


# =============================================================================
# PATH RESOLVER
# =============================================================================

class GachaPathResolver:
    """Resolves asset and output paths for gacha generation."""
    
    def __init__(self, base_dir: Optional[str] = None):
        if base_dir is None:
            # Go up one level from scripts/ to project root
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.base_dir = Path(base_dir)
        self.assets_dir = self.base_dir / "assets" / "gacharef"
        self.output_dir = self.base_dir / "output" / "gacha"
    
    def get_background(self) -> Path:
        return self.assets_dir / "gachabackground.jpeg"
    
    def get_awaken_button(self) -> Path:
        return self.assets_dir / "awakenbutton.png"
    
    def get_card_asset(self, card_type: CardType) -> Path:
        asset = CARD_ASSETS.get(card_type)
        if not asset:
            raise ValueError(f"Unknown card type: {card_type}")
        return self.assets_dir / asset.filename
    
    def get_output_path(self, name: str = "gacha_screen") -> Path:
        return self.output_dir / f"{name}.png"


# =============================================================================
# IMAGE LOADER
# =============================================================================

class GachaImageLoader:
    """Loads and prepares images for gacha composition."""
    
    @staticmethod
    def load(path: Path, mode: str = 'RGBA') -> Image.Image:
        """Load image with consistent settings."""
        if not path.exists():
            raise FileNotFoundError(f"Asset not found: {path}")
        img = Image.open(path)
        if img.mode != mode:
            img = img.convert(mode)
        return img
    
    @staticmethod
    def resize_exact(img: Image.Image, size: Tuple[int, int]) -> Image.Image:
        """Resize with LANCZOS for high quality."""
        return img.resize(size, Image.Resampling.LANCZOS)
    
    @staticmethod
    def crop_to_canvas(img: Image.Image, canvas_size: Tuple[int, int], 
                       offset: Tuple[int, int] = (0, 0)) -> Image.Image:
        """
        Crop/position an image to fit a canvas with given offset.
        Handles images larger than the canvas.
        """
        canvas_w, canvas_h = canvas_size
        offset_x, offset_y = offset
        
        # Create canvas
        canvas = Image.new('RGBA', canvas_size, (0, 0, 0, 0))
        
        # Calculate paste position (can be negative)
        paste_x = offset_x
        paste_y = offset_y
        
        # If image needs to be cropped (offset is negative)
        if paste_x < 0 or paste_y < 0:
            # Calculate crop box
            crop_left = max(0, -paste_x)
            crop_top = max(0, -paste_y)
            crop_right = min(img.width, canvas_w - paste_x)
            crop_bottom = min(img.height, canvas_h - paste_y)
            
            cropped = img.crop((crop_left, crop_top, crop_right, crop_bottom))
            canvas.paste(cropped, (max(0, paste_x), max(0, paste_y)))
        else:
            canvas.paste(img, (paste_x, paste_y))
        
        return canvas


# =============================================================================
# GACHA PULL PARSER
# =============================================================================

@dataclass
class GachaPull:
    """Represents a gacha pull configuration."""
    cards: List[CardType] = field(default_factory=list)
    
    @property
    def primal_count(self) -> int:
        return sum(1 for c in self.cards if CARD_ASSETS[c].is_primal)
    
    @property
    def sorcery_count(self) -> int:
        return sum(1 for c in self.cards if not CARD_ASSETS[c].is_primal)


class GachaPullParser:
    """
    Parses natural language gacha pull specifications.
    
    Examples:
        "1 5star primal, 9 3star sorcery"
        "2 primals (5star), 8 sorcery (3star)"
        "give me 1 legendary primal and 9 common sorcery cards"
    """
    
    # Rarity aliases
    RARITY_MAP = {
        "5star": 5, "5-star": 5, "legendary": 5, "gold": 5, "ssr": 5,
        "4star": 4, "4-star": 4, "epic": 4, "purple": 4, "sr": 4,
        "3star": 3, "3-star": 3, "rare": 3, "blue": 3, "common": 3, "r": 3,
    }
    
    def parse(self, spec: str) -> GachaPull:
        """
        Parse a pull specification string into a GachaPull.
        
        Returns a GachaPull with cards sorted: primals first, then sorcery.
        """
        spec_lower = spec.lower()
        cards = []
        
        # Pattern: "N [rarity] primal/sorcery"
        # Match patterns like "1 5star primal" or "9 3star sorcery"
        pattern = r'(\d+)\s*(?:x\s*)?(\d+[- ]?star|legendary|epic|rare|common|gold|purple|blue|ssr|sr|r)?\s*(primal|sorcery|primals|sorcerys|sorceries)'
        
        matches = re.findall(pattern, spec_lower)
        
        for count_str, rarity_str, card_type_str in matches:
            count = int(count_str)
            
            # Determine rarity (default to 3 if not specified)
            rarity = 3
            if rarity_str:
                rarity_key = rarity_str.replace(" ", "").replace("-", "")
                rarity = self.RARITY_MAP.get(rarity_key, 3)
            
            # Determine card type
            is_primal = "primal" in card_type_str
            
            # Map to CardType
            if is_primal:
                if rarity == 5:
                    card_type = CardType.PRIMAL_5STAR
                elif rarity == 4:
                    card_type = CardType.PRIMAL_4STAR
                else:
                    card_type = CardType.PRIMAL_3STAR
            else:
                if rarity == 5:
                    card_type = CardType.SORCERY_5STAR
                elif rarity == 4:
                    card_type = CardType.SORCERY_4STAR
                else:
                    card_type = CardType.SORCERY_3STAR
            
            # Add cards
            cards.extend([card_type] * count)
        
        # If no matches, try simpler parsing
        if not cards:
            # Try to find just numbers and types
            primal_match = re.search(r'(\d+)\s*primal', spec_lower)
            sorcery_match = re.search(r'(\d+)\s*sorcery', spec_lower)
            
            if primal_match:
                count = int(primal_match.group(1))
                # Check for rarity in context
                if "5star" in spec_lower or "5-star" in spec_lower or "gold" in spec_lower:
                    cards.extend([CardType.PRIMAL_5STAR] * count)
                else:
                    cards.extend([CardType.PRIMAL_3STAR] * count)
            
            if sorcery_match:
                count = int(sorcery_match.group(1))
                if "5star" in spec_lower or "5-star" in spec_lower:
                    cards.extend([CardType.SORCERY_5STAR] * count)
                else:
                    cards.extend([CardType.SORCERY_3STAR] * count)
        
        # Sort: primals first (by rarity desc), then sorcery (by rarity desc)
        cards.sort(key=lambda c: (
            0 if CARD_ASSETS[c].is_primal else 1,
            -CARD_ASSETS[c].rarity
        ))
        
        # Limit to 10 cards (max slots)
        cards = cards[:10]
        
        return GachaPull(cards=cards)
    
    def create_standard_pull(self, primal_5star: int = 0, primal_4star: int = 0,
                             primal_3star: int = 0, sorcery_5star: int = 0,
                             sorcery_4star: int = 0, sorcery_3star: int = 0) -> GachaPull:
        """Create a pull with explicit counts for each type."""
        cards = []
        
        cards.extend([CardType.PRIMAL_5STAR] * primal_5star)
        cards.extend([CardType.PRIMAL_4STAR] * primal_4star)
        cards.extend([CardType.PRIMAL_3STAR] * primal_3star)
        cards.extend([CardType.SORCERY_5STAR] * sorcery_5star)
        cards.extend([CardType.SORCERY_4STAR] * sorcery_4star)
        cards.extend([CardType.SORCERY_3STAR] * sorcery_3star)
        
        # Sort and limit
        cards.sort(key=lambda c: (
            0 if CARD_ASSETS[c].is_primal else 1,
            -CARD_ASSETS[c].rarity
        ))
        cards = cards[:10]
        
        return GachaPull(cards=cards)


# =============================================================================
# GACHA COMPOSITOR
# =============================================================================

class GachaCompositor:
    """
    Composites gacha screen layers using exact Figma positioning.
    
    Layer stack (bottom to top):
    1. Background image
    2. Cards (primals in first slots, then sorcery)
    3. Awaken button
    """
    
    def __init__(self, resolver: GachaPathResolver):
        self.resolver = resolver
        self.loader = GachaImageLoader()
        self.slots = CARD_SLOTS
    
    def composite(self, pull: GachaPull) -> Image.Image:
        """
        Composite a complete gacha screen.
        
        Args:
            pull: GachaPull configuration
            
        Returns:
            Final composited gacha screen image
        """
        canvas_size = (FIGMA.CANVAS_WIDTH, FIGMA.CANVAS_HEIGHT)
        
        # Layer 1: Background
        print("  → Loading background...")
        bg_path = self.resolver.get_background()
        background = self.loader.load(bg_path, 'RGB').convert('RGBA')
        
        # Resize background to match Figma spec
        bg_scaled = self.loader.resize_exact(background, (FIGMA.BG_WIDTH, FIGMA.BG_HEIGHT))
        
        # Position background with offset (crops top portion)
        canvas = self.loader.crop_to_canvas(
            bg_scaled, 
            canvas_size, 
            (FIGMA.BG_OFFSET_X, FIGMA.BG_OFFSET_Y)
        )
        print(f"  ✓ Background: {bg_path.name}")
        
        # Layer 2: Cards
        print("  → Placing cards...")
        card_cache: Dict[CardType, Image.Image] = {}
        
        for i, card_type in enumerate(pull.cards):
            if i >= len(self.slots):
                print(f"  ⚠ Too many cards, skipping card {i+1}")
                break
            
            slot = self.slots[i]
            asset = CARD_ASSETS[card_type]
            
            # Load and cache card image
            if card_type not in card_cache:
                card_path = self.resolver.get_card_asset(card_type)
                if card_path.exists():
                    card_img = self.loader.load(card_path)
                    card_cache[card_type] = card_img
                else:
                    print(f"  ⚠ Card asset not found: {card_path}")
                    continue
            
            card_img = card_cache[card_type]
            
            # Determine target size based on slot type
            if slot.is_primal_slot and asset.is_primal:
                target_size = (FIGMA.PRIMAL_WIDTH, FIGMA.PRIMAL_HEIGHT)
            else:
                target_size = (FIGMA.SORCERY_WIDTH, FIGMA.SORCERY_HEIGHT)
            
            # Resize card
            card_scaled = self.loader.resize_exact(card_img, target_size)
            
            # Create layer and paste card
            card_layer = Image.new('RGBA', canvas_size, (0, 0, 0, 0))
            card_layer.paste(card_scaled, (slot.x, slot.y), card_scaled)
            
            # Composite
            canvas = Image.alpha_composite(canvas, card_layer)
            
            rarity_str = f"{asset.rarity}★"
            type_str = "Primal" if asset.is_primal else "Sorcery"
            print(f"  ✓ Slot {i}: {type_str} {rarity_str} at ({slot.x}, {slot.y})")
        
        # Layer 3: Awaken button
        print("  → Adding Awaken button...")
        button_path = self.resolver.get_awaken_button()
        if button_path.exists():
            button_img = self.loader.load(button_path)
            button_scaled = self.loader.resize_exact(
                button_img, 
                (FIGMA.BUTTON_WIDTH, FIGMA.BUTTON_HEIGHT)
            )
            
            button_layer = Image.new('RGBA', canvas_size, (0, 0, 0, 0))
            button_layer.paste(button_scaled, (FIGMA.BUTTON_X, FIGMA.BUTTON_Y), button_scaled)
            canvas = Image.alpha_composite(canvas, button_layer)
            print(f"  ✓ Awaken button at ({FIGMA.BUTTON_X}, {FIGMA.BUTTON_Y})")
        else:
            print(f"  ⚠ Awaken button not found: {button_path}")
        
        return canvas


# =============================================================================
# MAIN GACHA GENERATOR
# =============================================================================

class GachaGenerator:
    """
    Main gacha screen generator.
    
    Parses pull specifications and composites the final screen.
    """
    
    def __init__(self, base_dir: Optional[str] = None):
        self.resolver = GachaPathResolver(base_dir)
        self.parser = GachaPullParser()
        self.compositor = GachaCompositor(self.resolver)
    
    def generate(self, pull_spec: str = None, 
                 primal_5star: int = 0, primal_4star: int = 0, primal_3star: int = 0,
                 sorcery_5star: int = 0, sorcery_4star: int = 0, sorcery_3star: int = 0,
                 output_name: str = None) -> Optional[Path]:
        """
        Generate a gacha screen.
        
        Args:
            pull_spec: Natural language pull specification
            primal_5star: Number of 5-star primal cards
            primal_4star: Number of 4-star primal cards
            primal_3star: Number of 3-star primal cards
            sorcery_5star: Number of 5-star sorcery cards
            sorcery_4star: Number of 4-star sorcery cards
            sorcery_3star: Number of 3-star sorcery cards
            output_name: Custom output filename
            
        Returns:
            Path to generated gacha screen image
        """
        print(f"\n{'='*60}")
        print("GACHA SCREEN GENERATOR (PIL)")
        print(f"{'='*60}")
        
        # Parse or create pull
        if pull_spec:
            print(f"  Parsing: \"{pull_spec}\"")
            pull = self.parser.parse(pull_spec)
        else:
            pull = self.parser.create_standard_pull(
                primal_5star=primal_5star,
                primal_4star=primal_4star,
                primal_3star=primal_3star,
                sorcery_5star=sorcery_5star,
                sorcery_4star=sorcery_4star,
                sorcery_3star=sorcery_3star,
            )
        
        print(f"  Primals: {pull.primal_count}")
        print(f"  Sorcery: {pull.sorcery_count}")
        print(f"  Total: {len(pull.cards)} cards")
        print(f"{'='*60}\n")
        
        # Composite
        print("Compositing gacha screen...")
        result = self.compositor.composite(pull)
        
        # Save
        print("\nSaving output...")
        self.resolver.output_dir.mkdir(parents=True, exist_ok=True)
        
        if output_name:
            output_path = self.resolver.output_dir / f"{output_name}.png"
        else:
            # Generate name from pull contents
            primal_str = f"{pull.primal_count}p" if pull.primal_count else ""
            sorcery_str = f"{pull.sorcery_count}s" if pull.sorcery_count else ""
            output_path = self.resolver.output_dir / f"gacha_{primal_str}{sorcery_str}.png"
        
        result.save(output_path, "PNG")
        
        print(f"\n{'='*60}")
        print(f"✓ SUCCESS: {output_path}")
        print(f"  Size: {result.size[0]}x{result.size[1]}px")
        print(f"{'='*60}\n")
        
        return output_path
    
    def list_presets(self):
        """Print available presets and card types."""
        print("\n" + "=" * 60)
        print("GACHA GENERATOR - AVAILABLE OPTIONS")
        print("=" * 60)
        
        print("\nCARD TYPES:")
        for card_type, asset in CARD_ASSETS.items():
            type_str = "Primal" if asset.is_primal else "Sorcery"
            print(f"  {type_str} {asset.rarity}★: {asset.filename}")
        
        print("\nSLOT LAYOUT (10 slots):")
        print("  Slot 0: Primal position (larger)")
        print("  Slots 1-4: Top row (cascading)")
        print("  Slots 5-9: Bottom row (cascading)")
        
        print("\nEXAMPLE SPECIFICATIONS:")
        print('  "1 5star primal, 9 3star sorcery"')
        print('  "2 primals (gold), 8 sorcery (blue)"')
        print('  "1 legendary primal and 9 common sorcery"')
        
        print("\nDIRECT PARAMETERS:")
        print("  --primal-5star N  : Number of 5★ primals")
        print("  --primal-4star N  : Number of 4★ primals")
        print("  --primal-3star N  : Number of 3★ primals")
        print("  --sorcery-5star N : Number of 5★ sorcery")
        print("  --sorcery-4star N : Number of 4★ sorcery")
        print("  --sorcery-3star N : Number of 3★ sorcery")
        print("=" * 60 + "\n")


# =============================================================================
# CLI
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Generate gacha pull screens using PIL.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python generate_gacha.py --pull "1 5star primal, 9 3star sorcery"
  python generate_gacha.py --primal-5star 1 --sorcery-3star 9
  python generate_gacha.py --primal-5star 2 --sorcery-4star 3 --sorcery-3star 5
  python generate_gacha.py --list
        """
    )
    
    parser.add_argument("--pull", "-p", help="Natural language pull specification")
    parser.add_argument("--primal-5star", type=int, default=0, help="5★ primal count")
    parser.add_argument("--primal-4star", type=int, default=0, help="4★ primal count")
    parser.add_argument("--primal-3star", type=int, default=0, help="3★ primal count")
    parser.add_argument("--sorcery-5star", type=int, default=0, help="5★ sorcery count")
    parser.add_argument("--sorcery-4star", type=int, default=0, help="4★ sorcery count")
    parser.add_argument("--sorcery-3star", type=int, default=0, help="3★ sorcery count")
    parser.add_argument("--output", "-o", help="Custom output filename")
    parser.add_argument("--list", "-l", action="store_true", help="List options")
    
    args = parser.parse_args()
    
    generator = GachaGenerator()
    
    if args.list:
        generator.list_presets()
    elif args.pull:
        generator.generate(pull_spec=args.pull, output_name=args.output)
    elif any([args.primal_5star, args.primal_4star, args.primal_3star,
              args.sorcery_5star, args.sorcery_4star, args.sorcery_3star]):
        generator.generate(
            primal_5star=args.primal_5star,
            primal_4star=args.primal_4star,
            primal_3star=args.primal_3star,
            sorcery_5star=args.sorcery_5star,
            sorcery_4star=args.sorcery_4star,
            sorcery_3star=args.sorcery_3star,
            output_name=args.output,
        )
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
