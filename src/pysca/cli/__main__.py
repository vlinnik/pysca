import typer
import os
from pathlib import Path
from pysca.cli.wm import app as wm
from pysca.cli.tools import app as tools
from pysca.cli.paths import app as paths
from pysca.cli.devices import app as devices
from pysca.cli.modules import app as modules
from pysca.cli.project import app as project

app = typer.Typer(help='Утилита для настройки/запуска pysca проекта')
app.add_typer(paths)
app.add_typer(tools)
app.add_typer(project)
app.add_typer(modules)
app.add_typer(devices)
app.add_typer(wm)
    
@app.callback(invoke_without_command=True,no_args_is_help=True)
def main(
    ctx: typer.Context,
    version: bool = typer.Option(False,'--version',help='Показать версию'),
    qtapi: str = typer.Option(None,help='Выбор используемой привязки pyqt5/6/pyside2/pyside6',envvar='QT_API'),
    workdir: Path = typer.Option(None,'-w','--workdir',dir_okay=True,resolve_path=True,help='Рабочий каталог проекта'),
):
    ctx.ensure_object(dict)
    
    if version==True:
        from pysca.__version__ import version as _version
        print(_version)
        return typer.Exit(0)

    if workdir:
        os.environ['PYSCAWORKDIR'] = str(workdir)
    
    if qtapi:
        os.environ['QT_API'] = qtapi
                    
def entry():
    app()
            
if __name__=='__main__':
    app( )