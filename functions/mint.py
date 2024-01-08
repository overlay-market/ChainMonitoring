import pandas as pd

from base.handler import BaseMonitoringHandler, Metric
from subgraph.client import ResourceClient as SubgraphClient
from constants import (
    AVAILABLE_MARKETS,
    MINT_DIVISOR,
    ALL_MARKET_LABEL,
    MAP_MARKET_ID_TO_NAME
)


class MintMetric(Metric):
    name = 'ovl_token_minted'
    labels = ['market', ]

    def calculate(subgraph_client):
        all_positions = subgraph_client.get_all_positions()
        if (not len(all_positions)):
            return
        all_positions_df = pd.DataFrame(all_positions)
        all_positions_df['mint'] = all_positions_df['mint'].apply(int)
        all_positions_df[['market', 'position_id']] = all_positions_df['id'].str.split(
            '-', expand=True)
        all_positions_df.drop(
            all_positions_df[~all_positions_df['market'].isin(AVAILABLE_MARKETS)].index,
            inplace = True
        )
        mint_total = all_positions_df['mint'].sum() / MINT_DIVISOR
        mint_total_per_market_df = all_positions_df.groupby(by='market')['mint'].sum().reset_index()
        mint_total_per_market = dict(
            zip(mint_total_per_market_df['market'], mint_total_per_market_df['mint']))

        result = {
            ALL_MARKET_LABEL: mint_total,
            **{
                MAP_MARKET_ID_TO_NAME[market_id]: mint_total_per_market[market_id] / MINT_DIVISOR
                for market_id in AVAILABLE_MARKETS
                if market_id in mint_total_per_market
            },
        }
        print('result', result)
        return result


class Handler(BaseMonitoringHandler):

    name = 'ovl_mint'
    metrics = [MintMetric, ]
    alert_rules = {
        'red': {
            'overmint': 'ovl_token_minted > 100',
        },
        'green': {
            'test_alert_green_1': 'ovl_token_minted <= 100 and ovl_token_minted >= 0',
            'test_alert_green_2': 'ovl_token_minted <= 100 and ovl_token_minted >= 0',
        },
        'orange': {
            'test_alert_orange_1': 'ovl_token_minted < 0',
            'test_alert_orange_2': 'ovl_token_minted == 0',
        },
    }
    def __init__(self):
        super().__init__()
        self.kwargs = {
            'subgraph_client': SubgraphClient(),
        }
