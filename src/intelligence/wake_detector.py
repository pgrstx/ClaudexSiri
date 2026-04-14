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
        Sliding-window wake word detection.
        Keeps a 3-second rolling buffer, advances by 0.5 s each step.
        This ensures "Hey Claude" is never split across chunk boundaries.
        """
        import collections
        from audio.recorder import CHUNK_SIZE
        from config import SAMPLE_RATE

        step_secs = 0.5          # how often we check
        window_secs = 3.0        # how much audio we transcribe each time
        step_frames = int(SAMPLE_RATE * step_secs)
        window_frames = int(SAMPLE_RATE * window_secs)

        # rolling deque of raw int16 bytes
        buf = collections.deque(maxlen=window_frames * 2)  # bytes, 2 bytes/sample

        while True:
            # read one step of audio from the persistent stream
            new_pcm = self.recorder.read_seconds(step_secs)
            buf.extend(new_pcm)

            if len(buf) < window_frames * 2:
                continue  # not enough audio yet

            window_pcm = bytes(list(buf)[-window_frames * 2:])
            wav_path = self.recorder.pcm_to_wav(window_pcm)
            try:
                result = self._model.transcribe(
                    wav_path,
                    language="en",
                    fp16=False,
                    task="transcribe",
                    condition_on_previous_text=False,
                )
                text = result.get("text", "").lower().strip()
                if text:
                    print(f"[Wake] heard: {text!r}", end="\r", flush=True)
                if self._matches_wake_word(text):
                    print()  # newline after the \r
                    return True
            except Exception:
                pass
            finally:
                try:
                    os.unlink(wav_path)
                except Exception:
                    pass

    @staticmethod
    def _matches_wake_word(text: str) -> bool:
        """
        Fuzzy match — Whisper tiny often mishears 'claude' as
        'cloud', 'clod', 'claud', 'claudia', etc.
        """
        # exact phrases
        triggers = [
            "hey claude", "hey, claude", "okay claude", "ok claude",
            "hey claud", "hey cloud", "hey clod", "hey clade",
            "a claude", "hey claudia", "hey clot",
            "hey kloud", "hey klod",
        ]
        if any(t in text for t in triggers):
            return True
        # just "claude" said alone (short utterance)
        words = text.split()
        if len(words) <= 3 and any(
            w in ("claude", "claud", "cloud", "claudia") for w in words
        ):
            return True
        return False

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
