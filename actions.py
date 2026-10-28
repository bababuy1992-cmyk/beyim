import time
from typing import Optional
import pyautogui
import pyperclip

# Включаем защитный механизм PyAutoGUI:
# Если пользователь дернет мышь в любой угол экрана (0, 0), выполнение мгновенно прервется
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.1

# Список допустимых специальных клавиш
KEY_MAP = {
    "enter": "enter",
    "return": "enter",
    "tab": "tab",
    "esc": "escape",
    "escape": "escape",
    "backspace": "backspace",
    "delete": "delete",
    "space": "space",
    "up": "up",
    "down": "down",
    "left": "left",
    "right": "right",
    "pageup": "pageup",
    "pagedown": "pagedown",
    "home": "home",
    "end": "end"
}

# Исправляем системную проблему PyAutoGUI на Windows:
# При активной русской раскладке PyAutoGUI не может нажимать английские буквы
# (включая Ctrl+V, Ctrl+A, Ctrl+C), так как VkKeyScanW возвращает -1.
# Патчим таблицу маппинга стандартными кодами клавиш Windows (0x41..0x5A, 0x30..0x39).
try:
    if hasattr(pyautogui, "_pyautogui_win") and hasattr(pyautogui._pyautogui_win, "keyboardMapping"):
        for char in "abcdefghijklmnopqrstuvwxyz":
            pyautogui._pyautogui_win.keyboardMapping[char] = ord(char.upper())
        for char in "0123456789":
            pyautogui._pyautogui_win.keyboardMapping[char] = ord(char)
except Exception as _patch_err:
    print(f"[!] Предупреждение: Не удалось пропатчить раскладку: {_patch_err}")

try:
    import win32api
    import win32con
    _HAS_WIN32 = True
except ImportError:
    _HAS_WIN32 = False

def move_mouse(x: int, y: int, duration: float = 0.25):
    """Плавно перемещает курсор мыши в точку (x, y)."""
    try:
        pyautogui.moveTo(x, y, duration=duration)
    except Exception as e:
        print(f"[!] Ошибка перемещения мыши: {e}")

def click(x: int, y: int):
    """Выполняет одиночный левый клик по координатам (x, y)."""
    try:
        pyautogui.moveTo(x, y, duration=0.2)
        time.sleep(0.05)
        pyautogui.click(x, y)
    except Exception as e:
        print(f"[!] Ошибка при клике ({x}, {y}): {e}")

def double_click(x: int, y: int):
    """Выполняет двойной клик левой кнопкой мыши."""
    try:
        pyautogui.moveTo(x, y, duration=0.2)
        time.sleep(0.05)
        pyautogui.doubleClick(x, y)
    except Exception as e:
        print(f"[!] Ошибка при двойном клике ({x}, {y}): {e}")

def right_click(x: int, y: int):
    """Выполняет клик правой кнопкой мыши."""
    try:
        pyautogui.moveTo(x, y, duration=0.2)
        time.sleep(0.05)
        pyautogui.rightClick(x, y)
    except Exception as e:
        print(f"[!] Ошибка при правом клике ({x}, {y}): {e}")

import ctypes
from ctypes import wintypes

PUL = ctypes.POINTER(ctypes.c_ulong)
class KeyBdInput(ctypes.Structure):
    _fields_ = [("wVk", wintypes.WORD), ("wScan", wintypes.WORD), ("dwFlags", wintypes.DWORD),
                ("time", wintypes.DWORD), ("dwExtraInfo", PUL)]
class MouseInput(ctypes.Structure):
    _fields_ = [("dx", wintypes.LONG), ("dy", wintypes.LONG), ("mouseData", wintypes.DWORD),
                ("dwFlags", wintypes.DWORD), ("time", wintypes.DWORD), ("dwExtraInfo", PUL)]
class HardwareInput(ctypes.Structure):
    _fields_ = [("uMsg", wintypes.DWORD), ("wParamL", wintypes.WORD), ("wParamH", wintypes.WORD)]
class Input_I(ctypes.Union):
    _fields_ = [("ki", KeyBdInput), ("mi", MouseInput), ("hi", HardwareInput)]
class Input(ctypes.Structure):
    _fields_ = [("type", wintypes.DWORD), ("ii", Input_I)]

def type_text(text: str):
    """
    Надежный ввод любого текста (английский, русский, цифры, спецсимволы).
    Использует прямой аппаратный Unicode-ввод Windows (SendInput KEYEVENTF_UNICODE).
    
    Преимущества:
    1. Не зависит от текущей раскладки Windows (РУС/ENG).
    2. Обходит защиту от вставки (onpaste / preventDefault на сайтах тестирования вроде IELTS).
    3. Активирует все события браузера (keydown, keypress, input, change).
    """
    if not text:
        return

    # Способ 1: Прямой посимвольный Unicode-ввод через SendInput (Win32 API)
    if _HAS_WIN32:
        try:
            INPUT_KEYBOARD = 1
            KEYEVENTF_UNICODE = 0x0004
            KEYEVENTF_KEYUP = 0x0002
            for ch in text:
                extra = ctypes.pointer(ctypes.c_ulong(0))
                ii_ = Input_I()
                ii_.ki = KeyBdInput(0, ord(ch), KEYEVENTF_UNICODE, 0, extra)
                x = Input(INPUT_KEYBOARD, ii_)
                ctypes.windll.user32.SendInput(1, ctypes.pointer(x), ctypes.sizeof(x))
                
                ii_.ki.dwFlags = KEYEVENTF_UNICODE | KEYEVENTF_KEYUP
                x = Input(INPUT_KEYBOARD, ii_)
                ctypes.windll.user32.SendInput(1, ctypes.pointer(x), ctypes.sizeof(x))
                time.sleep(0.015)
            time.sleep(0.05)
            return
        except Exception as e:
            print(f"[!] Ошибка прямого Unicode-ввода ({e}), используем резервный способ...")

    # Способ 2: Резервная вставка через буфер обмена с физическим кодом Ctrl+V
    try:
        pyperclip.copy(text)
        time.sleep(0.05)
        if _HAS_WIN32:
            win32api.keybd_event(win32con.VK_CONTROL, 0, 0, 0)
            win32api.keybd_event(ord('V'), 0, 0, 0)
            win32api.keybd_event(ord('V'), 0, win32con.KEYEVENTF_KEYUP, 0)
            win32api.keybd_event(win32con.VK_CONTROL, 0, win32con.KEYEVENTF_KEYUP, 0)
        else:
            pyautogui.hotkey("ctrl", "v")
        time.sleep(0.1)
    except Exception as e:
        print(f"[!] Ошибка при резервной вставке текста: {e}")

def press_key(key_name: str):
    """Нажимает специальную клавишу (Enter, Tab, Esc и т.д.) или комбинацию."""
    clean_key = key_name.strip().lower()
    try:
        # Для стандартных комбинаций с Ctrl (Ctrl+A, Ctrl+V, Ctrl+C) используем точные физические коды
        if clean_key == "ctrl+a" and _HAS_WIN32:
            win32api.keybd_event(win32con.VK_CONTROL, 0, 0, 0)
            win32api.keybd_event(ord('A'), 0, 0, 0)
            win32api.keybd_event(ord('A'), 0, win32con.KEYEVENTF_KEYUP, 0)
            win32api.keybd_event(win32con.VK_CONTROL, 0, win32con.KEYEVENTF_KEYUP, 0)
            time.sleep(0.05)
            return

        if clean_key == "ctrl+v" and _HAS_WIN32:
            win32api.keybd_event(win32con.VK_CONTROL, 0, 0, 0)
            win32api.keybd_event(ord('V'), 0, 0, 0)
            win32api.keybd_event(ord('V'), 0, win32con.KEYEVENTF_KEYUP, 0)
            win32api.keybd_event(win32con.VK_CONTROL, 0, win32con.KEYEVENTF_KEYUP, 0)
            time.sleep(0.05)
            return

        if "+" in clean_key:
            parts = [k.strip() for k in clean_key.split("+")]
            pyautogui.hotkey(*parts)
        elif clean_key in KEY_MAP:
            pyautogui.press(KEY_MAP[clean_key])
        else:
            pyautogui.press(clean_key)
        time.sleep(0.1)
    except Exception as e:
        print(f"[!] Ошибка при нажатии клавиши '{key_name}': {e}")

def scroll(amount: int, x: Optional[int] = None, y: Optional[int] = None):
    """
    Прокрутка страницы колесиком мыши.
    amount < 0: прокрутка вниз
    amount > 0: прокрутка вверх
    """
    try:
        if x is not None and y is not None:
            pyautogui.moveTo(x, y, duration=0.15)
        pyautogui.scroll(amount)
        time.sleep(0.2)
    except Exception as e:
        print(f"[!] Ошибка при прокрутке: {e}")

def drag(from_x: int, from_y: int, to_x: int, to_y: int, duration: float = 0.5):
    """Перетаскивание мышью из точки (from_x, from_y) в (to_x, to_y)."""
    try:
        pyautogui.moveTo(from_x, from_y, duration=0.2)
        pyautogui.dragTo(to_x, to_y, duration=duration, button="left")
    except Exception as e:
        print(f"[!] Ошибка при перетаскивании: {e}")

def wait(seconds: float):
    """Пауза ожидания загрузки страницы или элемента."""
    try:
        actual_delay = max(0.1, min(10.0, float(seconds)))
        time.sleep(actual_delay)
    except Exception:
        time.sleep(1.0)
