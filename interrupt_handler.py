import sys
import time
import threading
import ctypes
from typing import Optional, Tuple, List

# Коды виртуальных клавиш Windows (Virtual-Key Codes)
VK_PAUSE = 0x13  # Клавиша Pause / Break
VK_F8 = 0x77     # Клавиша F8
VK_F9 = 0x78     # Клавиша F9

def focus_console():
    """Переводит фокус операционной системы на окно консоли."""
    try:
        kernel32 = ctypes.windll.kernel32
        user32 = ctypes.windll.user32
        hwnd = kernel32.GetConsoleWindow()
        if hwnd:
            user32.ShowWindow(hwnd, 5)  # SW_SHOW
            user32.SetForegroundWindow(hwnd)
    except Exception:
        pass

class InterruptListener:
    """
    Глобальный фоновый слушатель горячих клавиш (по умолчанию F8 и Pause).
    Позволяет пользователю в любой момент приостановить робота нажатием одной клавиши,
    даже если активно другое окно (браузер, плеер и т.д.).
    """
    def __init__(self, hotkeys: Optional[List[int]] = None):
        self.hotkeys = hotkeys if hotkeys is not None else [VK_F8, VK_PAUSE]
        self._interrupted = threading.Event()
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def start(self):
        """Запускает фоновый поток отслеживания нажатия горячих клавиш."""
        self._interrupted.clear()
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._worker, daemon=True, name="InterruptListenerThread")
        self._thread.start()

    def stop(self):
        """Останавливает поток отслеживания."""
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=0.3)

    def is_interrupted(self) -> bool:
        """Проверяет, был ли подан сигнал прерывания."""
        return self._interrupted.is_set()

    def trigger(self):
        """Принудительно устанавливает флаг прерывания (например, при перехвате Ctrl+C)."""
        self._interrupted.set()

    def clear(self):
        """Сбрасывает флаг прерывания для продолжения работы."""
        self._interrupted.clear()

    def sleep_interruptible(self, duration: float) -> bool:
        """
        Засыпает на указанное количество секунд с шагом 50 мс,
        мгновенно просыпаясь при нажатии клавиши прерывания.
        Возвращает True, если пауза была прервана, иначе False.
        """
        end_time = time.time() + max(0.0, float(duration))
        while time.time() < end_time:
            if self._interrupted.is_set():
                return True
            time.sleep(min(0.05, max(0.01, end_time - time.time())))
        return self._interrupted.is_set()

    def _worker(self):
        """Внутренний цикл опроса состояния клавиш через Win32 GetAsyncKeyState."""
        user32 = ctypes.windll.user32
        while not self._stop_event.is_set():
            for vk in self.hotkeys:
                # 0x8000 указывает, что клавиша удерживается/нажата в данный момент
                if user32.GetAsyncKeyState(vk) & 0x8000:
                    self._interrupted.set()
                    # Ждем, пока пользователь отпустит клавишу, чтобы избежать повторных срабатываний
                    while (user32.GetAsyncKeyState(vk) & 0x8000) and not self._stop_event.is_set():
                        time.sleep(0.05)
                    break
            time.sleep(0.05)


def prompt_interruption_menu(current_goal: str, step: int) -> Tuple[Optional[str], str]:
    """
    Интерактивное меню паузы: позволяет перенаправить робота,
    уточнить текущую инструкцию или выйти.
    
    Возвращает:
        (new_goal_or_instruction, action_type):
        - action_type: 'redirect' (новая задача), 'clarify' (уточнение), 'resume' (продолжить), 'exit' (завершить)
    """
    try:
        # Звуковой сигнал привлечения внимания
        ctypes.windll.user32.MessageBeep(0)
    except Exception:
        pass

    focus_console()

    print("\n" + "=" * 65)
    print("      [⏸ РОБОТ ПРИОСТАНОВЛЕН ПОЛЬЗОВАТЕЛЕМ (ПАУЗА)]")
    print(f"[*] Текущий шаг: #{step}")
    print(f"[*] Текущая задача: {current_goal}")
    print("=" * 65)
    print("Что вы хотите сделать?")
    print("  [1] Задать НОВУЮ задачу (полностью сменить направление)")
    print("  [2] УТОЧНИТЬ текущую задачу (добавить указание/корректировку)")
    print("  [3] Продолжить выполнение текущей задачи без изменений")
    print("  [4] Завершить работу программы")

    while True:
        try:
            choice = input("\nВыберите действие [1/2/3/4, по умолчанию 1]: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n[!] Принудительный выход.")
            return None, "exit"

        if not choice or choice == "1":
            try:
                new_instruction = input("\n-> Введите новую инструкцию для робота: ").strip()
            except (EOFError, KeyboardInterrupt):
                return None, "exit"

            while not new_instruction:
                new_instruction = input("Пожалуйста, введите текст новой инструкции: ").strip()
            return new_instruction, "redirect"

        elif choice == "2":
            try:
                clarification = input("\n-> Введите уточнение/корректировку к текущей задаче: ").strip()
            except (EOFError, KeyboardInterrupt):
                return None, "exit"

            while not clarification:
                clarification = input("Пожалуйста, введите текст уточнения: ").strip()
            updated_goal = f"{current_goal} [Уточнение: {clarification}]"
            return updated_goal, "clarify"

        elif choice == "3":
            print("[+] Возобновление работы...")
            return current_goal, "resume"

        elif choice in ("4", "q", "quit", "exit"):
            print("[!] Работа программы завершена по запросу пользователя.")
            return None, "exit"

        else:
            print("[!] Неверный выбор. Введите 1, 2, 3 или 4.")
