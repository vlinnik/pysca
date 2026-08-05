import click
from pysca import app
from typing import cast

def pyplc_device(*_,device,port=9004,scan=100,**kwargs):
    from pysca.device import PYPLC
    return PYPLC(device,port=int(port),scan=int(scan))

def dummy_device(*args, **kwargs):
    pass

@click.group(invoke_without_command=True,help='Настройка устройства ввода-вывода')
@click.option('--name',help='Имя устройства (PLC etc)')
@click.option('--type',help='Используемый драйвер (pyplc etc)')
@click.option('--args',multiple=True)
@click.pass_context
def device(ctx,name,type,args):
    DEVICE_HANDLES = {
        'PYPLC' : pyplc_device
    }
    params = {}
    
    for arg in args:
        if '=' in arg:
            k, v = arg.split('=', 1)
            params[k.strip()] = v.strip()
    
    if name not in app.devices:
        if type.upper() in DEVICE_HANDLES:
            d = DEVICE_HANDLES[type.upper()](**params)
        else:
            d = dummy_device(**params)
        
        if d:
            app.devices[name] = d
            click.echo(f'   Добавлено устройство {name}')
        else:
            click.secho(f'  Не удалось создать устройство {name}',err=True,fg='red')
    else:
        click.echo(click.style(f'   Не удалось создать устройство либо уже есть {name}',fg='red'),err=True)
