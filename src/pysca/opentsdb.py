from pysca.bindable import Expressions
from .journal import MetricJournal, JournalEvent
from .alerts import AlertsJournal, Alert
from .__logging import console
from typing import List
from opentsdb import TSDBClient, Gauge
from opentsdb.metrics import Metric
import socket

_log = console('opentsdb')

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
            
    def register(self, id: str, metric: str):
        if hasattr(self._tsdb, id):
            delattr(self._tsdb, id)
        
        if id in self._metrics:
            self._metrics.remove(id)

        if metric is not None:
            setattr(self._tsdb, id, Gauge(metric, ['source','item_id'], optional_tags=True))
            if id not in self._metrics:
                self._metrics.append(id)

    def flush(self):
        for id in self._metrics:
            try:
                metric: Metric | None = self.metric(id)
                if metric is not None:
                    metric.tags(JournalEvent.Sources.SOURCE_SYSTEM, id)
                    metric.set(metric.value)
            except Exception as e:
                pass

class OpenTSDBAlerts(AlertsJournal):
    def __init__(self, ctx: Expressions, host:str='127.0.0.1',port=3000, parent = None):
        super().__init__( ctx, parent )
        self._tsdb = TSDBClient(host, port, static_tags={'host': socket.gethostname(), 'app': 'pysca-hmi'})

    def metric(self,item: str)->Metric|None:
        try:
            return getattr(self._tsdb, item)
        except AttributeError:
            return None

    def _alert(self, alert: Alert):
        super()._alert(alert)
        try:
            metric = self.metric(alert.item)
            if metric is None: raise RuntimeError(f'метрика {alert.item} не найдена')
            if alert.value is not None:
                tag_values = []
                for tag in metric.tag_names:
                    if tag in alert.tags:
                        tag_values.append(alert.tags[tag])
                    else:
                        tag_values.append(None)
                        
                metric.tags(*tag_values)
                metric.set(alert.value)
        except Exception as e:
            _log.error(e)
    
    def register(self, id: str, metric: str):
        if hasattr(self._tsdb, id):
            delattr(self._tsdb, id)
        
        if metric is not None:
            setattr(self._tsdb, id, Gauge(f'{metric}.alerts', ['item_id','group','level'] , optional_tags=True))
            if id not in self._metrics:
                self._metrics.append(id)    