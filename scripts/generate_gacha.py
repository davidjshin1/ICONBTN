#!/usr/bin/env python3
"""
Unified Gacha Screen Generator
==============================
Generates gacha screens using Playwright + CSS with on-demand Figma sync.

Every generation produces THREE outputs:
1. PNG screenshot
2. HTML source file  
3. Assets folder with all 2D assets used

Two modes:
1. GENERATE (default): Use cached Figma specs to render screens fast
2. SYNC: Pull fresh specs from Figma via MCP, update cache, then generate

The specs are stored in gacha_figma_specs.json and persist between runs.

Usage:
    # Normal generation (uses cached specs)
    python3 generate_gacha.py --pull "1 5star primal, 9 3star sorcery"
    
    # Sync from Figma first, then generate
    python3 generate_gacha.py--sync --pull "1 5star primal, 9 3star sorcery"
    
    # Just sync specs (no generation)
    python3 generate_gacha.py --sync-only
    
    # View current specs
    python3 generate_gacha.py --show-specs

Output structure:
    output/
    ├── gacha_1p9s.png           # Screenshot
    ├── gacha_1p9s.html          # HTML/CSS source
    └── gacha_1p9s_assets/       # All 2D assets
        ├── gachabackground.jpeg
        ├── awaken_button.png
        └── [card assets used]

Called by the Gacha Droid with natural language like:
    "generate a gacha with 2 primals"
    "sync from figma and generate a gacha with 1 primal"
    "update the design from figma"
"""

import os
import sys
import json
import argparse
import base64
import re
import shutil
import subprocess
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime
from enum import Enum, auto


# =============================================================================
# SPEC STORAGE
# =============================================================================

SPECS_FILE = Path(__file__).parent / "gacha_figma_specs.json"

@dataclass
class CardSlotSpec:
    """Specification for a single card slot."""
    index: int
    left: str
    top: str
    width: str
    height: str
    rotation: str
    is_primal: bool

@dataclass
class GachaFigmaSpecs:
    """
    Complete Figma specifications for the gacha screen.
    This is the cached design that gets updated when syncing from Figma.
    """
    # Metadata
    figma_node_id: str = "9064:2061"
    last_synced: str = ""
    
    # Canvas
    canvas_width: int = 852
    canvas_height: int = 393
    
    # Background
    bg_top: str = "-83px"
    bg_width: str = "852px"
    bg_height: str = "475.535px"
    
    # Layout container
    layout_width: str = "483px"
    layout_height: str = "329px"
    layout_left: str = "calc(50% + 0.5px)"
    layout_top: str = "50%"
    layout_transform: str = "translate(-50%, -50%)"
    
    # Primal card sizing
    primal_width: str = "96.205px"
    primal_height: str = "153.059px"
    primal_container_width: str = "106.067px"
    primal_container_height: str = "159.057px"
    primal_rotation: str = "356.228deg"
    
    # Sorcery card sizing
    sorcery_width: str = "78.123px"
    sorcery_height: str = "139.116px"
    sorcery_container_width: str = "88.608px"
    sorcery_container_height: str = "144.721px"
    sorcery_rotation: str = "355.582deg"
    
    # Button
    button_left: str = "668px"
    button_top: str = "349px"
    button_width: str = "113.527px"
    button_height: str = "25px"
    
    # Card slots (populated from Figma)
    card_slots: List[Dict] = field(default_factory=lambda: [
        {"index": 0, "left": "-2px", "top": "28px", "is_primal": True},
        {"index": 1, "left": "103px", "top": "20px", "is_primal": False},
        {"index": 2, "left": "199px", "top": "10px", "is_primal": False},
        {"index": 3, "left": "294.61px", "top": "4px", "is_primal": False},
        {"index": 4, "left": "390.22px", "top": "-2px", "is_primal": False},
        {"index": 5, "left": "11px", "top": "184px", "is_primal": False},
        {"index": 6, "left": "107px", "top": "177px", "is_primal": False},
        {"index": 7, "left": "203px", "top": "167px", "is_primal": False},
        {"index": 8, "left": "298.61px", "top": "161px", "is_primal": False},
        {"index": 9, "left": "394.22px", "top": "155px", "is_primal": False},
    ])
    
    def save(self, path: Path = SPECS_FILE):
        """Save specs to JSON file."""
        path.write_text(json.dumps(asdict(self), indent=2))
    
    @classmethod
    def load(cls, path: Path = SPECS_FILE) -> 'GachaFigmaSpecs':
        """Load specs from JSON file, or return defaults if not found."""
        if path.exists():
            data = json.loads(path.read_text())
            return cls(**data)
        return cls()


# =============================================================================
# FIGMA MCP SYNC
# =============================================================================

class FigmaMCPSync:
    """
    Syncs design specs from Figma using MCP connection.
    Parses the design context and extracts exact CSS values.
    """
    
    def __init__(self, node_id: str = "9064:2061"):
        self.node_id = node_id
    
    def extract_specs_from_figma_response(self, figma_code: str) -> GachaFigmaSpecs:
        """
        Parse the Figma-generated React/CSS code and extract specs.
        This handles the output from Figma Dev Mode's get_design_context.
        """
        specs = GachaFigmaSpecs()
        specs.figma_node_id = self.node_id
        specs.last_synced = datetime.now().isoformat()
        
        # Extract canvas dimensions from the main container
        # Look for: className="... h-[393px] ... w-[852px]..."
        canvas_match = re.search(r'data-name="Gacha"[^>]*', figma_code)
        
        # Extract background specs
        # Look for: top-[-83px] w-[852px] h-[475.535px]
        bg_match = re.search(r'top-\[(-?\d+(?:\.\d+)?px)\].*?w-\[(\d+(?:\.\d+)?px)\].*?h-\[(\d+(?:\.\d+)?px)\].*?gachabackground', figma_code)
        if bg_match:
            specs.bg_top = bg_match.group(1)
            specs.bg_width = bg_match.group(2)
            specs.bg_height = bg_match.group(3)
        
        # Extract layout container specs
        # Look for: left-[calc(50%+0.5px)] ... w-[483px] h-[329px]
        layout_match = re.search(r'w-\[(\d+(?:\.\d+)?px)\].*?Gacha Layout', figma_code)
        if layout_match:
            specs.layout_width = layout_match.group(1)
        
        # Extract primal card specs
        # Look for: rotate-[356.228deg] ... h-[153.059px] ... w-[96.205px]
        primal_match = re.search(r'rotate-\[(\d+(?:\.\d+)?deg)\][^}]*PrimalCard', figma_code)
        if primal_match:
            specs.primal_rotation = primal_match.group(1)
        
        primal_size = re.search(r'h-\[(\d+(?:\.\d+)?px)\].*?w-\[(\d+(?:\.\d+)?px)\].*?PrimalCard_Back', figma_code)
        if primal_size:
            specs.primal_height = primal_size.group(1)
            specs.primal_width = primal_size.group(2)
        
        # Extract sorcery card specs
        sorcery_match = re.search(r'rotate-\[(\d+(?:\.\d+)?deg)\][^}]*SorceryCard', figma_code)
        if sorcery_match:
            specs.sorcery_rotation = sorcery_match.group(1)
        
        sorcery_size = re.search(r'h-\[(\d+(?:\.\d+)?px)\].*?w-\[(\d+(?:\.\d+)?px)\].*?SorceryCard_Back', figma_code)
        if sorcery_size:
            specs.sorcery_height = sorcery_size.group(1)
            specs.sorcery_width = sorcery_size.group(2)
        
        # Extract card slot positions
        # Pattern: left-[XXpx] top-[YYpx] ... SorceryCard or PrimalCard
        slot_pattern = r'left-\[(-?\d+(?:\.\d+)?px)\].*?top-\[(-?\d+(?:\.\d+)?px)\].*?(Primal|Sorcery)Card'
        slots = []
        
        for i, match in enumerate(re.finditer(slot_pattern, figma_code)):
            left, top, card_type = match.groups()
            slots.append({
                "index": i,
                "left": left,
                "top": top,
                "is_primal": card_type == "Primal"
            })
        
        if slots:
            specs.card_slots = slots
        
        # Extract button position
        # Look for: left-[668px] top-[349px] ... Awaken
        button_match = re.search(r'left-\[(\d+(?:\.\d+)?px)\].*?top-\[(\d+(?:\.\d+)?px)\].*?w-\[(\d+(?:\.\d+)?px)\].*?h-\[(\d+(?:\.\d+)?px)\].*?Awaken', figma_code)
        if button_match:
            specs.button_left = button_match.group(1)
            specs.button_top = button_match.group(2)
            specs.button_width = button_match.group(3)
            specs.button_height = button_match.group(4)
        
        return specs
    
    def sync_via_mcp(self) -> GachaFigmaSpecs:
        """
        Trigger MCP sync - this will be called by the droid/agent.
        Returns updated specs.
        
        Note: In practice, this is called by Claude via the Figma MCP tools.
        The actual MCP call happens outside this script, and the response
        is passed to extract_specs_from_figma_response().
        """
        print(f"\n{'='*60}")
        print("FIGMA MCP SYNC")
        print(f"{'='*60}")
        print(f"  Node ID: {self.node_id}")
        print(f"  Requesting design context via MCP...")
        print(f"{'='*60}\n")
        
        # This is a placeholder - actual MCP calls happen via Claude
        # The calling agent should:
        # 1. Call Figma Dev Mode:get_design_context with node_id
        # 2. Pass the response to this script via --figma-response
        
        print("  ⚠ MCP sync must be triggered by the agent.")
        print("    Use: --figma-response '<figma_output>'")
        print("    Or let the Gacha Droid handle it automatically.")
        
        return GachaFigmaSpecs.load()


# =============================================================================
# CARD TYPES & PARSER (Same as before)
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
    card_type: CardType
    filename: str
    is_primal: bool
    rarity: int

CARD_ASSETS = {
    CardType.PRIMAL_5STAR: CardAsset(CardType.PRIMAL_5STAR, "PrimalCard_Back_5star-merge.png", True, 5),
    CardType.PRIMAL_4STAR: CardAsset(CardType.PRIMAL_4STAR, "PrimalCard_Back_4star-merge.png", True, 4),
    CardType.PRIMAL_3STAR: CardAsset(CardType.PRIMAL_3STAR, "PrimalCard_Back_3star-merge.png", True, 3),
    CardType.SORCERY_5STAR: CardAsset(CardType.SORCERY_5STAR, "SorceryCard_Back_5star-merge.png", False, 5),
    CardType.SORCERY_4STAR: CardAsset(CardType.SORCERY_4STAR, "SorceryCard_Back_4star-merge.png", False, 4),
    CardType.SORCERY_3STAR: CardAsset(CardType.SORCERY_3STAR, "SorceryCard_Back_3star-merge.png", False, 3),
}

@dataclass
class GachaPull:
    cards: List[CardType] = field(default_factory=list)
    
    @property
    def primal_count(self) -> int:
        return sum(1 for c in self.cards if CARD_ASSETS[c].is_primal)
    
    @property
    def sorcery_count(self) -> int:
        return sum(1 for c in self.cards if not CARD_ASSETS[c].is_primal)


class GachaPullParser:
    RARITY_MAP = {
        "5star": 5, "5-star": 5, "legendary": 5, "gold": 5, "ssr": 5,
        "4star": 4, "4-star": 4, "epic": 4, "purple": 4, "sr": 4,
        "3star": 3, "3-star": 3, "rare": 3, "blue": 3, "common": 3, "r": 3,
    }
    
    def parse(self, spec: str) -> GachaPull:
        spec_lower = spec.lower()
        cards = []
        
        pattern = r'(\d+)\s*(?:x\s*)?(\d+[- ]?star|legendary|epic|rare|common|gold|purple|blue|ssr|sr|r)?\s*(primal|sorcery|primals|sorcerys|sorceries)'
        matches = re.findall(pattern, spec_lower)
        
        for count_str, rarity_str, card_type_str in matches:
            count = int(count_str)
            rarity = 3
            if rarity_str:
                rarity_key = rarity_str.replace(" ", "").replace("-", "")
                rarity = self.RARITY_MAP.get(rarity_key, 3)
            
            is_primal = "primal" in card_type_str
            
            if is_primal:
                card_type = {5: CardType.PRIMAL_5STAR, 4: CardType.PRIMAL_4STAR}.get(rarity, CardType.PRIMAL_3STAR)
            else:
                card_type = {5: CardType.SORCERY_5STAR, 4: CardType.SORCERY_4STAR}.get(rarity, CardType.SORCERY_3STAR)
            
            cards.extend([card_type] * count)
        
        cards.sort(key=lambda c: (0 if CARD_ASSETS[c].is_primal else 1, -CARD_ASSETS[c].rarity))
        return GachaPull(cards=cards[:10])
    
    def create_pull(self, **kwargs) -> GachaPull:
        cards = []
        type_map = {
            'primal_5star': CardType.PRIMAL_5STAR,
            'primal_4star': CardType.PRIMAL_4STAR,
            'primal_3star': CardType.PRIMAL_3STAR,
            'sorcery_5star': CardType.SORCERY_5STAR,
            'sorcery_4star': CardType.SORCERY_4STAR,
            'sorcery_3star': CardType.SORCERY_3STAR,
        }
        for key, card_type in type_map.items():
            count = kwargs.get(key, 0)
            cards.extend([card_type] * count)
        
        cards.sort(key=lambda c: (0 if CARD_ASSETS[c].is_primal else 1, -CARD_ASSETS[c].rarity))
        return GachaPull(cards=cards[:10])


# =============================================================================
# HTML GENERATOR (Uses dynamic specs)
# =============================================================================

class DynamicHTMLGenerator:
    """
    Generates HTML using the cached Figma specs.
    Specs are loaded from gacha_figma_specs.json.
    """
    
    def __init__(self, specs: GachaFigmaSpecs, assets_dir: Path):
        self.specs = specs
        self.assets_dir = assets_dir
    
    def _get_asset_data_uri(self, filename: str) -> str:
        path = self.assets_dir / filename
        if not path.exists():
            return ""
        with open(path, "rb") as f:
            data = base64.b64encode(f.read()).decode()
        ext = path.suffix.lower()
        mime = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg"}.get(ext, "image/png")
        return f"data:{mime};base64,{data}"
    
    def _generate_card_html(self, card_type: CardType, slot_index: int) -> str:
        asset = CARD_ASSETS[card_type]
        
        if slot_index >= len(self.specs.card_slots):
            return ""
        
        slot = self.specs.card_slots[slot_index]
        use_primal = slot.get("is_primal", False) and asset.is_primal
        
        if use_primal:
            container_w = self.specs.primal_container_width
            container_h = self.specs.primal_container_height
            card_w = self.specs.primal_width
            card_h = self.specs.primal_height
            rotation = self.specs.primal_rotation
        else:
            container_w = self.specs.sorcery_container_width
            container_h = self.specs.sorcery_container_height
            card_w = self.specs.sorcery_width
            card_h = self.specs.sorcery_height
            rotation = self.specs.sorcery_rotation
        
        img_src = self._get_asset_data_uri(asset.filename)
        
        return f'''
        <div class="card-container" style="
            position: absolute;
            left: {slot['left']};
            top: {slot['top']};
            width: {container_w};
            height: {container_h};
            display: flex;
            align-items: center;
            justify-content: center;
        ">
            <div style="transform: rotate({rotation});">
                <img src="{img_src}" style="
                    width: {card_w};
                    height: {card_h};
                    object-fit: cover;
                " />
            </div>
        </div>
        '''
    
    def generate(self, pull: GachaPull) -> str:
        s = self.specs
        
        bg_uri = self._get_asset_data_uri("gachabackground.jpeg")
        button_uri = self._get_asset_data_uri("awaken_button.png")
        
        cards_html = "".join(
            self._generate_card_html(card_type, i)
            for i, card_type in enumerate(pull.cards)
        )
        
        return f'''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            width: {s.canvas_width}px;
            height: {s.canvas_height}px;
            overflow: hidden;
            background: white;
        }}
        .gacha-container {{
            position: relative;
            width: {s.canvas_width}px;
            height: {s.canvas_height}px;
        }}
        .background {{
            position: absolute;
            left: 0;
            top: {s.bg_top};
            width: {s.bg_width};
            height: {s.bg_height};
        }}
        .background img {{
            width: 100%;
            height: 100%;
            object-fit: cover;
        }}
        .gacha-layout {{
            position: absolute;
            left: {s.layout_left};
            top: {s.layout_top};
            transform: {s.layout_transform};
            width: {s.layout_width};
            height: {s.layout_height};
            overflow: visible;
        }}
        .awaken-button {{
            position: absolute;
            left: {s.button_left};
            top: {s.button_top};
            width: {s.button_width};
            height: {s.button_height};
        }}
        .awaken-button img {{
            width: 100%;
            height: 100%;
            object-fit: cover;
        }}
    </style>
</head>
<body>
    <div class="gacha-container">
        <div class="background">
            <img src="{bg_uri}" alt="background" />
        </div>
        <div class="gacha-layout">
            {cards_html}
        </div>
        <div class="awaken-button">
            <img src="{button_uri}" alt="AWAKEN" />
        </div>
    </div>
</body>
</html>
'''


# =============================================================================
# PLAYWRIGHT RENDERER
# =============================================================================

class PlaywrightRenderer:
    def render(self, html: str, output_path: Path, 
               width: int, height: int, scale: float = 1.0) -> Path:
        from playwright.sync_api import sync_playwright
        
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(
                viewport={"width": width, "height": height},
                device_scale_factor=scale
            )
            page.set_content(html)
            page.wait_for_load_state("networkidle")
            page.screenshot(path=str(output_path), type="png")
            browser.close()
        
        return output_path


# =============================================================================
# UNIFIED GENERATOR
# =============================================================================

class UnifiedGachaGenerator:
    """
    Main generator that uses cached specs and supports Figma sync.
    """
    
    def __init__(self, base_dir: str = None):
        if base_dir is None:
            # Go up one level from scripts/ to project root
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        self.base_dir = Path(base_dir)
        self.assets_dir = self.base_dir / "assets" / "gacharef"
        self.output_dir = self.base_dir / "output" / "gacha"
        self.specs_file = self.base_dir / "scripts" / "gacha_figma_specs.json"
        
        self.parser = GachaPullParser()
        self.renderer = PlaywrightRenderer()
        
        # Load cached specs
        self.specs = GachaFigmaSpecs.load(self.specs_file)
    
    def sync_from_figma(self, figma_response: str = None, node_id: str = "9064:2061") -> GachaFigmaSpecs:
        """
        Update specs from Figma response.
        
        Args:
            figma_response: Raw output from Figma MCP get_design_context
            node_id: Figma node ID to sync
        """
        print(f"\n{'='*60}")
        print("SYNCING FROM FIGMA")
        print(f"{'='*60}")
        
        if figma_response:
            syncer = FigmaMCPSync(node_id)
            self.specs = syncer.extract_specs_from_figma_response(figma_response)
            self.specs.save(self.specs_file)
            
            print(f"  ✓ Specs extracted and saved")
            print(f"  ✓ Last synced: {self.specs.last_synced}")
            print(f"  ✓ Card slots: {len(self.specs.card_slots)}")
            print(f"  ✓ Primal rotation: {self.specs.primal_rotation}")
            print(f"  ✓ Sorcery rotation: {self.specs.sorcery_rotation}")
        else:
            print("  ⚠ No Figma response provided")
            print("  → Agent should call Figma MCP and pass response")
        
        print(f"{'='*60}\n")
        return self.specs
    
    def show_specs(self):
        """Display current cached specs."""
        print(f"\n{'='*60}")
        print("CURRENT FIGMA SPECS")
        print(f"{'='*60}")
        print(f"  Source file: {self.specs_file}")
        print(f"  Last synced: {self.specs.last_synced or 'Never (using defaults)'}")
        print(f"  Figma node: {self.specs.figma_node_id}")
        print(f"\n  Canvas: {self.specs.canvas_width}x{self.specs.canvas_height}px")
        print(f"\n  Primal card:")
        print(f"    Size: {self.specs.primal_width} x {self.specs.primal_height}")
        print(f"    Rotation: {self.specs.primal_rotation}")
        print(f"\n  Sorcery card:")
        print(f"    Size: {self.specs.sorcery_width} x {self.specs.sorcery_height}")
        print(f"    Rotation: {self.specs.sorcery_rotation}")
        print(f"\n  Card slots: {len(self.specs.card_slots)}")
        for slot in self.specs.card_slots:
            slot_type = "PRIMAL" if slot.get('is_primal') else "SORCERY"
            print(f"    [{slot['index']}] {slot_type:8} at ({slot['left']}, {slot['top']})")
        print(f"{'='*60}\n")
    
    def generate(self, pull_spec: str = None,
                 primal_5star: int = 0, primal_4star: int = 0, primal_3star: int = 0,
                 sorcery_5star: int = 0, sorcery_4star: int = 0, sorcery_3star: int = 0,
                 output_name: str = None, scale: float = 2.0) -> Dict[str, Path]:
        """
        Generate a gacha screen.
        
        Always produces (all in same subfolder):
        1. PNG screenshot
        2. HTML source file
        3. Assets folder with all 2D assets used
        
        Returns:
            Dict with paths to 'png', 'html', and 'assets_dir'
        """
        
        print(f"\n{'='*60}")
        print("GACHA GENERATOR (Unified)")
        print(f"{'='*60}")
        print(f"  Specs from: {self.specs.last_synced or 'defaults'}")
        print(f"  Assets dir: {self.assets_dir}")
        
        # Parse pull
        if pull_spec:
            print(f"  Parsing: \"{pull_spec}\"")
            pull = self.parser.parse(pull_spec)
        else:
            pull = self.parser.create_pull(
                primal_5star=primal_5star, primal_4star=primal_4star, primal_3star=primal_3star,
                sorcery_5star=sorcery_5star, sorcery_4star=sorcery_4star, sorcery_3star=sorcery_3star,
            )
        
        print(f"  Primals: {pull.primal_count}")
        print(f"  Sorcery: {pull.sorcery_count}")
        print(f"  Scale: {scale}x")
        print(f"{'='*60}\n")
        
        # Generate HTML
        print("Step 1: Generating HTML from specs...")
        html_gen = DynamicHTMLGenerator(self.specs, self.assets_dir)
        html = html_gen.generate(pull)
        print(f"  ✓ HTML generated ({len(html):,} bytes)")
        
        # Prepare output paths - everything goes in a subfolder
        # Always add timestamp to make each generation unique
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if output_name:
            base_name = f"{output_name}_{timestamp}"
        else:
            primal_str = f"{pull.primal_count}p" if pull.primal_count else ""
            sorcery_str = f"{pull.sorcery_count}s" if pull.sorcery_count else ""
            base_name = f"gacha_{primal_str}{sorcery_str}_{timestamp}"
        
        # Create subfolder for this generation
        output_subfolder = self.output_dir / base_name
        output_subfolder.mkdir(parents=True, exist_ok=True)
        
        output_png = output_subfolder / f"{base_name}.png"
        output_html = output_subfolder / f"{base_name}.html"
        output_assets_dir = output_subfolder / "assets"
        
        # 1. Save HTML
        print("\nStep 2: Saving HTML...")
        output_html.write_text(html)
        print(f"  ✓ HTML: {output_html}")
        
        # 2. Create assets folder with all 2D assets used
        print("\nStep 3: Copying assets...")
        output_assets_dir.mkdir(parents=True, exist_ok=True)
        
        assets_copied = []
        
        # Copy background
        bg_src = self.assets_dir / "gachabackground.jpeg"
        if bg_src.exists():
            shutil.copy(bg_src, output_assets_dir / bg_src.name)
            assets_copied.append(bg_src.name)
        
        # Copy button
        btn_src = self.assets_dir / "awaken_button.png"
        if btn_src.exists():
            shutil.copy(btn_src, output_assets_dir / btn_src.name)
            assets_copied.append(btn_src.name)
        
        # Copy card assets (only the ones used in this pull)
        used_cards = set()
        for card_type in pull.cards:
            asset = CARD_ASSETS[card_type]
            if asset.filename not in used_cards:
                card_src = self.assets_dir / asset.filename
                if card_src.exists():
                    shutil.copy(card_src, output_assets_dir / asset.filename)
                    assets_copied.append(asset.filename)
                    used_cards.add(asset.filename)
        
        print(f"  ✓ Assets folder: {output_assets_dir}/")
        for asset_name in assets_copied:
            print(f"      - {asset_name}")
        
        # 3. Render PNG
        print("\nStep 4: Rendering PNG with Playwright...")
        self.renderer.render(
            html=html,
            output_path=output_png,
            width=self.specs.canvas_width,
            height=self.specs.canvas_height,
            scale=scale
        )
        
        actual_w = int(self.specs.canvas_width * scale)
        actual_h = int(self.specs.canvas_height * scale)
        
        print(f"\n{'='*60}")
        print(f"✓ GENERATION COMPLETE")
        print(f"{'='*60}")
        print(f"  PNG:    {output_png} ({actual_w}x{actual_h}px)")
        print(f"  HTML:   {output_html}")
        print(f"  Assets: {output_assets_dir}/ ({len(assets_copied)} files)")
        print(f"{'='*60}\n")
        
        return {
            'png': output_png,
            'html': output_html,
            'assets_dir': output_assets_dir,
        }


# =============================================================================
# CLI
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Unified gacha generator with Figma sync support.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate using cached specs (fast)
  python generate_gacha.py --pull "1 5star primal, 9 3star sorcery"
  
  # Sync from Figma first (when design changes)
  python generate_gacha.py --sync --pull "1 5star primal, 9 3star sorcery"
  
  # Just sync specs without generating
  python generate_gacha.py --sync-only --figma-response "<figma_output>"
  
  # View current specs
  python generate_gacha.py --show-specs

The Gacha Droid can handle natural language like:
  "generate a gacha with 2 primals"
  "sync from figma and make a gacha screen"
  "update the design from figma"
        """
    )
    
    # Sync options
    parser.add_argument("--sync", action="store_true",
                        help="Sync specs from Figma before generating")
    parser.add_argument("--sync-only", action="store_true",
                        help="Only sync specs, don't generate")
    parser.add_argument("--figma-response", metavar="JSON",
                        help="Raw Figma MCP response for syncing")
    parser.add_argument("--figma-file", metavar="PATH",
                        help="Path to file containing Figma MCP response")
    parser.add_argument("--show-specs", action="store_true",
                        help="Show current cached specs")
    
    # Generation options
    parser.add_argument("--pull", "-p", help="Natural language pull spec")
    parser.add_argument("--primal-5star", type=int, default=0)
    parser.add_argument("--primal-4star", type=int, default=0)
    parser.add_argument("--primal-3star", type=int, default=0)
    parser.add_argument("--sorcery-5star", type=int, default=0)
    parser.add_argument("--sorcery-4star", type=int, default=0)
    parser.add_argument("--sorcery-3star", type=int, default=0)
    parser.add_argument("--output", "-o", help="Custom output name (creates NAME.png, NAME.html, NAME_assets/)")
    parser.add_argument("--scale", "-s", type=float, default=2.0, help="Render scale (default: 2 for best quality)")
    
    args = parser.parse_args()
    
    generator = UnifiedGachaGenerator()
    
    # Handle sync
    if args.sync or args.sync_only:
        figma_response = args.figma_response
        if args.figma_file:
            figma_response = Path(args.figma_file).read_text()
        generator.sync_from_figma(figma_response)
        if args.sync_only:
            return
    
    # Show specs
    if args.show_specs:
        generator.show_specs()
        return
    
    # Generate
    if args.pull or any([args.primal_5star, args.primal_4star, args.primal_3star,
                         args.sorcery_5star, args.sorcery_4star, args.sorcery_3star]):
        generator.generate(
            pull_spec=args.pull,
            primal_5star=args.primal_5star,
            primal_4star=args.primal_4star,
            primal_3star=args.primal_3star,
            sorcery_5star=args.sorcery_5star,
            sorcery_4star=args.sorcery_4star,
            sorcery_3star=args.sorcery_3star,
            output_name=args.output,
            scale=args.scale,
        )
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
