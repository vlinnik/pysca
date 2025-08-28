from .events import MetricDairy,Event as AnnotationEvent
from .bindable import Expressions
from grafana_client import GrafanaApi, TokenAuth

class GrafanaAnnotations(MetricDairy):
    def __init__(self, ctx: Expressions, api_key: str, host:str='127.0.0.1',port=3000, parent = None):
        super().__init__( ctx, parent )
        self._grafana = GrafanaApi.from_url(
            url=f'http://{host}:{port}',
            credential=TokenAuth(token=api_key)
        )

    def _event(self, event: AnnotationEvent):
        if event.id is None:
            result = self._grafana.annotations.add_annotation(time_from=event.time_from,time_to=event.time_to,tags=event.tags,text=event.value)
            event.source.done.emit(result['id']) #type: ignore
        else:
            self._grafana.annotations.update_annotation(event.id, time_to = event.time_to,text = event.value,tags=event.tags)
