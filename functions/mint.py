from base.handler import BaseMonitoringHandler, BaseMetric


class MintMonitoringHandler(BaseMonitoringHandler):
    def set_name(self):
        self.name = 'mint'

    def set_metrics(self):
        self.metrics = [
            BaseMetric('ovl_token_minted')
        ]
