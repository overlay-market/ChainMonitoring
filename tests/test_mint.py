import datetime
import math
import time
import unittest

from unittest.mock import MagicMock

from prometheus_client import REGISTRY
from metrics.mint import query_single_time_window, initialize_metrics, query_mint
from constants import (
    ALL_MARKET_LABEL,
    MINT_DIVISOR,
    QUERY_INTERVAL
)

INITIAL_POSITIONS = [
    {
        "id": "0x02e5938904014901c96f534b063ec732ea3b48d5-0x02",
        "createdAtTimestamp": "1693633260",
        "mint": 1 * MINT_DIVISOR,
        "market": {
            "id": "0x02e5938904014901c96f534b063ec732ea3b48d5"
        }
    },
    {
        "id": "0x1067b7df86552a53d816ce3fed50d6d01310b48f-0x03",
        "createdAtTimestamp": "1693633261",
        "mint": 1 * MINT_DIVISOR,
        "market": {
            "id": "0x1067b7df86552a53d816ce3fed50d6d01310b48f"
        }
    },
    {
        "id": "0x33659282d39e62b62060c3f9fb2230e97db15f1e-0x04",
        "createdAtTimestamp": "1693633262",
        "mint": 1 * MINT_DIVISOR,
        "market": {
            "id": "0x33659282d39e62b62060c3f9fb2230e97db15f1e"
        }
    },
    {
        "id": "0x7c65c99ba1edfc94c535b7aa2d72b0f7357a676b-0x06",
        "createdAtTimestamp": "1693633264",
        "mint": 1 * MINT_DIVISOR,
        "market": {
            "id": "0x7c65c99ba1edfc94c535b7aa2d72b0f7357a676b"
        }
    },
    {
        "id": "0x833ba1a942dc6d33bc3e6959637ae00e0cdcb20b-0x07",
        "createdAtTimestamp": "1693633265",
        "mint": 1 * MINT_DIVISOR,
        "market": {
            "id": "0x833ba1a942dc6d33bc3e6959637ae00e0cdcb20b"
        }
    },
    {
        "id": "0xa811698d855153cc7472d1fb356149a94bd618e7-0x08",
        "createdAtTimestamp": "1693633266",
        "mint": 1 * MINT_DIVISOR,
        "market": {
            "id": "0xa811698d855153cc7472d1fb356149a94bd618e7"
        }
    },
    {
        "id": "0xc28350047d006ed387b0f210d4ea3218137a8a38-0x09",
        "createdAtTimestamp": "1693633267",
        "mint": 1 * MINT_DIVISOR,
        "market": {
            "id": "0xc28350047d006ed387b0f210d4ea3218137a8a38"
        }
    },
]

class TestMintMetric(unittest.TestCase):

    def test_initialize_metric(self):
        initialize_metrics(INITIAL_POSITIONS)
        mint_all_market =  REGISTRY.get_sample_value(
            'ovl_token_minted',
            labels={'market': ALL_MARKET_LABEL}
        )
        self.assertEqual(7.0, mint_all_market)

    def test_no_new_positions(self):
        initialize_metrics(INITIAL_POSITIONS)
        before =  REGISTRY.get_sample_value(
            'ovl_token_minted',
            labels={'market': ALL_MARKET_LABEL}
        )

        positions = []
        timestamp_lower = 1693671394

        timestamp_start = math.ceil(datetime.datetime.now().timestamp())
        next_timestamp_lower, next_timestamp_upper = query_single_time_window(
            positions=positions,
            timestamp_lower=timestamp_lower,
        )

        print('next_timestamp_lower', next_timestamp_lower)
        print('next_timestamp_upper', next_timestamp_upper)
        self.assertEqual(next_timestamp_lower, timestamp_lower)
        self.assertTrue(next_timestamp_upper >= timestamp_start)
        after =  REGISTRY.get_sample_value(
            'ovl_token_minted',
            labels={'market': ALL_MARKET_LABEL}
        )
        print('after', after)
        self.assertEqual(0, after - before)

    def test_one_new_position(self):
        initialize_metrics(INITIAL_POSITIONS)
        before =  REGISTRY.get_sample_value(
            'ovl_token_minted',
            labels={'market': ALL_MARKET_LABEL}
        )

        positions = [
            {
                "id": "0x02e5938904014901c96f534b063ec732ea3b48d5-0x02",
                "createdAtTimestamp": "1693633260",
                "mint": 2.5 * MINT_DIVISOR,
                "market": {
                    "id": "0x02e5938904014901c96f534b063ec732ea3b48d5"
                }
            },
        ]
        timestamp_lower = 1693633160
        timestamp_start = math.ceil(datetime.datetime.now().timestamp())

        next_timestamp_lower, next_timestamp_upper = query_single_time_window(
            positions=positions,
            timestamp_lower=timestamp_lower,
        )

        print('next_timestamp_lower', next_timestamp_lower)
        print('next_timestamp_upper', next_timestamp_upper)
        self.assertEqual(1693633260, next_timestamp_lower)
        self.assertTrue(next_timestamp_upper >= timestamp_start)
        after =  REGISTRY.get_sample_value(
            'ovl_token_minted',
            labels={'market': ALL_MARKET_LABEL}
        )
        print('after', after)
        self.assertEqual(2.5, after - before)

    def test_two_iterations(self):
        initialize_metrics(INITIAL_POSITIONS)
        initial =  REGISTRY.get_sample_value(
            'ovl_token_minted',
            labels={'market': ALL_MARKET_LABEL}
        )

        # Start first iteration
        positions_1 = [
            {
                "id": "0x02e5938904014901c96f534b063ec732ea3b48d5-0x02",
                "createdAtTimestamp": "1693633260",
                "mint": 2.5 * MINT_DIVISOR,
                "market": {
                    "id": "0x02e5938904014901c96f534b063ec732ea3b48d5"
                }
            },
        ]
        timestamp_start = math.ceil(datetime.datetime.now().timestamp())
        timestamp_lower_1 = 1693633160
        next_timestamp_lower, next_timestamp_upper = query_single_time_window(
            positions=positions_1,
            timestamp_lower=timestamp_lower_1,
        )
        self.assertEqual(next_timestamp_lower, 1693633260)
        self.assertTrue(next_timestamp_upper >= timestamp_start)
        after =  REGISTRY.get_sample_value(
            'ovl_token_minted',
            labels={'market': ALL_MARKET_LABEL}
        )
        self.assertEqual(2.5, after - initial)
        # End of first iteration

        time.sleep(QUERY_INTERVAL)

        # Second iteration
        positions_2 = [
            {
                "id": "0x1067b7df86552a53d816ce3fed50d6d01310b48f-0x02",
                "createdAtTimestamp": "1693633460",
                "mint": 3.5 * MINT_DIVISOR,
                "market": {
                    "id": "0x1067b7df86552a53d816ce3fed50d6d01310b48f"
                }
            },
        ]
        timestamp_lower_2 = next_timestamp_lower
        timestamp_start = math.ceil(datetime.datetime.now().timestamp())

        next_timestamp_lower, next_timestamp_upper = query_single_time_window(
            positions=positions_2,
            timestamp_lower=timestamp_lower_2,
        )
        print('next_timestamp_lower', next_timestamp_lower)
        print('next_timestamp_upper', next_timestamp_upper)
        self.assertEqual(next_timestamp_lower, 1693633460)
        self.assertTrue(next_timestamp_upper >= timestamp_start)
        after =  REGISTRY.get_sample_value(
            'ovl_token_minted',
            labels={'market': ALL_MARKET_LABEL}
        )
        print('after', after)
        self.assertEqual(6.0, after - initial)
        # End of second iteration

    def test_subgraph_client(self):
        mock_subgraph_client = MagicMock()
        mock_subgraph_client.get_all_positions.return_value = INITIAL_POSITIONS
        mock_subgraph_client.get_positions.return_value = []
        query_mint(
            subgraph_client=mock_subgraph_client,
            stop_at_iteration=2
        )
        mint_all_market =  REGISTRY.get_sample_value(
            'ovl_token_minted',
            labels={'market': ALL_MARKET_LABEL}
        )
        print('mint_all_market', mint_all_market)
        self.assertEqual(mint_all_market, 7.0)

    def test_subgraph_error_sets_metrics_to_nan(self):
        mock_subgraph_client = MagicMock()
        mock_subgraph_client.get_all_positions.return_value = INITIAL_POSITIONS
        mock_subgraph_client.get_positions.side_effect = Exception(
            'Subgraph API returned empty data'
        )
        query_mint(
            subgraph_client=mock_subgraph_client,
            stop_at_iteration=2
        )
        mint_all_market =  REGISTRY.get_sample_value(
            'ovl_token_minted',
            labels={'market': ALL_MARKET_LABEL}
        )
        print('mint_all_market', mint_all_market)
        self.assertTrue(math.isnan(mint_all_market))
