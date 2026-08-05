import typer
import os
from pathlib import Path
from typing import Optional,List
from pysca.config import init_env

app = typer.Typer(name='tool',help='Запуск утилит (designer etc.)',no_args_is_help=True)

@app.command(help='Запуск qt-designer')
def designer(ctx: typer.Context,
        workdir: Path = typer.Option(envvar='PYSCAWORKDIR'), 
        args: Optional[List[str]]=typer.Argument(None,help='Параметры запуска',allow_dash=True)
        ):
    import subprocess
    init_env( workdir )               # defaults or from config
    typer.echo(os.environ.get('PYSCAWIDGETSPATH'))
    os.environ.pop("PYSCARUNTIME",None) #загрузка пользовательских модулей не нужна    
    os.environ.pop("DIYED_PROJECT",None) #загрузка пользовательских модулей не нужна    
    subprocess.run(['designer']+(args or []))
