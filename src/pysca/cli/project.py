import typer
import sys
import os
from pathlib import Path
from types import ModuleType
from typing import Optional, List, Dict, Any
from pysca import app as _app, log
from pysca.config import init_env,update_config,config
from pathlib import Path
from typing import Dict,Any,cast
from ruamel.yaml import YAML
from pathlib import Path
from importlib.resources import files
from jinja2 import Environment, FileSystemLoader, Template
from pysca import log
from pysca.config import config

yaml = YAML()
yaml.preserve_quotes = True

app = typer.Typer(name='project', help='Запуск/настройка проекта')

def __load_template(base:Path, template_file: str)->Template:
    # шаблон
    env = Environment(
        loader=FileSystemLoader(str(base)),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    template = env.get_template(f"{template_file}")

    return template

def __merge_config(base: Dict[str,Any], new: dict):
    if base is None: return new
    for key, value in new.items():
        if (
            key in base
            and isinstance(base[key], dict)
            and isinstance(value, dict)
        ):
            __merge_config(base[key], value)
        elif (
            key in base 
            and isinstance(base[key],list)
            and isinstance(value,list)
        ):
            base[key]+= value
            base[key] = list(set(base[key]))
        else:
            base[key] = value

def __update_yaml(target_path:Path, target_yaml:Dict[str,Any]):
    if target_path.exists():
        data = yaml.load(target_path.read_text())
    else:
        data = target_yaml

    __merge_config(data,target_yaml)
    
    target_path.parent.mkdir(parents=True,exist_ok=True)
    with target_path.open("w+") as f:
        yaml.dump(data, f)

def init_grafana(
            suffix: str ,
            networks: str ,
            password: str ,
            ):
    opts = { 'suffix':suffix,'networks':networks,'password':password}
    template_base = Path(str(files("pysca.cli.templates.grafana").joinpath('docker-compose.yaml'))).parent
        
    templates = [
                ('docker-compose.yaml',config().workspace),
                ('datasources.yaml',config().workspace / 'grafana' / 'provisioning' / 'datasources') 
                ]
    
    for file,target in templates:
        try:
            template = __load_template(template_base,template_file=file)
            rendered_yaml = yaml.load(template.render(**opts))    
            __update_yaml(target.joinpath(file),rendered_yaml)
        except Exception as e:
            log.warning(f'При создании из шаблона {file} в {target} что-то пошло не так: {e}')

@app.command(help='Настройка/инициализация проекта')
def init(
    grafana: str = typer.Option(None,help='Инициализация grafana + opentsdb для исторических данных'), 
    suffix: Optional[str] = typer.Option(None,help='Суффикс для имён контейнеров'),
    password: str = typer.Option('admin',help='Пароль админа при инициализации grafana'),
    networks: str = typer.Option('monitoring',help='Сеть для контейнеров'),
    forms: Path = typer.Option('ui',help='Расположение UI-файлов окон'),
    widgets: Path = typer.Option('widgets',help='Где находятся пользовательские виджеты'),
    workdir: Path = typer.Argument(Path('src/gui/data'),envvar='PYSCAWORKDIR', help='Расположение конфигурационного файла проекта')):

    opts = { 'forms' : forms, 'widgets' : widgets }
    cwd = Path('.').resolve()
    loc = workdir

    template_base = Path(str(files("pysca.cli.templates").joinpath('settings.yaml'))).parent
        
    templates = [
                ('settings.yaml',loc ),
                ]
    
    for file,target in templates:
        try:
            template = __load_template(template_base,template_file=file)
            rendered_yaml = yaml.load(template.render(**opts))    
            __update_yaml(target.joinpath(file),rendered_yaml)
        except Exception as e:
            log.warning(f'При создании из шаблона {file} в {target} что-то пошло не так: {e}')

    settings = init_env( workdir )
    
    if grafana:
        init_grafana(suffix=suffix or cwd.name.lower(),password=password,networks=networks)
        typer.echo(f'Файл {cwd.joinpath('docker-compose.yaml')} обновлен')
        settings.update( { 'opentsdb': { 'host':'localhost','port':4242}} )
    elif 'opentsdb' in settings :
        settings.pop('opentsdb')
                    
    update_config(workdir,settings)

@app.command(help='Запуск проекта')
def run(
    dry: bool = typer.Option(False, help='Просто проверка возможности запуска'),
    simulator: bool = typer.Option(False, help='Запуск в режиме имитации'),
    asyncio: bool = typer.Option(False, help='Использовать asycio QEventLoop'),
    workdir: Path = typer.Option(envvar='PYSCAWORKDIR', help='Где расположен конфигурационный файл проекта')
):
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
    
    from qtpy.QtWidgets import QApplication
    from qtpy.QtCore import Qt,QObject
    qApp = QApplication.instance()
    if not qApp:
        QApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)
        qApp = QApplication([])

    _app.loadResources( )
    _app.config(config().db)

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
