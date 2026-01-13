from typing import Optional
from .types import Config
import inspect

_config: Optional[Config] = None
_config_origin: Optional[str] = None

def init_config(cfg: Config):
    global _config, _config_origin
    if _config is not None:
        raise RuntimeError(f"Уже инициализировано из {_config_origin}")
    _config = cfg

    # Получаем место вызова init_config()
    frame = inspect.stack()[1]
    caller_file = frame.filename
    caller_line = frame.lineno
    caller_func = frame.function

    _config_origin = f"{caller_file}:{caller_line} в {caller_func}()"


def config() -> Config:
    if _config is None:
        raise RuntimeError("Сначала  необходимо инициализировать настройки")
    return _config
