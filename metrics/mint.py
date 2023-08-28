import datetime
import math
import threading
import time

from prometheus_metrics import metrics
from subgraph.client import ResourceClient as SubgraphClient
from subgraph.constants import MAP_MARKET_ID_TO_NAME


def query_mint():
    print('[ovl_token_minted] Starting query...')
    subgraph_client = SubgraphClient()
    iteration = 1
    query_interval = 10 # in seconds
    timestamp_window = 20 # in seconds
    mint_divisor = 10 ** 18

    # Calculate the total mint so far from the subgraph
    mint_total, mint_total_per_market = subgraph_client.get_mint_total_per_market()
    metrics['mint_gauge'].labels(market='').set(mint_total / mint_divisor)
    for market_id in mint_total_per_market:
        metrics['mint_gauge'].labels(market=MAP_MARKET_ID_TO_NAME[market_id]).set(mint_total_per_market[market_id] / mint_divisor)

    # the first ever timestamp for positions is 1677258816
    timestamp_start = datetime.datetime.now().timestamp() - (timestamp_window)
    timestamp_lower = math.ceil(timestamp_start - timestamp_window)
    timestamp_upper = math.ceil(timestamp_start)

    while True:
        print('===================================')
        print(f'[ovl_token_minted] Running iteration #{iteration}...')
        print('[ovl_token_minted] timestamp_lower', datetime.datetime.utcfromtimestamp(timestamp_lower).strftime('%Y-%m-%d %H:%M:%S'))
        print('[ovl_token_minted] timestamp_upper', datetime.datetime.utcfromtimestamp(timestamp_upper).strftime('%Y-%m-%d %H:%M:%S'))
        
        # Update ovl_token_minted metric
        positions = subgraph_client.get_positions(timestamp_lower, timestamp_upper)
        print(f'[ovl_token_minted] positions', len(positions))
        for position in positions:
            mint = int(position['mint']) / mint_divisor
            metrics['mint_gauge'].labels(market=MAP_MARKET_ID_TO_NAME[position['market']['id']]).inc(mint)
            metrics['mint_gauge'].labels(market='').inc(mint)

        # Increment iteration
        iteration += 1

        # Wait for the next iteration
        time.sleep(query_interval)

        if positions:
            # set timestamp range lower bound to timestamp of latest event
            timestamp_lower = int(positions[0]['createdAtTimestamp'])
            if len(positions) > 1:
                timestamp_upper = int(positions[-1]['createdAtTimestamp'])
            else:
                timestamp_upper += timestamp_window
        else:
            timestamp_lower = timestamp_upper
            timestamp_upper += timestamp_window


thread = threading.Thread(target=query_mint)
