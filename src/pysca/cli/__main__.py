import typer
import os
import yaml
import sys
import importlib.util 
from pathlib import Path
from types import FunctionType
from typing import List,Optional,Dict,Any,TypeVar,Callable,cast
from pysca import log,app as _app
from pysca.cli import message
from pysca.cli.wm import app as wm
from pysca.cli.paths import app as paths
from pysca.cli.devices import app as devices
from pysca.cli.modules import app as modules
from pysca.cli.core.generic import main as core_main
from pysca.config import config

app = typer.Typer(chain=True)
app.add_typer(devices)
app.add_typer(wm)
app.add_typer(paths)
app.add_typer(modules)

_g_ctx = None

def teardown(result,*args,dry:bool=False,asyncio:bool = False, query: Optional[str] = None, **kwargs):
    global _g_ctx
    if _g_ctx is None or dry or query is not None:
        return
    
    from qtpy.QtWidgets import QApplication
    if QApplication.instance():
        _app.start( _g_ctx.obj.get('globals'),use_asyncio=asyncio )
    
    if simulator:
        from pysca.cli.core.simulator import close as stop_simulator
        stop_simulator( )
    
@app.callback(invoke_without_command=True,no_args_is_help=True,result_callback=teardown)
def main(
    ctx: typer.Context,
    version: bool = typer.Option(False,'--version',help='Показать версию'),
    workdir: Path = typer.Option(None,'-w','--workdir',dir_okay=True,resolve_path=True,help='Рабочий каталог проекта'),
    conf: Path = typer.Option(None,'--conf',resolve_path=True,help='База анимаций, переменных'),
    simulator: bool = typer.Option(False,help='Запуск в режиме имитации'),
    dry: bool = typer.Option(False,is_flag=True,help='Не запускать визуализацию (QApplication)'),
    stdout: Optional[str] = typer.Option(None,'--stdout',help='Уровень вывода отладочной информации на stdout'),
    stderr: Optional[str] = typer.Option(None,'--stderr',help='Уровень вывода отладочной информации на stderr'),
    settings:Optional[Path] = typer.Option(None,resolve_path=True,help='Расположение файла с настройками'),
    query: Optional[str] = typer.Option(None,'-q','--query',help='Выдать переменную/настройку и выйти'),
    asyncio: bool = typer.Option(None,'--asyncio',help='Запуск с использованием asyncio Qt')
):
    global _g_ctx
    _g_ctx = ctx
    ctx.ensure_object(dict)
    ctx.obj['modules'] = ctx.obj.get('modules',[ ])    # загруженные модули при помощи подкоманды module
    ctx.obj['globals'] = ctx.obj.get('globals',{ })    # все что доступно в сценариях 
    
    if version==True:
        from pysca.__version__ import version as _version
        print(_version)
        return typer.Exit(0)

    mods,syms = core_main(conf=conf,workdir=workdir,simulator=simulator,stdout=stdout,stderr=stderr,settings=settings,dry=dry or query is not None)
    
    ctx.obj['modules'] = mods
    ctx.obj['globals'].update(syms)

    if query is not None:
        match query:
            case 'conf': typer.echo( config().db )
            case 'workspace': typer.echo(config().workspace)
            case 'modules': typer.echo(os.pathsep.join([str(p) for p in config().modules]))
            case 'plugins': typer.echo(os.pathsep.join([str(p) for p in config().plugins]))
            case 'resources': 
                for p in config().resources: typer.echo(str(p))
            case 'forms': typer.echo(str(config().ui))
            case 'widgets': typer.echo(str(config().widgets))
            case 'simulator': typer.echo(str(config().logics))
            case _: typer.echo(f'Неизвестная переменная {query} запрошена')

    if not dry and not query:
        _app.ctx.update( syms )
        for m in mods:
            if hasattr(m,'on_start'):
                m.on_start( )
                
@app.command(help='Настройка параметров режима имитации')
def simulator():
    pass

@app.command(help='Запуск утилит (designer etc.)')
def tool(ctx: typer.Context, 
        designer: bool = typer.Option(False,help='Запустить Qt-Designer'),
        other: Optional[str] = typer.Option(None,help='Запустить что-то другое'),
        args: Optional[List[str]]=typer.Argument(None,help='Параметры запуска')
        ):
    import subprocess,sys
    from pysca.cli.core.paths import paths as core_paths
    core_paths( )   # defaults or from config
    os.environ.pop("PYSCARUNTIME",None) #загрузка пользовательских модулей не нужна    
    os.environ.pop("DIYED_PROJECT",None) #загрузка пользовательских модулей не нужна    
    if designer==True:
        subprocess.run(['designer']+(args or []))
    if isinstance(other,str):
        subprocess.run([other]+(args or []))
        
    
# @app.command(help='Загрузка параметров из конфигурационного файла YAML')
# def batch(
#     ctx: typer.Context, 
#     settings:Path = typer.Option('settings.yaml',resolve_path=True,help='Имя файла с настройками'),
#     env: bool = typer.Option(False,help='Загрузить только переменные окружения'),
#     ):
#     mods,syms = core_batch(settings=settings,only_paths=env) 
#     ctx.obj['modules']=mods
#     ctx.obj['globals'].update(syms)

def entry():
    app()
            
if __name__=='__main__':
    app( )