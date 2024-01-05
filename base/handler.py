from subgraph.client import ResourceClient as SubgraphClient
from typing import List
from utils import send_alert

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
    heartbeat: int  # seconds

    def __init__(self) -> None:
        self.set_name()
        self.set_clients()
        self.set_metrics()

    def set_name(self):
        pass

    def set_metrics(self):
        pass
        
    def calculate_metrics(self):
        # return {
        #     [{
        #         'name': metric.name,
        #         'value': metric.calculate(**self.kwargs)
        #     }]
        #     for metric in self.metrics
        # }
        return {
            metric.name: metric.calculate(**self.kwargs)
            for metric in self.metrics
        }

    def alert(self):
        # Calculate metrics
        calculated_metrics = self.calculate_metrics()
        print('calculated_metrics!!', calculated_metrics)

        # calculated_metrics = {
        #     'ovl_token_minted': {
        #         'ALL': -805.7973282971279,
        #         'LINK / USD': -94.96272053405455,
        #         'SOL / USD': -167.26353028247604,
        #         'APE / USD': -69.12437849497073,
        #         'Crypto Volatility Index': 240.00793524473616,
        #         'AVAX / USD': -84.59636423287223,
        #         'MATIC / USD': -100.97709948693603,
        #         'WBTC / USD': -528.8811705105545
        #     }
        # }

        for alert_level, rule in self.alert_rules.items():
            for rule_name, rule_func in rule.items():
                for metric_name, metric in calculated_metrics.items():
                    for metric_label, metric_value in metric.items():
                        print('alert_level', alert_level)
                        print('rule_name', rule_name)
                        print('metric_name', metric_name)
                        print('metric_label', metric_label)
                        should_alert = rule_func(metric_value)
                        print('should_alert', should_alert)
                        print('=================================')

                        if should_alert:
                            send_alert(
                                alert_level,
                                rule_name,
                                metric_name,
                                metric_label
                            )

    def run(self):
        # TO-DO: run alert function every heartbeat sec
        return
