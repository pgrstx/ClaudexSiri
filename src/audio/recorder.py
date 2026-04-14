"""
Audio recording with voice-activity detection.
Records until SILENCE_SECONDS of silence detected or max duration reached.
"""
import io
import wave
import tempfile
import threading
import time
import numpy as np
import pyaudio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import SAMPLE_RATE, CHANNELS, COMMAND_MAX_SECONDS, SILENCE_SECONDS


class AudioRecorder:
    def __init__(self):
        self.pa = pyaudio.PyAudio()

    # ── Public API ────────────────────────────────────────────────────────────

    def record_command(self) -> bytes:
        """
        Record a voice command.
        Stops when silence is detected or max duration is reached.
        Returns raw PCM bytes (16-bit, 16 kHz, mono).
        """
        chunk_size = 1024
        stream = self.pa.open(
            format=pyaudio.paInt16,
            channels=CHANNELS,
            rate=SAMPLE_RATE,
            input=True,
            frames_per_buffer=chunk_size,
        )

        frames = []
        silent_chunks = 0
        speaking_started = False
        max_chunks = int(SAMPLE_RATE / chunk_size * COMMAND_MAX_SECONDS)
        silence_chunks = int(SAMPLE_RATE / chunk_size * SILENCE_SECONDS)
        energy_threshold = self._calibrate_threshold(stream, chunk_size)

        try:
            for _ in range(max_chunks):
                data = stream.read(chunk_size, exception_on_overflow=False)
                frames.append(data)
                energy = self._rms(data)

                if energy > energy_threshold:
                    speaking_started = True
                    silent_chunks = 0
                elif speaking_started:
                    silent_chunks += 1
                    if silent_chunks >= silence_chunks:
                        break
        finally:
            stream.stop_stream()
            stream.close()

        return b"".join(frames)

    def record_chunk(self, seconds: float) -> bytes:
        """Record a fixed-duration chunk (used for wake-word detection)."""
        chunk_size = 1024
        num_chunks = int(SAMPLE_RATE / chunk_size * seconds)
        stream = self.pa.open(
            format=pyaudio.paInt16,
            channels=CHANNELS,
            rate=SAMPLE_RATE,
            input=True,
            frames_per_buffer=chunk_size,
        )
        frames = []
        try:
            for _ in range(num_chunks):
                data = stream.read(chunk_size, exception_on_overflow=False)
                frames.append(data)
        finally:
            stream.stop_stream()
            stream.close()
        return b"".join(frames)

    def pcm_to_wav(self, pcm_data: bytes) -> str:
        """Save PCM bytes to a temp WAV file and return the path."""
        tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        with wave.open(tmp.name, "wb") as wf:
            wf.setnchannels(CHANNELS)
            wf.setsampwidth(2)  # 16-bit = 2 bytes
            wf.setframerate(SAMPLE_RATE)
            wf.writeframes(pcm_data)
        return tmp.name

    def close(self):
        self.pa.terminate()

    # ── Private helpers ───────────────────────────────────────────────────────

    def _rms(self, data: bytes) -> float:
        arr = np.frombuffer(data, dtype=np.int16).astype(np.float32)
        return float(np.sqrt(np.mean(arr ** 2))) if len(arr) > 0 else 0.0

    def _calibrate_threshold(self, stream, chunk_size: int, duration: float = 0.5) -> float:
        """Sample ambient noise and set a dynamic silence threshold."""
        energies = []
        for _ in range(int(SAMPLE_RATE / chunk_size * duration)):
            data = stream.read(chunk_size, exception_on_overflow=False)
            energies.append(self._rms(data))
        ambient = float(np.mean(energies))
        return max(ambient * 2.5, 300)  # at least 300 RMS
