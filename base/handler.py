from typing import List
from subgraph.client import ResourceClient as SubgraphClient
from math import nan

class BaseResourceClient:
    name = ''


class Metric:
    name = 'name_of_metric'
    labels = []

    def calculate(self, **kwargs):
        raise NotImplementedError


class AlertRule:
    name = 'name_of_alert_rule'
    metric: Metric
    send_notifications: bool = True


class BaseMonitoringHandler:
    name: str = 'name_of_entity_being_monitored'
    clients: List = [SubgraphClient(), ]
    metrics: List[Metric] = []
    alert_rules: List[AlertRule] = []

    def __init__(self) -> None:
        self.set_name()
        self.set_clients()
        self.set_metrics()

    def set_name(self):
        pass

    def set_metrics(self):
        pass
        
    def calculate_metrics(self):
        return [
            {'name': metric.name, 'value': metric.calculate(**self.kwargs)}
            for metric in self.metrics
        ]
