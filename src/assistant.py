"""
Core assistant orchestrator.
Wake word → Record → Transcribe → Route → Act → Speak
"""
import subprocess
import threading
import time
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from config import WAKE_SOUND, DONE_SOUND, ERROR_SOUND
from audio.recorder import AudioRecorder
from audio.tts import Speaker
from intelligence.wake_detector import WakeDetector
from intelligence.transcriber import Transcriber
from intelligence.claude_client import ClaudeClient
from actions.system_actions import execute as run_action


class Assistant:
    def __init__(self, status_callback=None):
        """
        status_callback(state: str) — called with:
          "idle", "listening", "thinking", "speaking", "error"
        """
        self._status_cb = status_callback or (lambda s: None)
        self._running = False
        self._paused = False

        print("[Assistant] Initializing audio...")
        self.recorder = AudioRecorder()
        self.speaker = Speaker()

        print("[Assistant] Initializing intelligence...")
        self.transcriber = Transcriber()
        self.claude = ClaudeClient()
        self.wake = WakeDetector(self.recorder)

        print("[Assistant] All systems ready.\n")

    # ── Public control ────────────────────────────────────────────────────────

    def start(self):
        """Start the assistant in a background thread."""
        self._running = True
        t = threading.Thread(target=self._loop, daemon=True)
        t.start()

    def stop(self):
        self._running = False
        self.recorder.close()

    def pause(self):
        self._paused = True
        self._set_status("idle")

    def resume(self):
        self._paused = False

    def clear_context(self):
        """Reset conversation history."""
        self.claude.clear_history()

    # ── Main loop ─────────────────────────────────────────────────────────────

    def _loop(self):
        self._set_status("idle")
        print("[Assistant] Listening for 'Hey Claude'...")

        while self._running:
            if self._paused:
                time.sleep(0.5)
                continue

            # ── 1. Wait for wake word ──────────────────────────────────────
            self._set_status("idle")
            detected = self.wake.listen()
            if not detected:
                continue

            # ── 2. Acknowledge ─────────────────────────────────────────────
            self._play_sound(WAKE_SOUND)
            self._set_status("listening")
            print("[Assistant] Wake word detected! Recording command...")

            # ── 3. Record command ──────────────────────────────────────────
            try:
                pcm = self.recorder.record_command()
            except Exception as e:
                print(f"[Assistant] Recording error: {e}")
                self._play_sound(ERROR_SOUND)
                continue

            # ── 4. Transcribe ──────────────────────────────────────────────
            self._set_status("thinking")
            print("[Assistant] Transcribing...")
            try:
                text = self.transcriber.transcribe(pcm, self.recorder)
            except Exception as e:
                print(f"[Assistant] Transcription error: {e}")
                self.speaker.say("Sorry, I didn't catch that.")
                self._play_sound(ERROR_SOUND)
                continue

            if not text:
                self.speaker.say("I didn't hear anything. Try again.")
                continue

            print(f"[Assistant] You said: {text!r}")

            # ── 5. Route through Claude ────────────────────────────────────
            print("[Assistant] Thinking...")
            try:
                response = self.claude.process(text)
            except Exception as e:
                print(f"[Assistant] Claude error: {e}")
                self.speaker.say("I ran into an issue. Please try again.")
                self._play_sound(ERROR_SOUND)
                continue

            speech = response.get("speech", "")
            action = response.get("action", {})
            action_type = action.get("type", "none")
            params = action.get("params", {})

            print(f"[Assistant] Intent: {action_type}")
            print(f"[Assistant] Speech: {speech!r}")

            # ── 6. Speak response ──────────────────────────────────────────
            self._set_status("speaking")
            if speech:
                self.speaker.say(speech, blocking=False)

            # ── 7. Execute action ──────────────────────────────────────────
            if action_type not in ("none", "code", "cowork"):
                try:
                    status = run_action(action_type, params)
                    print(f"[Assistant] Action result: {status}")
                except Exception as e:
                    print(f"[Assistant] Action error: {e}")

            elif action_type == "code":
                self._handle_code(params.get("task", text))

            elif action_type == "cowork":
                self._handle_cowork(params.get("task", text))

            self._play_sound(DONE_SOUND)

    # ── Special intent handlers ───────────────────────────────────────────────

    def _handle_code(self, task: str):
        """Generate code and show it in a Terminal window."""
        print(f"[Assistant] Code task: {task}")
        code = self.claude.code_mode(task)
        # Write to a temp file and open in TextEdit / preferred editor
        import tempfile
        tmp = tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False, prefix="claude_code_"
        )
        tmp.write(code)
        tmp.close()
        subprocess.run(["open", tmp.name], check=False)
        self.speaker.say("I've written the code and opened it for you.")

    def _handle_cowork(self, task: str):
        """Placeholder for computer-use cowork mode."""
        print(f"[Assistant] Cowork task: {task}")
        self.speaker.say(
            "Cowork mode is coming soon. For now, you can describe what you need "
            "and I'll guide you step by step."
        )

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _set_status(self, state: str):
        self._status_cb(state)

    def _play_sound(self, path: str):
        subprocess.run(["afplay", path], check=False, capture_output=True)
