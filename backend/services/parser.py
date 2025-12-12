"""
Intent Parser - Consolidates all droid parsing logic into one service.
Parses natural language requests into structured generation commands.
"""
from dataclasses import dataclass, field
from typing import Optional, Literal
import re

AssetType = Literal["icon", "cta", "card", "boon", "gacha"]

@dataclass
class ParsedIntent:
    asset_type: AssetType
    params: dict = field(default_factory=dict)
    confidence: float = 0.5
    raw_message: str = ""

class IntentParser:
    """Parses natural language into generation commands."""
    
    # Keywords mapped from droid configs (order matters - more specific first)
    GACHA_TRIGGERS = ["gacha", "pull screen", "summon screen", "pull result"]
    CARD_TRIGGERS = ["card", "sorcery card", "primal card", "character card", "star card"]
    CTA_TRIGGERS = ["cta", "call to action", "button that says", "button labeled", "button with text"]
    BOON_TRIGGERS = ["boon", "buff icon", "debuff icon", "modifier icon", "damage increased", "damage decreased", "resistance"]
    ICON_TRIGGERS = ["icon", "ui icon", "game icon"]
    
    # Boon types from boon-droid
    BOON_TYPES = {
        "fire": ["fire", "flame", "burn", "heat", "inferno"],
        "ice": ["ice", "frost", "cold", "freeze", "frozen"],
        "celestial": ["celestial", "holy", "divine", "light", "sun", "moon", "star"],
        "earth": ["earth", "ground", "rock", "stone", "mountain"],
        "outer_dark": ["outer dark", "void", "dark", "shadow", "abyss", "eldritch"],
        "storm": ["storm", "lightning", "thunder", "electric", "shock"]
    }
    
    # Boon modifiers
    BOON_UP = ["increase", "increased", "boost", "boosted", "raise", "raised", "up", "more", "strengthen", "plus", "buff", "bonus"]
    BOON_DOWN = ["decrease", "decreased", "reduce", "reduced", "lower", "lowered", "down", "less", "weaken", "minus", "debuff", "penalty", "resistance"]
    
    # CTA indicators from cta-droid
    PRIMARY_CTA = ["primary", "main", "blue", "action", "confirm", "submit", "bright", "start", "play", "level up", "continue"]
    SECONDARY_CTA = ["secondary", "cancel", "gray", "grey", "dark", "back", "dismiss", "simple", "exit", "close", "no", "skip"]
    
    # Card callings from card-generator
    CALLINGS = ["cunning", "might", "wisdom", "spirit", "shadow"]
    RARITIES = ["3star", "3 star", "4star", "4 star", "5star", "5 star"]
    
    def parse(self, message: str) -> ParsedIntent:
        """Parse a natural language message into a structured intent."""
        message_lower = message.lower()
        
        # Detect asset type (order matters - more specific patterns first)
        if self._matches(message_lower, self.GACHA_TRIGGERS):
            return self._parse_gacha(message)
        elif self._matches(message_lower, self.CARD_TRIGGERS) or self._has_card_indicators(message_lower):
            return self._parse_card(message)
        elif self._matches(message_lower, self.BOON_TRIGGERS) or self._has_boon_indicators(message_lower):
            return self._parse_boon(message)
        elif self._matches(message_lower, self.CTA_TRIGGERS) or self._has_cta_indicators(message_lower):
            return self._parse_cta(message)
        else:
            # Default to icon for simple object requests
            return self._parse_icon(message)
    
    def _matches(self, text: str, triggers: list) -> bool:
        """Check if text contains any trigger phrases."""
        return any(trigger in text for trigger in triggers)
    
    def _has_card_indicators(self, text: str) -> bool:
        """Check for card-specific patterns."""
        has_rarity = any(r in text for r in self.RARITIES)
        has_calling = any(c in text for c in self.CALLINGS)
        return has_rarity and has_calling
    
    def _has_boon_indicators(self, text: str) -> bool:
        """Check for boon-specific patterns (element + modifier)."""
        has_element = any(any(kw in text for kw in keywords) for keywords in self.BOON_TYPES.values())
        has_modifier = any(m in text for m in self.BOON_UP + self.BOON_DOWN)
        return has_element and has_modifier
    
    def _has_cta_indicators(self, text: str) -> bool:
        """Check for button/CTA patterns."""
        return "button" in text or ("says" in text and any(word.isupper() for word in text.split()))
    
    def _parse_icon(self, message: str) -> ParsedIntent:
        """Parse icon generation request."""
        # Extract the icon subject - remove common words
        words_to_remove = ["icon", "ui", "game", "create", "make", "generate", "give", "me", "a", "an", "the", "please", "for"]
        words = message.lower().split()
        subject_words = [w for w in words if w not in words_to_remove]
        
        # Join remaining words as the icon name
        icon_name = " ".join(subject_words).strip()
        if not icon_name:
            icon_name = "button"
        
        return ParsedIntent(
            asset_type="icon",
            params={"name": icon_name},
            confidence=0.8,
            raw_message=message
        )
    
    def _parse_cta(self, message: str) -> ParsedIntent:
        """Parse CTA button request."""
        message_lower = message.lower()
        
        # Determine button type
        cta_type = "primary"
        if any(kw in message_lower for kw in self.SECONDARY_CTA):
            cta_type = "secondary"
        
        # Extract text - look for quoted text first
        text = None
        quoted = re.search(r'["\']([^"\']+)["\']', message)
        if quoted:
            text = quoted.group(1).upper()
        else:
            # Look for text after keywords
            patterns = [
                r'says?\s+(\w+(?:\s+\w+)?)',
                r'labeled?\s+(\w+(?:\s+\w+)?)',
                r'with\s+text\s+(\w+(?:\s+\w+)?)',
                r':\s*(\w+(?:\s+\w+)?)\s*$'
            ]
            for pattern in patterns:
                match = re.search(pattern, message, re.IGNORECASE)
                if match:
                    text = match.group(1).upper()
                    break
        
        if not text:
            # Try to extract any capitalized words as button text
            caps = re.findall(r'\b([A-Z]{2,}(?:\s+[A-Z]{2,})?)\b', message)
            if caps:
                text = caps[0]
            else:
                text = "BUTTON"
        
        # Extract color if specified
        color = None
        color_match = re.search(r'(?:in|with|using)\s+(\w+)\s*(?:color|theme)?', message_lower)
        if color_match:
            potential_color = color_match.group(1)
            if potential_color not in ["text", "a", "the"]:
                color = potential_color
        
        return ParsedIntent(
            asset_type="cta",
            params={"type": cta_type, "text": text, "color": color},
            confidence=0.9,
            raw_message=message
        )
    
    def _parse_card(self, message: str) -> ParsedIntent:
        """Parse card generation request."""
        message_lower = message.lower()
        
        # Extract rarity
        rarity = "3star"
        for r in ["5star", "5 star", "5-star"]:
            if r in message_lower:
                rarity = "5star"
                break
        for r in ["4star", "4 star", "4-star"]:
            if r in message_lower:
                rarity = "4star"
                break
        
        # Extract calling
        calling = None
        for c in self.CALLINGS:
            if c in message_lower:
                calling = c.capitalize()
                break
        
        # Extract character name - remove known keywords
        words_to_remove = ["card", "sorcery", "primal", "create", "make", "generate", "give", "me", "a", "an", 
                          "the", "for", "with", "calling", "star", "3star", "4star", "5star", "3", "4", "5"] + self.CALLINGS
        words = message_lower.split()
        char_words = [w for w in words if w not in words_to_remove and not w.isdigit()]
        character = " ".join(char_words).strip().title()
        
        return ParsedIntent(
            asset_type="card",
            params={"character": character, "rarity": rarity, "calling": calling},
            confidence=0.85,
            raw_message=message
        )
    
    def _parse_boon(self, message: str) -> ParsedIntent:
        """Parse boon icon request."""
        message_lower = message.lower()
        
        # Detect boon type
        boon_type = None
        for boon, keywords in self.BOON_TYPES.items():
            if any(kw in message_lower for kw in keywords):
                boon_type = boon
                break
        
        if not boon_type:
            boon_type = "fire"  # default
        
        # Detect modifier direction
        subicon = "up"  # default to buff
        if any(m in message_lower for m in self.BOON_DOWN):
            subicon = "down"
        
        return ParsedIntent(
            asset_type="boon",
            params={"boon": boon_type, "subicon": subicon},
            confidence=0.9,
            raw_message=message
        )
    
    def _parse_gacha(self, message: str) -> ParsedIntent:
        """Parse gacha pull screen request."""
        # Pass the full message to the gacha script's parser which handles all variations
        # e.g. "1 5star primal, 1 4star primal, 8 3star sorcery"
        return ParsedIntent(
            asset_type="gacha",
            params={"pull": message},
            confidence=0.85,
            raw_message=message
        )
