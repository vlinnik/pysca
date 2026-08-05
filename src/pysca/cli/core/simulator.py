import sys
import subprocess
import signal
from pysca import log
from pysca.config import config
from typing import List, Tuple
from pathlib import Path

_tasks: List[Tuple[str,subprocess.Popen] ] = []

def simulator(task: str, exec: Path, args: List[str] = [],**kwargs):
    exec = config().logics.joinpath( exec ).expanduser()
    logic = subprocess.Popen([sys.executable, exec, *args ],cwd=config().logics)
    log.debug(f'Запуск имитации задачи #{logic.pid}: {task}=>{exec} с аргументами {args}: {[sys.executable, exec, *args ]}')
    _tasks.append( (task,logic) )
    
def close():
    for task,proc in _tasks:
        log.debug(f'Завершение имитации задачи: {task}')
        proc.send_signal(sig=signal.SIGINT)
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            log.warning(f'Принудительное завершение задачи имитации: {task}')
            proc.kill()