import os
import typer
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List,Type,Dict,Optional,Any,TYPE_CHECKING
from pysca.config import init_env,update_config,config
from pysca.cli import args_parse
from pysca.cli.core.wm import navbar as core_navbar, window as core_window, view as core_view

if TYPE_CHECKING:
    from qtpy.QtWidgets import QWidget

app = typer.Typer(name='window',help='Настройка окон и шаблонов окон',chain=True,no_args_is_help=True)

@app.command( help='Настройка/создание окна или шаблона по ui файлу' )
def add(
    ui: Path = typer.Argument(..., resolve_path=True,help="ui-Файл с разметкой окна"),
    name: str = typer.Option(...,help='Имя окна/класса'),
    title: str = typer.Option(None,help='Заголовок окна'),
    module: Optional[str] = typer.Option(None, help="Python-модуль с реализациями класса для окна"),
    show: bool = typer.Option(False, help="Показать окно сразу после создания"),
    template: bool = typer.Option(False, help="Создать шаблон окна без создания экземпляра"),
    workdir: Path = typer.Option(envvar='PYSCAWORKDIR',help='Где расположен конфигурационный файл проекта'),
):
    conf = init_env(workdir)
    
    desc:Dict[str,Any] = { 'name':name,'ui': os.path.relpath(ui,config().ui),'show':show}
    if title: desc.update({'title':title})
    if module: desc.update({'module':module})
    if template: desc.update({'template':template})
    
    # if show and not template:
    #     core_window(ui=ui,name=name,title=title,module=module,show=show,template=template)   
    update_config(workdir,{'windows' : [ desc ]})

@app.command( help='Настройка окна по имени класса')
def view(
    template: str = typer.Argument(..., resolve_path=True,help="Родительский класс окна"),
    name: Optional[str] = typer.Option(None,help='Имя окна/класса'),
    title: Optional[str] = typer.Option(None,help='Заголовок окна'),
    parent: Optional[str] = typer.Option(None,help='Родительское окно'),
    show: bool = typer.Option(False, help="Показать окно сразу после создания"),
    args: Optional[ List[str] ] = typer.Option(None,"--args","--arg",help='Параметры окна в формате <property>=<value>'),
    workdir: Path = typer.Option(envvar='PYSCAWORKDIR',help='Где расположен конфигурационный файл проекта'),
):
    init_env(workdir)
    
    desc:Dict[str,Any] = { 'name':name,'template': template,'show':show }
    if title: desc.update({'title':title})
    if parent: desc.update({'parent': parent})
    params = args_parse(args)
    if params: desc.update({'args':params})
    update_config(workdir,{'views':[desc]})

@app.command( help='Главное окно с панелью навигации и рабочим пространством' )
def navbar(
    pages: List[str] = typer.Argument(..., resolve_path=True,help="ui-Файлы для размещения на основном рабочем пространстве" ),
    title: str = typer.Option(None,help='Заголовок окна'),
    tools: List[str] = typer.Option(None, help="Окна/View для размещения на панели инструментов"),
    workdir: Path = typer.Option(envvar='PYSCAWORKDIR',help='Где расположен конфигурационный файл проекта'),
):
    init_env(workdir)
    
    desc:Dict[str,Any] = { 'title':title,'pages':pages } if title else {'pages':pages}
    if tools: desc.update({'tools': tools})
    update_config(workdir,{'navbar':desc})
