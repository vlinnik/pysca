from typing import Any, List, Type
from enum import IntEnum
from .bindable import Property, Filter
from .journal import MetricFilter
from AnyQt.QtCore import QObject, QThread, pyqtSignal, pyqtSlot, QTimer,QCoreApplication
from time import time

class EventSource(QObject):
    done = pyqtSignal(int)
    def __init__(self, trigger: 'EventTrigger', parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.done.connect(self._done)
        self._trigger = trigger
    
    @pyqtSlot(int)
    def _done(self,id:int):
        self._trigger.last_id = id
    

class Event:
    def __init__(self, message: str|None = None, time_from: int | None = None, tags: List[str] = [],source:EventSource | None = None,id:int|None = None):
        now = int(time() * 1000)
        self.id = id
        self.message = message
        self.tags = tags
        self.time_from = time_from or now
        self.time_to = now
        self.source = source

    def __repr__(self):
        return f"<Event {self.message} | {self.time_from} | {self.time_to} | {self.tags}>"

class EventTrigger(MetricFilter):
    class Levels(IntEnum):
        LEVEL_LOW = 1
        LEVEL_NORM = 2
        LEVEL_HIGH = 3
        LEVEL_CRITICAL = 4
    
    def __init__(self, *, what: Property | None = None, next: Filter | None = None):
        super().__init__(what=what, next=next)
        self.source = EventSource(self)
        self.last_id = None
        self.level: EventTrigger.Levels | None = None
        self._trigger = ''   #выражение которое должно выполниться чтобы событие создать
        self._groups = ''    #группа(ы) через запятую, аннотация получит UPPER_CASE с префиксом GROUP_
        self._text = 'Случилось что-то в {metric} при {item_id}={value}' #будет вычисляться через eval, можно использовать значение {value},{metric}
        self._continuous = False
        self._time_from: int

    @MetricFilter.metric.setter
    def metric(self,metric: str | None):
        super().metric = metric
        self._update_tags( )

    @property
    def event_trigger(self):
        return self._trigger

    @event_trigger.setter
    def event_trigger(self, code: str):
        self._trigger = code

    @property
    def event_text(self):
        return self._text
    @event_text.setter
    def event_text(self,text:str):
        self._text = text

    @property
    def event_groups(self):
        return self._groups
    @event_groups.setter
    def event_groups(self,text:str):
        self._groups = text
        self._update_tags( )
        
    @property
    def event_level(self)->'EventTrigger.Levels|None':
        return self.level

    @event_level.setter
    def event_level(self,level: 'EventTrigger.Levels|int|None'):
        try:
            self.level = EventTrigger.Levels(level)
            self._update_tags()
        except:
            pass
        
    @property
    def event_continuous(self)->bool:
        return self._continuous
    
    @event_continuous.setter
    def event_continuous(self,value: bool):
        self._continuous = value
        
    def _update_tags(self):
        tags = []
        for g in self._groups.split(','):
            g = g.strip()
            if g: tags.append(f'GROUP_{g}'.upper())
        if not tags:tags.append('GROUP_ALL')
        if self.level: self.tags.append(self.level.name)
        for tag in self.tags:
            if tag not in tags:
                tags.append(tag)
                
        tags.append(self.name)
        tags.append(self.metric)
        self.tags = tags

class MetricDairy(QObject):
    dairy = pyqtSignal(Event)

    def __init__(self, parent = None):
        super().__init__(parent )
        self.dairy.connect(self._event)
        self._metrics: List[str] = []
        self._thread:QThread

    @pyqtSlot(Event)
    def _event(self, event: Event):
        event.source.done.emit( -1 )
        pass
    
    def factory(self)->Type[MetricFilter]:
        return EventTrigger

    @pyqtSlot()
    def flush(self):
        pass
        
    @pyqtSlot()
    def start(self):
        pass

    @pyqtSlot()
    def stop(self):
        if self._thread is not None:
            self._thread.quit()

    def spawn(self):
        self._thread =_thread = QThread(QCoreApplication.instance())
        QCoreApplication.instance().aboutToQuit.connect(self.stop)
        _thread.started.connect(self.start)
        self.moveToThread(_thread)
        _thread.start( )
