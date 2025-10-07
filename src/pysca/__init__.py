from .app import App,log
# import os
# from qtpy.QtWidgets import QApplication,QWidget
# from qtpy.QtCore import QObject,QResource,QVariant,QTimer,Qt
# from datetime import datetime
# import time
# import sys,os,glob,re,types
# import logging
# import argparse
# import json
# from typing import Any
# try:
#     from .__version__ import version
# except ImportError:
#     version = 'v0.0.0+unknown'
# from .bindable import Expressions,Property
# from .utils import LinearScale
# from .device import PYPLC
# from .journal import MetricJournal
# from .events import MetricDairy
# from .alerts import AlertsJournal

# if not QApplication.instance():
#     QApplication.setAttribute(Qt.AA_ShareOpenGLContexts)
#     qApp = QApplication(sys.argv)
# else:
#     qApp = QApplication.instance()

# parser = argparse.ArgumentParser(
#                     prog='PYSCA Project',
#                     description='Запуск проекта визуализации на Python+Qt',
#                     epilog='Пример: python -m pysca')

# parser.add_argument('--conf',action='store',default='default.scada',help='Конфигурационная база проекта (переменные, анимации, короткие события)')
# parser.add_argument('-w','--workdir',action='store',default='./',help='Рабочий каталог проекта')
# parser.add_argument('--opentsdb',action='store',default='none',help='Использовать OpenTSDB для хранения журнала, адрес сервера')
# parser.add_argument('--otsdb_port',action='store',default=4242,help='OpenTSDB port, по умолчанию 4242')
# parser.add_argument('--grafana',action='store',default='none',help='Использовать Grafana для хранения событий, адрес сервера')
# parser.add_argument('--grafana_port',action='store',default=3000,help='Grafana port, по умолчанию 3000')
# parser.add_argument('--grafana_key',action='store',default='',help='Grafana API-KEY, получить в Administrations->Service Accounts')

# args,ignored = parser.parse_known_args()
            
# app = App( )

# try:
#     os.chdir(args.workdir)
#     log.debug(f'working dir is {args.workdir}')
# except FileNotFoundError as e:
#     log.warning('cannot set workdir - not found') 

# if args.opentsdb!='none':
#     from .opentsdb import OpenTSDBJournal, OpenTSDBAlerts
#     app.journal = OpenTSDBJournal( args.opentsdb, args.otsdb_port )
#     app.journal.spawn( )
#     app.alerts = OpenTSDBAlerts( app.ctx, args.opentsdb, args.otsdb_port )
#     app.alerts.spawn( )


# if args.grafana!='none':
#     from .grafanaevents import GrafanaAnnotations
#     app.events = GrafanaAnnotations(app.ctx , args.grafana_key,args.grafana,args.grafana_port)
#     app.events.spawn( )

# try:
#     app.config( args.conf )
# except exc.SQLAlchemyError as e:
#     log.error(f'failed to open configuration')

app = App( )
__all__=['app','log']

