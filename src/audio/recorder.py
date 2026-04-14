"""
Audio recording with a single persistent microphone stream.
One stream stays open the whole time — no mic flickering.
"""
import wave
import tempfile
import numpy as np
import pyaudio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import SAMPLE_RATE, CHANNELS, COMMAND_MAX_SECONDS, SILENCE_SECONDS

CHUNK_SIZE = 1024


class AudioRecorder:
    def __init__(self):
        self.pa = pyaudio.PyAudio()
        self._stream = None
        self._energy_threshold = 500  # updated after first calibration
        self._open_stream()

    # ── Stream lifecycle ──────────────────────────────────────────────────────

    def _open_stream(self):
        """Open ONE persistent stream. Called once at startup."""
        if self._stream and not self._stream.is_stopped():
            return
        self._stream = self.pa.open(
            format=pyaudio.paInt16,
            channels=CHANNELS,
            rate=SAMPLE_RATE,
            input=True,
            frames_per_buffer=CHUNK_SIZE,
        )
        self._calibrate()

    def _calibrate(self, duration: float = 0.6):
        """Sample ambient noise to set dynamic silence threshold."""
        n = int(SAMPLE_RATE / CHUNK_SIZE * duration)
        energies = []
        for _ in range(n):
            data = self._stream.read(CHUNK_SIZE, exception_on_overflow=False)
            energies.append(self._rms(data))
        ambient = float(np.mean(energies))
        self._energy_threshold = max(ambient * 2.5, 300)

    # ── Public API ────────────────────────────────────────────────────────────

    def read_seconds(self, seconds: float) -> bytes:
        """Read a fixed duration of audio from the open stream."""
        n = int(SAMPLE_RATE / CHUNK_SIZE * seconds)
        frames = []
        for _ in range(n):
            frames.append(
                self._stream.read(CHUNK_SIZE, exception_on_overflow=False)
            )
        return b"".join(frames)

    def record_command(self) -> bytes:
        """
        Record until SILENCE_SECONDS of silence or COMMAND_MAX_SECONDS.
        Uses the already-open stream — no mic toggle.
        """
        max_chunks = int(SAMPLE_RATE / CHUNK_SIZE * COMMAND_MAX_SECONDS)
        silence_chunks = int(SAMPLE_RATE / CHUNK_SIZE * SILENCE_SECONDS)

        frames = []
        silent_chunks = 0
        speaking_started = False

        for _ in range(max_chunks):
            data = self._stream.read(CHUNK_SIZE, exception_on_overflow=False)
            frames.append(data)
            energy = self._rms(data)

            if energy > self._energy_threshold:
                speaking_started = True
                silent_chunks = 0
            elif speaking_started:
                silent_chunks += 1
                if silent_chunks >= silence_chunks:
                    break

        return b"".join(frames)

    def pcm_to_wav(self, pcm_data: bytes) -> str:
        """Save PCM bytes to a temp WAV file and return the path."""
        tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        with wave.open(tmp.name, "wb") as wf:
            wf.setnchannels(CHANNELS)
            wf.setsampwidth(2)
            wf.setframerate(SAMPLE_RATE)
            wf.writeframes(pcm_data)
        return tmp.name

    def close(self):
        if self._stream:
            self._stream.stop_stream()
            self._stream.close()
        self.pa.terminate()

    # ── Helper ────────────────────────────────────────────────────────────────

    def _rms(self, data: bytes) -> float:
        arr = np.frombuffer(data, dtype=np.int16).astype(np.float32)
        return float(np.sqrt(np.mean(arr ** 2))) if len(arr) > 0 else 0.0
