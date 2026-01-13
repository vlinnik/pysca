import typer
from typing import List
from pysca.cli import message
from pysca.cli.core.devices import device as core_device

app = typer.Typer()

@app.command(help='Настройка устройства ввода-вывода')
def device( ctx: typer.Context, name: str = typer.Argument(...,help='Имя устройства') ,
        type: str = typer.Option(...,help='Драйвер устройства'), 
        args: List[str] = typer.Option(None,'--arg','--args',help='Параметры устройства в виде param=value')):

    _args = { }
    for x in args or []:
        key,value = x.split('=',1)
        _args[key]=value
        
    core_device(name,type,_args)    
