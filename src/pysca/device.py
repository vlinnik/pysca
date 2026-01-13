from qtpy.QtCore import QTimer
from typing import Any
from .pyplc.subscriber import Subscriber
from .bindable import Property
from time import time

class PYPLC(Subscriber):
    def __init__(self, host:str='127.0.0.1', port=9004,timeout=10,scan:int=100):
        super().__init__(host, port,i_size=4096,o_size=512)
        self._timer = QTimer()
        self._timer.timeout.connect(self)
        self._timestamp = time()
        self._timeout = timeout
        self._scan = scan

    def subscribe(self, p: Property, **kwargs):
        s = super().subscribe(p.address, p.name)

        # при изменении переменной произвести запись в контроллер
        s.bind(p.remote)  # при изменении в контроллере записать в переменную
        p.changed(s.write) # при записи в переменную оповещать 

    def start(self, msec: int|None = None):
        self._timer.start(msec if msec else self._scan)

    def stop(self):
        self.close()
        self._timer.stop()

    def received(self, data):
        self._timestamp = time()
        return super().received(data)
    
    def connected(self):
        self._timestamp = time()
        return super().connected()
    
    def routine(self):
        if self._timestamp+self._timeout<time():
            self.close( )
        else:
            super().routine()
