import click
# from click_config_file import configuration_option
import yaml

import sys
import os
from qtpy.QtWidgets import QApplication,QMessageBox
from pysca import app,log
from sqlalchemy import exc

# def yaml_provider(file_path, cmd_name):
#     with open(file_path, 'r', encoding='utf-8') as f:
#         config = yaml.safe_load(f) or {}

#     return config.get(cmd_name, {}) if cmd_name in config else config

def run():
    for dname in app.devices:
        app.devices[dname].start( )
        
    app.start(ctx=globals())
    
    for dname in app.devices:
        app.devices[dname].stop( )

@click.group(invoke_without_command=True)
@click.option('--settings',type=click.Path(exists=True),help='Путь к YAML-файлу настроек')
@click.option('--conf', type=click.Path(exists=True), default='default.scada', help='Путь к файлу конфигурации (default.scada)')
@click.option('-w', '--workdir', type=click.Path(exists=True, file_okay=False), default=None, help='Рабочая директория')
@click.option('--opentsdb', nargs=1,metavar='<ip>[:port]', default=None, help='IP-адрес и порт OpenTSDB')
@click.option('--grafana', nargs=1,metavar='<ip>[:port]', default=None, help='IP-адрес и порт Grafana')
@click.option('--grafana-key',nargs=1,default=None, metavar='<grafana api admin/editor token>',help='API-Token для записи событий в grafana')
@click.option('--devices',type=click.Path(exists=True),help='Путь к YAML-файлу настроек устройств')
@click.pass_context
def cli(ctx,settings,**kwargs):
    if settings:
        ctx.ensure_object(dict)
        with open(settings, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f) or {}
        ctx.obj['config'] = config

        if 'main' in config:
            params = config['main']
            ctx.invoke(main,**params)
            
        if 'devices' in config:
            params = config['devices']
            for config in params:
                ctx.invoke(devices,**config)

        if ctx.invoked_subcommand is None:
            if 'navbar' in config:
                params = config['navbar']
                ctx.invoke(navbar,**params)
            elif 'multihead' in config:
                params = config['multihead']
                ctx.invoke(multihead,**params)
    else:
        ctx.invoke(main,**kwargs)
            
@cli.command()
@click.option('--conf', type=click.Path(exists=True), default='default.scada', help='Путь к файлу конфигурации (default.scada)')
@click.option('-w', '--workdir', type=click.Path(exists=True, file_okay=False), default=None, help='Рабочая директория')
@click.option('--opentsdb', nargs=1,metavar='<ip>[:port]', default=None, help='IP-адрес и порт OpenTSDB')
@click.option('--grafana', nargs=1,metavar='<ip>[:port]', default=None, help='IP-адрес и порт Grafana')
@click.option('--grafana-key',nargs=1,default=None, metavar='<grafana api admin/editor token>',help='API-Token для записи событий в grafana')
@click.option('--devices',type=click.Path(exists=True),help='Путь к YAML-файлу настроек устройств')
@click.pass_context
def main(ctx,conf,workdir,opentsdb,grafana,grafana_key,devices):
    if workdir:
        os.chdir(workdir)
        click.echo(f'\tРабочая директория установлена: {os.getcwd()}')

    if devices:
        with open(devices, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f) or {}
            
        if 'devices' in config:
            params = config['devices']
            for config in params:
                ctx.invoke(device,**config)

    if opentsdb:
        parts = opentsdb.split(':')
        ip = parts[0]
        if len(parts)>1:
            port = int(parts[1])
        else:
            port = 4242
        
        from .opentsdb import OpenTSDBJournal, OpenTSDBAlerts
        app.journal = OpenTSDBJournal( ip, port )
        app.journal.spawn( )
        app.alerts = OpenTSDBAlerts( app.ctx, ip, port )
        app.alerts.spawn( )
    
    if grafana:
        if not grafana_key:
            QMessageBox.critical(None,'Что-то не то..','Параметр grafana требует указать grafana-key')
            raise click.UsageError('Параметр grafana требует указать grafana-key')

        parts = grafana.split(':')
        ip = parts[0]
        if len(parts)>1:
            port = int(parts[1])
        else:
            port = 3000
            
        from .grafanaevents import GrafanaAnnotations
        app.events = GrafanaAnnotations(app.ctx , grafana_key,ip,port)
        app.events.spawn( )

    if conf:
        click.echo(f'\tФайл конфигурации: {conf}')
        try:
            app.config( conf )
        except exc.SQLAlchemyError as e:
            click.echo(f'failed to open configuration',err=True)
    else:
        click.echo('\tФайл конфигурации не указан!')
        
@cli.command()
@click.argument('pages',nargs=-1, type=click.Path(exists=True),required=False)
@click.option('--title', type=click.STRING,required=False)
@click.pass_context
def navbar(ctx,pages,title):
    from .navbar import append,instance
    for p in pages:
        p = app.window(p)
        if not p:
            continue
        append(p)
        globals()[p.objectName()] = p
    if title:
        instance.setWindowTitle(f'{title}')
    instance.show()
    run()
        
@cli.command()
@click.argument('pages',nargs=-1, type=click.Path(exists=True),required=False)
@click.option('--title', type=click.STRING,required=False)
@click.pass_context
def multihead(ctx,pages,title):
    from .multihead import append,instance
    for p in pages:
        p = app.window(p)
        if not p:
            continue
        append(p)
        globals()[p.objectName()] = p
    if title:
        instance.setWindowTitle(f'{title}')
    instance.show()
    run()
    
def pyplc_device(*_,device,port=9004,scan=100,**kwargs):
    from .device import PYPLC
    return PYPLC(device,port=port,scan=scan)

def dummy_device(*args, **kwargs):
    pass

@cli.command(context_settings={"ignore_unknown_options": True, "allow_extra_args": True})
@click.argument('device')
@click.option('--type')
@click.option('--param',multiple=True)
@click.pass_context
def device(ctx,device,type,param):
    DEVICE_HANDLES = {
        'PYPLC' : pyplc_device
    }
    params = {}
    if isinstance(param,dict):
        params.update(param)
    else:
        for p in param:
            if '=' in p:
                k, v = p.split('=', 1)
                params[k.strip()] = v.strip()
    
    if device not in app.devices:
        if type in DEVICE_HANDLES:
            d = DEVICE_HANDLES[type](**params)
        else:
            d = dummy_device(**params)
        
        if d:
            app.devices[device] = d
            click.echo(f'\tДобавлено устройство {device}')
        else:
            click.secho(f'\tНе удалось создать устройство {device}',err=True,fg='red')
    else:
        click.echo(click.style(f'\tНе удалось создать устройство либо уже есть {device}',fg='red'),err=True)
                
if __name__ == '__main__':
    qapp = QApplication(sys.argv)
    try:
        cli()
        pass
    except Exception as e:
        QMessageBox.critical(None,'Что-то пошло не так',f'{e}')
        click.echo(e,err=True)

def __main():
    from . import app
    from qtpy.QtCore import QResource
    import argparse
    parser = argparse.ArgumentParser(
                        prog='PYSCA Project',
                        description='Запуск проекта визуализации на Python+Qt',
                        epilog='Пример: python -m pysca')

    parser.add_argument('forms',help='Загружаемые окна',nargs='+')
    parser.add_argument('-w','--workdir',action='store', help='Рабочий каталог проекта')
    parser.add_argument('--conf',action='store', help='Конфигурационная база проекта (переменные, анимации, короткие события)')
    parser.add_argument('--resources',action='store',default='', help='Файл ресурсов')
    parser.add_argument('--start',action='store', help='Какое окно главное')
    parser.add_argument('--init',action='store',default='', help='Выполнить')
    
    args,ignored = parser.parse_known_args()
    
    import os.path
    if os.path.isfile(args.resources):
        QResource.registerResource(args.resources)
    
    _g = globals()
    startup = None
    for file in args.forms:
        w = app.window(file)
        if w:
            _g[w.objectName()] = w
            if startup is None:startup = w
            if args.start==w.objectName():
                startup = w
                
    if args.init:
        with open(args.init) as f:
            exec(f.read(),globals())
            
    if startup: 
        startup.show( )        
        app.start( ctx = globals() )

# if __name__=='__main__': 
#     main()
