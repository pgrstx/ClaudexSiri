# ClaudexSiri — Hey Claude, macOS Voice Assistant

Replace Siri with Claude. Say **"Hey Claude"** and your Mac listens.

## Features

| What you say | What happens |
|---|---|
| "Hey Claude, open Spotify" | Opens Spotify |
| "Hey Claude, set a 10 minute pasta timer" | Background timer with notification |
| "Hey Claude, set volume to 40" | Sets system volume |
| "Hey Claude, turn on dark mode" | Toggles dark mode |
| "Hey Claude, remind me to call mom at 5pm" | Creates a Reminder |
| "Hey Claude, search for best sushi in NYC" | Opens Google search |
| "Hey Claude, message Sarah I'm on my way" | Sends iMessage |
| "Hey Claude, write a Python function that..." | Opens code in editor |
| "Hey Claude, what's the capital of France?" | Answers conversationally |

## Quick Start

```bash
git clone https://github.com/pgrstx/ClaudexSiri
cd ClaudexSiri
chmod +x setup.sh && ./setup.sh
# Edit .env — add your ANTHROPIC_API_KEY
source .venv/bin/activate
python src/main.py
```

## Architecture

```
src/
├── main.py                   # macOS menu bar app (rumps)
├── assistant.py              # Main orchestration loop
├── config.py                 # All settings
├── audio/
│   ├── recorder.py           # PyAudio capture + VAD
│   └── tts.py                # macOS say(1) TTS
├── intelligence/
│   ├── wake_detector.py      # "Hey Claude" detection (Whisper or Porcupine)
│   ├── transcriber.py        # Whisper speech-to-text
│   └── claude_client.py      # Anthropic API + intent routing
└── actions/
    └── system_actions.py     # macOS AppleScript / shell actions
```

**Pipeline:** Wake word → Record → Whisper STT → Claude intent routing → macOS action + TTS response

## Wake Word Engines

| Engine | Setup | CPU | Offline |
|---|---|---|---|
| **whisper** (default) | None | Medium | Yes |
| **porcupine** | Free key at console.picovoice.ai | Very low | Yes |

To use Porcupine: set `WAKE_WORD_ENGINE=porcupine` and `PICOVOICE_ACCESS_KEY=...` in `.env`, then download a custom `hey-claude.ppn` keyword from the Picovoice Console and place it at `keywords/hey-claude.ppn`.

## Configuration

All settings live in `.env` (copy from `.env.example`):

```env
ANTHROPIC_API_KEY=sk-ant-...
WHISPER_MODEL=base          # tiny | base | small
WAKE_WORD_ENGINE=whisper    # whisper | porcupine
TTS_VOICE=Samantha          # macOS voice (say -v '?' to list)
TTS_RATE=210
```

## Requirements

- macOS 13+
- Python 3.11+
- Homebrew (`portaudio`, `brightness`, `blueutil`)
- Anthropic API key
