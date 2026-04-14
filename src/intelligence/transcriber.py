"""
Speech-to-text using OpenAI Whisper (local, fully offline).
"""
import os
import sys
import tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import WHISPER_MODEL


class Transcriber:
    def __init__(self):
        import whisper
        print(f"[Transcriber] Loading Whisper '{WHISPER_MODEL}' model...")
        self._model = whisper.load_model(WHISPER_MODEL)
        print("[Transcriber] Ready.")

    def transcribe(self, pcm_data: bytes, recorder) -> str:
        """
        Transcribe raw PCM audio bytes.
        `recorder` is the AudioRecorder instance (used to convert PCM → WAV).
        """
        wav_path = recorder.pcm_to_wav(pcm_data)
        try:
            result = self._model.transcribe(
                wav_path,
                language="en",
                fp16=False,
                task="transcribe",
            )
            text = result.get("text", "").strip()
            return text
        finally:
            try:
                os.unlink(wav_path)
            except Exception:
                pass

    def transcribe_file(self, wav_path: str) -> str:
        """Transcribe a WAV file at the given path."""
        result = self._model.transcribe(
            wav_path,
            language="en",
            fp16=False,
            task="transcribe",
        )
        return result.get("text", "").strip()
