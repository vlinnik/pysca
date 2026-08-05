from typing import Any, List, Type
from enum import IntEnum
from pysca import log
from pysca.bindable import Property, Filter
from pysca.helpers import Signal,Slot
from qtpy.QtCore import QObject, QThread, QTimer,QCoreApplication

class JournalEvent:
    class Sources(IntEnum):
        SOURCE_SYSTEM = 0
        SOURCE_USER = 1
        
    def __init__(self, item: str, metric: str, value: Any, source: 'JournalEvent.Sources',  **kwargs):
        self.value = value
        self.item = item
        self.metric = metric
        self.source = source
        self.tags = kwargs
        self.tags['source'] = source
        self.tags['item_id'] = item

    def __repr__(self):
        return f"<JournalEvent {self.item} | {self.metric:.3f} | {self.source.name}| {self.value} | {self.tags}>"

class MetricFilter(Filter):
    def __init__(self, *, what: Property|None = None, next: Filter|None = None):
        super().__init__(what=what, next=next)
        self._metric:str 
        self._initialized = False
        
    def _update_metric(self):
        pass
    
    @property
    def metric(self) -> str:
        try:
            return self._metric
        except:
            return ''
    
    @metric.setter
    def metric(self,metric: str):
        self._metric = metric
        if self._next is not None:
            self._next.config('metric',metric)
        self._update_metric(  )
            
    @property
    def name(self) -> str:
        if self._prop is not None and self._prop.name is not None:
            return self._prop.name
        return ''
        
class JournalFilter(MetricFilter):
    def __init__(self, journal: 'MetricJournal', *, what: Property|None = None, next: Filter|None = None):
        super().__init__( what=what, next=next)
        self.journal:MetricJournal = journal

    def raw2eu(self, raw: Any):
        eu = super().raw2eu(raw)
        
        if not self.metric:
            self.metric = self.name
            
        if self.journal and self.metric and self.name:
            if not self._initialized:
                self.journal.register( self.name,self.metric )
                self._initialized = True
            self.emit(JournalEvent( self.name, self.metric, eu, source=JournalEvent.Sources.SOURCE_SYSTEM))
            
        return eu
    
    def _update_metric(self):
        pass
        
    def emit(self, event: JournalEvent):
        self.journal.book.emit(event) #type: ignore
        
    def eu2raw(self, eu: Any):
        if self.metric is not None and self.name is not None:
            self.emit(JournalEvent(self.name, self.metric, eu, source=JournalEvent.Sources.SOURCE_USER))
        return super().eu2raw(eu)
        
class MetricJournal(QObject):
    book = Signal(JournalEvent)

    def __init__(self, parent = None):
        super().__init__(parent )
        self.book.connect(self._journal) #type: ignore
        self._metrics: List[str] = []
        self._thread: QThread
        self._timer: QTimer

    @Slot(JournalEvent)
    def _journal(self, event: JournalEvent):
        pass

    @Slot()
    def flush(self):
        pass
    
    def register(self, id: str, metric: str):
        pass
    
    def factory(self)->Type[JournalFilter]:
        this = self
        class _JournalFilter(JournalFilter):
            def __init__(self, *, what: Property | None = None, next: Filter | None = None):
                super().__init__(this, what=what, next=next)
        return _JournalFilter
        
    @Slot()
    def start(self):
        log.info(f'Запуск журналирования: {self}')
        _timer = QTimer(self)
        _timer.timeout.connect(self.flush)
        _timer.start(60000)
        self._timer = _timer
        
    @Slot()
    def stop(self):
        if self._thread is not None:
            log.info('Останов журналирования: {self}')
            self._timer.stop()
            self._thread.quit( )

    def spawn(self):
        self._thread = _thread = QThread(QCoreApplication.instance())
        QCoreApplication.instance().aboutToQuit.connect(self.stop) #type: ignore
        _thread.started.connect(self.start)
        self.moveToThread(_thread)
        _thread.start( )

    def __repr__(self):
        return f"<{self.__class__.__name__}>"
