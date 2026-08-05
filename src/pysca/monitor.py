from typing import Any,Callable,Dict

class Monitor():
    """Класс для вычисления/выполнения кода по условиям
    
    К переменной(Property) можно можно прикрепить несколько Monitor (Property.monitor = Monitor), после этого 
    если переменная при изменении вызывает Monitor.__call__(<новое значение>). Где происходит обработка нового 
    значения. 
    
    если <новое значение> is not None то выполняется код из monitorAction иначе monitorNoneAction
    в контексте выполнения кода доступны переменные value & old_value
    
    Один монитор настраивается через конфигурационную базу.
    """
    def __init__(self,execute: Callable[[str,Dict[str, Any]],None],evaluate: Callable[[str,Dict[str, Any]],Any],*,monitorAction: str='',monitorNoneAction:str='',monitorCondition:str='',monitorConditionalAction:str='',comment:str='', subject: Any=None, **kwargs) -> None:
        self._value: Any = None
        self.comment: str = comment
        self.action:str = monitorAction
        self.invalidAction:str = monitorNoneAction
        self.condition: str = monitorCondition
        self.conditionAction: str = monitorConditionalAction
        self.exec = execute
        self.eval = evaluate
        self.user_ctx = kwargs
        self.subject = subject
    
    def __call__(self,value:Any, *_,user: bool=False, **kwargs):
        ctx = dict( comment=self.comment,this=self, self=self.subject, **self.user_ctx, **kwargs )
        if value is None and self.invalidAction:
            ctx.update( dict(value=value,old_value = self._value) )
            self.exec(self.invalidAction,ctx)
        elif value is not None:
            ctx.update( dict(value=value,old_value=self._value)  )
            self.exec(self.action,ctx)
        if self._value!=value:
            self._value = value
            if self.condition and self.eval(self.condition,ctx)==True:
                self.exec(self.conditionAction,ctx)