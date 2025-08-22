from typing import Any
from .bindable import Property, Filter
from .events import EventTrigger,MetricDairy,Event as AnnotationEvent
from grafana_client import GrafanaApi, TokenAuth

class _AnnotationTrigger(EventTrigger):
    def __init__(self, target: MetricDairy,  *, what: Property|None = None, next: Filter|None = None):
        super().__init__(what=what, next=next)
        self._target = target
    
    def raw2eu(self, raw: Any):
        eu = super().raw2eu(raw)
        try:
            locs = {'value' : eu, 'metric':self.metric,'item_id':self.name,'self' : self._prop}
            ret = eval(self._trigger, None, locs)
            text = eval(f"f'{self.event_text}'",None,locs)
            if ret == True:
                annotation = AnnotationEvent(message=text,tags=self.tags,source=self.source)
                self._time_from = int(annotation.time_from)
                self._target.dairy.emit(annotation)
            else:
                if self.event_continuous and self.last_id is not None:
                    self._target.dairy.emit(AnnotationEvent(id=self.last_id, time_from=self._time_from,message=text,tags=self.tags))
                self.last_id = None
        except Exception as e:
            pass

        return eu

class GrafanaAnnotations(MetricDairy):
    def __init__(self,api_key:str, host:str='127.0.0.1',port=3000, parent = None):
        super().__init__( parent )
        self._grafana = GrafanaApi.from_url(
            url=f'http://{host}:{port}',
            credential=TokenAuth(token=api_key)
        )

    def factory(self) -> EventTrigger:
        this = self
        class AnnotationTrigger(_AnnotationTrigger):
            def __init__(self, *, what: Property | None = None, next: Filter | None = None):
                super().__init__(this, what=what, next=next)
        return AnnotationTrigger
    
    def _event(self, event: AnnotationEvent):
        if event.id is None:
            result = self._grafana.annotations.add_annotation(time_from=event.time_from,time_to=event.time_to,tags=event.tags,text=event.message)
            event.source.done.emit(result['id'])
        else:
            self._grafana.annotations.update_annotation(event.id, time_to = event.time_to,text = event.message,tags=event.tags)
