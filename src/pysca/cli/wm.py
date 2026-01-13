import typer
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List,Type,TYPE_CHECKING
from pysca.cli.core.wm import navbar as core_navbar

if TYPE_CHECKING:
    from qtpy.QtWidgets import QWidget

app = typer.Typer()
        
@app.command( help='Главное окно с панелью навигации и рабочим пространством' )
def navbar(ctx:typer.Context,
        title: str = typer.Option(None,help='Заголовок окна'),
        pages: List[Path] = typer.Option(None, help="ui-Файлы для размещения на основном рабочем пространстве" ),
        tools: List[Path] = typer.Option(None, help="ui-Файлы для размещения на панели инструментов"),
        modules: List[str]= typer.Option(None, help="Python-модули с реализациями классов для ui-окон")
        ):
    
    return core_navbar(title=title,pages=pages,tools=tools,modules=modules,dry=ctx.obj.get('dry',False))
