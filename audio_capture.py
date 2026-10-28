import io
import time
from pathlib import Path
from typing import Optional, Tuple
import numpy as np

try:
    import soundcard as sc
    import soundfile as sf
    _AUDIO_SUPPORTED = True
except ImportError:
    _AUDIO_SUPPORTED = False

def is_audio_available() -> bool:
    """ÐŸÑ€Ð¾Ð²ÐµÑ€ÑÐµÑ‚, Ð´Ð¾ÑÑ‚ÑƒÐ¿ÐµÐ½ Ð»Ð¸ Ð·Ð°Ñ…Ð²Ð°Ñ‚ ÑÐ¸ÑÑ‚ÐµÐ¼Ð½Ð¾Ð³Ð¾ Ð·Ð²ÑƒÐºÐ° (loopback) Ð½Ð° Ð´Ð°Ð½Ð½Ð¾Ð¼ ÐºÐ¾Ð¼Ð¿ÑŒÑŽÑ‚ÐµÑ€Ðµ."""
    if not _AUDIO_SUPPORTED:
        return False
    try:
        speaker = sc.default_speaker()
        if not speaker:
            return False
        mic = sc.get_microphone(id=str(speaker.name), include_loopback=True)
        return mic is not None
    except Exception:
        return False

def record_system_audio(
    duration: float = 5.0,
    sample_rate: int = 16000
) -> Optional[Tuple[bytes, float]]:
    """
    Ð—Ð°Ñ…Ð²Ð°Ñ‚Ñ‹Ð²Ð°ÐµÑ‚ ÑÐ¸ÑÑ‚ÐµÐ¼Ð½Ñ‹Ð¹ Ð·Ð²ÑƒÐº (Ð·Ð²ÑƒÐº Ð¸Ð· Ð±Ñ€Ð°ÑƒÐ·ÐµÑ€Ð°/ÑÐ°Ð¹Ñ‚Ð° Ñ‡ÐµÑ€ÐµÐ· WASAPI loopback).
    
    ÐŸÐ°Ñ€Ð°Ð¼ÐµÑ‚Ñ€Ñ‹:
        duration: Ð”Ð»Ð¸Ñ‚ÐµÐ»ÑŒÐ½Ð¾ÑÑ‚ÑŒ Ð·Ð°Ð¿Ð¸ÑÐ¸ Ð² ÑÐµÐºÑƒÐ½Ð´Ð°Ñ… (Ð¿Ð¾ ÑƒÐ¼Ð¾Ð»Ñ‡Ð°Ð½Ð¸ÑŽ 5.0).
        sample_rate: Ð§Ð°ÑÑ‚Ð¾Ñ‚Ð° Ð´Ð¸ÑÐºÑ€ÐµÑ‚Ð¸Ð·Ð°Ñ†Ð¸Ð¸ (16000 Ð“Ñ† Ð¾Ð¿Ñ‚Ð¸Ð¼Ð°Ð»ÑŒÐ½Ð° Ð´Ð»Ñ Gemini Speech/Audio).
        
    Ð’Ð¾Ð·Ð²Ñ€Ð°Ñ‰Ð°ÐµÑ‚:
        ÐšÐ¾Ñ€Ñ‚ÐµÐ¶ (wav_bytes, rms_volume) Ð¸Ð»Ð¸ None Ð¿Ñ€Ð¸ Ð¾ÑˆÐ¸Ð±ÐºÐµ:
        - wav_bytes: ÐÑƒÐ´Ð¸Ð¾Ð·Ð°Ð¿Ð¸ÑÑŒ Ð² Ñ„Ð¾Ñ€Ð¼Ð°Ñ‚Ðµ WAV (PCM 16-bit, Ð¼Ð¾Ð½Ð¾).
        - rms_volume: Ð¡Ñ€ÐµÐ´Ð½ÐµÐºÐ²Ð°Ð´Ñ€Ð°Ñ‚Ð¸Ñ‡Ð½Ð°Ñ Ð³Ñ€Ð¾Ð¼ÐºÐ¾ÑÑ‚ÑŒ (0.0 â€” Ð¿Ð¾Ð»Ð½Ð°Ñ Ñ‚Ð¸ÑˆÐ¸Ð½Ð°).
    """
    if not _AUDIO_SUPPORTED:
        print("[!] Ð‘Ð¸Ð±Ð»Ð¸Ð¾Ñ‚ÐµÐºÐ¸ soundcard/soundfile Ð½Ðµ ÑƒÑÑ‚Ð°Ð½Ð¾Ð²Ð»ÐµÐ½Ñ‹.")
        return None

    duration = max(1.0, min(60.0, float(duration)))

    try:
        speaker = sc.default_speaker()
        if not speaker:
            print("[!] Ð£ÑÑ‚Ñ€Ð¾Ð¹ÑÑ‚Ð²Ð¾ Ð²Ð¾ÑÐ¿Ñ€Ð¾Ð¸Ð·Ð²ÐµÐ´ÐµÐ½Ð¸Ñ Ð¿Ð¾ ÑƒÐ¼Ð¾Ð»Ñ‡Ð°Ð½Ð¸ÑŽ Ð½Ðµ Ð½Ð°Ð¹Ð´ÐµÐ½Ð¾.")
            return None

        # ÐŸÐ¾Ð»ÑƒÑ‡Ð°ÐµÐ¼ loopback Ð¼Ð¸ÐºÑ€Ð¾Ñ„Ð¾Ð½ Ð´Ð»Ñ Ð¿ÐµÑ€ÐµÑ…Ð²Ð°Ñ‚Ð° Ñ‚Ð¾Ð³Ð¾, Ñ‡Ñ‚Ð¾ Ð·Ð²ÑƒÑ‡Ð¸Ñ‚ Ð² Ð´Ð¸Ð½Ð°Ð¼Ð¸ÐºÐ°Ñ…/Ð½Ð°ÑƒÑˆÐ½Ð¸ÐºÐ°Ñ…
        loopback_mic = sc.get_microphone(id=str(speaker.name), include_loopback=True)
        if not loopback_mic:
            print("[!] ÐÐµ ÑƒÐ´Ð°Ð»Ð¾ÑÑŒ Ð¸Ð½Ð¸Ñ†Ð¸Ð°Ð»Ð¸Ð·Ð¸Ñ€Ð¾Ð²Ð°Ñ‚ÑŒ loopback ÑƒÑÑ‚Ñ€Ð¾Ð¹ÑÑ‚Ð²Ð¾ Ð·Ð°Ñ…Ð²Ð°Ñ‚Ð° Ð·Ð²ÑƒÐºÐ°.")
            return None

        num_frames = int(duration * sample_rate)
        print(f"[ðŸŽ§] Ð—Ð°Ð¿Ð¸ÑÑŒ Ð·Ð²ÑƒÐºÐ° Ð¸Ð· Ð±Ñ€Ð°ÑƒÐ·ÐµÑ€Ð°/ÑÐ¸ÑÑ‚ÐµÐ¼Ñ‹ ({duration:.1f} ÑÐµÐº)...")
        
        with loopback_mic.recorder(samplerate=sample_rate) as recorder:
            recorded_data = recorder.record(numframes=num_frames)

        # ÐŸÑ€ÐµÐ¾Ð±Ñ€Ð°Ð·ÑƒÐµÐ¼ Ð¼Ð½Ð¾Ð³Ð¾ÐºÐ°Ð½Ð°Ð»ÑŒÐ½Ñ‹Ð¹ Ð·Ð²ÑƒÐº Ð² Ð¼Ð¾Ð½Ð¾ Ð´Ð»Ñ ÑÐºÐ¾Ð½Ð¾Ð¼Ð¸Ð¸ Ñ‚Ñ€Ð°Ñ„Ð¸ÐºÐ° Ð¸ Ð»ÑƒÑ‡ÑˆÐµÐ³Ð¾ Ð¿Ð¾Ð½Ð¸Ð¼Ð°Ð½Ð¸Ñ Ð¼Ð¾Ð´ÐµÐ»ÑŒÑŽ
        if recorded_data.ndim > 1 and recorded_data.shape[1] > 1:
            mono_data = np.mean(recorded_data, axis=1)
        else:
            mono_data = recorded_data.flatten()

        # Ð’Ñ‹Ñ‡Ð¸ÑÐ»ÑÐµÐ¼ Ð³Ñ€Ð¾Ð¼ÐºÐ¾ÑÑ‚ÑŒ Ð·Ð²ÑƒÐºÐ°
        rms = float(np.sqrt(np.mean(mono_data ** 2)))

        # ÐšÐ¾Ð´Ð¸Ñ€ÑƒÐµÐ¼ Ð² WAV (PCM 16-bit, Ð¼Ð¾Ð½Ð¾)
        buffer = io.BytesIO()
        sf.write(buffer, mono_data, sample_rate, format="WAV", subtype="PCM_16")
        wav_bytes = buffer.getvalue()

        return wav_bytes, rms

    except Exception as e:
        print(f"[!] ÐžÑˆÐ¸Ð±ÐºÐ° Ð¿Ñ€Ð¸ Ð·Ð°Ñ…Ð²Ð°Ñ‚Ðµ Ð·Ð²ÑƒÐºÐ°: {e}")
        return None

def save_audio_file(audio_bytes: bytes, file_path: Path):
    """Ð¡Ð¾Ñ…Ñ€Ð°Ð½ÑÐµÑ‚ Ð±Ð°Ð¹Ñ‚Ñ‹ Ð°ÑƒÐ´Ð¸Ð¾ Ð² Ñ„Ð°Ð¹Ð» WAV."""
    try:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_bytes(audio_bytes)
    except Exception as e:
        print(f"[!] ÐÐµ ÑƒÐ´Ð°Ð»Ð¾ÑÑŒ ÑÐ¾Ñ…Ñ€Ð°Ð½Ð¸Ñ‚ÑŒ Ð°ÑƒÐ´Ð¸Ð¾Ñ„Ð°Ð¹Ð» {file_path}: {e}")
def record_microphone(
    duration: float = 5.0,
    sample_rate: int = 16000
) -> Optional[Tuple[bytes, float]]:
    """Записывает голос с микрофона."""
    if not _AUDIO_SUPPORTED:
        return None

    duration = max(1.0, min(60.0, float(duration)))

    try:
        mic = sc.default_microphone()
        if not mic:
            print("[!] Микрофон по умолчанию не найден.")
            return None

        num_frames = int(duration * sample_rate)
        print(f"[*] Говорите... ({duration:.1f} сек)")
        
        with mic.recorder(samplerate=sample_rate) as recorder:
            recorded_data = recorder.record(numframes=num_frames)

        if recorded_data.ndim > 1 and recorded_data.shape[1] > 1:
            mono_data = np.mean(recorded_data, axis=1)
        else:
            mono_data = recorded_data.flatten()

        rms = float(np.sqrt(np.mean(mono_data ** 2)))

        buffer = io.BytesIO()
        sf.write(buffer, mono_data, sample_rate, format="WAV", subtype="PCM_16")
        wav_bytes = buffer.getvalue()

        return wav_bytes, rms

    except Exception as e:
        print(f"[!] Ошибка при записи микрофона: {e}")
        return None
