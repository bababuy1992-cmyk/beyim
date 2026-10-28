# 🤖 BEYIM • AI Desktop Agent

<div align="center">

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Gemini Vision](https://img.shields.io/badge/Google%20Gemini-Vision-4285F4?style=for-the-badge&logo=google&logoColor=white)
![Platform](https://img.shields.io/badge/Platform-Windows-0078D6?style=for-the-badge&logo=windows&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)

**Компьютер мен браузерді дербес басқаратын интеллектуалды десктоп AI-агент**  
*Автономный интеллектуальный AI-агент с графическим чат-интерфейсом для управления компьютером и браузером.*

</div>

---

## 🌟 Негізгі ерекшеліктері / Особенности

- 🎨 **Ыңғайлы әрі жағымды заманауи интерфейс (Modern Dark UI)**:
  - Чат форматындағы көрініс, әр қадамның (клик, мәтін жазу, скролл, дыбыс тыңдау) визуалды карточкалары.
  - Түсірілген скриншоттарды бір батырмамен ашып көру мүмкіндігі.
  - Жылдам үлгілер (Quick Prompts: Google іздеу, YouTube, Блокнот, т.б.).
- 🔑 **API кілтті қауіпсіз басқару және бастапқы кодтан бөлу**:
  - API кілті бастапқы кодта сақталмайды, қауіпсіз `.env` файлында немесе баптаулар терезесінде енгізіледі.
  - Кіріктірілген **«Байланысты тексеру»** батырмасы арқылы кілттің жарамдылығын алдын ала тексеру.
- 👁️ **Мультимодальды көру (Google Gemini Vision)**:
  - `gemini-2.5-flash`, `gemini-2.0-flash`, `gemini-2.5-pro` немесе `gemini-3.5-flash-lite` үлгілерін таңдау.
  - Экрандағы кез келген батырма, мәтін енгізу өрісі, сілтемелер мен модальды терезелерді тану және басқару.
- 🎤 **Дауыспен тапсырма беру (Voice Input)**:
  - Микрофон арқылы дауысты жазып, оны Gemini арқылы дәл мәтінге айналдыру.
- 🎧 **Жүйелік дыбысты тыңдау (WASAPI Loopback)**:
  - Браузердегі бейнежазбалар немесе сайт дыбыстарын тыңдап, қажетті мәліметті шығару.
- 🛡️ **Қауіпсіздік және шұғыл тоқтату (Emergency Stop)**:
  - `F8` немесе `Pause` пернелері арқылы лезде тоқтату.
  - Графикалық интерфейстегі `⏹ Тоқтату` батырмасы.
  - PyAutoGUI Fail-Safe: тінтуірді экранның жоғарғы сол бұрышына `(0, 0)` апарғанда дереу тоқтату.

---

## 🚀 Орнату және іске қосу

### 1. Репозиторийді жүктеу
```bash
git clone https://github.com/<сіздің-аккаунтыңыз>/beyim.git
cd beyim
```

### 2. Тәуелділіктерді орнату
```powershell
pip install -r requirements.txt
```

### 3. Бағдарламаны іске қосу
```powershell
python main.py
```
немесе `start.bat` файлын екі рет басу арқылы.

Алғаш рет қосқанда бағдарлама терезесі шығып, **Google AI Studio** тегін API кілтін сұрайды. Оны [aistudio.google.com](https://aistudio.google.com/) сайтынан тегін алуға болады.

---

## ⚙️ Скомпилированная версия (EXE)

Қосымша дербес Windows `.exe` қосымшасы ретінде жиналады (Python орнатуды талап етпейді):
```
dist\BeyimAgent\BeyimAgent.exe
```

Қайта жинау (компиляция) үшін:
```powershell
pyinstaller BeyimAgent.spec --noconfirm --clean
```

---

## 📁 Жоба құрылымы / Структура проекта

```
beyim/
├── main.py              # Негізгі кіру нүктесі (Entry point)
├── gui_chat.py          # Баптаулары бар заманауи графикалық чат-интерфейс
├── agent.py             # Компьютерді автономды басқару агентінің циклі
├── ai_client.py         # Google Gemini API клиенті (Vision & Audio)
├── actions.py           # Тінтуір мен пернетақта әрекеттері (Unicode қолдауымен)
├── screen_capture.py    # Экран мен терезелерді түсіру
├── audio_capture.py     # Жүйелік дыбыс пен микрофонды жазу
├── overlay.py           # Скриншоттардағы әрекет таңбалары (Viz markers)
├── interrupt_handler.py # F8/Pause шұғыл тоқтату перехваты
├── config.py            # Конфигурация мен параметрлерді қауіпсіз басқару
├── test_agent.py        # Автоматтандырылған тесттер жинағы
├── requirements.txt     # Python кітапханалары
├── BeyimAgent.spec      # PyInstaller жинақтау файлы
├── start.bat            # Ыңғайлы іске қосу скрипті
├── .env.example         # Параметрлер үлгісі (кілтсіз)
└── .gitignore           # Қауіпсіздік және артық файлдарды елемеу
```

---

## 🧪 Тесттерді орындау

Барлық модульдердің дұрыс жұмыс істеуін тексеру:
```powershell
python -m unittest test_agent.py
```

---

## 👥 Авторлар мен контрибьюторлар (Contributors)

- 👑 **Жоба авторы және жетекшісі:** [@bababuy1992-cmyk](https://github.com/bababuy1992-cmyk)
- 🤖 **AI Жұптас бағдарламашы (AI Pair Programmer):** Antigravity (Google DeepMind)

---

## 📄 Лицензия

MIT License © 2026 Beyim Project
