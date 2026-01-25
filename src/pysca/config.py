import inspect
import sys
import os
import yaml
from typing import Optional,Dict,Any
from pathlib import Path
from pysca.types import Config

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

def __merge_config(base: dict, new: dict):
    if base is None: return new
    for key, value in new.items():
        if (
            key in base
            and isinstance(base.get(key), dict)
            and isinstance(value, dict)
        ):
            __merge_config(base.get(key), value)
        elif (
            key in base 
            and isinstance(base.get(key),list)
            and isinstance(value,list)
        ):
            base[key]+= value
        else:
            base[key] = value

def update_config( workdir: Path, settings: dict ):
    from ruamel.yaml import YAML
    yaml = YAML()
    yaml.preserve_quotes = True
    cfg = workdir.joinpath(Path('settings.yaml')).resolve()
    before = None
    if Path(cfg).exists():
        with open(cfg,'r') as file:
            before = yaml.load(file)
        __merge_config(before,settings)
                        
    with open(cfg,'w+') as file:
        yaml.dump(before or settings,file)

def __load_config(workdir: Path)->Dict[str,Any]:
    try:
        config()
        return {}
    except:
        pass
    
    cfg = Path(workdir).joinpath('settings.yaml').resolve()
    if Path(cfg).exists():
        with open(cfg,'r') as file:
            conf = yaml.safe_load(file)
        main = conf.get('main',{})
        paths = conf.get('paths',{})
        init_config(
            Config(
                workdir=workdir,
                workspace=paths.get('workspace',os.path.relpath(workdir,Path('.'))),
                ui=paths.get('forms','ui'),
                widgets=paths.get('widgets','widgets'),
                modules=paths.get('modules',['.']),
                plugins=paths.get('plugins',['.']),
                resources=paths.get('resources',['.']),
                db=main.get('config','default.scada'),
                logics=Path('.')
                ))
    else:
        init_config(Config())
    return conf

def init_env(workdir: Path)->Dict[str,Any]:
    conf = __load_config(workdir)
    sys.path = list(dict.fromkeys([str(workdir.joinpath(m).resolve()) for m in config().modules] + sys.path )) #list(set([ str(Path(p).resolve()) for p in modules] + sys.path))
    from site import USER_SITE
    # all = list([str(p) for p in config().plugins ]) + list([p for p in sys.path if 'dist-packages' in p or 'site-packages' in p ])
    all = list([str(p) for p in config().plugins ]) + list([p for p in sys.path ])
    if USER_SITE: all.append(USER_SITE)
    all = set([str(s) for s in all])        
    os.environ['PYQTDESIGNERPATH'] = os.pathsep.join([str(p) for p in all])
    os.environ['PYSCAWORKSPACE'] = str(config().workspace)
    os.environ['PYSCAWIDGETSPATH'] = str(config().widgets)
    return conf
