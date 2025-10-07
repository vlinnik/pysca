import click
from click_config_file import configuration_option
import yaml

import sys
import os
from qtpy.QtWidgets import QApplication,QMessageBox
from pysca import app,log
from sqlalchemy import exc

def yaml_provider(file_path, cmd_name):
    with open(file_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f) or {}
        
    return config   #.get(cmd_name, {})  # извлекаем блок по имени команды

@click.group(invoke_without_command=True)
@configuration_option('--settings', provider=yaml_provider, help='Путь к YAML-файлу настроек')
@click.argument('filename', type=click.Path(exists=True),required=False)
@click.option('--conf', type=click.Path(exists=True), help='Путь к файлу конфигурации (default.scada)')
@click.option('-w', '--workdir', type=click.Path(exists=True, file_okay=False), help='Рабочая директория')
@click.option('--opentsdb', nargs=1,metavar='<ip>[:port]', help='IP-адрес и порт OpenTSDB')
@click.option('--grafana', nargs=1,metavar='<ip>[:port]', help='IP-адрес и порт Grafana')
@click.option('--grafana-key',nargs=1,metavar='<grafana api admin/editor token>',help='API-Token для записи событий в grafana')
def main(filename,conf,workdir,opentsdb,grafana,grafana_key):
    if workdir:
        os.chdir(workdir)
        click.echo(f'\tРабочая директория установлена: {os.getcwd()}')

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
            click.error(f'failed to open configuration',err=True)
    else:
        click.echo('\tФайл конфигурации не указан!')
        
    if filename:
        w = app.window(filename)
        if w:
            globals()[w.objectName()] = w
            w.show( )
            
    app.start( ctx=globals() )
    
@main.command()
@click.argument('items', nargs=-1, required=True)
def navbar(items):
    from .navbar import append
    for item in items:
        append(app.window(item))
        
                
if __name__ == '__main__':
    qapp = QApplication(sys.argv)
    try:
        main()
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
