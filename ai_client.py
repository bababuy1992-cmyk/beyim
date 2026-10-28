import io
import json
import re
from typing import Optional, List, Dict, Any, Literal, Tuple
from PIL import Image
from pydantic import BaseModel, Field
from google import genai
from google.genai import types

class ActionDecision(BaseModel):
    thought: str = Field(
        description="Скриншотты және экран күйін талдау, келесі әрекетті таңдау себебі. Подробный анализ скриншота и обоснование выбора следующего действия."
    )
    action: Literal[
        "click", "double_click", "right_click", "type", "press", "scroll", "wait", "listen", "done", "fail"
    ] = Field(
        description="Экранда орындалатын әрекет түрі / Тип действия для выполнения на экране."
    )
    x: Optional[int] = Field(
        default=None,
        description="Нормализацияланған X координатасы 0-ден 1000-ға дейін (0 - сол жақ, 1000 - оң жақ)."
    )
    y: Optional[int] = Field(
        default=None,
        description="Нормализацияланған Y координатасы 0-ден 1000-ға дейін (0 - жоғарғы жиек, 1000 - төменгі жиек)."
    )
    text: Optional[str] = Field(
        default=None,
        description="Енгізілетін мәтін (action == 'type' кезінде)."
    )
    key: Optional[str] = Field(
        default=None,
        description="Басылатын перне аты: enter, tab, escape, backspace, space, pageup, pagedown және т.б."
    )
    amount: Optional[int] = Field(
        default=None,
        description="Скролл мәні: төменге жылжу үшін теріс сан (-500), жоғарыға оң сан (+500)."
    )
    duration: Optional[float] = Field(
        default=None,
        description="Дыбысты тыңдау ұзақтығы секундпен (action == 'listen' кезінде, мысалы 3.0, 5.0, 10.0)."
    )
    message: Optional[str] = Field(
        default=None,
        description="Пайдаланушыға арналған қысқаша түсінікті сипаттама (тапсырма берілген тілде: қазақша немесе орысша)."
    )

SYSTEM_PROMPT = """Ты — интеллектуальный агент управления браузером и графическим интерфейсом компьютера (Computer Use Agent).
Сен — компьютер интерфейсі мен браузерді басқаратын дербес зияткерлік агентсің.

Твоя цель: выполнить поставленную пользователем задачу, шаг за шагом анализируя скриншоты экрана/окна браузера и выдавая команды для управления мышью и клавиатурой.
Жауапты, ойлауды (thought) және хабарламаны (message) пайдаланушы тапсырманы қай тілде (қазақша, орысша немесе ағылшынша) жазса, сол тілде ұсын!

КООРДИНАТНАЯ СЕТКА / КООРДИНАТАЛЫҚ ТОР:
- Координаты нормализованы в диапазоне от 0 до 1000 для осей X и Y.
- (x=0, y=0) — верхний левый угол окна/скриншота.
- (x=1000, y=1000) — нижний правый угол окна/скриншота.
- Всегда выбирай координаты (x, y) ТОЧНО В ЦЕНТРЕ нужной кнопки, ссылки, иконки или поля ввода.

ПРАВИЛА И СТРАТЕГИЯ / НЕГІЗГІ ЕРЕЖЕЛЕР:

1. АЙРЫҚША МАҢЫЗДЫ: БРАУЗЕРДІҢ МЕКЕНЖАЙ ЖОЛЫ (URL BAR / OMNIBOX) МЕН САЙТТЫҢ ІШКІ ІЗДЕУІН ШАТАСТЫРМА!
   - КРИТИЧЕСКИ ВАЖНОЕ ПРАВИЛО: НЕ ПУТАЙ АДРЕСНУЮ СТРОКУ БРАУЗЕРА И ВНУТРЕННИЙ ПОИСК САЙТА!
   - Егер сен сайтқа кіріп қойған болсаң (мысалы, YouTube, Wikipedia, маркетплейс немесе кез келген басқа портал):
     ЕШҚАШАН іздеу сөзін браузердің ең үстіндегі мекенжай жолағына (URL / Omnibox: "https://...", әдетте y < 80) жазба!
     Мекенжай жолағына сұраныс жазсаң, браузер сайтты тастап, Google/Яндекс/Bing іздеу парақшасына өтіп кетеді.
   - YouTube-те іздеу: Строка поиска YouTube орналасқан жері — веб-беттің жоғарғы ортасында (y шамамен 90-130 аралығында), оң жағында лупа 🔍 белгісі бар.
     Әрдайым ДӘЛ ОСЫ YouTube-тің ішкі іздеу өрісін (y ≈ 105, x ≈ 480-550) басып, мәтінді сол жерге енгіз!
   - Бұл ереже барлық сайттарға қатысты: сайт ішіндегі контентті іздеу үшін тек сайттың өзінің іздеу өрісін қолдан.

2. Для ввода текста (`type`):
   - ВСЕГДА указывай координаты `x, y` поля ввода прямо в действии `type`, либо предварительно выполни `click` по полю ввода, чтобы установить текстовый курсор! Не пытайся вводить текст вслепую.
   - Если после ввода нужно отправить форму или начать поиск — нажми клавишу Enter (`press`, key="enter") или кликни по кнопке с иконкой лупы 🔍.

3. Для прокрутки страницы, если нужный контент находится ниже:
   - Используй `action: "scroll"` с `amount: -500` (отрицательное число скроллит вниз).

4. Если страница еще загружается или открывается модальное окно:
   - Используй `action: "wait"` с нужным временем ожидания (1-3 секунды).

5. Для воспроизведения медиа / прослушивания звука (`listen`):
   - Если пользователь попросил включить песню, видео или музыку:
     a) Введи название песни в поисковую строку САЙТА (YouTube).
     b) Нажми Enter или кнопку поиска.
     c) На странице результатов КЛИКНИ ПО ПЕРВОМУ ПОДХОДЯЩЕМУ ВИДЕО (превью или названию), чтобы началось воспроизведение!
     d) Убедись, что воспроизведение началось, после чего заверши задачу (`done`).

6. Когда цель пользователя ПОЛНОСТЬЮ достигнута:
   - Выдай `action: "done"` и в `message` опиши итог работы (мысалы: "YouTube-те сұралған ән табылып, қосылды!").

7. Если возникла неустранимая ошибка или задачу невозможно выполнить:
   - Выдай `action: "fail"` с описанием причины.

8. Не повторяй одно и то же действие, если после прошлого шага страница не изменилась — попробуй альтернативный способ (другую кнопку, скролл или поиск).

9. СМЕНА НАПРАВЛЕНИЯ ПОЛЬЗОВАТЕЛЕМ (`redirect`):
   - Если пользователь прервал работу и задал новую инструкцию:
     Мгновенно переключись на новую цель! Оцени текущий скриншот и начни выполнять шаги для достижения обновленной задачи.
"""

class GeminiAgentClient:
    def __init__(self, api_key: str, model_name: str = "gemini-2.5-flash"):
        self.api_key = api_key.strip()
        self.model_name = model_name.strip() or "gemini-2.5-flash"
        self.client = genai.Client(api_key=self.api_key)

    def test_connection(self) -> Tuple[bool, str]:
        """
        API кілтінің жарамдылығын және Gemini байланысын тексереді.
        """
        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents="Ping. Respond with single word: OK"
            )
            if response and response.text:
                return True, "Байланыс сәтті орнатылды! / Связь успешно установлена!"
            return False, "Бос жауап қайтарылды / Получен пустой ответ"
        except Exception as e:
            err = str(e)
            if "API_KEY_INVALID" in err or "400" in err:
                return False, "API кілті қате немесе жарамсыз (API_KEY_INVALID)."
            if "RESOURCE_EXHAUSTED" in err or "429" in err:
                return False, "Сұраныс лимиті таусылды (Quota Exceeded / Rate Limit)."
            return False, f"Қате: {err}"

    def transcribe_audio(self, wav_bytes: bytes) -> str:
        """Переводит голос в текст через Gemini API."""
        try:
            audio_part = types.Part.from_bytes(data=wav_bytes, mime_type="audio/wav")
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=[audio_part, "Transcribe this audio precisely in Kazakh, Russian or the spoken language. Return ONLY the transcribed text, without any formatting or extra words."]
            )
            return response.text.strip() if response.text else ""
        except Exception as e:
            print(f"[!] Ошибка распознавания речи: {e}")
            return ""

    def _image_to_part(self, image: Image.Image) -> types.Part:
        """Конвертирует PIL изображение в JPEG Part для Gemini API."""
        buffer = io.BytesIO()
        if image.mode != "RGB":
            image = image.convert("RGB")
        image.save(buffer, format="JPEG", quality=85)
        image_bytes = buffer.getvalue()
        return types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg")

    def decide_next_action(
        self,
        goal: str,
        current_image: Image.Image,
        history: List[Dict[str, Any]],
        step_number: int
    ) -> ActionDecision:
        """
        Отправляет скриншот и контекст задачи в Gemini API и возвращает структурированное решение.
        """
        img_part = self._image_to_part(current_image)

        history_text = "Алдыңғы әрекеттер жоқ (алғашқы қадам) / Предыдущих действий нет."
        if history:
            items = []
            for h in history[-5:]:
                step_idx = h.get("step", "?")
                act = h.get("action", "")
                detail = h.get("detail", "")
                thought_prev = h.get("thought", "")
                items.append(f"Қадам {step_idx}: Әрекет '{act}' ({detail}). Ой: {thought_prev}")
            history_text = "\n".join(items)

        user_prompt = f"""ПАЙДАЛАНУШЫ ТАПСЫРМАСЫ / ЗАДАЧА ПОЛЬЗОВАТЕЛЯ:
{goal}

АҒЫМДАҒЫ ҚАДАМ / ТЕКУЩИЙ ШАГ: #{step_number}

СОҢҒЫ ОРЫНДАЛҒАН ҚАДАМДАР ТАРИХЫ / ИСТОРИЯ ШАГОВ:
{history_text}

Қоса берілген скриншотты мұқият талдап, мақсатқа жету үшін БІР келесі әрекетті таңда.
ЕСКЕРТУ: Егер сайт ашық болса (мысалы, YouTube), іздеу сөзін браузердің мекенжай жолағына ЕМЕС, сайттың өзінің ішкі іздеу жолағына енгіз!
Жауапты қатаң түрде JSON пішімінде берілген схема бойынша қайтар.
"""

        gen_config = types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            temperature=0.2,
            response_mime_type="application/json",
            response_schema=ActionDecision
        )

        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=[img_part, user_prompt],
                config=gen_config
            )

            if hasattr(response, "parsed") and isinstance(response.parsed, ActionDecision):
                return response.parsed

            response_text = response.text or ""
            return ActionDecision.model_validate_json(response_text)

        except Exception as e:
            try:
                raw_text = getattr(response, "text", "")
                match = re.search(r"\{.*\}", raw_text, re.DOTALL)
                if match:
                    data = json.loads(match.group(0))
                    return ActionDecision(**data)
            except Exception:
                pass
            raise RuntimeError(f"Gemini Vision API қатесі: {e}")

    def analyze_audio(self, audio_bytes: bytes, goal_context: str) -> str:
        """
        Отправляет аудиозапись из браузера/сайта в Gemini для расшифровки речи или анализа звукового контента.
        """
        audio_part = types.Part.from_bytes(data=audio_bytes, mime_type="audio/wav")
        prompt = f"""Ниже прикреплена аудиозапись, перехваченная с вкладки сайта/браузера во время выполнения задачи:
ТАПСЫРМА КОНТЕКСТІ / КОНТЕКСТ ЗАДАЧИ: {goal_context}

Тапсырма:
1. Егер жазбада адам дауысы не сөздер болса — мәтінін дәл жазып бер.
2. Егер дауыс болмаса — дыбыс сипатын түсіндір (музыка, дыбыстық белгі, тыныштық).
3. Агентке келесі қадамды орындауға қажетті ақпаратты шығар."""

        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=[audio_part, prompt]
            )
            return response.text.strip() if response.text else "Аудиозапись пуста или не содержит распознаваемого звука."
        except Exception as e:
            return f"Аудио талдау сәтсіз аяқталды: {e}"
