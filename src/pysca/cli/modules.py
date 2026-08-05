import typer
import csv  
from pathlib import Path
from typing import List,Optional,Dict,Any,Union
from pysca.cli import args_parse
from pysca.config import init_env,update_config
from pysca.cli.core.modules import modules as core_module

app = typer.Typer(name='modules',help='Настройка загрузки пользовательских/системных модулей',no_args_is_help=True)

@app.command( help='Загрузка пользовательского/системного модуля.' )
def add(
    workdir: Path = typer.Option(envvar='PYSCAWORKDIR',help='Где расположен конфигурационный файл проекта'),
    alias: str = typer.Option(None,help='Результат createInstance или сам модуль доступен в скриптах по имени <alias>. Не указано - тогда <name>'),
    args: Optional[List[str]] = typer.Option(None,help='Параметры для вызова createInstance в формате <arg>=<value>'),
    test: bool = typer.Option(False,help='Попробовать возможность загрузки'),
    name: str = typer.Argument(...,help='Модуль для загрузки.'),
):
    init_env(workdir)
    desc:Dict[str,Any] = { 'name':name }
    if alias: desc['alias'] = alias
    params = args_parse(args)
    if params:
        desc['args'] = params 
        
    if test:
        mod,_ = core_module(name=name,args=params)
        if not mod: return typer.Exit(1)
        
    settings = { 'modules': [ desc ]}
    update_config(workdir,settings)