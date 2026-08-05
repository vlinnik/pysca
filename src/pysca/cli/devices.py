import typer
from typing import List,Dict,Any
from pathlib import Path
from pysca.cli import args_parse
from pysca.config import init_env,update_config
from pysca.cli.core.devices import device as core_device

app = typer.Typer(name='devices',help='Настройка устройств ввода-вывода',no_args_is_help=True)

@app.command(help='Настройка устройства ввода-вывода')
def add( 
    ctx: typer.Context, 
    name: str = typer.Argument(...,help='Имя устройства') ,
    type: str = typer.Option(...,help='Драйвер устройства'),
    test: bool = typer.Option(False,help='Попробовать загрузить'), 
    args: List[str] = typer.Option(None,'--arg','--args',help='Параметры устройства в виде param=value'),
    workdir: Path = typer.Option(envvar='PYSCAWORKDIR',help='Где расположен конфигурационный файл проекта'),
):
    init_env(workdir)
    _args = args_parse(args)
    
    desc:Dict[str,Any] = { 'name':name,'type':type }
    if _args: desc.update({'args':_args})
    
    if test and core_device(name,type,_args or {} ) is None: return typer.Exit(1) 
    update_config(workdir,{'devices' : [ desc ]})
