import os
import sys
from pathlib import Path
from typing import Optional,List
from pysca.config import config

def _paths( 
        *args,
        modules: Optional[List[Path]] = None,
        plugins: Optional[List[Path]] = None,
        workspace: Optional[Path] = None,
        resources: Optional[List[Path]] = None,
        forms: Optional[Path] = None,
        widgets: Optional[Path] = None,
        simulator: Optional[Path] = None,
        **kwargs
        ):

    if modules:
        sys.path = list(dict.fromkeys([str(Path(m).resolve()) for m in modules] + sys.path )) #list(set([ str(Path(p).resolve()) for p in modules] + sys.path))
        config().modules = [Path(p).resolve() for p in sys.path]
        
    if plugins:
        from site import USER_SITE
        all = list([ Path(p).resolve() for p in plugins]) + list([p for p in sys.path if 'dist-packages' in p or 'site-packages' in p ]) 
        if USER_SITE: all.append(USER_SITE)
        all = set([str(s) for s in all])
        config().plugins = [Path(p) for p in all]
        
    os.environ['PYQTDESIGNERPATH'] = os.pathsep.join([str(p) for p in config().plugins])
        
    if resources:
        config().resources = [Path(p).resolve() for p in resources]
        
    if workspace:
        config().workspace = Path(workspace).resolve()
    os.environ['PYSCAWORKSPACE'] = str(config().workspace)
        
    if forms:
        config().ui = Path(forms).resolve()
    
    if widgets:
        config().widgets = Path(widgets).resolve()
    os.environ['PYSCAWIDGETSPATH'] = str(config().widgets)
        
    if simulator:
        config().logics = config().workspace.joinpath(simulator).resolve()
        