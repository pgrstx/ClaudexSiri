"""
ClaudexSiri — macOS menu bar entry point.
Run with:  python src/main.py
"""
import sys
import os
import threading

# ── Dependency check before heavy imports ─────────────────────────────────────
def _check_deps():
    missing = []
    for pkg in ["rumps", "anthropic", "whisper", "pyaudio", "numpy", "dotenv"]:
        try:
            __import__(pkg)
        except ImportError:
            missing.append(pkg)
    if missing:
        print(
            f"Missing packages: {', '.join(missing)}\n"
            "Run:  pip install -r requirements.txt"
        )
        sys.exit(1)

_check_deps()

import rumps
import anthropic

sys.path.insert(0, os.path.dirname(__file__))
from assistant import Assistant

# ── Status icons ──────────────────────────────────────────────────────────────
ICONS = {
    "idle":      "🎙",
    "listening": "👂",
    "thinking":  "🧠",
    "speaking":  "🔊",
    "error":     "⚠️",
    "paused":    "⏸",
}


class ClaudexSiriApp(rumps.App):
    def __init__(self):
        super().__init__("🎙 Hey Claude", quit_button=None)
        self.menu = [
            rumps.MenuItem("Status: Idle"),
            None,  # separator
            rumps.MenuItem("Pause / Resume", callback=self.toggle_pause),
            rumps.MenuItem("Clear Context", callback=self.clear_context),
            rumps.MenuItem("Settings", callback=self.open_settings),
            None,
            rumps.MenuItem("Quit Hey Claude", callback=self.quit_app),
        ]
        self._status_item = self.menu["Status: Idle"]
        self._paused = False

        # Start assistant in background
        self._assistant = Assistant(status_callback=self._on_status)
        threading.Thread(target=self._assistant.start, daemon=True).start()

    # ── Menu callbacks ────────────────────────────────────────────────────────

    def toggle_pause(self, _):
        if self._paused:
            self._assistant.resume()
            self._paused = False
            self.title = ICONS["idle"] + " Hey Claude"
            self._status_item.title = "Status: Listening"
        else:
            self._assistant.pause()
            self._paused = True
            self.title = ICONS["paused"] + " Hey Claude"
            self._status_item.title = "Status: Paused"

    def clear_context(self, _):
        self._assistant.clear_context()
        rumps.notification(
            "Hey Claude",
            "Context cleared",
            "Conversation history reset.",
        )

    def open_settings(self, _):
        env_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), ".env"
        )
        if not os.path.exists(env_path):
            env_example = env_path + "example" if os.path.exists(env_path + "example") else None
            if env_example:
                import shutil
                shutil.copy(env_example, env_path)
        os.system(f"open -a TextEdit {env_path!r}")

    def quit_app(self, _):
        self._assistant.stop()
        rumps.quit_application()

    # ── Status updates from assistant thread ──────────────────────────────────

    def _on_status(self, state: str):
        icon = ICONS.get(state, "🎙")
        # rumps UI updates must be minimal from non-main threads
        self.title = f"{icon} Hey Claude"
        if self._status_item:
            self._status_item.title = f"Status: {state.capitalize()}"


# ── CLI fallback (no menu bar) ────────────────────────────────────────────────

def run_cli():
    """Run in terminal without menu bar (useful for debugging)."""
    import signal

    print("╔══════════════════════════════════╗")
    print("║     Hey Claude — Voice Mode      ║")
    print("╚══════════════════════════════════╝")
    print("Say 'Hey Claude' to wake up.\nCtrl-C to exit.\n")

    assistant = Assistant()
    assistant.start()

    # Keep the main thread alive; survive SIGHUP (terminal close)
    signal.signal(signal.SIGHUP, signal.SIG_IGN)

    try:
        while True:
            import time
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nGoodbye!")
        assistant.stop()


if __name__ == "__main__":
    if "--cli" in sys.argv:
        run_cli()
    else:
        ClaudexSiriApp().run()
