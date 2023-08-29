from prometheus_client import Gauge

metrics = {
   'mint_gauge': Gauge(
        'ovl_token_minted',
        'Number of OVL tokens minted',
        ['market']
    ),
   'upnl_gauge': Gauge(
        'upnl',
        'Unrealised profit and loss',
        ['market']
    ),
   'collateral_rem_gauge': Gauge(
        'collateral_rem',
        'Collateral',
        ['market']
    ),
   'upnl_pct_gauge': Gauge(
        'upnl_pct',
        'Unrealised profit and loss (Percentage)',
        ['market']
    ),
}
