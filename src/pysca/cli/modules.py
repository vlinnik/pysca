import typer
import importlib
from pathlib import Path
from typing import List,Optional
from pysca import log
from pysca.cli import message
from pysca.cli.core.modules import modules as core_modules

app = typer.Typer(help='Динамическая загрузка пользовательских/системных модулей ')

@app.command( help='Загрузка пользовательского/системного модуля. Доступен в скриптах как <alias>' )
def module(ctx: typer.Context, 
        name: str = typer.Option(...,help='Модуль для загрузки.  Вызывает 1) createInstance 2) on_load (если они есть).'),
        alias: str = typer.Option(None,help='Результат createInstance или сам модуль доступен в скриптах по имени <alias>. Не указано - тогда <name>'),
        args: Optional[List[str]] = typer.Option(None,help='Параметры для вызова createInstance в формате <arg>=<value>')
        ):
    params = { }
    if args:
        for arg in args:
            key,val = arg.split("=",1)
            params[key] = val
    # Импортируем модуль по имени
    mod,instance = core_modules(name=name,args=params)
    ctx.obj['modules'].append(mod)
    ctx.obj['globals'].update( { alias or name: instance or mod} )
