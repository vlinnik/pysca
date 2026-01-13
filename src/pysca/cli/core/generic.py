import sys
import os
import yaml
from pysca import log
from pysca.config import config,init_config,Config
from pysca.cli.core.wm import navbar
from pysca.cli.core.devices import device as core_device
from typing import Optional,List,Any,Tuple,Dict
from pathlib import Path
from types import ModuleType

def main(
    conf: Optional[Path] = None,
    simulator: bool = False,
    workdir: Optional[Path]=None,
    stdout: Optional[str] = None,
    stderr: Optional[str] = None,
    settings:Optional[Path] = None,
    dry:bool = False, 
    override:bool=False, #используется для рекурсивного вызова из себя
    **kwargs
    )->Tuple[List[ModuleType],Dict[str,Any]]:
    if stdout or stderr:
        log.remove()
    if stdout:
        low, high = stdout.split(":",1) if ":" in stdout else (stdout, 'CRITICAL')
        low, high = log.level(low or 'DEBUG').no, log.level(high or 'CRITICAL').no
        log.add(sys.stdout,level=low, filter=lambda record,low=low,high=high:  
            (min(low,high) <= record["level"].no <= max(low,high))
            )
    if stderr:
        low, high = stderr.split(":",1) if ":" in stderr else (stderr, 'CRITICAL')
        low, high = log.level(low or 'DEBUG').no, log.level(high or 'CRITICAL').no
        log.add(sys.stderr,level=low,filter=lambda record,low=low,high=high:  
            (min(low,high) <= record["level"].no <= max(low,high))
            )

    if workdir:
        os.chdir(str(workdir))
            
    try:
        config()
    except Exception as e:
        init_config(Config())

    if simulator:
        pass
    
    if conf:
        config().db = Path(conf).resolve()
        
# def batch( *args, settings:Path ,only_paths:bool=False)->Tuple[List[ModuleType],Dict[str,Any]]:
    modules = []
    ctx = { }

    if override:    #только переопределение настроек
        return modules,ctx
    
    if settings:
        if not os.path.exists(settings):
            return modules,ctx
    else:
        settings = Path('settings.yaml').resolve( )
        
    with open(str(settings), 'r', encoding='utf-8') as f:
        params:dict = yaml.safe_load(f) or {}
    
    conf_main:dict = params.get('main',{})
    if conf_main:
        main(**conf_main,override=True)
        
    conf_path:dict = params.get('paths',{})
    if conf_path:
        from pysca.cli.core.paths import paths as core_paths
        core_paths(**conf_path)
        
    conf_mods:List[Any] = params.get('modules',[])
    if conf_mods and not dry:
        from pysca.cli.core.modules import modules as core_modules
        for params in conf_mods:
            mod,instance = core_modules(**params)
            if mod: modules.append(mod)
            if instance: ctx[params.get('alias',params['name'])] = instance

    conf_sim: List[dict] = params.get('simulator',[])            
    if conf_sim and not dry and simulator:
        from pysca.cli.core.simulator import simulator as core_simulator
        for s in conf_sim:
            core_simulator(**s)
        
    conf_dev: List[dict] = params.get("devices",[ ])
    if conf_dev and not dry:
        for d in conf_dev:
            core_device(**d,simulator=simulator)
            
    conf_nav:dict = params.get('navbar',{ })
    if conf_nav and not dry:
        navbar(**conf_nav)
        
    return modules,ctx
