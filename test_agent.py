import os
import sys
import unittest
from pathlib import Path
from PIL import Image

import config
import actions
import screen_capture
from ai_client import ActionDecision, GeminiAgentClient
from overlay import draw_action_overlay

class TestAgentComponents(unittest.TestCase):

    def test_coordinate_mapping(self):
        """Проверка точности пересчета нормализованных координат (0..1000) в реальные пиксели."""
        bbox = (100, 200, 1000, 800)  # x_offset=100, y_offset=200, width=1000, height=800

        # Центр (500, 500) -> 100 + 500 = 600, 200 + 400 = 600
        real_x, real_y = screen_capture.normalized_to_screen_coords(500, 500, bbox)
        self.assertEqual(real_x, 600)
        self.assertEqual(real_y, 600)

        # Верхний левый угол (0, 0) -> (100, 200)
        x0, y0 = screen_capture.normalized_to_screen_coords(0, 0, bbox)
        self.assertEqual(x0, 100)
        self.assertEqual(y0, 200)

        # Нижний правый угол (1000, 1000) -> (1100, 1000)
        x1, y1 = screen_capture.normalized_to_screen_coords(1000, 1000, bbox)
        self.assertEqual(x1, 1100)
        self.assertEqual(y1, 1000)

        # Выход за границы (должен ограничиваться clamp)
        x_neg, y_neg = screen_capture.normalized_to_screen_coords(-50, 1200, bbox)
        self.assertEqual(x_neg, 100)
        self.assertEqual(y_neg, 1000)

    def test_action_decision_schema(self):
        """Проверка валидации JSON ответа от Gemini через Pydantic."""
        valid_json = """
        {
            "thought": "Іздеу батырмасын басу керек / Нужно кликнуть по Поиск",
            "action": "click",
            "x": 450,
            "y": 320,
            "message": "Іздеу батырмасын басу"
        }
        """
        decision = ActionDecision.model_validate_json(valid_json)
        self.assertEqual(decision.action, "click")
        self.assertEqual(decision.x, 450)
        self.assertEqual(decision.y, 320)
        self.assertIn("Іздеу", decision.thought)

        type_json = """
        {
            "thought": "Мәтін енгізу / Ввожу поисковый запрос",
            "action": "type",
            "text": "Сәлем, әлем!",
            "message": "Мәтін жазылуда"
        }
        """
        type_decision = ActionDecision.model_validate_json(type_json)
        self.assertEqual(type_decision.action, "type")
        self.assertEqual(type_decision.text, "Сәлем, әлем!")

        listen_json = """
        {
            "thought": "Бейнежазба үнін тыңдау керек",
            "action": "listen",
            "duration": 5.0,
            "message": "Дыбысты тыңдау"
        }
        """
        listen_decision = ActionDecision.model_validate_json(listen_json)
        self.assertEqual(listen_decision.action, "listen")
        self.assertEqual(listen_decision.duration, 5.0)

    def test_audio_capture_module(self):
        """Проверка модуля захвата звука audio_capture."""
        import audio_capture
        self.assertTrue(hasattr(audio_capture, "record_system_audio"))
        self.assertTrue(hasattr(audio_capture, "is_audio_available"))
        self.assertTrue(hasattr(audio_capture, "save_audio_file"))
        self.assertTrue(audio_capture.is_audio_available())

    def test_overlay_drawing(self):
        """Проверка генерации визуальных меток на изображении."""
        test_img = Image.new("RGB", (800, 600), color=(200, 200, 200))
        overlay = draw_action_overlay(
            image=test_img,
            action="click",
            norm_x=500,
            norm_y=500,
            thought="Тестілік ойлау / Тестовое рассуждение"
        )
        self.assertEqual(overlay.size, (800, 600))
        self.assertEqual(overlay.mode, "RGB")

    def test_config_settings_persistence(self):
        """Конфигурация сақтау және қайта жүктеу тесті."""
        initial_model = config.GEMINI_MODEL
        test_model = "gemini-2.5-flash"
        config.save_settings(model=test_model, step_delay=3.5)
        self.assertEqual(config.GEMINI_MODEL, test_model)
        self.assertEqual(config.STEP_DELAY, 3.5)
        # Қалпына келтіру
        config.save_settings(model=initial_model, step_delay=4.0)

    def test_client_test_connection_invalid_key(self):
        """Жарамсыз API кілтпен қосылысты тексеру тесті."""
        client = GeminiAgentClient(api_key="INVALID_TEST_KEY_12345", model_name="gemini-2.5-flash")
        ok, msg = client.test_connection()
        self.assertFalse(ok)
        self.assertTrue(len(msg) > 0)

    def test_gui_module_components(self):
        """GUI модульдерінің дұрыс импортталуын тексеру."""
        import gui_chat
        self.assertTrue(hasattr(gui_chat, "ChatApp"))
        self.assertTrue(hasattr(gui_chat, "SettingsDialog"))
        self.assertTrue(len(gui_chat.AVAILABLE_MODELS) >= 3)


if __name__ == "__main__":
    unittest.main()
