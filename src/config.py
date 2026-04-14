"""
ClaudexSiri Configuration
"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ── API Keys ──────────────────────────────────────────────────────────────────
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
PICOVOICE_ACCESS_KEY = os.getenv("PICOVOICE_ACCESS_KEY", "")  # optional

# ── Wake Word ─────────────────────────────────────────────────────────────────
# "whisper"    – fully offline, uses tiny Whisper model, no API key needed
# "porcupine"  – ultra-low CPU, needs free Picovoice key (picovoice.ai)
WAKE_WORD_ENGINE = os.getenv("WAKE_WORD_ENGINE", "whisper")
WAKE_WORDS = ["hey claude", "hey, claude", "okay claude", "ok claude"]

# ── Speech-to-Text ────────────────────────────────────────────────────────────
# tiny  – fastest, lowest accuracy
# base  – good balance (default)
# small – better accuracy, slower
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "base")

# ── Claude ────────────────────────────────────────────────────────────────────
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-opus-4-6")

# ── Text-to-Speech ────────────────────────────────────────────────────────────
# macOS voices: Samantha (US), Karen (AU), Daniel (UK), Moira (IE)
TTS_VOICE = os.getenv("TTS_VOICE", "Samantha")
TTS_RATE = int(os.getenv("TTS_RATE", "210"))  # words per minute

# ── Audio ─────────────────────────────────────────────────────────────────────
SAMPLE_RATE = 16000
CHANNELS = 1
CHUNK_SECONDS = 2          # seconds of audio per wake-word detection chunk
COMMAND_MAX_SECONDS = 20   # max recording time for a command
SILENCE_SECONDS = 1.2      # silence after speech = end of command

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent.parent
SOUNDS_DIR = BASE_DIR / "sounds"

# macOS system sound for feedback
WAKE_SOUND = "/System/Library/Sounds/Ping.aiff"
DONE_SOUND = "/System/Library/Sounds/Pop.aiff"
ERROR_SOUND = "/System/Library/Sounds/Basso.aiff"
