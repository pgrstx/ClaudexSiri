"""
Claude API client with conversation history support.
"""
import os
import sys
import json
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import CLAUDE_MODEL, ANTHROPIC_API_KEY
import anthropic

SYSTEM_PROMPT = """\
You are Claude, an AI voice assistant running on macOS — the user's replacement for Siri.

When given a transcribed voice command, you must:
1. Understand the intent.
2. Decide what action (if any) to take on macOS.
3. Reply ONLY with a JSON object in this exact schema:

{
  "speech": "<what you say aloud — conversational, concise, no markdown>",
  "action": {
    "type": "<one of: none | open_app | quit_app | system_control | timer | reminder | search | music | message | code | cowork>",
    "params": { ... }
  }
}

Action params by type:
  open_app        → {"app": "Spotify"}
  quit_app        → {"app": "Zoom"}
  system_control  → {"control": "volume|brightness|wifi|bluetooth|dark_mode|do_not_disturb", "value": <0-100 or true/false>}
  timer           → {"minutes": 5, "label": "pasta"}
  reminder        → {"text": "Call mom", "time": "5pm"}
  search          → {"query": "best coffee in SF"}
  music           → {"action": "play|pause|next|previous|volume", "query": "Daft Punk", "value": 70}
  message         → {"to": "Mom", "text": "On my way!", "app": "Messages"}
  code            → {"task": "full user request verbatim"}
  cowork          → {"task": "full user request verbatim"}
  none            → {}

Rules:
- For general conversation / questions → type "none", put full answer in "speech".
- Keep "speech" under 3 sentences unless the user asks for detail.
- Never include markdown, bullet points, or code fences in "speech".
- "code" intent means the user wants code written. Put the task in params, keep speech brief.
- "cowork" means the user wants you to control the computer (computer-use style tasks).
- Only output the JSON object — no prose before or after it.
"""


class ClaudeClient:
    def __init__(self):
        self._client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        self._history: list[dict] = []

    # ── Public API ────────────────────────────────────────────────────────────

    def process(self, user_text: str) -> dict:
        """
        Send a voice command to Claude and return the parsed response dict.
        Maintains conversation history for context.
        """
        self._history.append({"role": "user", "content": user_text})

        response = self._client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=self._history,
        )

        raw = response.content[0].text.strip()
        self._history.append({"role": "assistant", "content": raw})

        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            # If Claude didn't follow the schema, treat it as plain chat
            return {
                "speech": raw,
                "action": {"type": "none", "params": {}},
            }

    def clear_history(self):
        """Reset conversation context."""
        self._history.clear()

    def code_mode(self, task: str) -> str:
        """
        Extended code generation — no history, full response, returns raw text.
        Used when action type is "code".
        """
        response = self._client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=4096,
            messages=[{"role": "user", "content": task}],
        )
        return response.content[0].text.strip()
