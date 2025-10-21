from typing import Any,Callable,Dict

class Monitor():
    def __init__(self,evaluate: Callable[[str,Dict[str, Any]],None],*,monitorAction: str='',monitorNoneAction:str='',comment:str='', subject: Any=None, **kwargs) -> None:
        self._value: Any = None
        self.comment: str = comment
        self.action:str = monitorAction
        self.invalidAction:str = monitorNoneAction
        self.exec = evaluate
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