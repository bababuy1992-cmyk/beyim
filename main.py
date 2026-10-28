import sys
import os

# Инициализируем рабочую директорию
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import config
from gui_chat import ChatApp

def main():
    # Запуск графического интерфейса с чатом
    app = ChatApp()
    app.mainloop()

if __name__ == "__main__":
    main()
