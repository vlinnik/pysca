from pysca import app,log
from typing import Dict,Any

def pyplc_device(*_,device:str,port:int=9004,scan:int=100,simulator: bool = False, **kwargs):
    from pysca.device import PYPLC
    return PYPLC(device if not simulator else '127.0.0.1',port=int(port),scan=int(scan))

def dummy_device(*args, **kwargs):
    pass

def device( name: str ,
        type: str , 
        args: Dict[str,Any],
        simulator:bool = False, **kwargs):

    DEVICE_HANDLES = {
        'PYPLC' : pyplc_device
    }

    try:
        if name not in app.devices:
            if type.upper() in DEVICE_HANDLES:
                d = DEVICE_HANDLES[type.upper()](**args,simulator=simulator)
            else:
                d = dummy_device(**args)
            
            if d:
                app.devices[name] = d
                return d
            else:
                log.error(f'Не удалось создать устройство {name}')
        else:
            log.error(f'Не удалось создать устройство либо уже есть {name}')
    except Exception as e:
        log.error(f'При создании устройства IO что-то пошло не так: {e}')
