import pandas as pd

from base.handler import AlertRule, BaseMonitoringHandler
from subgraph.client import ResourceClient as SubgraphClient
from constants import (
    AVAILABLE_MARKETS,
    MINT_DIVISOR,
    ALL_MARKET_LABEL,
    MAP_MARKET_ID_TO_NAME,
)


def overmint(calculated_metrics):
    return calculated_metrics['ovl_token_minted'] > 0


class Handler(BaseMonitoringHandler):
    name = 'ovl_mint'
    alert_rules = [
        AlertRule(
            level='red',
            name='Overminting (Function)',
            message='Overmint happened!',
            formula=None,
            function=overmint,
        ),
        AlertRule(
            level='red',
            name='Overminting (Formula)',
            message='Overmint happened!',
            formula='ovl_token_minted > 0',
            function=None,
        ),
        # {
        #     'level': 'red',
        #     'name': 'overmint',
        #     # 'formula': 'ovl_token_minted - ovl_token_minted__offset_5m == 0',
        #     'function': overmint,
        #     'message': 'Overmint happened...',
        # },
        # {
        #     'level': 'red',
        #     'name': 'undermint',
        #     'formula': 'ovl_token_minted < -1000',
        # },
        # {
        #     'level': 'green',
        #     'name': 'sample_alert_green',
        #     'formula': 'ovl_token_minted - ovl_token_minted__offset_5m == 0',
        # },
        # {
        #     'level': 'orange',
        #     'name': 'sample_alert_orange',
        #     'formula': 'ovl_token_minted < 0'
        # },
        # {
        #     'level': 'orange',
        #     'name': 'no_change_in_5m',
        #     'formula': 'ovl_token_minted - ovl_token_minted == 0',
        # },
    ]

    def __init__(self):
        super().__init__()
        self.subgraph_client = SubgraphClient()
        self.kwargs = {
            'subgraph_client': SubgraphClient(),
        }

    def calculate_metrics(self):
        """
        Returns calculated metrics:

        Simplified: use tuple or enum
        calculated_metrics = {
            'ALL': (100, 50),
            'LINK / USD': (80, 120),
        }

        calculated_metrics = [
            {
                'label': 'ALL',
                'results': [
                    {
                        'metric_name': 'ovl_token_minted',
                        'value': 100,
                    },
                    {
                        'metric_name': 'ovl_token_minted__offset_5m',
                        'value': 50,
                    }
                ]
            },
            {
                'label': 'LINK / USD',
                'results': [
                    {
                        'metric_name': 'ovl_token_minted',
                        'value': 81,
                    },
                    {
                        'metric_name': 'ovl_token_minted__offset_5m',
                        'value': 120,
                    }
                ]
            }
        ]
        """
        all_positions = self.subgraph_client.get_all_positions()
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

        results_dict = {
            ALL_MARKET_LABEL: {
                'ovl_token_minted': mint_total,
                'ovl_token_minted__offset_5m': mint_total
            },
            **{
                MAP_MARKET_ID_TO_NAME[market_id]: {
                    'ovl_token_minted': mint_total_per_market[market_id] / MINT_DIVISOR,
                    'ovl_token_minted__offset_5m': mint_total_per_market[market_id] / MINT_DIVISOR,
                }
                for market_id in AVAILABLE_MARKETS
                if market_id in mint_total_per_market
            },
        }
        print('results_dict', results_dict)

        metric_names = ['ovl_token_minted', 'ovl_token_minted__offset_5m', ]
        results = [
            {
                'label': MAP_MARKET_ID_TO_NAME[market_id],
                'results': [
                    {
                        'metric_name': metric_name,
                        'value': results_dict[MAP_MARKET_ID_TO_NAME[market_id]][metric_name]
                    }
                    for metric_name in metric_names
                ]
            }
            for market_id in AVAILABLE_MARKETS
        ]
        print('results', results)
        return results
