import typer
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List,Type,Optional,TYPE_CHECKING
from pysca.cli.core.wm import navbar as core_navbar, window as core_window

if TYPE_CHECKING:
    from qtpy.QtWidgets import QWidget

app = typer.Typer()

@app.command( help='Настройка/создание окна' )
def window(ctx:typer.Context,
        name: str = typer.Option(...,help='Имя окна/класса'),
        title: str = typer.Option(None,help='Заголовок окна'),
        module: Optional[str] = typer.Option(None, help="Python-модуль с реализациями класса для окна"),
        ui: Path = typer.Argument(..., resolve_path=True,help="ui-Файл с разметкой окна"),
        show: bool = typer.Option(False, help="Показать окно сразу после создания"),
        template: bool = typer.Option(False, help="Создать шаблон окна без создания экземпляра"),
        ):

    return core_window(ui=ui,name=name,title=title,module=module,show=show,template=template)

@app.command( help='Главное окно с панелью навигации и рабочим пространством' )
def navbar(ctx:typer.Context,
        title: str = typer.Option(None,help='Заголовок окна'),
        pages: List[Path] = typer.Option(None, resolve_path=True,help="ui-Файлы для размещения на основном рабочем пространстве" ),
        tools: List[Path] = typer.Option(None, help="ui-Файлы для размещения на панели инструментов"),
        modules: List[str]= typer.Option(None, help="Python-модули с реализациями классов для ui-окон")
        ):
    
    return core_navbar(title=title,pages=pages,tools=tools,modules=modules,dry=ctx.obj.get('dry',False))
