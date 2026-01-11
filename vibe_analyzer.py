import anthropic
import base64
import json
import re
from pathlib import Path

from models import VibeResult


async def analyze_vibe(image_path: Path, anthropic_api_key: str) -> VibeResult:
    """
    Analyze an image using Claude's vision capabilities and return a vibe score.
    
    Args:
        image_path: Path to the image file
        anthropic_api_key: Anthropic API key
        
    Returns:
        VibeResult with score (1-10) and funny explanation
    """
    # Read and encode the image
    with open(image_path, "rb") as f:
        image_data = base64.standard_b64encode(f.read()).decode("utf-8")
    
    # Determine media type
    suffix = image_path.suffix.lower()
    media_type_map = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".gif": "image/gif",
        ".webp": "image/webp",
        ".heic": "image/heic",
    }
    media_type = media_type_map.get(suffix, "image/jpeg")
    
    client = anthropic.Anthropic(api_key=anthropic_api_key)
    
    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": image_data,
                        },
                    },
                    {
                        "type": "text",
                        "text": """You are a hilarious "vibe check" judge at a fun iOS development workshop. 
                        
Analyze this photo and give it a VIBE SCORE from 1-10, along with a SHORT, FUNNY explanation (1-2 sentences max).

Be playful, witty, and roast-y but keep it light and fun - nothing mean-spirited. Think of it like a friendly roast between developer friends.

Examples of the tone we're going for:
- "7/10: This person definitely mass-assigns as their first solution to app crashes"
- "4/10: Looks like they mass-assigned their fashion sense too"
- "9/10: Main character energy. Probably mass-assigns their way through life and it works"
- "6/10: The lighting says 'I know what I'm doing' but the angle says 'first try'"

Respond with ONLY valid JSON in this exact format (no other text):
{"score": <number 1-10>, "explanation": "<your funny 1-2 sentence explanation>"}"""
                    }
                ],
            }
        ],
    )
    
    # Parse the response
    response_text = message.content[0].text.strip()
    
    # Try to extract JSON from the response
    try:
        # First try direct parse
        data = json.loads(response_text)
    except json.JSONDecodeError:
        # Try to find JSON in the response
        json_match = re.search(r'\{[^}]+\}', response_text)
        if json_match:
            data = json.loads(json_match.group())
        else:
            # Fallback if parsing fails
            return VibeResult(
                score=5,
                explanation="This photo broke my vibe-o-meter. That's either really good or really bad."
            )
    
    # Validate and clamp score
    score = max(1, min(10, int(data.get("score", 5))))
    explanation = data.get("explanation", "No explanation available.")
    
    return VibeResult(score=score, explanation=explanation)



