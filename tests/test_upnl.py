import math
import pandas as pd
import unittest
from prometheus_client import REGISTRY


from constants import ALL_MARKET_LABEL
from metrics.upnl import set_metrics


INITIAL_LIVE_POSITIONS_DF = pd.DataFrame([
    {
        'timestamp': '1694434146',
        'collateral': 0.059919,
        'id': '0x833ba1a942dc6d33bc3e6959637ae00e0cdcb20b-0xe5',
        'position.currentOi': 0.019513225671706737,
        'position.fractionUnwound': 0.0,
        'owner.id': '0x85f66dbe1ed470a091d338cfc7429aa871720283',
        'market': '0x833ba1a942dc6d33bc3e6959637ae00e0cdcb20b',
        'position_id': 229,
        'collateral_rem': 0.059919,
        'value': 0.0619529498953552,
        'upnl': 0.0020339498953552,
        'upnl_pct': 0.033944990659977636
    },
    {
        'timestamp': '1694398139',
        'collateral': 0.38,
        'id': '0xc28350047d006ed387b0f210d4ea3218137a8a38-0x3c2',
        'position.currentOi': 1.4780077650657e-05,
        'position.fractionUnwound': 0.0,
        'owner.id': '0x6331351a6ee4e4684bdce0d622397a806c06d163',
        'market': '0xc28350047d006ed387b0f210d4ea3218137a8a38',
        'position_id': 962,
        'collateral_rem': 0.38,
        'value': 0.38336056223125,
        'upnl': 0.003360562231249975,
        'upnl_pct': 0.008843584819078881
    },
    {
        'timestamp': '1694184076',
        'collateral': 0.817122,
        'id': '0x7c65c99ba1edfc94c535b7aa2d72b0f7357a676b-0x1d',
        'position.currentOi': 0.019277535407519947,
        'position.fractionUnwound': 0.0,
        'owner.id': '0x42e372d3ab3ac53036997bae6d1ab77c2ecd64b3',
        'market': '0x7c65c99ba1edfc94c535b7aa2d72b0f7357a676b',
        'position_id': 29,
        'collateral_rem': 0.817122,
        'value': 0.8585595602059759,
        'upnl': 0.04143756020597589,
        'upnl_pct': 0.05071159533824311
    },
    {
        'timestamp': '1694098372',
        'collateral': 0.3,
        'id': '0xc28350047d006ed387b0f210d4ea3218137a8a38-0x3c1',
        'position.currentOi': 4.6664547777814e-05,
        'position.fractionUnwound': 0.0,
        'owner.id': '0x143b5d7e1a11b5dc301d97a51264eb73dd5a37ec',
        'market': '0xc28350047d006ed387b0f210d4ea3218137a8a38',
        'position_id': 961,
        'collateral_rem': 0.3,
        'value': 0.2784120291988138,
        'upnl': -0.021587970801186185,
        'upnl_pct': -0.07195990267062062
    },
    {
        'timestamp': '1694066759',
        'collateral': 10.0,
        'id': '0x02e5938904014901c96f534b063ec732ea3b48d5-0x154',
        'position.currentOi': 4.094339038344929,
        'position.fractionUnwound': 0.0,
        'owner.id': '0xf9107317b0ff77ed5b7adea15e50514a3564002b',
        'market': '0x02e5938904014901c96f534b063ec732ea3b48d5',
        'position_id': 340,
        'collateral_rem': 10.0,
        'value': 7.736257239478319,
        'upnl': -2.263742760521681,
        'upnl_pct': -0.2263742760521681
    }
])


class TestUpnlMetric(unittest.TestCase):

    def test_non_empty_live_positions(self):
        set_metrics(INITIAL_LIVE_POSITIONS_DF)
        upnl_avax =  REGISTRY.get_sample_value(
            'upnl',
            labels={'market': 'AVAX / USD'}
        )
        print('upnl_avax', upnl_avax)
        self.assertEqual(0.0020339498953552, upnl_avax)
        
        upnl_wbtc =  REGISTRY.get_sample_value(
            'upnl',
            labels={'market': 'WBTC / USD'}
        )
        print('upnl_wbtc', upnl_wbtc)
        self.assertEqual(-0.01822740856993621, upnl_wbtc)

        upnl_cryptovol =  REGISTRY.get_sample_value(
            'upnl',
            labels={'market': 'Crypto Volatility Index'}
        )
        print('upnl_cryptovol', upnl_cryptovol)
        self.assertEqual(0.04143756020597589, upnl_cryptovol)

        upnl_link =  REGISTRY.get_sample_value(
            'upnl',
            labels={'market': 'LINK / USD'}
        )
        print('upnl_link', upnl_link)
        self.assertEqual(-2.263742760521681, upnl_link)

        upnl_allmarket =  REGISTRY.get_sample_value(
            'upnl',
            labels={'market': ALL_MARKET_LABEL}
        )
        print('upnl_allmarket', upnl_allmarket)
        self.assertEqual(
            upnl_avax + upnl_wbtc + upnl_cryptovol + upnl_link,
            upnl_allmarket
        )

    def test_no_live_positsions(self):
        set_metrics(pd.DataFrame([]))
        upnl_allmarket =  REGISTRY.get_sample_value(
            'upnl',
            labels={'market': ALL_MARKET_LABEL}
        )
        print('upnl_allmarket', upnl_allmarket)
        self.assertTrue(math.isnan(upnl_allmarket))
