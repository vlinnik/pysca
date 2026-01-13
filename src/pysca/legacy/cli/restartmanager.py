import os
import threading
import sys

# Зависимости: pip install watchdog pystray Pillow
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from pystray import Icon, Menu, MenuItem
from PIL import Image, ImageDraw, ImageFont
from typing import Callable,Optional

class FileChangeHandler(FileSystemEventHandler):
    """
    Обработчик событий watchdog для отслеживания изменений файлов.
    При изменении файла вызывает создание иконки в системном трее.
    """
    def __init__(self, tray_manager):
        self.tray_manager = tray_manager

    def on_modified(self, event):
        # Игнорируем директории, только файлы
        if not event.is_directory:
            self.tray_manager.create_tray()

class FileWatcherTray:
    """
    Основной класс для мониторинга файлов и создания иконки в systray при изменениях.
    Совместим с Windows и Linux (требует установки watchdog, pystray, Pillow).
    
    Имеет свойство quit(функция), которую вызывает при завершении
    
    Пример использования:
        watcher = FileWatcherTray(qApp.quit)
        watcher.watch(["/path/to/file1.py", "/path/to/file2.txt"])
        watcher.start()
    """
    def __init__(self,quit:Optional[Callable[[],None]]=None):
        self.observer = Observer()
        self.handler = FileChangeHandler(self)
        self.watching_paths = set()
        self.icon = None
        self.created = False
        self.thread = None
        self.quit:Optional[Callable[[],None]] = quit
        self.cmd = sys.argv
        
    def run(self):
        while True:
            self.icon.run( )
            os.execv( self.cmd[0],self.cmd[0:])
            break
                
        self.quit()
        self.stop( )
        

    def create_tray(self):
        if self.created:
            return

        # Создаем простую иконку с помощью PIL (красный круг с текстом "R" для Restart)
        image = Image.new('RGB', (64, 64), color='red')
        draw = ImageDraw.Draw(image)
        font = ImageFont.load_default(40)
        draw.text((20, 10), "R", fill="white", font=font)

        def on_restart(icon, item):
            """Функция перезапуска: запускает текущий скрипт заново и выходит."""
            # Запуск текущей программы в новом процессе
            # subprocess.Popen([sys.executable, __file__] + sys.argv[1:])
            # Выход из текущего процесса
            icon.stop()

        # Меню для иконки: только опция "Restart"
        menu = Menu(
            MenuItem("Restart", on_restart)
        )

        # Создаем иконку
        self.icon = Icon(
            "FileWatcher Restart",
            image,
            menu=menu
        )

        # Запускаем иконку в отдельном потоке, чтобы не блокировать основной
        self.thread = threading.Thread(target=self.run, daemon=True)
        self.thread.start()

        self.created = True
        
    def start(self):
        # Запускаем observer в фоне
        # Запускаем мониторинг для каждой директории
        for path in self.watching_paths:
            self.observer.schedule(self.handler, path, recursive=False)
        self.observer.start()

    def watch(self, file_path: str):
        """
        Устанавливает список файлов для мониторинга.
        Мониторит директории, содержащие эти файлы (не рекурсивно).
        При изменении любого файла создается иконка в systray.
        
        Args:
            files: Файл
        """
        # Собираем уникальные директории для мониторинга
        if os.path.isfile(file_path):
            if os.path.islink(file_path):
                file_path = os.path.realpath(file_path)
            dir_path = os.path.dirname(os.path.abspath(file_path))
            if dir_path and dir_path not in self.watching_paths:
                self.watching_paths.add(dir_path)
        else:
            print(f"Warning: {file_path} is not a file, skipping.")

    def stop(self):
        """Останавливает мониторинг и systray."""
        if self.observer.is_alive:
            self.observer.stop()
            self.observer.join(timeout=1.0)
        self.watching_paths.clear()
