import typer
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List,Type,Dict,Optional,Any,TYPE_CHECKING
from pysca.cli.core.wm import navbar as core_navbar, window as core_window, view as core_view

import csv  

if TYPE_CHECKING:
    from qtpy.QtWidgets import QWidget

app = typer.Typer()

def __args_parse(raw: str)->Dict[str,Any]:
    reader = csv.reader([raw]) 
    items = next(reader) 
    result = {} 
    for item in items: 
        key, value = item.split("=", 1) 
        result[key] = value 
    return result    

@app.command( help='Настройка/создание окна по ui файлу' )
def window(
        name: str = typer.Option(...,help='Имя окна/класса'),
        title: str = typer.Option(None,help='Заголовок окна'),
        module: Optional[str] = typer.Option(None, help="Python-модуль с реализациями класса для окна"),
        ui: Path = typer.Argument(..., resolve_path=True,help="ui-Файл с разметкой окна"),
        show: bool = typer.Option(False, help="Показать окно сразу после создания"),
        template: bool = typer.Option(False, help="Создать шаблон окна без создания экземпляра"),
        ):

    return core_window(ui=ui,name=name,title=title,module=module,show=show,template=template)

@app.command( help='Создание окона по имени класса')
def view(
        name: Optional[str] = typer.Option(None,help='Имя окна/класса'),
        title: Optional[str] = typer.Option(None,help='Заголовок окна'),
        parent: Optional[str] = typer.Option(None,help='Родительское окно'),
        show: bool = typer.Option(True, help="Показать окно сразу после создания"),
        data: str = typer.Option(None,help='Url для открытия если cls==browser'),
        args: Optional[ List[str] ] = typer.Option(None,"--args","--arg",help='Параметры окна в формате <property>=<value>'),
        cls: str = typer.Argument(..., resolve_path=True,help="Родительский класс окна"),
        ):
    params = { }
    if args:
        for arg in args:
            params.update( __args_parse(arg) )
            
    return core_view(cls=cls,name=name,title=title,show=show,parent=parent,data=data,**params)

@app.command( help='Главное окно с панелью навигации и рабочим пространством' )
def navbar(ctx:typer.Context,
        title: str = typer.Option(None,help='Заголовок окна'),
        pages: List[Path] = typer.Option(None, resolve_path=True,help="ui-Файлы для размещения на основном рабочем пространстве" ),
        tools: List[Path] = typer.Option(None, help="ui-Файлы для размещения на панели инструментов"),
        modules: List[str]= typer.Option(None, help="Python-модули с реализациями классов для ui-окон")
        ):
    
    return core_navbar(title=title,pages=pages,tools=tools,modules=modules,dry=ctx.obj.get('dry',False))
