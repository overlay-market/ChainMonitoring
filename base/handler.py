from py_expression_eval import Parser
import time
from typing import List

from subgraph.client import ResourceClient as SubgraphClient
from utils import send_alert


class BaseMonitoringHandler:
    name: str = 'name_of_entity_being_monitored'
    clients: List = [SubgraphClient(), ]
    metrics = []
    alert_rules = []
    heartbeat: int  = 300   # seconds

    def calculate_metrics(self):
        raise NotImplementedError

    def alert(self):
        """Send alert notifications."""
        calculated_metrics = self.calculate_metrics()
        print('calculated_metrics!!', calculated_metrics)

        formula_parser = Parser()
        for alert_rule in self.alert_rules:
            formula = formula_parser.parse(alert_rule['formula'])
            for calc_metric in calculated_metrics:
                metric_values_dict = {item['metric_name']: item['value'] for item in calc_metric['results']}
                should_alert = formula.evaluate(metric_values_dict)
                if should_alert:
                    send_alert(
                        alert_rule['level'],
                        alert_rule['name'],
                        alert_rule['formula'],
                        calc_metric['label'],
                    )

    def run(self):
        """Send alerts per heartbeat."""
        while True:
            self.alert()
            time.sleep(self.heartbeat)
