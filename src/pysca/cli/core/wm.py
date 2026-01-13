import importlib
import xml.etree.ElementTree as ET
import sys
from pathlib import Path
from typing import List,Type,Optional,Dict,Any, TYPE_CHECKING
from pysca import log

if TYPE_CHECKING:
    from qtpy.QtWidgets import QWidget

qApp = None

def __prepare_qt():
    global qApp
    from qtpy.QtCore import Qt
    from qtpy.QtWidgets import QApplication
    from pysca import pysca_rcc
    
    QApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)
    
    if not QApplication.instance():
        qApp = QApplication(sys.argv)
        
    pysca_rcc( )


def resolve_class(ui_path:str,mods:List[Type]):
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
    return mods

def load_windows(pages,modules,globs: Dict[str,Any] = {} )->List['QWidget']:
    from pysca import app as _app
    wins = []
            
    for p in pages:
        # manager.watch(p)
        cls = resolve_class(p,modules)
        if cls is not None:
            w = _app.window(p,baseinstance=cls(),ctx=globs )
        else:
            w = _app.window(p,ctx=globs)
        if not w:
            continue
        _app.context().update( { w.objectName():w} )
        wins.append(w)
    return wins
        
def navbar(*args,
        title: Optional[str] = None,
        pages: Optional[List[Path]] = None ,
        tools: Optional[List[Path]] = None,
        modules: Optional[List[str]] = None,
        dry: bool = False,
        **kwargs
        ):
    
    __prepare_qt( )
        
    import pysca.navbar as navbar
    mods = load_modules(modules) if modules else [] 
    wins = load_windows(pages,mods) if pages else []
    for w in wins:
        navbar.append(w)
    wins = load_windows(tools,mods) if tools else []
    for w in wins:
        navbar.tools(w)
    if title:
        navbar.instance.setWindowTitle(title)
    if not dry: navbar.instance.show()
    return navbar.instance
