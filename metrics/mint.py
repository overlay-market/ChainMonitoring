import datetime
import math
import threading
import time

from constants import MAP_MARKET_ID_TO_NAME, AVAILABLE_MARKETS, ALL_MARKET_LABEL
from prometheus_metrics import metrics
from subgraph.client import ResourceClient as SubgraphClient


subgraph_client = SubgraphClient()


def set_metrics_to_nan():
    # Set metric to NaN to indicate that something went wrong with the query
    metrics['mint_gauge'].labels(market=ALL_MARKET_LABEL).set(math.nan)
    for market in AVAILABLE_MARKETS:
        metrics['mint_gauge'].labels(market=MAP_MARKET_ID_TO_NAME[market]).set(math.nan)


def query_mint():
    print('[ovl_token_minted] Starting query...')
    try:
        iteration = 1
        query_interval = 10 # in seconds
        timestamp_window = 20 # in seconds
        mint_divisor = 10 ** 18

        # Calculate the total mint so far from the subgraph
        mint_total, mint_total_per_market = subgraph_client.get_mint_total_per_market()
        metrics['mint_gauge'].labels(market=ALL_MARKET_LABEL).set(mint_total / mint_divisor)
        for market_id in mint_total_per_market:
            if market_id not in AVAILABLE_MARKETS:
                continue
            metrics['mint_gauge'].labels(market=MAP_MARKET_ID_TO_NAME[market_id]).set(mint_total_per_market[market_id] / mint_divisor)

        # the first ever timestamp for positions is 1677258816
        timestamp_start = datetime.datetime.now().timestamp() - (timestamp_window)
        timestamp_lower = math.ceil(timestamp_start - timestamp_window)
        timestamp_upper = math.ceil(timestamp_start)

        while True:
            try:
                print('===================================')
                print(f'[ovl_token_minted] Running iteration #{iteration}...')
                print(
                    '[ovl_token_minted] timestamp_lower',
                    datetime.datetime.utcfromtimestamp(timestamp_lower).strftime('%Y-%m-%d %H:%M:%S')
                )
                print(
                    '[ovl_token_minted] timestamp_upper',
                    datetime.datetime.utcfromtimestamp(timestamp_upper).strftime('%Y-%m-%d %H:%M:%S')
                )
                
                # if iteration == 5:
                #     1 / 0

                # Update ovl_token_minted metric
                positions = subgraph_client.get_positions(timestamp_lower, timestamp_upper)
                positions = [
                    position
                    for position in positions
                    if position['market']['id'] in AVAILABLE_MARKETS
                ]
                print(f'[ovl_token_minted] positions', len(positions))
                for position in positions:
                    mint = int(position['mint']) / mint_divisor
                    market = MAP_MARKET_ID_TO_NAME[position['market']['id']]
                    metrics['mint_gauge'].labels(market=market).inc(mint)
                    metrics['mint_gauge'].labels(market=ALL_MARKET_LABEL).inc(mint)

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
                    timestamp_upper = datetime.datetime.now().timestamp()
            except Exception as e:
                print(
                    f"[ovl_token_minted] An error occurred on iteration "
                    f"{iteration} timestamp_lower "
                    f"{datetime.datetime.utcfromtimestamp(timestamp_lower).strftime('%Y-%m-%d %H:%M:%S')}:", e)
                
    except Exception as e:
        print(f"[ovl_token_minted] An error occurred:", e)
        set_metrics_to_nan()


thread = threading.Thread(target=query_mint)
