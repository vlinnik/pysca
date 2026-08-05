import importlib
import sys
from types import ModuleType
from typing import Dict,Any,Optional,Tuple
from pysca import log
from pysca.config import config

def modules(
        *_,
        name: str,
        args: Optional[Dict[str,Any]]=None,
        **kwargs
        )->Tuple[ModuleType,Any]:
    params = args or { }
    try:
        # Импортируем модуль по имени
        sys.path = list(set(sys.path + [str(p) for p in config().modules]))
        mod = importlib.import_module(name)
        if mod:
            log.debug(f"Загружен пользовательский модуль {name}")
        if hasattr(mod,'on_load'):
            mod.on_load()
        # Проверяем, есть ли функция initialize
        if hasattr(mod, 'createInstance') and callable(getattr(mod, 'createInstance')):
            instance = mod.createInstance(**params)
            return mod,instance
        else:
            return mod,None
    except ImportError:
        log.error(f"Ошибка: Модуль {name} не найден")
    except Exception as e:
        log.error(f"Ошибка при выполнении загрузки модуля {name}: {str(e)}")                
        
    return None,None