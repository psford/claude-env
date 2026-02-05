"""
Theme Generator Service
FastAPI sidecar that uses Claude API to generate and refine theme JSON.

Usage:
    cd helpers
    .\\theme-generator-env\\Scripts\\Activate.ps1
    uvicorn theme_generator:app --port 8001
"""

import json
import os
import re
from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
import anthropic

from theme_schema import (
    THEME_SCHEMA,
    DARK_BASE_DEFAULTS,
    LIGHT_BASE_DEFAULTS,
    DEFAULT_FONTS
)

# Load environment variables from project root
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))

# Initialize FastAPI
app = FastAPI(
    title="Theme Generator",
    description="AI-powered theme generation for Stock Analyzer",
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

# Initialize Anthropic client
client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

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
    return {"status": "healthy", "service": "theme-generator"}


@app.post("/generate", response_model=ThemeResponse)
async def generate_theme(request: GenerateRequest):
    """Generate a new theme from a natural language prompt."""

    if not os.getenv("ANTHROPIC_API_KEY"):
        raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY not configured")

    # Determine theme name and ID
    theme_name = request.name or f"Custom Theme"
    theme_id = create_theme_id(theme_name)

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

    if not os.getenv("ANTHROPIC_API_KEY"):
        raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY not configured")

    # Get original prompt if available
    original_prompt = request.theme.get("meta", {}).get("originalPrompt", "unknown")
    theme_name = request.theme.get("name", "Custom Theme")

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
