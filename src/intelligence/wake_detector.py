"""
Wake word detection.

Two backends:
  - "whisper"    : offline, transcribes 2-s chunks with Whisper tiny, checks for
                   "hey claude" / "hey, claude" / similar phrases.
  - "porcupine"  : Picovoice Porcupine — ultra-low CPU, fully offline, needs a
                   free access key from console.picovoice.ai and a custom
                   "Hey Claude" keyword file (.ppn).
"""
import time
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import (
    WAKE_WORD_ENGINE,
    WAKE_WORDS,
    CHUNK_SECONDS,
    PICOVOICE_ACCESS_KEY,
)


class WakeDetector:
    def __init__(self, recorder):
        self.recorder = recorder
        self.engine = WAKE_WORD_ENGINE
        self._model = None
        self._porcupine = None
        self._load_backend()

    def listen(self) -> bool:
        """
        Block until a wake word is heard.
        Returns True when detected.
        """
        if self.engine == "porcupine":
            return self._listen_porcupine()
        return self._listen_whisper()

    # ── Whisper backend ───────────────────────────────────────────────────────

    def _load_backend(self):
        if self.engine == "whisper":
            import whisper as _whisper
            print("[WakeDetector] Loading Whisper tiny for wake-word detection...")
            self._model = _whisper.load_model("tiny")
            print("[WakeDetector] Ready.")
        elif self.engine == "porcupine":
            self._load_porcupine()

    def _listen_whisper(self) -> bool:
        import tempfile
        import os
        while True:
            pcm = self.recorder.record_chunk(CHUNK_SECONDS)
            wav_path = self.recorder.pcm_to_wav(pcm)
            try:
                result = self._model.transcribe(
                    wav_path,
                    language="en",
                    fp16=False,
                    task="transcribe",
                )
                text = result.get("text", "").lower().strip()
                if any(w in text for w in WAKE_WORDS):
                    return True
            except Exception:
                pass
            finally:
                try:
                    os.unlink(wav_path)
                except Exception:
                    pass

    # ── Porcupine backend ─────────────────────────────────────────────────────

    def _load_porcupine(self):
        try:
            import pvporcupine
            # Look for a custom .ppn keyword file next to this script
            keyword_path = os.path.join(
                os.path.dirname(__file__), "..", "..", "keywords", "hey-claude.ppn"
            )
            if os.path.exists(keyword_path):
                self._porcupine = pvporcupine.create(
                    access_key=PICOVOICE_ACCESS_KEY,
                    keyword_paths=[keyword_path],
                )
            else:
                # Fallback to "hey google" built-in keyword as a stand-in
                self._porcupine = pvporcupine.create(
                    access_key=PICOVOICE_ACCESS_KEY,
                    keywords=["hey google"],
                )
                print(
                    "[WakeDetector] No hey-claude.ppn found — using 'hey google' "
                    "as wake word.\n"
                    "  → Create a custom keyword at console.picovoice.ai and save "
                    "it to keywords/hey-claude.ppn"
                )
        except ImportError:
            print("[WakeDetector] pvporcupine not installed — falling back to Whisper.")
            self.engine = "whisper"
            self._load_backend()

    def _listen_porcupine(self) -> bool:
        import pyaudio
        import struct
        pa = pyaudio.PyAudio()
        stream = pa.open(
            rate=self._porcupine.sample_rate,
            channels=1,
            format=pyaudio.paInt16,
            input=True,
            frames_per_buffer=self._porcupine.frame_length,
        )
        try:
            while True:
                pcm = stream.read(
                    self._porcupine.frame_length, exception_on_overflow=False
                )
                pcm = struct.unpack_from("h" * self._porcupine.frame_length, pcm)
                idx = self._porcupine.process(pcm)
                if idx >= 0:
                    return True
        finally:
            stream.stop_stream()
            stream.close()
            pa.terminate()
