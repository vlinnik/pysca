import typer
import os
import sys
from pathlib import Path
from typing import List,Optional,Any,Dict
from pysca.config import config,init_env,update_config

app = typer.Typer(name='paths',help='Настройка путей и расположения управляющих файлов проекта',no_args_is_help=True)

@app.command( help='Настройка путей и расположения управляющих файлов проекта' )
def set(ctx: typer.Context, 
        modules: List[Path] = typer.Option(None,help='Пути поиска python модулей'),
        plugins: List[Path] = typer.Option(None,help='Пути поиска pyqt-designer расширений'),
        workspace: Optional[Path] = typer.Option(None,help='Расположение проекта'),
        forms: Optional[Path] = typer.Option(None,help='Расположение форм приложения'),
        widgets: Optional[Path] = typer.Option(None,help='Расположение элементов окон'),
        simulator: Optional[Path] = typer.Option(None,help='Расположение проекта(ов) логики для запуска в режиме имитации'),
        resources: List[Path] = typer.Option(None,help='Расположение ресурсов проекта'),
        workdir: Path = typer.Option(envvar='PYSCAWORKDIR',help='Где расположен конфигурационный файл проекта'),
        ):
    vars: Dict[str,Any] = { }
    if modules: vars['modules'] = list([str(p) for p in modules])
    if plugins: vars['plugins'] = list([str(p) for p in plugins])
    if resources: vars['resources'] = list([str(p) for p in resources])
    if workspace: vars['workspace'] = str(workspace)
    if simulator: vars['logics'] = str(simulator)
    if forms: vars['forms'] = str(forms)
    if widgets: vars['widgets'] = str(widgets)
    update_config(workdir,{'paths':vars } )

@app.command( help='Получить настройки путей проекта')
def query(
    ctx:typer.Context,
    workdir: Path = typer.Option(envvar='PYSCAWORKDIR',help='Где расположен конфигурационный файл проекта'),
    modules: bool = typer.Option(False,help='Пути поиска модулей'),
    plugins: bool = typer.Option(False,help='Пути поиска *plugin.py файлов (PYQTDESIGNERPATH)'),
    workspace: bool = typer.Option(False,help='Расположение проекта'),
    forms: bool = typer.Option(False,help='Расположение экранных форм'),
    widgets: bool = typer.Option(False,help='Расположение пользовательских виджетов'),
    resources: bool = typer.Option(None,help='Расположение ресурсов проекта'),
    raw: bool = typer.Option(False,help='Списком без дополнений')
    ):
    init_env(workdir)
    def output(what: List[Any],as_list: bool = False):
        if as_list:
            for p in what:
                typer.echo(str(p))
        else:
            typer.echo(os.pathsep.join([str(p) for p in what]))
        
    if modules:
        if raw: output(config().modules,True)
        else: output(config().modules + sys.path)
    if plugins:
        if raw: output(config().plugins,True)
        else: typer.echo(os.environ.get('PYQTDESIGNERPATH'))
    if forms: typer.echo(str(config().ui))
    if widgets: typer.echo(str(config().widgets))
    if workspace: typer.echo(config().workspace)
    if resources: output(config().resources,True)