import os
import sys
import ctypes
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

if getattr(sys, "frozen", False):
    BASE_DIR = Path(sys.executable).resolve().parent
else:
    BASE_DIR = Path(__file__).resolve().parent

ENV_PATH = BASE_DIR / ".env"
RUN_LOGS_DIR = BASE_DIR / "run_logs"

def init_dpi_awareness():
    """Windows жүйесінде жоғары DPI анықтығын (HiDPI) қосады."""
    if sys.platform == "win32":
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except Exception:
            try:
                ctypes.windll.user32.SetProcessDPIAware()
            except Exception:
                pass

init_dpi_awareness()

# Орта айнымалыларын жүктеу
load_dotenv(dotenv_path=ENV_PATH)

def get_env_bool(key: str, default: bool = False) -> bool:
    val = os.getenv(key)
    if val is None:
        return default
    return val.strip().lower() in ("true", "1", "yes", "y", "on")

def get_env_int(key: str, default: int) -> int:
    try:
        val = os.getenv(key)
        return int(val) if val is not None else default
    except ValueError:
        return default

def get_env_float(key: str, default: float) -> float:
    try:
        val = os.getenv(key)
        return float(val) if val is not None else default
    except ValueError:
        return default

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip()
CONFIRM_ACTIONS = get_env_bool("CONFIRM_ACTIONS", False)
STEP_DELAY = get_env_float("STEP_DELAY", 4.0)
MAX_STEPS = get_env_int("MAX_STEPS", 200)
SAVE_SCREENSHOTS = get_env_bool("SAVE_SCREENSHOTS", True)
AUDIO_ENABLED = get_env_bool("AUDIO_ENABLED", True)
DEFAULT_LISTEN_DURATION = get_env_float("DEFAULT_LISTEN_DURATION", 5.0)

def reload_config():
    """Конфигурацияны .env файлынан қайта жүктейді."""
    global GEMINI_API_KEY, GEMINI_MODEL, CONFIRM_ACTIONS, STEP_DELAY
    global MAX_STEPS, SAVE_SCREENSHOTS, AUDIO_ENABLED, DEFAULT_LISTEN_DURATION
    load_dotenv(dotenv_path=ENV_PATH, override=True)
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
    GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip()
    CONFIRM_ACTIONS = get_env_bool("CONFIRM_ACTIONS", False)
    STEP_DELAY = get_env_float("STEP_DELAY", 4.0)
    MAX_STEPS = get_env_int("MAX_STEPS", 200)
    SAVE_SCREENSHOTS = get_env_bool("SAVE_SCREENSHOTS", True)
    AUDIO_ENABLED = get_env_bool("AUDIO_ENABLED", True)
    DEFAULT_LISTEN_DURATION = get_env_float("DEFAULT_LISTEN_DURATION", 5.0)

def save_settings(
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    step_delay: Optional[float] = None,
    max_steps: Optional[int] = None,
    save_screenshots: Optional[bool] = None,
    audio_enabled: Optional[bool] = None
):
    """
    Параметрлерді .env файлына қауіпсіз сақтайды және орта айнымалыларын жаңартады.
    """
    if not ENV_PATH.exists():
        example_path = BASE_DIR / ".env.example"
        if example_path.exists():
            content = example_path.read_text(encoding="utf-8")
        else:
            content = (
                "# Beyim Agent Конфигурациясы\n"
                "GEMINI_API_KEY=\n"
                "GEMINI_MODEL=gemini-2.5-flash\n"
                "CONFIRM_ACTIONS=false\n"
                "STEP_DELAY=4.0\n"
                "MAX_STEPS=200\n"
                "SAVE_SCREENSHOTS=true\n"
                "AUDIO_ENABLED=true\n"
            )
    else:
        content = ENV_PATH.read_text(encoding="utf-8")

    lines = content.splitlines()
    keys_map = {}
    if api_key is not None:
        keys_map["GEMINI_API_KEY"] = api_key.strip()
    if model is not None:
        keys_map["GEMINI_MODEL"] = model.strip()
    if step_delay is not None:
        keys_map["STEP_DELAY"] = str(step_delay)
    if max_steps is not None:
        keys_map["MAX_STEPS"] = str(max_steps)
    if save_screenshots is not None:
        keys_map["SAVE_SCREENSHOTS"] = "true" if save_screenshots else "false"
    if audio_enabled is not None:
        keys_map["AUDIO_ENABLED"] = "true" if audio_enabled else "false"

    updated_keys = set()
    new_lines = []
    for line in lines:
        matched = False
        for k, v in keys_map.items():
            if line.startswith(f"{k}="):
                new_lines.append(f"{k}={v}")
                updated_keys.add(k)
                matched = True
                break
        if not matched:
            new_lines.append(line)

    for k, v in keys_map.items():
        if k not in updated_keys:
            new_lines.append(f"{k}={v}")

    ENV_PATH.write_text("\n".join(new_lines) + "\n", encoding="utf-8")

    for k, v in keys_map.items():
        os.environ[k] = v

    reload_config()

def save_api_key(api_key: str):
    """API кілтін сақтау (кері үйлесімділік үшін)."""
    save_settings(api_key=api_key)
