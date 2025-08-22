from .journal import MetricJournal,JournalEvent,MetricFilter
from enum import IntEnum
from typing import Any, List, Type
from .__logging import console
from .bindable import Property, Filter
from AnyQt.QtCore import QObject, QThread, pyqtSignal, pyqtSlot, QTimer
from opentsdb import TSDBClient, Gauge
from opentsdb.metrics import Metric
import socket

_log = console('opentsdb')

class _OpenTSDBFilter(MetricFilter):
    class Sources(IntEnum):
        SOURCE_SYSTEM = 1
        SOURCE_USER = 2

    def __init__(self, journal: 'OpenTSDBJournal', *, what: Property|None = None, next: Filter|None = None):
        super().__init__( what=what, next=next)
        self.journal:OpenTSDBJournal = journal
        self.tags: List[str] = ['source', 'item_id']

    def raw2eu(self, raw: Any):
        eu = super().raw2eu(raw)
        
        if self.metric is None:
            self.metric = self._prop.address
        if self.journal and self.metric is not None:
            self.journal.book.emit(JournalEvent(
                self.name, self.metric, eu, source=_OpenTSDBFilter.Sources.SOURCE_SYSTEM, item_id=self.name))
        return eu
    
    @MetricFilter.metric.setter
    def metric(self,metric: str | None):
        self.journal.register(self.name, metric, self.tags)
        super().metric = metric
        

    def eu2raw(self, eu: Any):
        if self.metric is not None:
            self.journal.book.emit(JournalEvent(
                self.name, self.metric, eu, source=_OpenTSDBFilter.Sources.SOURCE_USER, item_id=self.name))
        return super().eu2raw(eu)


class OpenTSDBJournal(MetricJournal):
    def __init__(self,host:str='127.0.0.1',port=4242, parent = None):
        super().__init__( parent )
        self._metrics: List[str] = []
        self._tsdb = TSDBClient(host, port, static_tags={'host': socket.gethostname(), 'app': 'pysca-hmi'})

    def metric(self,item: str)->Metric|None:
        try:
            return getattr(self._tsdb, item)
        except AttributeError:
            return None

    def _journal(self, event: JournalEvent):
        try:
            metric = self.metric(event.item)
            if metric is None: raise RuntimeError(f'метрика {event.item} не найдена')
            tag_values = []
            for tag in metric.tag_names:
                if tag in event.tags:
                    tag_values.append(event.tags[tag])
                else:
                    tag_values.append(None)
            metric.tags(*tag_values)

            if event.value is not None:
                metric.set(event.value)
        except Exception as e:
            _log.error(e)
            
    def factory(self) -> MetricFilter:
        this = self
        class OpenTSDBFilter(_OpenTSDBFilter):
            def __init__(self, *, what: Property | None = None, next: Filter | None = None):
                super().__init__(this, what=what, next=next)
        return OpenTSDBFilter

    def register(self, id: str, metric: str|None, tags: List[str], repeat=True):
        if hasattr(self._tsdb, id):
            delattr(self._tsdb, id)
        
        if id in self._metrics:
            self._metrics.remove(id)

        if metric is not None:
            setattr(self._tsdb, id, Gauge(metric, tags, optional_tags=True))
            if repeat == True and id not in self._metrics:
                self._metrics.append(id)

    def flush(self):
        for id in self._metrics:
            try:
                metric: Metric | None = self.metric(id)
                if metric is not None:
                    metric.tags(_OpenTSDBFilter.Sources.SOURCE_SYSTEM, id)
                    metric.set(metric.value)
            except Exception as e:
                pass
