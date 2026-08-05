from importlib import resources
from .app import App,log

app = App( )

def pysca_rcc():
    try:
        from qtpy.QtCore import QResource
        with resources.as_file(resources.files("pysca.data") / "pysca.rcc" ) as p:
            QResource.registerResource(str(p))
    except Exception as e:
        log.warning(f'Проблема при загрузке pysca-ресурсов {e}')
        pass
        
__all__=['app','log']
    