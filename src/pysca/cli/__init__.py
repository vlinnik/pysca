import click
import yaml
import os

from pysca.cli.restartmanager import FileWatcherTray

manager = FileWatcherTray()

@click.group(invoke_without_command=True)
@click.option('-w', '--workdir', type=click.Path(exists=True, file_okay=False), default='.', help='Рабочая директория')
@click.option('--settings',type=click.Path(exists=True,resolve_path=True),help='Путь к YAML-файлу настроек')
@click.option('--conf', type=click.Path(exists=True), help='Путь к файлу конфигурации (default.scada)')
@click.option('--opentsdb', nargs=1,metavar='<ip>[:port]',  help='IP-адрес и порт OpenTSDB')
@click.option('--grafana', nargs=1,metavar='<ip>[:port]',  help='IP-адрес и порт Grafana')
@click.option('--grafana-key',nargs=1, metavar='<grafana api admin/editor token>',help='API-Token для записи событий в grafana')
@click.option('--simulator',is_flag=True,help='Запустить имитацию логики')
@click.option('--with-asyncio',is_flag=True,help='Использовать qasync QEventLoop для поддержки asyncio')
@click.option('--version',is_flag=True,help='Показать версию pysca')
@click.pass_context
def cli(ctx,settings,workdir,version, **kwargs):
    ctx.ensure_object(dict)
    ctx.obj['modules'] = []     #загружаемые модули с createInstance 
    ctx.obj['globals'] = { }    #что доступно в сценариях

    if workdir:
        import sys
        os.chdir(workdir)
        click.echo(f'   Рабочая директория установлена: {os.getcwd()}')
        sys.path.insert(0, workdir)
    if version:
        from ..__version__ import version
        click.echo(f'   Версия библиотеки pysca: {version}')
        
    if settings:
        with open(settings, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f) or {}
        ctx.obj['config'] = config

        if 'main' in config:
            params:dict = config['main']
            if 'workdir' in params:
                if not workdir:
                    os.chdir(params.pop('workdir'))
                    click.echo(f'   Рабочая директория установлена: {os.getcwd()}')
                else:
                    params.pop('workdir')
            if 'qt_api' in params:
                ctx.obj['qt_api'] = params.pop('qt_api')
            
            ctx.invoke(start,**params)
                        
        if 'devices' in config:
            devices = config['devices']
            for dev in devices:
                if 'args' in dev:
                    args = tuple( f'{key}={val}' for key,val in dev['args'].items() )
                    dev['args'] = args
                ctx.invoke(device,**dev)    
                
        if 'modules' in config:
            modules = config['modules']
            for mod in modules:
                if 'args' in mod:
                    args = tuple( f'{key}={val}' for key,val in mod['args'].items() )
                    mod['args'] = args
                ctx.invoke(module,**mod)

        if 'navbar' in config:
            params = config['navbar']
            ctx.invoke(navbar,**params)
        elif 'multihead' in config:
            params = config['multihead']
            ctx.invoke(multihead,**params)
        elif 'generic' in config:
            params = config['generic']
            ctx.invoke(generic,**params)
        if manager: manager.watch(settings)
    else:
        args = { }
        for key,val in kwargs.items():
            if val is not None:
                args[key] = val
        ctx.invoke(start,**args)
        
from pysca.cli.common import start,navbar,generic,multihead,device,module
all = [device,module,navbar,multihead,generic]

cli.add_command(start,'start')
cli.add_command(navbar,'navbar')
cli.add_command(multihead,'multihead')
cli.add_command(generic,'generic')
cli.add_command(device,'device')
cli.add_command(module,'module')
for cmd in all:
    device.add_command(cmd)
    module.add_command(cmd)    
