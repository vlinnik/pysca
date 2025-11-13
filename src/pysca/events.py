from typing import Any, List, Type,Dict 
from enum import IntEnum
from .bindable import Property, Filter, Expressions
from .journal import MetricFilter
from qtpy.QtCore import QObject, QThread, Signal, Slot, QCoreApplication
from time import time

class EventSource(QObject):
    done = Signal(int) 
    def __init__(self, trigger: 'EventTrigger', parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.done.connect(self._done) #type: ignore
        self._trigger = trigger
    
    @Slot(int)
    def _done(self,id:int):
        self._trigger.last_id = id
        self._trigger._active = True

class Event:
    def __init__(self, item: str, value: Any, time_from: int | None = None, tags: List[str] = [],source:EventSource | None = None,id:int|None = None):
        now = int(time() * 1000)
        self.id = id
        self.value = value
        self.tags = tags
        self.time_from = time_from or now
        self.time_to = now
        self.source = source
        self.item = item

    def __repr__(self):
        return f"<Event {self.value} | {self.time_from} | {self.time_to} | {self.tags}>"

class EventTrigger(MetricFilter):
    class Levels(IntEnum):
        LEVEL_SILENT = 0
        LEVEL_NORMAL = 1
        LEVEL_LOW = 2
        LEVEL_HIGH = 3
        LEVEL_CRITICAL = 4
    
    def __init__(self, target: 'MetricDairy', *, what: Property | None = None, next: Filter | None = None):
        super().__init__(what=what, next=next)
        self.source = EventSource(self)
        self.last_id: int 
        self.level: EventTrigger.Levels = ...
        self.tags = []
        self._trigger = ''   #выражение которое должно выполниться чтобы событие создать
        self._groups = ''    #группа(ы) через запятую, аннотация получит UPPER_CASE с префиксом GROUP_
        self._text = 'Случилось что-то в {metric} при {item_id}={value}' #будет вычисляться через eval, можно использовать значение {value},{metric}
        self._continuous = False
        self._time_from: int
        self._locals:Dict[str,Any] = { 'value':None, 'self':self._prop , 'metric': None }
        self._target = target
        self._expression: Expressions.Expression = ...
        self._state = None #
        self._message:str
        self._active = False

    def _trigger_changed(self,value: Any):
        self._state = value
        if self._state == True:
            self._message = eval(f"f'{self.event_text}'",self._expression,self._locals)
            annotation = Event(self.name, value=self._message,tags=self.tags,source=self.source)
            self._time_from = int(annotation.time_from)
            self.emit(annotation)
        else:
            if self.event_continuous and self._active:
                self.emit(Event(item = self.name, id=self.last_id, time_from=self._time_from,value=self._message,tags=self.tags))
            self._active = False
            
    def emit(self,event: Event):
        if self._target is not None:
            self._target.dairy.emit(event) #type: ignore

    def raw2eu(self, raw: Any):
        eu = super().raw2eu(raw)
        try:
            self._locals['value'] = eu
            if not self._initialized:
                self._locals['metric'] = self.metric
                self._expression = self._target._ctx.create( bool, self._trigger,self._locals)
                self._expression.bind(self._trigger_changed)
                self._target.register(self.name,self.metric,self.tags)
                self._initialized = True
                                
            if self._expression is not Ellipsis:
                self._state = self._expression.evaluate( )
            else:
                self._state = bool(self._locals['value'])
                self._trigger_changed(eu)
        except Exception as e:
            pass

        return eu
    
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
        self._update_metric( )
        
    @property
    def event_level(self)->'EventTrigger.Levels|None':
        return self.level

    @event_level.setter
    def event_level(self,level: 'EventTrigger.Levels|int|None'):
        try:
            self.level = EventTrigger.Levels(level)
            self._update_metric( )
        except:
            pass
        
    @property
    def event_continuous(self)->bool:
        return self._continuous
    
    @event_continuous.setter
    def event_continuous(self,value: bool):
        self._continuous = value
        
    def _update_metric(self):
        tags = []
        for g in self._groups.split(','):
            g = g.strip()
            if g: tags.append(f'GROUP_{g}'.upper())
        for tag in self.tags:
            if tag not in tags:
                tags.append(tag)
        if not tags:tags.append('GROUP_ALL')
        if self.level is not Ellipsis and self.level.name not in tags:
            tags.append(self.level.name)
                
        self.tags = tags
        
class MetricDairy(QObject):
    dairy = Signal(Event)

    def __init__(self, ctx: Expressions, parent = None):
        super().__init__( parent )
        self.dairy.connect(self._event) #type: ignore
        self._metrics: List[str] = []
        self._thread:QThread
        self._ctx: Expressions = ctx

    @Slot(Event)
    def _event(self, event: Event):
        # event.source.done.emit( -1 )
        pass

    def register(self, id: str, metric: str, tags: List[str], **kwargs):
        pass
    
    def factory(self)->Type[MetricFilter]:
        this = self
        class _EventTrigger(EventTrigger):
            def __init__(self, *, what: Property | None = None, next: Filter | None = None):
                super().__init__(what=what, next=next, target=this)
        return _EventTrigger

    @Slot()
    def flush(self):
        pass
        
    @Slot()
    def start(self):
        pass

    @Slot()
    def stop(self):
        if self._thread is not None:
            self._thread.quit()

    def spawn(self):
        self._thread =_thread = QThread(QCoreApplication.instance())
        QCoreApplication.instance().aboutToQuit.connect(self.stop) #type: ignore
        _thread.started.connect(self.start)
        self.moveToThread(_thread)
        _thread.start( )    