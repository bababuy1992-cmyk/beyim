import time
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any, Callable
from PIL import Image

import config
import actions
import screen_capture
import audio_capture
from interrupt_handler import InterruptListener, prompt_interruption_menu
from ai_client import GeminiAgentClient, ActionDecision
from overlay import save_step_image

class BrowserAgent:
    def __init__(
        self,
        ai_client: GeminiAgentClient,
        target_hwnd: Optional[int] = None,
        confirm_actions: bool = False,
        step_delay: float = 4.0,
        max_steps: int = 200,
        save_screenshots: bool = True,
        on_step: Optional[Callable[[Dict[str, Any]], None]] = None,
        on_status: Optional[Callable[[str], None]] = None,
        on_finish: Optional[Callable[[bool, str], None]] = None
    ):
        self.ai_client = ai_client
        self.target_hwnd = target_hwnd  # None = полный экран (Full Desktop Control)
        self.confirm_actions = confirm_actions  # False = полный автомат (Full Control)
        self.step_delay = step_delay
        self.max_steps = max_steps
        self.save_screenshots = save_screenshots

        # Callbacks для GUI
        self.on_step = on_step
        self.on_status = on_status
        self.on_finish = on_finish

        self._stop_requested = False

        # Директория для скриншотов сессии
        session_name = datetime.now().strftime("session_%Y%m%d_%H%M%S")
        self.session_dir = config.RUN_LOGS_DIR / session_name
        self.history: List[Dict[str, Any]] = []

    def stop(self):
        """Запрашивает немедленную остановку выполнения."""
        self._stop_requested = True

    def _notify_status(self, text: str):
        if self.on_status:
            try:
                self.on_status(text)
            except Exception:
                pass

    def run(self, goal: str) -> bool:
        """
        Запускает цикл автономного выполнения задачи с полным контролем.
        """
        self._stop_requested = False
        print("\n" + "=" * 60)
        print(f"[*] СТАРТ ЗАДАЧИ (Полный контроль): {goal}")
        print(f"[*] Максимум шагов: {self.max_steps} | Задержка: {self.step_delay}с")
        print(f"[*] Папка визуальных логов: {self.session_dir}")
        print("=" * 60 + "\n")

        self._notify_status(f"Старт задачи: {goal}")

        if self.target_hwnd:
            screen_capture.focus_window(self.target_hwnd)
            time.sleep(0.5)

        current_goal = goal
        listener = InterruptListener()
        listener.start()

        try:
            step = 1
            while step <= self.max_steps:
                if self._stop_requested:
                    print("\n[!] Выполнение остановлено по запросу пользователя.")
                    self._notify_status("Остановлено пользователем")
                    if self.on_finish:
                        self.on_finish(False, "Остановлено пользователем")
                    return False

                # Проверка горячей клавиши F8 / Pause
                if listener.is_interrupted():
                    listener.clear()
                    print("\n[!] Нажата клавиша паузы F8/Pause.")
                    if self.confirm_actions:
                        new_instruction, action_type = prompt_interruption_menu(current_goal, step)
                        if action_type in ("redirect", "clarify") and new_instruction:
                            current_goal = new_instruction
                            self.history.append({
                                "step": step,
                                "action": "redirect",
                                "thought": f"Пользователь сменил цель: {new_instruction}",
                                "detail": f"Новая инструкция: {new_instruction}"
                            })
                            print(f"\n[🔄] НАПРАВЛЕНИЕ ОБНОВЛЕНО: {current_goal}\n")
                            continue
                        elif action_type == "exit":
                            if self.on_finish:
                                self.on_finish(False, "Остановлено пользователем")
                            return False
                    else:
                        print("[!] Работа приостановлена пользователем (F8).")
                        self._notify_status("Остановлено клавишей F8")
                        if self.on_finish:
                            self.on_finish(False, "Остановлено клавишей F8")
                        return False

                print(f"\n--- [ШАГ {step}/{self.max_steps}] ---")
                self._notify_status(f"Шаг {step}/{self.max_steps}: Анализ экрана...")

                try:
                    # 1. Захватываем скриншот экрана
                    image, bbox = screen_capture.capture_screen(self.target_hwnd)
                    img_w, img_h = image.size

                    # 2. Запрос к Gemini
                    decision = None
                    for attempt in range(1, 4):
                        if self._stop_requested:
                            break
                        try:
                            decision = self.ai_client.decide_next_action(
                                goal=current_goal,
                                current_image=image,
                                history=self.history,
                                step_number=step
                            )
                            break
                        except Exception as e:
                            err_str = str(e).lower()
                            is_rate_limit = any(k in err_str for k in ("429", "quota", "rate", "resource_exhausted"))
                            if is_rate_limit and attempt < 3:
                                wait_sec = 15 * attempt
                                print(f"[!] Превышен лимит запросов к API. Жду {wait_sec} сек...")
                                self._notify_status(f"Лимит API: ожидание {wait_sec} сек...")
                                for _ in range(wait_sec):
                                    if self._stop_requested or listener.is_interrupted():
                                        break
                                    time.sleep(1)
                            else:
                                print(f"[X] Ошибка запроса к ИИ (попытка {attempt}/3): {e}")
                                if attempt == 3:
                                    msg = f"Ошибка Gemini API: {e}"
                                    if self.on_finish:
                                        self.on_finish(False, msg)
                                    return False

                    if self._stop_requested:
                        if self.on_finish:
                            self.on_finish(False, "Остановлено пользователем")
                        return False

                    if decision is None:
                        if self.on_finish:
                            self.on_finish(False, "Не получен ответ от модели")
                        return False

                    # Вычисляем экранные координаты
                    real_x, real_y = None, None
                    if decision.x is not None and decision.y is not None:
                        real_x, real_y = screen_capture.normalized_to_screen_coords(
                            decision.x, decision.y, bbox
                        )

                    # 3. Сохраняем визуальный лог
                    saved_path = None
                    if self.save_screenshots:
                        saved_path = save_step_image(
                            image=image,
                            session_dir=self.session_dir,
                            step_num=step,
                            action=decision.action,
                            norm_x=decision.x,
                            norm_y=decision.y,
                            text_info=decision.text or decision.key,
                            thought=decision.thought
                        )

                    # 4. Вывод информации
                    print(f"[Мысль ИИ]: {decision.thought}")
                    action_desc = f"[ДЕЙСТВИЕ]: {decision.action.upper()}"
                    if real_x is not None and real_y is not None:
                        action_desc += f" в ({real_x}, {real_y})"
                    if decision.text:
                        action_desc += f" -> Ввод: '{decision.text}'"
                    if decision.key:
                        action_desc += f" -> Клавиша: '{decision.key}'"
                    if decision.amount is not None:
                        action_desc += f" -> Прокрутка: {decision.amount}"
                    if decision.message:
                        action_desc += f" ({decision.message})"
                    print(action_desc)

                    # Оповещаем GUI о шаге
                    step_info = {
                        "step": step,
                        "max_steps": self.max_steps,
                        "thought": decision.thought,
                        "action": decision.action,
                        "real_x": real_x,
                        "real_y": real_y,
                        "text": decision.text,
                        "key": decision.key,
                        "amount": decision.amount,
                        "message": decision.message,
                        "screenshot_path": str(saved_path) if saved_path else None
                    }
                    if self.on_step:
                        try:
                            self.on_step(step_info)
                        except Exception:
                            pass

                    # 5. Проверка завершения
                    if decision.action == "done":
                        finish_msg = decision.message or "Задача успешно выполнена!"
                        print("\n" + "=" * 60)
                        print(f"[V] ЗАДАЧА ВЫПОЛНЕНА: {finish_msg}")
                        print("=" * 60 + "\n")
                        self._notify_status("Выполнено успешно!")
                        if self.on_finish:
                            self.on_finish(True, finish_msg)
                        return True

                    if decision.action == "fail":
                        fail_msg = decision.message or "Не удалось выполнить задачу"
                        print("\n" + "=" * 60)
                        print(f"[X] ОШИБКА: {fail_msg}")
                        print("=" * 60 + "\n")
                        self._notify_status(f"Ошибка: {fail_msg}")
                        if self.on_finish:
                            self.on_finish(False, fail_msg)
                        return False

                    # 6. Режим подтверждения (если когда-либо включен)
                    if self.confirm_actions:
                        user_cmd = input("-> Выполнить? [Enter - да, Q - выход]: ").strip().lower()
                        if user_cmd in ("q", "quit", "exit"):
                            if self.on_finish:
                                self.on_finish(False, "Прервано пользователем")
                            return False

                    # 7. Выполняем действие
                    action_result = self._execute_action(decision, real_x, real_y, goal=current_goal, step=step)

                    # 8. Запись в историю
                    detail_val = action_result or decision.text or decision.key
                    if not detail_val and decision.x is not None:
                        detail_val = f"({decision.x}, {decision.y})"
                    self.history.append({
                        "step": step,
                        "action": decision.action,
                        "thought": decision.thought,
                        "detail": detail_val or "OK"
                    })

                    # 9. Пауза между шагами
                    end_pause = time.time() + self.step_delay
                    while time.time() < end_pause:
                        if self._stop_requested or listener.is_interrupted():
                            break
                        time.sleep(0.1)

                    step += 1

                except KeyboardInterrupt:
                    print("\n[!] Принудительная остановка (Ctrl+C).")
                    if self.on_finish:
                        self.on_finish(False, "Остановлено пользователем")
                    return False

            limit_msg = f"Достигнут лимит шагов ({self.max_steps})"
            print(f"\n[!] {limit_msg}.")
            if self.on_finish:
                self.on_finish(False, limit_msg)
            return False

        finally:
            listener.stop()

    def _execute_action(
        self,
        decision: ActionDecision,
        real_x: Optional[int],
        real_y: Optional[int],
        goal: str = "",
        step: int = 1
    ) -> Optional[str]:
        """Выполняет реальное действие на компьютере с полным контролем."""
        if self.target_hwnd:
            screen_capture.focus_window(self.target_hwnd)

        act = decision.action
        if act == "click" and real_x is not None and real_y is not None:
            actions.click(real_x, real_y)
        elif act == "double_click" and real_x is not None and real_y is not None:
            actions.double_click(real_x, real_y)
        elif act == "right_click" and real_x is not None and real_y is not None:
            actions.right_click(real_x, real_y)
        elif act == "type" and decision.text:
            if real_x is not None and real_y is not None:
                actions.click(real_x, real_y)
                time.sleep(0.2)
            actions.type_text(decision.text)
        elif act == "press" and decision.key:
            actions.press_key(decision.key)
        elif act == "scroll":
            amount = decision.amount if decision.amount is not None else -400
            actions.scroll(amount, real_x, real_y)
        elif act == "wait":
            actions.wait(2.0)
        elif act == "listen":
            listen_dur = decision.duration if decision.duration else config.DEFAULT_LISTEN_DURATION
            rec = audio_capture.record_system_audio(duration=listen_dur)
            if rec is not None:
                wav_bytes, rms = rec
                audio_path = self.session_dir / f"step_{step:02d}_audio.wav"
                audio_capture.save_audio_file(wav_bytes, audio_path)
                analysis = self.ai_client.analyze_audio(wav_bytes, goal)
                print(f"[🎧 Результат прослушивания]: {analysis}")
                return f"Услышано: {analysis}"
        return None
