from importlib import resources
from qtpy.QtCore import QResource
from .app import App,log

app = App( )
__all__=['app','log']

try:
    with resources.as_file(resources.files("pysca.data") / "pysca.rcc" ) as p:
        QResource.registerResource(str(p))
except:
    pass