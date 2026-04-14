"""
Text-to-speech using macOS `say` command.
Supports streaming (sentence-by-sentence) for faster perceived response.
"""
import subprocess
import threading
import queue
import re
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import TTS_VOICE, TTS_RATE


class Speaker:
    def __init__(self):
        self.voice = TTS_VOICE
        self.rate = TTS_RATE
        self._queue: queue.Queue = queue.Queue()
        self._stop = threading.Event()
        self._worker = threading.Thread(target=self._run, daemon=True)
        self._worker.start()

    # ── Public API ────────────────────────────────────────────────────────────

    def say(self, text: str, blocking: bool = False):
        """Speak text. Non-blocking by default."""
        text = text.strip()
        if not text:
            return
        self._queue.put(text)
        if blocking:
            self._queue.join()

    def say_stream(self, text: str):
        """
        Split text into sentences and enqueue each so speech starts
        before the full response is received (useful for long Claude replies).
        """
        for sentence in self._split_sentences(text):
            self.say(sentence)

    def stop(self):
        """Stop current speech immediately."""
        self._stop.set()
        subprocess.run(["pkill", "-x", "say"], capture_output=True)
        self._stop.clear()

    def set_voice(self, voice: str):
        self.voice = voice

    # ── Internal ──────────────────────────────────────────────────────────────

    def _run(self):
        while True:
            text = self._queue.get()
            if not self._stop.is_set():
                try:
                    subprocess.run(
                        ["say", "-v", self.voice, "-r", str(self.rate), text],
                        check=False,
                    )
                except Exception:
                    pass
            self._queue.task_done()

    @staticmethod
    def _split_sentences(text: str) -> list[str]:
        """Split text on sentence boundaries, keeping punctuation."""
        parts = re.split(r"(?<=[.!?])\s+", text.strip())
        return [p for p in parts if p]
