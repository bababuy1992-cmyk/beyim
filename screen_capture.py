import time
import sys
from typing import List, Dict, Optional, Tuple
from PIL import Image, ImageGrab
import mss

# Windows API для работы с окнами
if sys.platform == "win32":
    import win32gui
    import win32con
    import win32process
else:
    win32gui = None
    win32con = None
    win32process = None

# Известные имена браузеров для быстрой фильтрации
KNOWN_BROWSERS = [
    "chrome", "msedge", "firefox", "brave", "opera", "vivaldi", "yandex", "browser"
]

class WindowInfo:
    def __init__(self, hwnd: int, title: str, rect: Tuple[int, int, int, int]):
        self.hwnd = hwnd
        self.title = title
        self.rect = rect  # (left, top, right, bottom)
        self.width = rect[2] - rect[0]
        self.height = rect[3] - rect[1]

    def __repr__(self):
        return f"<Window '{self.title}' ({self.width}x{self.height})>"

def get_open_windows(filter_browsers: bool = False) -> List[WindowInfo]:
    """Возвращает список открытых видимых окон пользователей."""
    if not win32gui:
        return []

    windows = []

    def enum_handler(hwnd, _):
        if not win32gui.IsWindowVisible(hwnd):
            return
        title = win32gui.GetWindowText(hwnd).strip()
        if not title:
            return

        # Игнорируем служебные системные окна Windows
        ignored_titles = [
            "Program Manager", "Default IME", "MSCTFIME UI", "Settings",
            "Windows Shell Experience Host", "Task Switching", "Cortana"
        ]
        if title in ignored_titles:
            return

        rect = win32gui.GetWindowRect(hwnd)
        width = rect[2] - rect[0]
        height = rect[3] - rect[1]

        # Окно должно быть нормального размера (не свернуто в точку)
        if width < 200 or height < 150:
            return

        is_browser = False
        lower_title = title.lower()
        for b in KNOWN_BROWSERS:
            if b in lower_title:
                is_browser = True
                break

        if filter_browsers and not is_browser:
            return

        windows.append(WindowInfo(hwnd, title, rect))

    try:
        win32gui.EnumWindows(enum_handler, None)
    except Exception as e:
        print(f"[!] Ошибка при перечислении окон: {e}")

    # Сортируем: сначала окна браузеров, затем остальные по алфавиту
    windows.sort(key=lambda w: (
        not any(b in w.title.lower() for b in KNOWN_BROWSERS),
        w.title.lower()
    ))
    return windows

def focus_window(hwnd: int) -> bool:
    """Активирует и выводит окно на передний план."""
    if not win32gui:
        return False
    try:
        if win32gui.IsIconic(hwnd):
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        win32gui.SetForegroundWindow(hwnd)
        time.sleep(0.3)
        return True
    except Exception as e:
        print(f"[!] Предупреждение: Не удалось активировать окно: {e}")
        return False

def capture_screen(hwnd: Optional[int] = None) -> Tuple[Image.Image, Tuple[int, int, int, int]]:
    """
    Делает скриншот либо конкретного окна, либо всего основного экрана.
    Возвращает: (PIL.Image, (offset_x, offset_y, width, height))
    """
    bbox = None
    if hwnd and win32gui:
        try:
            focus_window(hwnd)
            left, top, right, bottom = win32gui.GetWindowRect(hwnd)
            width = right - left
            height = bottom - top
            if width > 50 and height > 50:
                bbox = (left, top, width, height)
        except Exception as e:
            print(f"[!] Ошибка получения координат окна: {e}")

    # 1. Попытка захвата через MSS
    try:
        with mss.MSS() as sct:
            if bbox:
                monitor = {
                    "left": bbox[0],
                    "top": bbox[1],
                    "width": bbox[2],
                    "height": bbox[3]
                }
            else:
                monitor = sct.monitors[1]  # Основной монитор
                bbox = (monitor["left"], monitor["top"], monitor["width"], monitor["height"])

            sct_img = sct.grab(monitor)
            img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
            return img, bbox
    except Exception:
        pass

    # 2. Резервный способ через PIL ImageGrab
    try:
        if bbox:
            img = ImageGrab.grab(bbox=(bbox[0], bbox[1], bbox[0] + bbox[2], bbox[1] + bbox[3]))
        else:
            img = ImageGrab.grab()
            bbox = (0, 0, img.width, img.height)
        return img, bbox
    except Exception as e:
        # Если запущено в среде без активного графического контекста (например, CI/тесты)
        print(f"[!] Захват экрана недоступен в данной сессии ({e}), используется тестовое полотно.")
        dummy_img = Image.new("RGB", (1280, 720), color=(240, 240, 240))
        return dummy_img, (0, 0, 1280, 720)

def normalized_to_screen_coords(
    norm_x: int,
    norm_y: int,
    bbox: Tuple[int, int, int, int]
) -> Tuple[int, int]:
    """
    Преобразует нормализованные координаты (0..1000) от Gemini
    в реальные экранные координаты пикселей Windows (x, y).
    bbox: (offset_x, offset_y, width, height)
    """
    # Ограничиваем значения диапазоном [0, 1000]
    clamped_x = max(0, min(1000, norm_x))
    clamped_y = max(0, min(1000, norm_y))

    real_x = int(bbox[0] + (clamped_x / 1000.0) * bbox[2])
    real_y = int(bbox[1] + (clamped_y / 1000.0) * bbox[3])
    return real_x, real_y
