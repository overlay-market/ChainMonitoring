from prometheus_client import Gauge

metrics = {}
metrics['mint_gauge'] = Gauge('ovl_token_minted', 'Number of OVL tokens minted', ['market'])
metrics['upnl_gauge'] = Gauge('upnl', 'Unrealised profit and loss', ['market'])
metrics['upnl_pct_gauge'] = Gauge('upnl_pct', 'Unrealised profit and loss (percent)', ['market'])
