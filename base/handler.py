from py_expression_eval import Parser
import time
from typing import List

from subgraph.client import ResourceClient as SubgraphClient
from utils import send_alert


class CalculatedMetric:
    pass


class AlertRule:
    def __init__(self, level, name, message, formula, function):
        if not formula and not function:
            raise Exception('AlertRule should have either formula or function!')
        self.level = level
        self.name = name
        self.message = message
        self.function = function

        if formula:
            formula_parser = Parser()
            self.formula = formula_parser.parse(formula)
        else:
            self.formula = None

    def should_alert(self, calculated_metrics_dict):
        if self.formula and self.function:
            return (
                self.formula.evaluate(calculated_metrics_dict)
                or self.function(calculated_metrics_dict)
            )
        elif self.formula:
            return self.formula.evaluate(calculated_metrics_dict)
        elif self.function:
            return self.function(calculated_metrics_dict)


class BaseMonitoringHandler:
    name: str = 'name_of_entity_being_monitored'
    clients: List = [SubgraphClient(), ]
    metrics = []
    alert_rules: List[AlertRule] = []
    heartbeat: int  = 300   # seconds

    def calculate_metrics(self):
        raise NotImplementedError

    def alert(self):
        """Send alert notifications."""
        calculated_metrics = self.calculate_metrics()
        print('calculated_metrics!!', calculated_metrics)

        for alert_rule in self.alert_rules:
            for calc_metric in calculated_metrics:
                metric_values_dict = {
                    item['metric_name']: item['value']
                    for item in calc_metric['results']
                }
                # metric_values_dict = {
                #     'ovl_token_minted': 100,
                #     'ovl_token_minted__offset_5m': 50,
                # }
                # formula = 'ovl_token_minted - ovl_token_minted__offset_5m == 0'
                print('metric_values_dict', metric_values_dict)
                #  To-do: use enum to pass variables
                if alert_rule.should_alert(metric_values_dict):
                    print(f"SHOULD ALERT !!! {alert_rule.name}")
                    send_alert(
                        alert_rule.level,
                        alert_rule.name,
                        alert_rule.formula or alert_rule.function,
                        calc_metric['label'],
                    )

    def run(self):
        """Send alerts per heartbeat."""
        while True:
            self.alert()
            time.sleep(self.heartbeat)
