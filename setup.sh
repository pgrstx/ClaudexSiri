#!/bin/bash
set -e

echo "╔══════════════════════════════════════╗"
echo "║   ClaudexSiri — Setup               ║"
echo "╚══════════════════════════════════════╝"

# Python version check
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "Python: $python_version"

# Create and activate venv
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi
source .venv/bin/activate

# Install PortAudio (required by pyaudio)
if ! brew list portaudio &>/dev/null; then
    echo "Installing PortAudio via Homebrew..."
    brew install portaudio
fi

# Optional tools
echo "Installing optional macOS tools..."
brew install brightness blueutil 2>/dev/null || true

# Install Python deps
echo "Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Copy .env if not present
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo ""
    echo "⚠️  Edit .env and add your ANTHROPIC_API_KEY"
fi

echo ""
echo "✅ Setup complete!"
echo ""
echo "To start Hey Claude:"
echo "  source .venv/bin/activate"
echo "  python src/main.py          # menu bar app"
echo "  python src/main.py --cli    # terminal mode (debug)"
echo ""
echo "To add to Login Items (auto-start):"
echo "  System Settings → General → Login Items → add ClaudexSiri"
