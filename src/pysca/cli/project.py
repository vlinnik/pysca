import typer
import sys
import os
from pathlib import Path
from types import ModuleType
from typing import Optional, List, Dict, Any
from pysca import app as _app, log
from pysca.config import init_env,update_config
from pysca.cli.core.components import init_grafana

app = typer.Typer(name='project', help='Запуск/настройка проекта')

@app.command(help='Настройка/инициализация проекта')
def init(
    ctx: typer.Context,
    opentsdb: bool = typer.Option(True,help='Используем opentsdb для исторических данных'), 
    suffix: Optional[str] = typer.Option(None,help='Суффикс для имён контейнеров'),
    password: str = typer.Option('admin',help='Пароль админа при инициализации grafana'),
    networks: str = typer.Option('monitoring',help='Сеть для контейнеров'),
    forms: Path = typer.Option('ui',help='Расположение UI-файлов окон'),
    widgets: Path = typer.Option('widgets',help='Где находятся пользовательские виджеты'),
    conf: Path = typer.Argument('src/gui/data/default.scada',help='Имя файла с базой анимаций, переменных'),
    workdir: Path = typer.Option(envvar='PYSCAWORKDIR', help='Где расположен конфигурационный файл проекта')):

    cwd = Path('.').resolve()
    loc = Path(conf).resolve().parent

    settings: Dict[str,Any] = {
        'main':{'config':conf.name,'stdout':'DEBUG:INFO','stderr':'WARNING:'},
        'paths': 
        { 
        'workspace': os.path.relpath(cwd,loc) ,
        'modules': ['..','../..'] ,
        'simulator' : '.',
        'resources' : '.',
        'forms' : os.path.relpath(str(loc.joinpath(forms).resolve()),str(loc)),
        'widgets' : os.path.relpath(str(loc.joinpath(widgets).resolve()),str(loc))
        }
        }

    settings = init_env( workdir )
    
    if opentsdb:
        init_grafana(suffix=suffix or cwd.name.lower(),password=password,networks=networks)
        typer.echo(f'Файл {cwd.joinpath('docker-compose.yaml')} обновлен')
        settings.update( { 'opentsdb': { 'host':'localhost','port':4242}} )
    else:
        settings.pop('opentsdb')
                    
    update_config(workdir,settings)

@app.command(help='Запуск проекта')
def run(
        dry: bool = typer.Option(False, help='Просто проверка возможности запуска'),
        simulator: bool = typer.Option(False, help='Запуск в режиме имитации'),
        asyncio: bool = typer.Option(False, help='Использовать asycio QEventLoop'),
        workdir: Path = typer.Option(envvar='PYSCAWORKDIR', help='Где расположен конфигурационный файл проекта')):
    settings = init_env(workdir)
    main_conf: dict = settings.get('main', {})
    stdout = main_conf.get('stdout')
    stderr = main_conf.get('stderr')
    if stdout or stderr:
        log.remove()
    if stdout:
        low, high = stdout.split(
            ":", 1) if ":" in stdout else (stdout, 'CRITICAL')
        low, high = log.level(low or 'DEBUG').no, log.level(
            high or 'CRITICAL').no
        log.add(sys.stdout, level=low, filter=lambda record, low=low, high=high:
                (min(low, high) <= record["level"].no <= max(low, high)), format='<dim>{time:HH:mm:ss.SSS}</dim> | <level>{level:7}</level> | {name:>20}.py:{line:<5} | <level>{message}</level> '
                )
    if stderr:
        low, high = stderr.split(
            ":", 1) if ":" in stderr else (stderr, 'CRITICAL')
        low, high = log.level(low or 'DEBUG').no, log.level(
            high or 'CRITICAL').no
        log.add(sys.stderr, level=low, filter=lambda record, low=low, high=high:
                (min(low, high) <= record["level"].no <= max(low, high)), format='<red>{time:HH:mm:ss.SSS}</red> | <level>{level:7}</level> | {name:>20}.py:{line:<5} | <level>{message}</level> '
                )

    if workdir:
        os.chdir(str(workdir))

    os.environ['PYSCARUNTIME'] = '1'

    modules: List[ModuleType] = []  # загруженные модули
    ctx: Dict[str, Any] = {}  # то что доступно для выражений/скриптов

    conf_tsdb: dict = settings.get('opentsdb', {})
    if conf_tsdb and not dry:
        from pysca.opentsdb import OpenTSDBJournal
        _app.journal = OpenTSDBJournal(**conf_tsdb)

    conf_mods: List[Any] = settings.get('modules', [])
    if conf_mods and not dry:
        from pysca.cli.core.modules import modules as core_modules
        for mod_params in conf_mods:
            mod, instance = core_modules(**mod_params)
            if mod:
                modules.append(mod)
            if instance:
                ctx[mod_params.get('alias', mod_params['name'])] = instance

    conf_sim: List[dict] = settings.get('simulator', [])
    if conf_sim and not dry and simulator:
        from pysca.cli.core.simulator import simulator as core_simulator
        for s in conf_sim:
            core_simulator(**s)

    conf_dev: List[dict] = settings.get("devices", [])
    if conf_dev and not dry:
        from pysca.cli.core.devices import device as core_device
        for d in conf_dev:
            core_device(**d, simulator=simulator)

    conf_win: List[Dict[str, Any]] = settings.get('windows', [])
    if conf_win and not dry:
        from pysca.cli.core.wm import window as core_window
        for win in conf_win:
            key, sym = core_window(**win)
            ctx.update({key: sym})

    conf_view: List[Dict[str, Any]] = settings.get('views', [])
    if conf_view and not dry:
        from pysca.cli.core.wm import view as core_view
        for view in conf_view:
            key, sym = core_view(**view)
            ctx.update({key: sym})

    conf_nav: dict = settings.get('navbar', {})
    if conf_nav and not dry:
        from pysca.cli.core.wm import navbar
        ctx.update({'navbar': navbar(**conf_nav)})

    if not dry:
        _app.context().update(ctx)
        for m in modules:
            if hasattr(m, 'on_start'):
                m.on_start()

        from qtpy.QtWidgets import QApplication
        if QApplication.instance():
            _app.start(ctx, use_asyncio=asyncio)

        if simulator:
            from pysca.cli.core.simulator import close as stop_simulator
            stop_simulator()
