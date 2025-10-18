import click
import yaml

import os
from qtpy.QtWidgets import QMessageBox,QWidget
from pysca import app
from sqlalchemy import exc

from pysca.cli.devices import device
from pysca.cli.modules import module
from qtpy.QtWidgets import qApp
from pysca.cli.restartmanager import FileWatcherTray

manager = FileWatcherTray(qApp.quit)

@click.pass_context
def run(ctx):
    for m in ctx.obj['modules']:
        if hasattr(m,'initialize') and callable(getattr(m,'initialize')):
            m.initialize( ctx=globals() )
        
        
    for dname in app.devices:
        app.devices[dname].start( )

    manager.start( )
    app.start(ctx=globals())
    manager.stop( )
    
    for dname in app.devices:
        app.devices[dname].stop( )
        
    if 'logic' in ctx.obj:
        logic = ctx.obj['logic']
        logic.terminate( )

import xml.etree.ElementTree as ET
from typing import List,Type

def resolve_class(ui_path:str,mods:List[Type]):
    if len(mods)>0:
        tree = ET.parse(ui_path)
        root = tree.getroot()
        class_tag = root.find('class')
        class_name = class_tag.text if class_tag is not None else None
        cls = None
        if class_name:
            for m in mods:
                if hasattr(m,class_name):
                    cls = getattr(m,class_name)
                    break
        return cls
    return None    
def load_modules(modules):
    mods = []
    if len(modules)>0:
        import importlib
        for m in modules:
            mods.append(importlib.import_module(m))
    return mods
def load_windows(pages,modules)->List[QWidget]:
    wins = []
            
    for p in pages:
        manager.watch(p)
        cls = resolve_class(p,modules)
        if cls is not None:
            w = app.window(p,baseinstance=cls())
        else:
            w = app.window(p)
        if not w:
            continue
        globals()[w.objectName()] = w
        wins.append(w)
    return wins

@click.group(invoke_without_command=True)
@click.option('-w', '--workdir', type=click.Path(exists=True, file_okay=False), default='.', help='Рабочая директория')
@click.option('--settings',type=click.Path(exists=True),help='Путь к YAML-файлу настроек')
@click.option('--conf', type=click.Path(exists=True), help='Путь к файлу конфигурации (default.scada)')
@click.option('--opentsdb', nargs=1,metavar='<ip>[:port]',  help='IP-адрес и порт OpenTSDB')
@click.option('--grafana', nargs=1,metavar='<ip>[:port]',  help='IP-адрес и порт Grafana')
@click.option('--grafana-key',nargs=1, metavar='<grafana api admin/editor token>',help='API-Token для записи событий в grafana')
@click.option('--simulator',is_flag=True,help='Запустить имитацию логики')
@click.pass_context
def cli(ctx,settings,workdir,**kwargs):
    if workdir:
        os.chdir(workdir)
        click.echo(f'   Рабочая директория установлена: {os.getcwd()}')

    ctx.ensure_object(dict)
    ctx.obj['modules'] = []
    if settings:
        manager.watch(settings)
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
    else:
        args = { }
        for key,val in kwargs.items():
            if val is not None:
                args[key] = val
        ctx.invoke(start,**args)
            
@cli.command(help='Настройка основных параметров')
@click.option('--conf', type=click.Path(exists=True), default='default.scada', help='Путь к файлу конфигурации (default.scada)')
@click.option('--opentsdb', nargs=1,metavar='<ip>[:port]',  help='IP-адрес и порт OpenTSDB')
@click.option('--grafana', nargs=1,metavar='<ip>[:port]',  help='IP-адрес и порт Grafana')
@click.option('--grafana-key',nargs=1, metavar='<grafana api admin/editor token>',help='API-Token для записи событий в grafana')
@click.option('--simulator',is_flag=True,help='Запустить имитацию логики')
@click.pass_context
def start(ctx,conf,opentsdb,grafana,grafana_key,simulator):
    if opentsdb:
        parts = opentsdb.split(':')
        ip = parts[0]
        if len(parts)>1:
            port = int(parts[1])
        else:
            port = 4242
        
        from pysca.opentsdb import OpenTSDBJournal, OpenTSDBAlerts
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
            
        from pysca.grafanaevents import GrafanaAnnotations
        app.events = GrafanaAnnotations(app.ctx , grafana_key,ip,port)
        app.events.spawn( )

    if conf:
        manager.watch(conf)
        click.echo(f'   Файл конфигурации: {conf}')
        try:
            app.config( conf )
        except exc.SQLAlchemyError as e:
            click.echo(f'failed to open configuration',err=True)
    else:
        click.echo('   Файл конфигурации не указан!')
        
    if simulator:
        import subprocess
        ctx.obj['logic'] = subprocess.Popen(["python3", "src/krax.py"])
            
@cli.command(help='Запуск в окне с навигацией, панелью инструментов')
@click.argument('pages',nargs=-1, type=click.Path(exists=True),required=False)
@click.option('--title', type=click.STRING,required=False)
@click.option('--tools',multiple=True, type=click.Path(exists=True),required=False)
@click.option('--modules',multiple=True, type=click.STRING,required=False)
@click.pass_context
def navbar(ctx,pages,title,tools,modules):
    import pysca.navbar as navbar
    mods = load_modules(modules)
    wins = load_windows(pages,mods)
    for w in wins:
        navbar.append(w)
    wins = load_windows(tools,mods)
    for w in wins:
        navbar.tools(w)
    if title:
        navbar.instance.setWindowTitle(f'{title}')
    navbar.instance.show()
    globals()['_MAIN_'] = navbar.instance
    run()
        
@cli.command(help='Запуск в окне с навигацией на несколько мониторов')
@click.argument('pages',nargs=-1, type=click.Path(exists=True),required=False)
@click.option('--title', type=click.STRING,required=False)
@click.option('--tools',multiple=True, type=click.Path(exists=True),required=False)
@click.option('--modules',multiple=True, type=click.STRING,required=False)
@click.pass_context
def multihead(ctx,pages,title,tools,modules):
    import pysca.multihead as navbar
    mods = load_modules(modules)
    wins = load_windows(pages,mods)
    for w in wins:
        navbar.append(w)
    wins = load_windows(tools,mods)
    for w in wins:
        navbar.tools(w)        
    if title:
        navbar.instance.setWindowTitle(f'{title}')
    navbar.instance.show()
    globals()['_MAIN_'] = navbar.instance
    run()

@cli.command(help='Запуск пользовательских окон')
@click.argument('pages',nargs=-1, type=click.Path(exists=True),required=False)
@click.option('--modules',multiple=True, type=click.STRING,required=False)
@click.pass_context
def generic(ctx,pages,modules):
    mods = load_modules(modules)
    wins = load_windows(pages,mods)
    for w in wins:
        w.show( )
    globals()['_MAIN_'] = w
    run()

all = [device,module,navbar,multihead,generic]

cli.add_command(device,'device')
cli.add_command(module,'module')
for cmd in all:
    device.add_command(cmd)
    module.add_command(cmd)

def entry():
    try:
        cli()
    except Exception as e:
        QMessageBox.critical(None,'Что-то пошло не так',f'{e}')
        click.echo(e,err=True)
    
if __name__ == '__main__':
    entry()