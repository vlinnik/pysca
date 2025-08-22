from typing import Any, List, Type
from .bindable import Property, Filter
from AnyQt.QtCore import QObject, QThread, pyqtSignal, pyqtSlot, QTimer,QCoreApplication

class JournalEvent:
    def __init__(self, item: str, metric: str, value: Any, **kwargs):
        self.value = value
        self.tags = kwargs
        self.item = item
        self.metric = metric

    def __repr__(self):
        return f"<JournalEvent {self.item} | {self.metric:.3f} | {self.value} | {self.tags}>"

class MetricFilter(Filter):
    def __init__(self, *, what: Property|None = None, next: Filter|None = None):
        super().__init__(what=what, next=next)
        self._metric:str | None = ''
        self.tags: List[str] = []
        
    @property
    def metric(self) -> str|None:
        return self._metric

    @metric.setter
    def metric(self, metric: str|None):
        self._metric = metric
        if self._next:
            self._next.config('metric', metric)

    @property
    def name(self) -> str:
        return self._prop.name

class MetricJournal(QObject):
    book = pyqtSignal(JournalEvent)

    def __init__(self, parent = None):
        super().__init__(parent )
        self.book.connect(self._journal)
        self._metrics: List[str] = []
        self._thread: QThread
        self._timer: QTimer

    @pyqtSlot(JournalEvent)
    def _journal(self, event: JournalEvent):
        pass
    
    def register(self,metric: str | None):
        pass
    
    def factory(self)->Type[MetricFilter]:
        return MetricFilter

    @pyqtSlot()
    def flush(self):
        pass
        
    @pyqtSlot()
    def start(self):
        _timer = QTimer(self)
        _timer.timeout.connect(self.flush)
        _timer.start(60000)
        self._timer = _timer
        
    @pyqtSlot()
    def stop(self):
        if self._thread is not None:
            self._timer.stop()
            self._thread.quit( )

    def spawn(self):
        self._thread = _thread = QThread(QCoreApplication.instance())
        QCoreApplication.instance().aboutToQuit.connect(self.stop)
        _thread.started.connect(self.start)
        self.moveToThread(_thread)
        _thread.start( )

