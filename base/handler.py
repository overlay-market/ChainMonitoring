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
        """
        Determines whether an alert should be triggered based on the provided calculated metrics.

        Args:
            self: The instance of the class containing the alert logic.
            calculated_metrics_dict (dict): A dictionary containing the calculated metrics needed for evaluation.

        Returns:
            bool: True if an alert should be triggered, False otherwise.

        Note:
            The method checks for the presence of a formula and/or a function to decide whether to trigger an alert.
            If both a formula and a function are present, the result is the logical OR of their evaluations.
            If only a formula or a function is present, the result is the evaluation of the respective one.

        Example:
            Consider an instance of the class with a formula and a function:
            ```
            should_trigger = alert_instance.should_alert(calculated_metrics)
            ```
        """
        if self.formula and self.function:
            return (
                self.formula.evaluate(calculated_metrics_dict)
                or self.function(calculated_metrics_dict)
            )
        elif self.formula:
            return self.formula.evaluate(calculated_metrics_dict)
        elif self.function:
            return self.function(calculated_metrics_dict)

    def send_alert(self, metric_label):
        send_alert(self, metric_label)


class BaseMonitoringHandler:
    name: str = 'name_of_entity_being_monitored'
    clients: List = [SubgraphClient(), ]
    metrics = []
    alert_rules: List[AlertRule] = []
    heartbeat: int  = 300   # seconds

    def __init__(self, name, clients, alert_rules, heartbeat):
        self.name = name
        self.clients = clients
        self.alert_rules = alert_rules
        self.heartbeat = heartbeat

    def calculate_metrics(self):
        raise NotImplementedError

    def alert(self) -> None:
        """
        Send alert notifications based on the defined alert rules and calculated metrics.

        Returns:
            None

        Note:
            The method calculates metrics, iterates through the defined alert rules, and checks whether each rule
            should trigger an alert based on the calculated metric values. If an alert should be triggered, the
            alert rule's `send_alert` method is called with the corresponding metric label.

        Example:
            Consider an instance of the AlertManager class:
            ```
            alert_manager = AlertManager(alert_rules=[alert_rule_1, alert_rule_2, ...])
            alert_manager.alert()
            ```
            This will trigger alerts for any alert rule that evaluates to True based on the calculated metrics.
        """
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
                    alert_rule.send_alert(calc_metric['label'])

    def run(self):
        """Send alerts per heartbeat."""
        while True:
            self.alert()
            time.sleep(self.heartbeat)
