import os
import sys
import time
import queue
import threading
import webbrowser
from pathlib import Path
from typing import Optional, Dict, Any, List

import tkinter as tk
from tkinter import ttk, messagebox

import config
import audio_capture
from ai_client import GeminiAgentClient
from agent import BrowserAgent

# ==========================================
# Заманауи түстер палитрасы (Obsidian / Catppuccin Dark)
# ==========================================
BG_MAIN = "#0d1117"        # Негізгі фон
BG_PANEL = "#161b22"       # Жоғарғы және төменгі панель
BG_CARD = "#1c2128"        # Карталар фоны
BG_INPUT = "#21262d"       # Енгізу өрістері және түймелер
BG_HOVER = "#30363d"       # Түйменің үстіне барғандағы түс
BG_USER_BUBBLE = "#1f2937" # Пайдаланушы хабарламасы
TEXT_MAIN = "#f0f6fc"      # Негізгі мәтін (ашық)
TEXT_MUTED = "#8b949e"     # Қосалқы мәтін (сұр)
BORDER_COLOR = "#30363d"   # Жиектер түсі

ACCENT_BLUE = "#58a6ff"    # Басты батырмалар
ACCENT_GREEN = "#3fb950"   # Сәтті / Дайын күй
ACCENT_RED = "#f85149"     # Қате / Тоқтату
ACCENT_YELLOW = "#d29922"  # Ағымдағы қадам
ACCENT_PURPLE = "#bc8cff"  # Модель белгісі

AVAILABLE_MODELS = [
    "gemini-2.5-flash",
    "gemini-2.0-flash",
    "gemini-1.5-flash",
    "gemini-2.5-pro",
    "gemini-3.5-flash-lite"
]

class SettingsDialog(tk.Toplevel):
    """
    Параметрлер мен API кілтін баптау терезесі (Settings & API Key Modal)
    """
    def __init__(self, parent, on_saved=None):
        super().__init__(parent)
        self.title("⚙️ Баптаулар • Настройки Beyim Agent")
        self.geometry("560x520")
        self.resizable(False, False)
        self.configure(bg=BG_MAIN)
        self.transient(parent)
        self.grab_set()

        self.on_saved = on_saved
        self._center_window(parent)
        self._build_ui()

    def _center_window(self, parent):
        self.update_idletasks()
        pw = parent.winfo_width()
        ph = parent.winfo_height()
        px = parent.winfo_rootx()
        py = parent.winfo_rooty()
        w, h = 560, 520
        if pw > 100 and ph > 100:
            x = px + (pw - w) // 2
            y = py + (ph - h) // 2
        else:
            x = (self.winfo_screenwidth() - w) // 2
            y = (self.winfo_screenheight() - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")

    def _build_ui(self):
        container = tk.Frame(self, bg=BG_MAIN, padx=24, pady=20)
        container.pack(fill=tk.BOTH, expand=True)

        # 1. Тақырып
        lbl_title = tk.Label(
            container,
            text="🔑 Google Gemini API & Параметрлер",
            font=("Segoe UI", 15, "bold"),
            bg=BG_MAIN,
            fg=TEXT_MAIN
        )
        lbl_title.pack(anchor="w", pady=(0, 4))

        lbl_sub = tk.Label(
            container,
            text="API кілті мен агент жұмысын өз қалауыңызша баптаңыз.",
            font=("Segoe UI", 9),
            bg=BG_MAIN,
            fg=TEXT_MUTED
        )
        lbl_sub.pack(anchor="w", pady=(0, 16))

        # 2. API Key бөлімі
        key_box = tk.LabelFrame(
            container,
            text=" Google AI Studio API Кілт ",
            font=("Segoe UI", 10, "bold"),
            bg=BG_CARD,
            fg=ACCENT_BLUE,
            padx=14,
            pady=10,
            relief=tk.GROOVE,
            highlightthickness=0
        )
        key_box.pack(fill=tk.X, pady=(0, 14))

        link_lbl = tk.Label(
            key_box,
            text="👉 Тегін кілтті алу: aistudio.google.com",
            font=("Segoe UI", 9, "underline"),
            bg=BG_CARD,
            fg=ACCENT_BLUE,
            cursor="hand2"
        )
        link_lbl.pack(anchor="w", pady=(0, 6))
        link_lbl.bind("<Button-1>", lambda e: webbrowser.open("https://aistudio.google.com/"))

        row_key = tk.Frame(key_box, bg=BG_CARD)
        row_key.pack(fill=tk.X, pady=(0, 6))

        self.key_var = tk.StringVar(value=config.GEMINI_API_KEY)
        self.entry_key = tk.Entry(
            row_key,
            textvariable=self.key_var,
            font=("Consolas", 10),
            bg=BG_INPUT,
            fg=TEXT_MAIN,
            insertbackground=TEXT_MAIN,
            relief=tk.FLAT,
            show="•"
        )
        self.entry_key.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=5, padx=(0, 6))

        btn_paste = tk.Button(
            row_key,
            text="Қою / Вставить",
            font=("Segoe UI", 9),
            bg=BG_HOVER,
            fg=TEXT_MAIN,
            relief=tk.FLAT,
            command=self._paste_clipboard,
            padx=8,
            pady=3,
            cursor="hand2"
        )
        btn_paste.pack(side=tk.RIGHT)

        row_key_opts = tk.Frame(key_box, bg=BG_CARD)
        row_key_opts.pack(fill=tk.X)

        self.show_key_var = tk.BooleanVar(value=False)
        chk_show = tk.Checkbutton(
            row_key_opts,
            text="Кілтті көрсету / Показать",
            variable=self.show_key_var,
            font=("Segoe UI", 9),
            bg=BG_CARD,
            fg=TEXT_MUTED,
            selectcolor=BG_INPUT,
            activebackground=BG_CARD,
            activeforeground=TEXT_MAIN,
            command=self._toggle_show_key
        )
        chk_show.pack(side=tk.LEFT)

        self.btn_test = tk.Button(
            row_key_opts,
            text="🔍 Тексеру / Проверить API",
            font=("Segoe UI", 9, "bold"),
            bg="#238636",
            fg="#ffffff",
            activebackground="#2ea043",
            activeforeground="#ffffff",
            relief=tk.FLAT,
            command=self._test_api_connection,
            padx=10,
            pady=2,
            cursor="hand2"
        )
        self.btn_test.pack(side=tk.RIGHT)

        self.lbl_test_status = tk.Label(
            key_box,
            text="",
            font=("Segoe UI", 9),
            bg=BG_CARD,
            fg=TEXT_MUTED,
            wraplength=480,
            justify=tk.LEFT
        )
        self.lbl_test_status.pack(anchor="w", pady=(4, 0))

        # 3. Модель және параметрлер
        opts_box = tk.LabelFrame(
            container,
            text=" Модель және орындалу параметрлері ",
            font=("Segoe UI", 10, "bold"),
            bg=BG_CARD,
            fg=ACCENT_PURPLE,
            padx=14,
            pady=10,
            relief=tk.GROOVE,
            highlightthickness=0
        )
        opts_box.pack(fill=tk.X, pady=(0, 16))

        # Модель таңдау
        row_m = tk.Frame(opts_box, bg=BG_CARD)
        row_m.pack(fill=tk.X, pady=(0, 8))
        lbl_m = tk.Label(row_m, text="Gemini Моделі:", font=("Segoe UI", 9, "bold"), bg=BG_CARD, fg=TEXT_MAIN, width=16, anchor="w")
        lbl_m.pack(side=tk.LEFT)

        self.model_var = tk.StringVar(value=config.GEMINI_MODEL)
        self.cmb_model = ttk.Combobox(
            row_m,
            textvariable=self.model_var,
            values=AVAILABLE_MODELS,
            state="readonly",
            font=("Segoe UI", 9)
        )
        self.cmb_model.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Қадам кідірісі (Step delay)
        row_d = tk.Frame(opts_box, bg=BG_CARD)
        row_d.pack(fill=tk.X, pady=(0, 8))
        lbl_d = tk.Label(row_d, text="Кідіріс (сек):", font=("Segoe UI", 9, "bold"), bg=BG_CARD, fg=TEXT_MAIN, width=16, anchor="w")
        lbl_d.pack(side=tk.LEFT)

        self.delay_var = tk.DoubleVar(value=config.STEP_DELAY)
        spn_d = tk.Spinbox(
            row_d,
            from_=1.0,
            to=15.0,
            increment=0.5,
            textvariable=self.delay_var,
            font=("Segoe UI", 9),
            bg=BG_INPUT,
            fg=TEXT_MAIN,
            width=10,
            relief=tk.FLAT
        )
        spn_d.pack(side=tk.LEFT)
        lbl_d_hint = tk.Label(row_d, text=" (Flash үшін 3.0 - 4.0 ұсынылады)", font=("Segoe UI", 8), bg=BG_CARD, fg=TEXT_MUTED)
        lbl_d_hint.pack(side=tk.LEFT, padx=6)

        # Чекбокстар
        row_chk = tk.Frame(opts_box, bg=BG_CARD)
        row_chk.pack(fill=tk.X)

        self.shot_var = tk.BooleanVar(value=config.SAVE_SCREENSHOTS)
        chk_shot = tk.Checkbutton(
            row_chk,
            text="Скриншоттарды сақтау",
            variable=self.shot_var,
            font=("Segoe UI", 9),
            bg=BG_CARD,
            fg=TEXT_MAIN,
            selectcolor=BG_INPUT,
            activebackground=BG_CARD,
            activeforeground=TEXT_MAIN
        )
        chk_shot.pack(side=tk.LEFT, padx=(0, 14))

        self.audio_var = tk.BooleanVar(value=config.AUDIO_ENABLED)
        chk_audio = tk.Checkbutton(
            row_chk,
            text="Дыбысты өңдеу (Аудио)",
            variable=self.audio_var,
            font=("Segoe UI", 9),
            bg=BG_CARD,
            fg=TEXT_MAIN,
            selectcolor=BG_INPUT,
            activebackground=BG_CARD,
            activeforeground=TEXT_MAIN
        )
        chk_audio.pack(side=tk.LEFT)

        # 4. Төменгі сақтау батырмасы
        btn_box = tk.Frame(container, bg=BG_MAIN)
        btn_box.pack(fill=tk.X, side=tk.BOTTOM)

        btn_save = tk.Button(
            btn_box,
            text="💾 Сақтау және қолдану / Сохранить",
            font=("Segoe UI", 11, "bold"),
            bg=ACCENT_BLUE,
            fg="#0f111a",
            activebackground="#79b8ff",
            activeforeground="#0f111a",
            relief=tk.FLAT,
            command=self._save_and_close,
            pady=8,
            cursor="hand2"
        )
        btn_save.pack(fill=tk.X)

    def _toggle_show_key(self):
        if self.show_key_var.get():
            self.entry_key.config(show="")
        else:
            self.entry_key.config(show="•")

    def _paste_clipboard(self):
        try:
            val = self.clipboard_get().strip()
            self.key_var.set(val)
        except Exception:
            pass

    def _test_api_connection(self):
        key = self.key_var.get().strip()
        if not key:
            self.lbl_test_status.config(text="⚠️ Алдымен API кілтті енгізіңіз!", fg=ACCENT_YELLOW)
            return

        model = self.model_var.get().strip() or "gemini-2.5-flash"
        self.lbl_test_status.config(text="⏳ Gemini API тексерілуде...", fg=ACCENT_BLUE)
        self.btn_test.config(state=tk.DISABLED)

        def _worker():
            try:
                client = GeminiAgentClient(api_key=key, model_name=model)
                ok, msg = client.test_connection()
                if ok:
                    self.lbl_test_status.config(text=f"✅ {msg}", fg=ACCENT_GREEN)
                else:
                    self.lbl_test_status.config(text=f"❌ {msg}", fg=ACCENT_RED)
            except Exception as e:
                self.lbl_test_status.config(text=f"❌ Қате: {e}", fg=ACCENT_RED)
            finally:
                self.btn_test.config(state=tk.NORMAL)

        threading.Thread(target=_worker, daemon=True).start()

    def _save_and_close(self):
        key = self.key_var.get().strip()
        model = self.model_var.get().strip()
        delay = float(self.delay_var.get())
        shots = bool(self.shot_var.get())
        audio = bool(self.audio_var.get())

        config.save_settings(
            api_key=key,
            model=model,
            step_delay=delay,
            save_screenshots=shots,
            audio_enabled=audio
        )

        if self.on_saved:
            self.on_saved(key, model)
        self.destroy()


class ChatApp(tk.Tk):
    """
    BEYIM • AI Desktop Agent басты терезесі
    """
    def __init__(self):
        super().__init__()
        self.title("🤖 BEYIM • AI Desktop Agent")
        self.geometry("960x740")
        self.minsize(760, 560)
        self.configure(bg=BG_MAIN)

        self._center_window()
        self.queue = queue.Queue()
        self.current_agent: Optional[BrowserAgent] = None
        self.agent_thread: Optional[threading.Thread] = None
        self.is_running = False
        self.current_agent_box = None

        self._build_ui()

        # Оқиғалар кезегін тексеру
        self.after(50, self._process_queue)

        # Іске қосылғанда кілтті тексеру
        self.after(200, self._check_api_key_on_startup)

    def _center_window(self):
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        w, h = 960, 740
        x = max(0, (sw - w) // 2)
        y = max(0, (sh - h) // 2)
        self.geometry(f"{w}x{h}+{x}+{y}")

    def _check_api_key_on_startup(self):
        if not config.GEMINI_API_KEY:
            self._open_settings_dialog()

    def _open_settings_dialog(self):
        dlg = SettingsDialog(self, on_saved=self._on_settings_saved)
        self.wait_window(dlg)

    def _on_settings_saved(self, key: str, model: str):
        self.badge_model.config(text=f"✨ {model}")
        if key:
            self._add_system_message("✅ Баптаулар сақталды және API байланысы белсенді!")

    def _build_ui(self):
        # 1. Жоғарғы тақырыпша (Header)
        header = tk.Frame(self, bg=BG_PANEL, padx=18, pady=12, highlightbackground=BORDER_COLOR, highlightthickness=1)
        header.pack(fill=tk.X, side=tk.TOP)

        hdr_left = tk.Frame(header, bg=BG_PANEL)
        hdr_left.pack(side=tk.LEFT)

        lbl_app_name = tk.Label(
            hdr_left,
            text="⚡ BEYIM AGENT",
            font=("Segoe UI", 14, "bold"),
            bg=BG_PANEL,
            fg=TEXT_MAIN
        )
        lbl_app_name.pack(side=tk.LEFT, padx=(0, 10))

        self.badge_model = tk.Label(
            hdr_left,
            text=f"✨ {config.GEMINI_MODEL}",
            font=("Segoe UI", 9, "bold"),
            bg=BG_INPUT,
            fg=ACCENT_PURPLE,
            padx=8,
            pady=3,
            cursor="hand2"
        )
        self.badge_model.pack(side=tk.LEFT, padx=(0, 8))
        self.badge_model.bind("<Button-1>", lambda e: self._open_settings_dialog())

        badge_mode = tk.Label(
            hdr_left,
            text="🖥️ Толық автобасқару (Full Control)",
            font=("Segoe UI", 9),
            bg=BG_INPUT,
            fg=ACCENT_GREEN,
            padx=8,
            pady=3
        )
        badge_mode.pack(side=tk.LEFT)

        hdr_right = tk.Frame(header, bg=BG_PANEL)
        hdr_right.pack(side=tk.RIGHT)

        btn_clear = tk.Button(
            hdr_right,
            text="🧹 Тазалау",
            font=("Segoe UI", 9),
            bg=BG_INPUT,
            fg=TEXT_MAIN,
            activebackground=BG_HOVER,
            activeforeground=TEXT_MAIN,
            relief=tk.FLAT,
            command=self._clear_chat,
            padx=8,
            pady=3,
            cursor="hand2"
        )
        btn_clear.pack(side=tk.RIGHT, padx=(6, 0))

        btn_logs = tk.Button(
            hdr_right,
            text="📁 Логтар",
            font=("Segoe UI", 9),
            bg=BG_INPUT,
            fg=TEXT_MAIN,
            activebackground=BG_HOVER,
            activeforeground=TEXT_MAIN,
            relief=tk.FLAT,
            command=self._open_logs_folder,
            padx=8,
            pady=3,
            cursor="hand2"
        )
        btn_logs.pack(side=tk.RIGHT, padx=(6, 0))

        btn_settings = tk.Button(
            hdr_right,
            text="⚙️ Баптаулар",
            font=("Segoe UI", 9, "bold"),
            bg=BG_HOVER,
            fg=TEXT_MAIN,
            activebackground=BORDER_COLOR,
            activeforeground=TEXT_MAIN,
            relief=tk.FLAT,
            command=self._open_settings_dialog,
            padx=10,
            pady=3,
            cursor="hand2"
        )
        btn_settings.pack(side=tk.RIGHT)

        # 2. Чат алаңы (Scrollable Canvas)
        chat_container = tk.Frame(self, bg=BG_MAIN, padx=16, pady=8)
        chat_container.pack(fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(chat_container, bg=BG_MAIN, highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(chat_container, orient=tk.VERTICAL, command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.messages_frame = tk.Frame(self.canvas, bg=BG_MAIN)
        self.canvas_window = self.canvas.create_window((0, 0), window=self.messages_frame, anchor="nw")

        self.messages_frame.bind("<Configure>", self._on_frame_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

        # Сәлемдесу және жылдам үлгілер
        self._add_welcome_message()

        # 3. Төменгі басқару тақтасы (Bottom Panel)
        bottom_panel = tk.Frame(self, bg=BG_PANEL, padx=16, pady=10, highlightbackground=BORDER_COLOR, highlightthickness=1)
        bottom_panel.pack(fill=tk.X, side=tk.BOTTOM)

        # Үстіңгі күй жолы мен опциялар
        opts_frame = tk.Frame(bottom_panel, bg=BG_PANEL)
        opts_frame.pack(fill=tk.X, pady=(0, 6))

        self.minimize_var = tk.BooleanVar(value=True)
        chk_min = tk.Checkbutton(
            opts_frame,
            text="Іске қосқанда терезені кішірейту (агент толық экранды көруі үшін)",
            variable=self.minimize_var,
            font=("Segoe UI", 9),
            bg=BG_PANEL,
            fg=TEXT_MUTED,
            selectcolor=BG_INPUT,
            activebackground=BG_PANEL,
            activeforeground=TEXT_MAIN
        )
        chk_min.pack(side=tk.LEFT)

        self.lbl_status = tk.Label(
            opts_frame,
            text="🟢 Дайын / F8 немесе Pause — тоқтату",
            font=("Segoe UI", 9),
            bg=BG_PANEL,
            fg=ACCENT_GREEN
        )
        self.lbl_status.pack(side=tk.RIGHT)

        # Жылдам шаблон түймелері (Quick action chips)
        chips_frame = tk.Frame(bottom_panel, bg=BG_PANEL)
        chips_frame.pack(fill=tk.X, pady=(0, 6))

        lbl_quick = tk.Label(chips_frame, text="Жылдам үлгілер:", font=("Segoe UI", 8, "bold"), bg=BG_PANEL, fg=TEXT_MUTED)
        lbl_quick.pack(side=tk.LEFT, padx=(0, 6))

        quick_prompts = [
            ("🌐 Ауа райы", "Google Chrome-ды ашып, Алматыдағы ауа райын ізде"),
            ("🎵 YouTube", "Браузерді ашып, youtube.com сайтынан қазақша күй қос"),
            ("📝 Блокнот", "Notepad (Блокнот) бағдарламасын ашып, сәлемдесу мәтінін жаз"),
            ("🔍 Жаңалықтар", "Браузерде бүгінгі соңғы жаңалықтарды аш")
        ]
        for label, prompt in quick_prompts:
            btn_chip = tk.Button(
                chips_frame,
                text=label,
                font=("Segoe UI", 8),
                bg=BG_CARD,
                fg=ACCENT_BLUE,
                activebackground=BG_HOVER,
                activeforeground=TEXT_MAIN,
                relief=tk.FLAT,
                command=lambda p=prompt: self._insert_prompt(p),
                padx=6,
                pady=1,
                cursor="hand2"
            )
            btn_chip.pack(side=tk.LEFT, padx=3)

        # Мәтін енгізу жолы мен батырмалар
        input_row = tk.Frame(bottom_panel, bg=BG_PANEL)
        input_row.pack(fill=tk.X)

        self.text_input = tk.Text(
            input_row,
            height=2,
            font=("Segoe UI", 11),
            bg=BG_INPUT,
            fg=TEXT_MAIN,
            insertbackground=TEXT_MAIN,
            relief=tk.FLAT,
            padx=10,
            pady=8,
            wrap=tk.WORD
        )
        self.text_input.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))
        self.text_input.bind("<Return>", self._on_return_pressed)

        self.btn_voice = tk.Button(
            input_row,
            text="🎤 Дауыс",
            font=("Segoe UI", 10),
            bg=BG_INPUT,
            fg=TEXT_MAIN,
            activebackground=BG_HOVER,
            activeforeground=TEXT_MAIN,
            relief=tk.FLAT,
            command=self._record_voice_prompt,
            padx=12,
            pady=6,
            cursor="hand2"
        )
        self.btn_voice.pack(side=tk.LEFT, padx=(0, 6))

        self.btn_send = tk.Button(
            input_row,
            text="▶ Іске қосу",
            font=("Segoe UI", 11, "bold"),
            bg=ACCENT_BLUE,
            fg="#0d1117",
            activebackground="#79b8ff",
            activeforeground="#0d1117",
            relief=tk.FLAT,
            command=self._send_task,
            padx=18,
            pady=6,
            cursor="hand2"
        )
        self.btn_send.pack(side=tk.LEFT, padx=(0, 6))

        self.btn_stop = tk.Button(
            input_row,
            text="⏹ Тоқтату",
            font=("Segoe UI", 11, "bold"),
            bg=ACCENT_RED,
            fg="#ffffff",
            activebackground="#da3633",
            activeforeground="#ffffff",
            relief=tk.FLAT,
            command=self._stop_task,
            padx=14,
            pady=6,
            state=tk.DISABLED,
            cursor="hand2"
        )
        self.btn_stop.pack(side=tk.LEFT)

    def _insert_prompt(self, text: str):
        self.text_input.delete("1.0", tk.END)
        self.text_input.insert("1.0", text)
        self.text_input.focus_set()

    def _clear_chat(self):
        for widget in self.messages_frame.winfo_children():
            widget.destroy()
        self.current_agent_box = None
        self._add_welcome_message()

    def _on_frame_configure(self, event=None):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas_configure(self, event):
        self.canvas.itemconfig(self.canvas_window, width=event.width)

    def _on_mousewheel(self, event):
        if event.delta:
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _scroll_to_bottom(self):
        self.update_idletasks()
        self.canvas.yview_moveto(1.0)

    def _on_return_pressed(self, event):
        if not event.state & 0x0001:
            self._send_task()
            return "break"

    def _open_logs_folder(self):
        config.RUN_LOGS_DIR.mkdir(parents=True, exist_ok=True)
        try:
            os.startfile(str(config.RUN_LOGS_DIR))
        except Exception as e:
            messagebox.showerror("Қате", f"Логтар папкасын ашу мүмкін болмады: {e}", parent=self)

    def _add_welcome_message(self):
        card = tk.Frame(self.messages_frame, bg=BG_CARD, padx=16, pady=14, highlightbackground=BORDER_COLOR, highlightthickness=1)
        card.pack(fill=tk.X, pady=(0, 10), padx=4)

        lbl_head = tk.Label(
            card,
            text="👋 Сәлем! Мен дербес AI көмекші Beyim агентімін",
            font=("Segoe UI", 12, "bold"),
            bg=BG_CARD,
            fg=ACCENT_BLUE
        )
        lbl_head.pack(anchor="w", pady=(0, 6))

        msg = (
            "• Жүйелік үлгі: Google Gemini Vision (мультимодальды көру және дыбыс талдау)\n"
            "• Мүмкіндік: Компьютер экранын көру, тінтуір мен пернетақтаны толық автоматты басқару\n"
            "• Қолдану тәсілі: Төмендегі өріске қазақша немесе орысша тапсырма жазыңыз және «Іске қосу» басыңыз\n"
            "• Шұғыл тоқтату: Кез келген сәтте [F8] пернесі, «Тоқтату» батырмасы немесе тінтуірді (0, 0) бұрышына апару"
        )
        lbl_body = tk.Label(card, text=msg, font=("Segoe UI", 9), bg=BG_CARD, fg=TEXT_MAIN, justify=tk.LEFT)
        lbl_body.pack(anchor="w")

    def _add_user_message(self, text: str):
        row = tk.Frame(self.messages_frame, bg=BG_MAIN)
        row.pack(fill=tk.X, pady=6, padx=4)

        bubble = tk.Frame(row, bg=BG_USER_BUBBLE, padx=14, pady=10, highlightbackground="#374151", highlightthickness=1)
        bubble.pack(side=tk.RIGHT, anchor="e")

        lbl_title = tk.Label(bubble, text="👤 Сіздің тапсырмаңыз:", font=("Segoe UI", 9, "bold"), bg=BG_USER_BUBBLE, fg=ACCENT_BLUE)
        lbl_title.pack(anchor="w", pady=(0, 2))

        lbl_text = tk.Label(bubble, text=text, font=("Segoe UI", 11), bg=BG_USER_BUBBLE, fg="#ffffff", justify=tk.LEFT, wraplength=680)
        lbl_text.pack(anchor="w")
        self._scroll_to_bottom()

    def _add_agent_container(self) -> tk.Frame:
        row = tk.Frame(self.messages_frame, bg=BG_MAIN)
        row.pack(fill=tk.X, pady=6, padx=4)

        container = tk.Frame(row, bg=BG_CARD, padx=14, pady=12, highlightbackground=BORDER_COLOR, highlightthickness=1)
        container.pack(fill=tk.X, expand=True)

        lbl_title = tk.Label(
            container,
            text=f"🤖 Агент Beyim ({config.GEMINI_MODEL})",
            font=("Segoe UI", 10, "bold"),
            bg=BG_CARD,
            fg=ACCENT_GREEN
        )
        lbl_title.pack(anchor="w", pady=(0, 6))

        self.current_agent_box = container
        self._scroll_to_bottom()
        return container

    def _add_step_card(self, step_data: Dict[str, Any]):
        if not self.current_agent_box or not self.current_agent_box.winfo_exists():
            self._add_agent_container()

        step_num = step_data.get("step", 1)
        action = step_data.get("action", "").lower()
        thought = step_data.get("thought", "")
        real_x = step_data.get("real_x")
        real_y = step_data.get("real_y")
        text = step_data.get("text")
        key = step_data.get("key")
        amount = step_data.get("amount")
        shot_path = step_data.get("screenshot_path")

        # Әрекетке байланысты белгі мен түс
        action_icons = {
            "click": ("🖱️ Клик", ACCENT_BLUE),
            "double_click": ("🖱️ Қос клик", ACCENT_BLUE),
            "right_click": ("🖱️ Оң жақ клик", ACCENT_BLUE),
            "type": ("⌨️ Мәтін енгізу", ACCENT_GREEN),
            "press": ("🔘 Батырма басу", ACCENT_PURPLE),
            "scroll": ("📜 Айналдыру", ACCENT_YELLOW),
            "listen": ("🎧 Дыбыс тыңдау", ACCENT_PURPLE),
            "wait": ("⏳ Күту", TEXT_MUTED),
            "done": ("✅ Аяқталды", ACCENT_GREEN),
            "fail": ("❌ Тоқтатылды", ACCENT_RED),
        }
        action_name, action_color = action_icons.get(action, (f"⚡ {action.upper()}", ACCENT_BLUE))

        card = tk.Frame(self.current_agent_box, bg=BG_INPUT, padx=12, pady=8, highlightbackground=BORDER_COLOR, highlightthickness=1)
        card.pack(fill=tk.X, pady=4)

        hdr_frame = tk.Frame(card, bg=BG_INPUT)
        hdr_frame.pack(fill=tk.X)

        badge_step = tk.Label(hdr_frame, text=f"Қадам #{step_num}", font=("Segoe UI", 9, "bold"), bg=BG_PANEL, fg=ACCENT_YELLOW, padx=6, pady=2)
        badge_step.pack(side=tk.LEFT, padx=(0, 6))

        badge_act = tk.Label(hdr_frame, text=action_name, font=("Segoe UI", 9, "bold"), bg=BG_PANEL, fg=action_color, padx=6, pady=2)
        badge_act.pack(side=tk.LEFT, padx=(0, 8))

        # Мәліметтер
        details = []
        if real_x is not None and real_y is not None:
            details.append(f"({real_x}, {real_y})")
        if text:
            details.append(f"«{text}»")
        if key:
            details.append(f"[{key}]")
        if amount is not None:
            details.append(f"scroll={amount}")

        if details:
            lbl_det = tk.Label(hdr_frame, text=" ".join(details), font=("Consolas", 9), bg=BG_INPUT, fg=TEXT_MAIN)
            lbl_det.pack(side=tk.LEFT)

        if shot_path and Path(shot_path).exists():
            btn_shot = tk.Button(
                hdr_frame,
                text="📷 Скриншот",
                font=("Segoe UI", 8),
                bg=BG_CARD,
                fg=ACCENT_BLUE,
                relief=tk.FLAT,
                command=lambda p=shot_path: os.startfile(p),
                cursor="hand2",
                padx=6,
                pady=1
            )
            btn_shot.pack(side=tk.RIGHT)

        if thought:
            lbl_thought = tk.Label(card, text=f"💡 Ой: {thought}", font=("Segoe UI", 9), bg=BG_INPUT, fg=TEXT_MUTED, justify=tk.LEFT, wraplength=720)
            lbl_thought.pack(anchor="w", pady=(4, 0))

        self._scroll_to_bottom()

    def _add_system_message(self, text: str, color: str = ACCENT_GREEN):
        card = tk.Frame(self.messages_frame, bg=BG_MAIN)
        card.pack(fill=tk.X, pady=4, padx=4)

        lbl = tk.Label(card, text=text, font=("Segoe UI", 10, "italic"), bg=BG_MAIN, fg=color)
        lbl.pack(anchor="center")
        self._scroll_to_bottom()

    def _add_result_message(self, success: bool, message: str):
        if not self.current_agent_box or not self.current_agent_box.winfo_exists():
            self._add_agent_container()

        color = ACCENT_GREEN if success else ACCENT_RED
        icon = "✅" if success else "❌"

        res_frame = tk.Frame(self.current_agent_box, bg=BG_INPUT, padx=12, pady=10, highlightbackground=color, highlightthickness=1)
        res_frame.pack(fill=tk.X, pady=(6, 0))

        lbl = tk.Label(
            res_frame,
            text=f"{icon} {message}",
            font=("Segoe UI", 11, "bold"),
            bg=BG_INPUT,
            fg=color,
            justify=tk.LEFT,
            wraplength=720
        )
        lbl.pack(anchor="w")
        self._scroll_to_bottom()

    def _record_voice_prompt(self):
        if not config.GEMINI_API_KEY:
            self._open_settings_dialog()
            if not config.GEMINI_API_KEY:
                return

        self.btn_voice.config(text="🔴 Тыңдалуда (6с)...", state=tk.DISABLED, bg=ACCENT_RED)
        self.lbl_status.config(text="● Микрофон арқылы дауыс жазылуда (6 сек)...", fg=ACCENT_RED)
        self.update_idletasks()

        def _worker():
            try:
                rec = audio_capture.record_microphone(duration=6.0)
                if not rec:
                    self.queue.put({"type": "voice_result", "text": "", "error": "Микрофон дыбыс жазбады."})
                    return
                wav_bytes, _ = rec
                client = GeminiAgentClient(api_key=config.GEMINI_API_KEY, model_name=config.GEMINI_MODEL)
                transcribed = client.transcribe_audio(wav_bytes)
                self.queue.put({"type": "voice_result", "text": transcribed, "error": None})
            except Exception as e:
                self.queue.put({"type": "voice_result", "text": "", "error": str(e)})

        threading.Thread(target=_worker, daemon=True).start()

    def _send_task(self):
        if self.is_running:
            return

        if not config.GEMINI_API_KEY:
            self._open_settings_dialog()
            if not config.GEMINI_API_KEY:
                return

        goal = self.text_input.get("1.0", tk.END).strip()
        if not goal:
            messagebox.showinfo("Тапсырма енгізу", "Өтініш, агентке тапсырма мәтінін жазыңыз.", parent=self)
            return

        self.text_input.delete("1.0", tk.END)
        self._add_user_message(goal)
        self._add_agent_container()

        self.is_running = True
        self.btn_send.config(state=tk.DISABLED)
        self.btn_stop.config(state=tk.NORMAL)
        self.btn_voice.config(state=tk.DISABLED)
        self.lbl_status.config(text="● Агент дайындалуда... Басталуда", fg=ACCENT_YELLOW)

        self.agent_thread = threading.Thread(target=self._run_agent_thread, args=(goal,), daemon=True)
        self.agent_thread.start()

    def _run_agent_thread(self, goal: str):
        try:
            for i in range(3, 0, -1):
                self.queue.put({"type": "status", "text": f"Агент {i} секундтан кейін бастайды..."})
                time.sleep(1)

            if self.minimize_var.get():
                self.queue.put({"type": "minimize"})
                time.sleep(0.5)

            ai_client = GeminiAgentClient(
                api_key=config.GEMINI_API_KEY,
                model_name=config.GEMINI_MODEL
            )

            agent = BrowserAgent(
                ai_client=ai_client,
                target_hwnd=None,
                confirm_actions=False,
                step_delay=config.STEP_DELAY,
                max_steps=config.MAX_STEPS,
                save_screenshots=config.SAVE_SCREENSHOTS,
                on_step=lambda data: self.queue.put({"type": "step", "data": data}),
                on_status=lambda txt: self.queue.put({"type": "status", "text": txt}),
                on_finish=lambda ok, msg: self.queue.put({"type": "finish", "success": ok, "message": msg})
            )
            self.current_agent = agent
            agent.run(goal)

        except Exception as e:
            self.queue.put({"type": "finish", "success": False, "message": f"Агент қатесі: {e}"})

    def _stop_task(self):
        if self.current_agent:
            self.current_agent.stop()
        self.lbl_status.config(text="● Тоқтату сұралды...", fg=ACCENT_RED)

    def _restore_window(self):
        try:
            self.deiconify()
            self.lift()
            self.focus_force()
        except Exception:
            pass

    def _process_queue(self):
        try:
            while True:
                msg = self.queue.get_nowait()
                mtype = msg.get("type")

                if mtype == "status":
                    txt = msg.get("text", "")
                    self.lbl_status.config(text=f"● {txt}", fg=ACCENT_BLUE)

                elif mtype == "minimize":
                    try:
                        self.iconify()
                    except Exception:
                        pass

                elif mtype == "step":
                    data = msg.get("data", {})
                    self._add_step_card(data)

                elif mtype == "voice_result":
                    self.btn_voice.config(text="🎤 Дауыс", state=tk.NORMAL, bg=BG_INPUT)
                    err = msg.get("error")
                    txt = msg.get("text", "")
                    if err:
                        messagebox.showwarning("Дауыспен енгізу", f"Дауысты тану қатесі: {err}", parent=self)
                    elif txt:
                        self.text_input.insert(tk.END, txt)
                        self.lbl_status.config(text="● Дауыс танылды!", fg=ACCENT_GREEN)
                    else:
                        self.lbl_status.config(text="● Сөз анықталмады.", fg=TEXT_MUTED)

                elif mtype == "finish":
                    success = msg.get("success", False)
                    res_msg = msg.get("message", "")
                    self._restore_window()
                    self._add_result_message(success, res_msg)

                    self.is_running = False
                    self.btn_send.config(state=tk.NORMAL)
                    self.btn_stop.config(state=tk.DISABLED)
                    self.btn_voice.config(state=tk.NORMAL)
                    status_text = "🟢 Тапсырма аяқталды" if success else "🔴 Тоқтатылды немесе Қате"
                    self.lbl_status.config(text=status_text, fg=ACCENT_GREEN if success else ACCENT_RED)

        except queue.Empty:
            pass

        self.after(50, self._process_queue)


def main():
    app = ChatApp()
    app.mainloop()

if __name__ == "__main__":
    main()
