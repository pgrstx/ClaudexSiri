"""
Wake word detection using a persistent audio stream (no mic flickering).

Two backends:
  - "whisper"    : offline, transcribes 2-s chunks with Whisper tiny.
  - "porcupine"  : ultra-low CPU, needs free Picovoice key + .ppn file.
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import WAKE_WORD_ENGINE, WAKE_WORDS, CHUNK_SECONDS, PICOVOICE_ACCESS_KEY


class WakeDetector:
    def __init__(self, recorder):
        self.recorder = recorder
        self.engine = WAKE_WORD_ENGINE
        self._model = None
        self._porcupine = None
        self._load_backend()

    def listen(self) -> bool:
        """Block until a wake word is heard. Returns True when detected."""
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
        """
        Read 2-second chunks from the ALREADY-OPEN recorder stream.
        No open/close — mic light stays solid.
        """
        while True:
            # read from persistent stream — no open/close
            pcm = self.recorder.read_seconds(CHUNK_SECONDS)
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
            keyword_path = os.path.join(
                os.path.dirname(__file__), "..", "..", "keywords", "hey-claude.ppn"
            )
            if os.path.exists(keyword_path):
                self._porcupine = pvporcupine.create(
                    access_key=PICOVOICE_ACCESS_KEY,
                    keyword_paths=[keyword_path],
                )
            else:
                self._porcupine = pvporcupine.create(
                    access_key=PICOVOICE_ACCESS_KEY,
                    keywords=["hey google"],
                )
                print("[WakeDetector] No hey-claude.ppn — using 'hey google' as wake word.")
        except ImportError:
            print("[WakeDetector] pvporcupine not installed — falling back to Whisper.")
            self.engine = "whisper"
            self._load_backend()

    def _listen_porcupine(self) -> bool:
        import struct
        while True:
            pcm = self.recorder.read_seconds(
                self._porcupine.frame_length / self._porcupine.sample_rate
            )
            pcm_ints = struct.unpack_from("h" * self._porcupine.frame_length, pcm)
            if self._porcupine.process(pcm_ints) >= 0:
                return True
