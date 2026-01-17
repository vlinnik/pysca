import importlib
import xml.etree.ElementTree as ET
import sys
from pathlib import Path
from types import ModuleType
from typing import List,Type,Optional,Dict,Any, TYPE_CHECKING
from pysca import log
from pysca.config import config

if TYPE_CHECKING:
    from qtpy.QtWidgets import QWidget

qApp = None
_wins: Dict[str,'QWidget']  = { }   #

def __prepare_qt():
    global qApp
    from qtpy.QtCore import Qt
    from qtpy.QtWidgets import QApplication
    from pysca import pysca_rcc
    
    QApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)
    
    if not QApplication.instance():
        qApp = QApplication(sys.argv)
        
    pysca_rcc( )


def resolve_class(ui_path:str,mods:List[ModuleType]):
    if len(mods)>0:
        tree = ET.parse(ui_path)
        root = tree.getroot()
        class_tag = root.find('class')
        class_name = class_tag.text if class_tag is not None else None
        cls = None
        if class_name:
            for m in mods:
                if hasattr(m,class_name):
                    cls = getattr(m,class_name)
                    break
        return cls
    return None    

def load_modules(modules):
    mods = []
    if len(modules)>0:
        for m in modules:
            try:
                mod = importlib.import_module(m)
                mods.append(mod)
            except ImportError as e:
                log.error(f'Модуль {m} не удалось загрузить: {e}')
    try:
        config().imported+=mods
    except:
        pass
    return mods

def load_windows(pages: List[Path],modules: List[ModuleType],globs: Dict[str,Any] = {} )->List['QWidget']:
    from pysca import app as _app
    wins = []
            
    for p in pages:
        ui_path = config().ui.joinpath(p)
        # manager.watch(p)
        cls = resolve_class(str(ui_path),modules)
        if cls is not None:
            w = _app.window(str(ui_path),baseinstance=cls(),ctx=globs )
        else:
            w = _app.window(str(ui_path),ctx=globs)
        if not w:
            continue
        _app.context().update( { w.objectName():w} )
        wins.append(w)
    return wins
        
def navbar(*args,
        name: Optional[str] = None,
        title: Optional[str] = None,
        pages: Optional[List[str]] = None ,
        tools: Optional[List[str]] = None,
        modules: Optional[List[str]] = None,
        dry: bool = False,
        **kwargs
        ):
    global _wins
    __prepare_qt( )
        
    import pysca.navbar as navbar
    for w in pages or []:
        if w in _wins:
            navbar.append(_wins[w])
    for w in tools or []:
        if w in _wins:
            navbar.tools(_wins[w])                    
    if title:
        navbar.instance.setWindowTitle(title)
    if not dry: navbar.instance.show()
    return navbar.instance

def window(*args,
        ui: Path,
        name: str,
        title: Optional[str] = None,
        module: Optional[str] = None,
        show: bool = False,
        template: bool = False,
        **kwargs
        ):
    global _wins
    __prepare_qt( )
        
    mods = load_modules([module]) if module else [] 
    if not template:
        wins = load_windows([ui],modules=mods)
        if not wins or not wins[0]:
            return None
        win = wins[0]

        setup = getattr(win, "setupUi", None) 
        try:
            if callable(setup): setup()
        except Exception as e:
            log.error(f'Ошибка инициализации окна {name}.setupUi(): {e}')                                         
        
        if title:
            win.setWindowTitle(title)
            
        if show:
            win.show( )
        _wins[name] = win
        return win
    else:
        log.warning('Создание шаблона окна пока не реализовано')
    return None
    
