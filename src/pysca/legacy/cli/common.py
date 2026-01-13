import click
import sys

from sqlalchemy import exc

from pysca import app
from pysca.cli import manager
from pysca.cli.devices import device
from pysca.cli.modules import module

from typing import TYPE_CHECKING,Optional

if TYPE_CHECKING:
    from qtpy.QtWidgets import QWidget

@click.pass_context
def run(ctx):
    from qtpy.QtWidgets import QApplication
    from qtpy import API_NAME
    for m in ctx.obj['modules']:
        if hasattr(m,'initialize') and callable(getattr(m,'initialize')):
            m.initialize( ctx=globals() )
        
    for dname in app.devices:
        app.devices[dname].start( )

    if 'qt_api' in ctx.obj and API_NAME not in ctx.obj['qt_api']:
        click.echo(f'   Используется backend {API_NAME}, указаны возможные варианты {ctx.obj["qt_api"]}')
        
    qApp = QApplication.instance()
    manager.quit = qApp.quit if qApp else None
    manager.start( )
    for on_start in ctx.obj['on_start']:
        on_start( )
    app.start(ctx=globals(),use_asyncio=ctx.obj['asyncio'] if 'asyncio' in ctx.obj else False)
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

def load_modules(ctx,modules):
    mods = []
    if len(modules)>0:
        import importlib
        for m in modules:
            try:
                mod = importlib.import_module(m)
                mods.append(mod)
            except ImportError as e:
                click.echo(f'Модуль {m} не удалось загрузить: {e}',err=True,color=True)
    return mods

def load_windows(ctx,pages,modules)->List['QWidget']:
    wins = []
            
    for p in pages:
        manager.watch(p)
        cls = resolve_class(p,modules)
        if cls is not None:
            w = app.window(p,baseinstance=cls(),ctx=ctx.obj['globals'])
        else:
            w = app.window(p,ctx=ctx.obj['globals'])
        if not w:
            continue
        app.context().update( { w.objectName():w} )
        # globals()[w.objectName()] = w
        wins.append(w)
    return wins

@click.command(help='Настройка основных параметров')
@click.option('--conf', type=click.Path(exists=True), default='default.scada', help='Путь к файлу конфигурации (default.scada)')
@click.option('--opentsdb', nargs=1,metavar='<ip>[:port]',  help='IP-адрес и порт OpenTSDB')
@click.option('--grafana', nargs=1,metavar='<ip>[:port]',  help='IP-адрес и порт Grafana')
@click.option('--grafana-key',nargs=1, metavar='<grafana api admin/editor token>',help='API-Token для записи событий в grafana')
@click.option('--simulator',is_flag=True,help='Запустить имитацию логики')
@click.option('--with-asyncio',is_flag=True,help='Использовать qasync QEventLoop для поддержки asyncio')
@click.option('--paths',multiple=True,help='Пути поиска python-модулей')
@click.option('--modules',multiple=True,help='Загрузить модули')
@click.pass_context
def start(ctx,conf,opentsdb,grafana,grafana_key,simulator,with_asyncio,paths,modules):
    from qtpy.QtWidgets import QMessageBox
    ctx.obj['asyncio'] = with_asyncio
    ctx.obj['on_start'] = []

    for p in paths:
        sys.path.insert(0, p)        
    
    if modules:
        mods=load_modules(ctx,modules)
        for m in mods:
            defname = str(m.__name__).replace('.','_')
            name = getattr(m,'MODULE',defname)
            on_load = getattr(m,'on_load',lambda: None)
            on_start= getattr(m,'on_start',lambda: None)
            app.context().update({name:m})
            on_load()
            ctx.obj['on_start'].append(on_start)
            
        
    if opentsdb and isinstance(opentsdb,str):
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
    
    if grafana and isinstance(grafana,str):
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

@click.command(help='Запуск в окне с навигацией, панелью инструментов')
@click.argument('pages',nargs=-1, type=click.Path(exists=True),required=False)
@click.option('--title', type=click.STRING,required=False)
@click.option('--tools',multiple=True, type=click.Path(exists=True),required=False)
@click.option('--modules',multiple=True, type=click.STRING,required=False)
@click.pass_context
def navbar(ctx,pages,title,tools,modules):
    import pysca.navbar as navbar
    mods = load_modules(ctx,modules)
    wins = load_windows(ctx,pages,mods)
    for w in wins:
        navbar.append(w)
    wins = load_windows(ctx,tools,mods)
    for w in wins:
        navbar.tools(w)
    if title:
        navbar.instance.setWindowTitle(f'{title}')
    navbar.instance.show()
    globals()['_MAIN_'] = navbar.instance
    run()
        
@click.command(help='Запуск в окне с навигацией на несколько мониторов')
@click.argument('pages',nargs=-1, type=click.Path(exists=True),required=False)
@click.option('--title', type=click.STRING,required=False)
@click.option('--tools',multiple=True, type=click.Path(exists=True),required=False)
@click.option('--modules',multiple=True, type=click.STRING,required=False)
@click.pass_context
def multihead(ctx,pages,title,tools,modules):
    import pysca.multihead as navbar
    mods = load_modules(ctx,modules)
    wins = load_windows(ctx,pages,mods)
    for w in wins:
        navbar.append(w)
    wins = load_windows(ctx,tools,mods)
    for w in wins:
        navbar.tools(w)        
    if title:
        navbar.instance.setWindowTitle(f'{title}')
    navbar.instance.show()
    globals()['_MAIN_'] = navbar.instance
    run()

@click.command(help='Запуск пользовательских окон')
@click.argument('pages',nargs=-1, type=click.Path(exists=True),required=False)
@click.option('--modules',multiple=True, type=click.STRING,required=False)
@click.pass_context
def generic(ctx,pages,modules):
    mods = load_modules(ctx,modules)
    wins = load_windows(ctx,pages,mods)
    for w in wins:
        w.show( )
    globals()['_MAIN_'] = w
    run()            