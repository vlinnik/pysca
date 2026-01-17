import typer
import os
import sys
from pathlib import Path
from typing import List,Optional
from pysca.cli import message
from pysca.cli.core.paths import paths as core_paths

app = typer.Typer(help='Настройка путей и расположения управляющих файлов проекта')

@app.command( help='Настройка путей и расположения управляющих файлов проекта' )
def paths(ctx: typer.Context, 
        modules: List[Path] = typer.Option(None,help='Пути поиска python модулей'),
        plugins: List[Path] = typer.Option(None,help='Пути поиска pyqt-designer расширений'),
        workspace: Optional[Path] = typer.Option('.',help='Расположение проекта',resolve_path=True),
        forms: Optional[Path] = typer.Option('ui',help='Расположение форм приложения',resolve_path=True),
        widgets: Optional[Path] = typer.Option('widgets',help='Расположение элементов окон',resolve_path=True),
        simulator: Optional[Path] = typer.Option('simulator',help='Расположение проекта(ов) логики для запуска в режиме имитации',resolve_path=True),
        resources: List[Path] = typer.Option(None,help='Расположение ресурсов проекта')
        ):

    if isinstance(modules,list):
        core_paths( modules=modules)
        
    if isinstance(plugins,list):
        core_paths( plugins= plugins )
        
    if isinstance(workspace, str):
        core_paths(workspace= workspace)
    
    if forms: 
        core_paths(forms=forms)
    
    if widgets: 
        core_paths(widgets=widgets)
    
    if simulator:
        core_paths(simulator=simulator)
        
    if isinstance(resources,list):
        core_paths( resources= [ Path(p).resolve() for p in resources] )