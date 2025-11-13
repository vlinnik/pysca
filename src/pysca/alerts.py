from typing import Any, List, Type,Callable,Dict
from enum import IntEnum
from .bindable import Property, Filter, Expressions
from .journal import MetricFilter
from qtpy.QtCore import QObject, QThread, Signal, Slot, QTimer,QCoreApplication
from time import time
from queue import Queue

class Alert:
    """Описание тревоги. Уже произошла, и ее нужно записать 
    """
    def __init__(self, item: str, value: Any, time_from: int | None = None, tags: Dict[str,Any] = {}):
        now = int(time() * 1000)
        self.item = item
        self.value = value
        self.tags = tags
        self.time_from = time_from or now

    def __repr__(self):
        return f"<Alert {self.value} | {self.time_from} | {self.tags}>"
    
class AlertTimer(QObject):
    def __init__(self, target: 'AlertsJournal',  parent: QObject | None = None ) -> None:
        super().__init__(parent)
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._timeout)
        self._target = target
        self._pending: Alert

    def emit(self,alert: Alert | None):
        if alert is not None:
            self._pending = alert
            if self._timer.interval()>0:
                self._timer.start()
            else:
                self._timeout( )
        else:
            self._timer.stop( )
        
    @Slot()
    def _timeout(self):
        self._target.dairy.emit( self._pending )
        
    @property
    def delay(self):
        return self._timer.interval()
    
    @delay.setter
    def delay(self,msec: int):
        self._timer.setInterval(msec)
        

class AlertRule(MetricFilter):
    """Описания условия тревоги о обработка изменения связанных переменных
    """
    
    class Levels(IntEnum):
        LEVEL_SILENT = 0
        LEVEL_LOW = 1
        LEVEL_ELEVATED = 2
        LEVEL_SEVERE = 3
        LEVEL_CRITICAL = 4
    
    def __init__(self, target: 'AlertsJournal',  *, what: Property | None = None, next: Filter | None = None):
        super().__init__(what=what, next=next)
        self.level: AlertRule.Levels = AlertRule.Levels.LEVEL_SILENT
        self.tags={ }
        self._expression: Expressions.Expression = ...
        self._trigger = ''   #выражение которое должно выполниться чтобы авария выполнилась
        self._groups = ''    #группа(ы) через запятую, аннотация получит UPPER_CASE с префиксом GROUP_
        self._text = 'Случилось что-то в {metric} при {item_id}={value}' #будет вычисляться через eval, можно использовать значение {value},{metric}
        self._time_from: int
        self._locals = {'value':None, 'self':self._prop, 'metric': '' }
        self._target = target
        self._state = None #
        self._delay = 0
        self._timer = AlertTimer( target )

    def _trigger_changed(self,value: Any):
        if self._state and not value:
            self._target.queue.put(self.name)
        self._state = value
        if self._state == True:
            self.emit( Alert(self.name, self._locals['value'],tags = self.tags ))
        else:
            self.emit( None )

    def emit(self,alert: Alert|None):
        self._timer.emit(alert)

    def raw2eu(self, raw: Any):
        eu = super().raw2eu(raw)
        try:
            self._locals['value'] = eu
            if not self._initialized:
                self._locals['metric'] = self.metric
                self._locals['self'] = self._prop
                self.tags = { 'item_id':self.name, 'group': 'GLOBAL' , 'level':self.alert_level.name}
                self._expression = self._target._ctx.create( bool, self._trigger,self._locals)
                self._expression.bind(self._trigger_changed)
                self._target.register(self.name,self.metric)
                self._initialized = True
                
            if self._expression is not Ellipsis:
                self._state = self._expression.evaluate( )
            else:
                self._state = bool(eu)
                self._trigger_changed(eu)
        except Exception as e:
            pass

        return eu
    
    @property
    def alert_trigger(self):
        return self._trigger

    @alert_trigger.setter
    def alert_trigger(self, code: str):
        self._trigger = code

    @property
    def alert_groups(self)->List[str]:
        return [g.strip( ) for g in self._groups.split(',')]
    
    @alert_groups.setter
    def alert_groups(self,text:str):
        self._groups = text
        self._update_metric( )
        
    @property
    def alert_level(self)->'AlertRule.Levels':
        return self.level

    @alert_level.setter
    def alert_level(self,level: 'AlertRule.Levels|int'):
        try:
            self.level = AlertRule.Levels(level)
            self._update_metric(  )
        except:
            pass
        
    @property
    def alert_delay(self)->int:
        return self._timer.delay
    
    @alert_delay.setter
    def alert_delay(self,value: int):
        self._timer.delay = value
        
    def _update_metric(self):
        try:
            self._locals['metric'] = self.metric
        except:
            pass
        
class AlertsJournal(QObject):
    dairy = Signal(Alert)

    def __init__(self, ctx: Expressions, parent = None):
        super().__init__( parent )
        self.dairy.connect(self._alert) #type: ignore
        self.queue = Queue( )   #очередь вышедших 
        self._metrics: Dict[str,Alert] = { }
        self._thread:QThread
        self._ctx: Expressions = ctx

    @Slot(Alert)
    def _alert(self, alert: Alert):
        if alert.item not in self._metrics:
            self._metrics[alert.item] = alert
            
    def register(self, id: str, metric: str):
        pass
    
    def factory(self)->Type[MetricFilter]:
        this = self
        class _AlertRule(AlertRule):
            def __init__(self, *, what: Property | None = None, next: Filter | None = None):
                super().__init__(this, what=what, next=next)
        return _AlertRule

    @Slot()
    def flush(self):
        while not self.queue.empty():
            id = self.queue.get_nowait( )
            if id in self._metrics:
                self._metrics.pop(id)
                
        for id,alert in self._metrics.items():
            self._alert(alert)
        
    @Slot()
    def start(self):
        _timer = QTimer(self)
        _timer.timeout.connect(self.flush)
        _timer.start(60000)
        self._timer = _timer

    @Slot()
    def stop(self):
        if self._thread is not None:
            self._timer.stop()
            self._thread.quit( )

    def spawn(self):
        self._thread =_thread = QThread(QCoreApplication.instance())
        QCoreApplication.instance().aboutToQuit.connect(self.stop) #type: ignore
        _thread.started.connect(self.start)
        self.moveToThread(_thread)
        _thread.start( )    