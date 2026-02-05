"""
Theme Generator Service
FastAPI sidecar that uses Claude API to generate and refine theme JSON.

MODES:
    - Development (default): Returns mock themes, no API calls, no cost
    - Production: Set THEME_GENERATOR_LIVE=true to enable real API calls

Usage:
    cd helpers
    python theme_generator.py                    # Mock mode (default)
    THEME_GENERATOR_LIVE=true python theme_generator.py  # Live mode (costs tokens)
"""

import json
import os
import re
import random
from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

from theme_schema import (
    THEME_SCHEMA,
    DARK_BASE_DEFAULTS,
    LIGHT_BASE_DEFAULTS,
    DEFAULT_FONTS
)

# Load environment variables from project root
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))

# Check if we're in live mode (production) or mock mode (development)
LIVE_MODE = os.getenv("THEME_GENERATOR_LIVE", "").lower() == "true"

# Initialize FastAPI
mode_desc = "LIVE MODE - API calls enabled" if LIVE_MODE else "MOCK MODE - No API calls"
app = FastAPI(
    title="Theme Generator",
    description=f"AI-powered theme generation for Stock Analyzer ({mode_desc})",
    version="1.0.0"
)

# CORS for browser access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5000", "https://psfordtaurus.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Anthropic client only in live mode
if LIVE_MODE:
    import anthropic
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
else:
    client = None

# ============================================================================
# MOCK THEMES - Used in development mode to avoid API costs
# ============================================================================
MOCK_THEMES = {
    "hotdog-stand": {
        "id": "hotdog-stand",
        "name": "Hotdog Stand",
        "version": "1.0.0",
        "meta": {"category": "light", "icon": "sun", "iconColor": "#FFFF00"},
        "variables": {
            **LIGHT_BASE_DEFAULTS,
            # Classic Windows 3.1 Hotdog Stand - red background, yellow accents
            "bg-primary": "#FF0000",
            "bg-secondary": "#CC0000",
            "bg-tertiary": "#990000",
            "bg-code": "#660000",
            "text-primary": "#FFFF00",
            "text-secondary": "#FFFF99",
            "text-muted": "#FFCC00",
            "text-inverted": "#FF0000",
            "accent": "#FFFF00",
            "accent-hover": "#FFFF99",
            "accent-light": "#FFFFCC",
            "accent-bg": "rgba(255, 255, 0, 0.2)",
            "accent-bg-subtle": "rgba(255, 255, 0, 0.1)",
            "border-primary": "#FFFF00",
            "border-secondary": "#FFCC00",
            "success": "#00FF00",
            "error": "#FFFFFF",
            "warning": "#FF6600",
            "btn-primary-bg": "#FFFF00",
            "btn-primary-bg-hover": "#FFFF99",
            "btn-primary-text": "#FF0000",
            "btn-primary-glow": "0 0 10px #FFFF00",
            "chart-bg": "#CC0000",
            "chart-text": "#FFFF00",
            "chart-grid": "#FF6666",
            "chart-line-primary": "#FFFF00",
            "chart-line-secondary": "#FFFF99",
            "chart-candle-up": "#00FF00",
            "chart-candle-down": "#FFFFFF",
            "price-up": "#00FF00",
            "price-down": "#FFFFFF",
            "tile-title-color": "#FFFF00",
        },
        "effects": {},
        "fonts": DEFAULT_FONTS.copy()
    },
    "sunset": {
        "id": "sunset-glow",
        "name": "Sunset Glow",
        "version": "1.0.0",
        "meta": {"category": "dark", "icon": "sun", "iconColor": "#ff7b54"},
        "variables": {
            **DARK_BASE_DEFAULTS,
            "bg-primary": "#1a1216",
            "bg-secondary": "#2d1f24",
            "bg-tertiary": "#3d2930",
            "text-primary": "#fff5f0",
            "text-secondary": "#d4a89a",
            "accent": "#ff7b54",
            "accent-hover": "#ff9a76",
            "accent-light": "#ffb89a",
            "accent-bg": "rgba(255, 123, 84, 0.15)",
            "accent-bg-subtle": "rgba(255, 123, 84, 0.08)",
            "border-primary": "#ff7b54",
            "border-secondary": "#3d2930",
            "success": "#7ed56f",
            "error": "#ff6b6b",
            "btn-primary-bg": "#ff7b54",
            "btn-primary-bg-hover": "#ff9a76",
            "btn-primary-text": "#1a1216",
            "chart-line-primary": "#ff7b54",
            "chart-line-secondary": "#ffb89a",
        },
        "effects": {"vignette": {"enabled": True, "strength": 0.3}},
        "fonts": DEFAULT_FONTS.copy()
    },
    "ocean": {
        "id": "deep-ocean",
        "name": "Deep Ocean",
        "version": "1.0.0",
        "meta": {"category": "dark", "icon": "moon", "iconColor": "#00b4d8"},
        "variables": {
            **DARK_BASE_DEFAULTS,
            "bg-primary": "#0a1628",
            "bg-secondary": "#0d2137",
            "bg-tertiary": "#123049",
            "text-primary": "#e0f7ff",
            "text-secondary": "#90cdf4",
            "accent": "#00b4d8",
            "accent-hover": "#48cae4",
            "accent-light": "#90e0ef",
            "accent-bg": "rgba(0, 180, 216, 0.15)",
            "accent-bg-subtle": "rgba(0, 180, 216, 0.08)",
            "border-primary": "#00b4d8",
            "border-secondary": "#123049",
            "success": "#00f5d4",
            "error": "#ff6b6b",
            "btn-primary-bg": "#00b4d8",
            "btn-primary-bg-hover": "#48cae4",
            "btn-primary-text": "#0a1628",
            "chart-line-primary": "#00b4d8",
            "chart-line-secondary": "#90e0ef",
        },
        "effects": {"bloom": {"enabled": True, "contrast": 1.05, "brightness": 1.02}},
        "fonts": DEFAULT_FONTS.copy()
    },
    "forest": {
        "id": "forest-night",
        "name": "Forest Night",
        "version": "1.0.0",
        "meta": {"category": "dark", "icon": "moon", "iconColor": "#52b788"},
        "variables": {
            **DARK_BASE_DEFAULTS,
            "bg-primary": "#0d1b14",
            "bg-secondary": "#1a2f23",
            "bg-tertiary": "#264234",
            "text-primary": "#e8f5e9",
            "text-secondary": "#a5d6a7",
            "accent": "#52b788",
            "accent-hover": "#74c69d",
            "accent-light": "#95d5b2",
            "accent-bg": "rgba(82, 183, 136, 0.15)",
            "accent-bg-subtle": "rgba(82, 183, 136, 0.08)",
            "border-primary": "#52b788",
            "border-secondary": "#264234",
            "success": "#40916c",
            "error": "#e63946",
            "btn-primary-bg": "#52b788",
            "btn-primary-bg-hover": "#74c69d",
            "btn-primary-text": "#0d1b14",
            "chart-line-primary": "#52b788",
            "chart-line-secondary": "#95d5b2",
        },
        "effects": {},
        "fonts": DEFAULT_FONTS.copy()
    },
    "lavender": {
        "id": "lavender-dream",
        "name": "Lavender Dream",
        "version": "1.0.0",
        "meta": {"category": "light", "icon": "sun", "iconColor": "#7c3aed"},
        "variables": {
            **LIGHT_BASE_DEFAULTS,
            "bg-primary": "#faf5ff",
            "bg-secondary": "#f3e8ff",
            "bg-tertiary": "#e9d5ff",
            "text-primary": "#3b0764",
            "text-secondary": "#6b21a8",
            "accent": "#7c3aed",
            "accent-hover": "#8b5cf6",
            "accent-light": "#a78bfa",
            "accent-bg": "rgba(124, 58, 237, 0.12)",
            "accent-bg-subtle": "rgba(124, 58, 237, 0.06)",
            "border-primary": "#c4b5fd",
            "border-secondary": "#ddd6fe",
            "success": "#22c55e",
            "error": "#ef4444",
            "btn-primary-bg": "#7c3aed",
            "btn-primary-bg-hover": "#8b5cf6",
            "btn-primary-text": "#ffffff",
            "chart-line-primary": "#7c3aed",
            "chart-line-secondary": "#a78bfa",
        },
        "effects": {},
        "fonts": DEFAULT_FONTS.copy()
    },
}


def get_mock_theme(prompt: str, name: str, base_theme: str) -> tuple[dict, bool]:
    """Return a mock theme based on keywords in the prompt.

    Returns:
        tuple: (theme dict, matched: bool indicating if keywords matched)
    """
    prompt_lower = prompt.lower()
    matched = True

    # Match based on keywords - order matters, more specific first
    if any(w in prompt_lower for w in ["hotdog", "hot dog", "windows 3.1", "windows 3", "hotdog stand"]):
        theme = MOCK_THEMES["hotdog-stand"].copy()
    elif any(w in prompt_lower for w in ["sunset", "orange", "warm", "coral"]):
        theme = MOCK_THEMES["sunset"].copy()
    elif any(w in prompt_lower for w in ["ocean", "blue", "sea", "water", "aqua"]):
        theme = MOCK_THEMES["ocean"].copy()
    elif any(w in prompt_lower for w in ["forest", "green", "nature", "earth"]):
        theme = MOCK_THEMES["forest"].copy()
    elif any(w in prompt_lower for w in ["purple", "lavender", "violet"]):
        theme = MOCK_THEMES["lavender"].copy()
    else:
        # Random selection - no match
        theme = random.choice(list(MOCK_THEMES.values())).copy()
        matched = False

    # Override with provided name
    theme["name"] = name
    theme["id"] = re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')
    theme["meta"]["originalPrompt"] = prompt

    return theme, matched


# Color palettes for mock refinement
MOCK_COLOR_PALETTES = {
    "yellow": {"accent": "#fbbf24", "accent-hover": "#f59e0b", "accent-light": "#fcd34d"},
    "gold": {"accent": "#d4af37", "accent-hover": "#c9a227", "accent-light": "#e6c349"},
    "pink": {"accent": "#ec4899", "accent-hover": "#db2777", "accent-light": "#f472b6"},
    "magenta": {"accent": "#d946ef", "accent-hover": "#c026d3", "accent-light": "#e879f9"},
    "red": {"accent": "#ef4444", "accent-hover": "#dc2626", "accent-light": "#f87171"},
    "crimson": {"accent": "#dc143c", "accent-hover": "#b91c1c", "accent-light": "#f87171"},
    "orange": {"accent": "#f97316", "accent-hover": "#ea580c", "accent-light": "#fb923c"},
    "coral": {"accent": "#ff7f50", "accent-hover": "#ff6347", "accent-light": "#ffa07a"},
    "green": {"accent": "#22c55e", "accent-hover": "#16a34a", "accent-light": "#4ade80"},
    "teal": {"accent": "#14b8a6", "accent-hover": "#0d9488", "accent-light": "#2dd4bf"},
    "cyan": {"accent": "#06b6d4", "accent-hover": "#0891b2", "accent-light": "#22d3ee"},
    "blue": {"accent": "#3b82f6", "accent-hover": "#2563eb", "accent-light": "#60a5fa"},
    "indigo": {"accent": "#6366f1", "accent-hover": "#4f46e5", "accent-light": "#818cf8"},
    "purple": {"accent": "#a855f7", "accent-hover": "#9333ea", "accent-light": "#c084fc"},
    "violet": {"accent": "#8b5cf6", "accent-hover": "#7c3aed", "accent-light": "#a78bfa"},
    "white": {"accent": "#f8fafc", "accent-hover": "#f1f5f9", "accent-light": "#ffffff"},
}


def apply_mock_refinement(theme: dict, feedback: str) -> dict:
    """Apply mock refinements based on feedback keywords."""
    import copy
    theme = copy.deepcopy(theme)
    feedback_lower = feedback.lower()

    if "variables" not in theme:
        theme["variables"] = {}

    vars = theme["variables"]

    # Check for color keywords and apply accent changes
    for color_name, palette in MOCK_COLOR_PALETTES.items():
        if color_name in feedback_lower:
            vars["accent"] = palette["accent"]
            vars["accent-hover"] = palette["accent-hover"]
            vars["accent-light"] = palette["accent-light"]
            vars["accent-bg"] = f"rgba({int(palette['accent'][1:3], 16)}, {int(palette['accent'][3:5], 16)}, {int(palette['accent'][5:7], 16)}, 0.15)"
            vars["accent-bg-subtle"] = f"rgba({int(palette['accent'][1:3], 16)}, {int(palette['accent'][3:5], 16)}, {int(palette['accent'][5:7], 16)}, 0.08)"
            vars["border-primary"] = palette["accent"]
            vars["btn-primary-bg"] = palette["accent"]
            vars["btn-primary-bg-hover"] = palette["accent-hover"]
            vars["chart-line-primary"] = palette["accent"]
            vars["chart-line-secondary"] = palette["accent-light"]
            break

    # Handle background adjustments
    if any(w in feedback_lower for w in ["darker", "more dark", "deep"]):
        # Darken backgrounds
        vars["bg-primary"] = "#050508"
        vars["bg-secondary"] = "#0a0a10"
        vars["bg-tertiary"] = "#10101a"
    elif any(w in feedback_lower for w in ["lighter", "more light", "bright background"]):
        # Lighten backgrounds
        vars["bg-primary"] = "#1a1a24"
        vars["bg-secondary"] = "#24242e"
        vars["bg-tertiary"] = "#2e2e3a"

    # Handle text adjustments
    if "brighter text" in feedback_lower or "lighter text" in feedback_lower:
        vars["text-primary"] = "#ffffff"
        vars["text-secondary"] = "#d0d0e0"
    elif "dimmer text" in feedback_lower or "darker text" in feedback_lower:
        vars["text-primary"] = "#c0c0d0"
        vars["text-secondary"] = "#808090"

    # Handle vibrant/muted requests
    if any(w in feedback_lower for w in ["vibrant", "vivid", "saturated", "brighter"]):
        # Make accent more vibrant by increasing saturation conceptually
        # For mock, we just use neon-like colors
        if "accent" in vars:
            current_accent = vars["accent"]
            # Neon up the accent
            vars["btn-primary-glow"] = f"0 0 20px {current_accent}"
            vars["chart-line-glow"] = "drop-shadow(0 0 6px currentColor)"
    elif any(w in feedback_lower for w in ["muted", "subtle", "desaturated", "softer"]):
        # Disable glow effects
        vars["btn-primary-glow"] = "none"
        vars["chart-line-glow"] = "none"

    # Handle effects
    if "effects" not in theme:
        theme["effects"] = {}

    if any(w in feedback_lower for w in ["scanlines", "crt", "retro"]):
        theme["effects"]["scanlines"] = {"enabled": True, "opacity": 0.08, "size": 3}
    elif "no scanlines" in feedback_lower or "remove scanlines" in feedback_lower:
        theme["effects"]["scanlines"] = {"enabled": False}

    if any(w in feedback_lower for w in ["vignette", "dark edges", "shadowed edges"]):
        theme["effects"]["vignette"] = {"enabled": True, "strength": 0.4}
    elif "no vignette" in feedback_lower or "remove vignette" in feedback_lower:
        theme["effects"]["vignette"] = {"enabled": False}

    if any(w in feedback_lower for w in ["glow", "bloom", "neon"]):
        theme["effects"]["bloom"] = {"enabled": True, "contrast": 1.08, "brightness": 1.05}
    elif "no bloom" in feedback_lower or "no glow" in feedback_lower:
        theme["effects"]["bloom"] = {"enabled": False}

    if any(w in feedback_lower for w in ["rain", "rainy", "cyberpunk rain"]):
        theme["effects"]["rain"] = {"enabled": True}
    elif "no rain" in feedback_lower or "remove rain" in feedback_lower:
        theme["effects"]["rain"] = {"enabled": False}

    if any(w in feedback_lower for w in ["flicker", "crt flicker"]):
        theme["effects"]["crtFlicker"] = {"enabled": True}
    elif "no flicker" in feedback_lower:
        theme["effects"]["crtFlicker"] = {"enabled": False}

    return theme

# System prompt for theme generation
SYSTEM_PROMPT = """You are a professional UI/UX designer specializing in color theory and theme design for financial applications.

You are creating themes for a stock analysis dashboard application. The themes must be:
1. Visually cohesive with good color harmony
2. Accessible with sufficient contrast (WCAG AA minimum)
3. Functional for data visualization (charts, indicators, price movements)
4. Consistent across all UI elements

IMPORTANT COLOR GUIDELINES:
- Background colors should form a clear hierarchy (primary > secondary > tertiary)
- Text colors must have sufficient contrast against their backgrounds
- Accent colors should be vibrant but not overwhelming
- Chart colors must be distinguishable from each other
- Price up/down colors should be clearly different (typically green/red family)
- Semantic colors (success, error, warning) should be intuitive

EFFECTS (optional):
- scanlines: Retro CRT effect (good for cyberpunk themes)
- vignette: Darkened edges (adds depth)
- crtFlicker: Subtle screen flicker (use sparingly)
- rain: Animated rain drops (for moody themes)
- bloom: Slight glow/contrast boost (for neon themes)

OUTPUT FORMAT:
Return ONLY valid JSON matching the theme schema. No markdown, no explanations outside the JSON.
The JSON should be complete and immediately usable.

CRITICAL: The color section MUST be named "variables" (not "colors"). This is required for CSS custom property mapping.

VARIABLE REFERENCE (all required):
Background: bg-primary, bg-secondary, bg-tertiary, bg-code
Text: text-primary, text-secondary, text-muted, text-inverted
Borders: border-primary, border-secondary
Accent: accent, accent-hover, accent-light, accent-bg, accent-bg-subtle
Status: success, error, warning, warning-light
Highlights: highlight-bg, highlight-text
Danger: danger-bg, danger-border
Star: star-color, star-bg, star-glow
Price: price-up, price-up-glow, price-down, price-down-glow
Audio: audio-active-bg
Music: music-active-color, music-active-bg, music-active-glow, viz-bar-color, viz-bar-glow
Buttons: btn-primary-bg, btn-primary-bg-hover, btn-primary-text, btn-primary-glow, btn-primary-glow-hover
Loader: loader-bg, loader-accent
Shadows: shadow-sm, shadow-md, shadow-lg, shadow-xl
Radius: radius-sm, radius-md, radius-lg
Tiles: tile-title-color, tile-title-transform, tile-title-spacing, tile-title-weight, tile-title-glow
Chart: chart-bg, chart-text, chart-grid, chart-axis, chart-line-primary, chart-line-secondary
Chart SMAs: chart-line-sma20, chart-line-sma50, chart-line-sma200
Chart Candles: chart-candle-up, chart-candle-down
Chart Volume: chart-volume-up, chart-volume-down
Chart Indicators: chart-rsi, chart-macd, chart-macd-signal, chart-stochastic, chart-stochastic-d
Chart Zones: chart-overbought, chart-oversold, chart-bollinger
Chart Glow: chart-line-glow, chart-line-glow-color, chart-line-glow-width
Chart Markers: chart-marker-up, chart-marker-down, chart-marker-up-outline, chart-marker-down-outline, chart-marker-symbol, chart-marker-size
Grid: grid-dot, grid-dot-active
Zoom: zoom-bg, zoom-border
Measure: measure-bg, measure-line
Placeholder: placeholder-bg, placeholder-border
Locked: locked-pattern"""


# Request/Response models
class GenerateRequest(BaseModel):
    prompt: str
    base_theme: Optional[str] = "dark"  # "dark" or "light"
    name: Optional[str] = None


class RefineRequest(BaseModel):
    theme: dict
    feedback: str


class ThemeResponse(BaseModel):
    theme: dict
    explanation: str


def create_theme_id(name: str) -> str:
    """Convert theme name to valid ID (lowercase, hyphens)."""
    return re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')


def merge_with_defaults(theme_vars: dict, base: str) -> dict:
    """Merge generated variables with defaults to ensure completeness."""
    defaults = DARK_BASE_DEFAULTS if base == "dark" else LIGHT_BASE_DEFAULTS
    merged = {**defaults, **theme_vars}
    return merged


def extract_json_from_response(text: str) -> dict:
    """Extract JSON from Claude's response, handling potential markdown wrapping."""
    # Try to find JSON block
    json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', text)
    if json_match:
        text = json_match.group(1)

    # Try to parse as-is first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try to find object boundaries
    start = text.find('{')
    end = text.rfind('}')
    if start != -1 and end != -1:
        try:
            return json.loads(text[start:end+1])
        except json.JSONDecodeError:
            pass

    raise ValueError("Could not extract valid JSON from response")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "theme-generator",
        "mode": "live" if LIVE_MODE else "mock"
    }


@app.post("/generate", response_model=ThemeResponse)
async def generate_theme(request: GenerateRequest):
    """Generate a new theme from a natural language prompt."""

    # Determine theme name and ID
    theme_name = request.name or "Custom Theme"
    theme_id = create_theme_id(theme_name)

    # MOCK MODE: Return pre-built theme without API call
    # In dev, this just matches keywords to pre-built themes.
    # For custom themes, ask Claude Code directly.
    if not LIVE_MODE:
        theme, matched = get_mock_theme(request.prompt, theme_name, request.base_theme)
        explanation = "[MOCK MODE] "
        if matched:
            explanation += f"Matched pre-built '{theme['name']}' theme based on keywords."
        else:
            explanation += "No keyword match - returned random theme. For custom themes, describe your vision to Claude Code in VS Code and paste the generated JSON."
        return ThemeResponse(
            theme=theme,
            explanation=explanation
        )

    # LIVE MODE: Call Anthropic API
    if not os.getenv("ANTHROPIC_API_KEY"):
        raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY not configured")

    # Build the prompt
    user_prompt = f"""Create a theme based on this description: {request.prompt}

Base this on a {request.base_theme} theme foundation.

Theme metadata:
- id: "{theme_id}"
- name: "{theme_name}"
- version: "1.0.0"
- category: "{request.base_theme}"

Store the original prompt in meta.originalPrompt.

Return the complete theme JSON with ALL variables filled in."""

    try:
        # Call Claude API
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=8192,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}]
        )

        # Extract the response text
        response_text = response.content[0].text
        print(f"DEBUG: Raw response length: {len(response_text)}")
        print(f"DEBUG: First 500 chars: {response_text[:500]}")

        # Parse the JSON
        theme = extract_json_from_response(response_text)
        print(f"DEBUG: Parsed theme keys: {list(theme.keys())}")

        # Handle Claude returning "colors" instead of "variables"
        if "colors" in theme and "variables" not in theme:
            theme["variables"] = theme.pop("colors")

        # Ensure the theme has required structure
        if "variables" not in theme:
            raise ValueError(f"Theme missing 'variables' section. Got keys: {list(theme.keys())}. Raw first 1000 chars: {response_text[:1000]}")

        # Merge with defaults to fill any gaps
        theme["variables"] = merge_with_defaults(
            theme.get("variables", {}),
            request.base_theme
        )

        # Ensure effects and fonts exist
        if "effects" not in theme:
            theme["effects"] = {}
        if "fonts" not in theme:
            theme["fonts"] = DEFAULT_FONTS.copy()

        # Store original prompt in meta
        if "meta" not in theme:
            theme["meta"] = {}
        theme["meta"]["originalPrompt"] = request.prompt

        return ThemeResponse(
            theme=theme,
            explanation=f"Generated '{theme_name}' theme based on: {request.prompt}"
        )

    except anthropic.APIError as e:
        raise HTTPException(status_code=500, detail=f"Claude API error: {str(e)}")
    except ValueError as e:
        raise HTTPException(status_code=500, detail=f"Failed to parse theme: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


@app.post("/refine", response_model=ThemeResponse)
async def refine_theme(request: RefineRequest):
    """Refine an existing theme based on feedback."""

    # Get original prompt if available
    original_prompt = request.theme.get("meta", {}).get("originalPrompt", "unknown")
    theme_name = request.theme.get("name", "Custom Theme")

    # MOCK MODE: Apply keyword-based modifications without API call
    if not LIVE_MODE:
        theme = apply_mock_refinement(request.theme, request.feedback)
        if "meta" not in theme:
            theme["meta"] = {}
        theme["meta"]["lastRefinement"] = request.feedback
        return ThemeResponse(
            theme=theme,
            explanation=f"[MOCK MODE] Refined '{theme_name}' based on: {request.feedback}"
        )

    # LIVE MODE: Call Anthropic API
    if not os.getenv("ANTHROPIC_API_KEY"):
        raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY not configured")

    # Build the refinement prompt
    user_prompt = f"""Here is the current theme JSON:

```json
{json.dumps(request.theme, indent=2)}
```

Original generation prompt was: "{original_prompt}"

Please refine this theme based on the following feedback:
{request.feedback}

Return the complete updated theme JSON with the refinements applied.
Keep the same id, name, and version. Update only what the feedback requests.
Maintain color harmony and accessibility."""

    try:
        # Call Claude API
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=8192,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}]
        )

        # Extract the response text
        response_text = response.content[0].text

        # Parse the JSON
        theme = extract_json_from_response(response_text)

        # Handle Claude returning "colors" instead of "variables"
        if "colors" in theme and "variables" not in theme:
            theme["variables"] = theme.pop("colors")

        # Ensure the theme has required structure
        if "variables" not in theme:
            raise ValueError("Theme missing 'variables' section")

        # Preserve original ID and name if not in response
        if "id" not in theme:
            theme["id"] = request.theme.get("id", "custom-theme")
        if "name" not in theme:
            theme["name"] = request.theme.get("name", "Custom Theme")

        # Ensure effects and fonts exist
        if "effects" not in theme:
            theme["effects"] = request.theme.get("effects", {})
        if "fonts" not in theme:
            theme["fonts"] = request.theme.get("fonts", DEFAULT_FONTS.copy())

        # Preserve original prompt, add refinement history
        if "meta" not in theme:
            theme["meta"] = {}
        theme["meta"]["originalPrompt"] = original_prompt

        return ThemeResponse(
            theme=theme,
            explanation=f"Refined '{theme_name}' based on: {request.feedback}"
        )

    except anthropic.APIError as e:
        raise HTTPException(status_code=500, detail=f"Claude API error: {str(e)}")
    except ValueError as e:
        raise HTTPException(status_code=500, detail=f"Failed to parse theme: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8001)
