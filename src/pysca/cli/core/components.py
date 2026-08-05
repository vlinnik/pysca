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

# import yaml

def __load_template(base:Path, template_file: str)->Template:
    # шаблон
    env = Environment(
        loader=FileSystemLoader(str(base)),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    template = env.get_template(f"{template_file}")

    return template


def __update_yaml(target_path:Path, target_yaml:Dict[str,Any]):
    if target_path.exists():
        data = yaml.load(target_path.read_text())
    else:
        data = { }

    data.update(target_yaml)

    target_path.parent.mkdir(parents=True,exist_ok=True)
    with target_path.open("w") as f:
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
