import json
import datetime
import math
import pandas as pd
import threading
import time

from constants import (
    MAP_MARKET_ID_TO_NAME,
    AVAILABLE_MARKETS,
    ALL_MARKET_LABEL,
    QUERY_INTERVAL,
    MINT_DIVISOR
)
from prometheus_metrics import metrics
from subgraph.client import ResourceClient as SubgraphClient


subgraph_client = SubgraphClient()

def write_to_json(data, filename):
    with open(filename, 'w') as json_file:
        json.dump({"data": data}, json_file, indent=4)


def set_metrics_to_nan():
    # Set metric to NaN to indicate that something went wrong with the query
    metrics['mint_gauge'].labels(market=ALL_MARKET_LABEL).set(math.nan)
    for market in AVAILABLE_MARKETS:
        metrics['mint_gauge'].labels(market=MAP_MARKET_ID_TO_NAME[market]).set(math.nan)


def initialize_metrics(all_positions):
    if (not len(all_positions)):
        return
    all_positions_df = pd.DataFrame(all_positions)
    all_positions_df[['market', 'position_id']] = all_positions_df['id'].str.split(
        '-', expand=True)
    all_positions_df.drop(
        all_positions_df[~all_positions_df['market'].isin(AVAILABLE_MARKETS)].index,
        inplace = True
    )
    mint_total = all_positions_df['mint'].sum() / MINT_DIVISOR
    mint_total_per_market_df = all_positions_df.groupby(by='market')['mint'].sum().reset_index()
    mint_total_per_market = dict(zip(mint_total_per_market_df['market'], mint_total_per_market_df['mint']))

    metrics['mint_gauge'].labels(market=ALL_MARKET_LABEL).set(mint_total)
    for market_id in mint_total_per_market:
        if market_id not in AVAILABLE_MARKETS:
            continue
        market_total_mint = mint_total_per_market[market_id] / MINT_DIVISOR
        metrics['mint_gauge'].labels(market=MAP_MARKET_ID_TO_NAME[market_id]).set(
            market_total_mint)


def query_single_time_window(
        positions,
        timestamp_start,
        timestamp_lower,
        timestamp_upper
    ):
    print('timestamp_start', timestamp_start)
    print('timestamp_lower', timestamp_lower)
    print('timestamp_upper', timestamp_upper)
    positions = [
        position
        for position in positions
        if position['market']['id'] in AVAILABLE_MARKETS
    ]
    print(f'[ovl_token_minted] positions', len(positions))
    # metrics['mint_gauge'].labels(market='LINK / USD').inc(500)
    # metrics['mint_gauge'].labels(market='SOL / USD').inc(-500)
    for position in positions:
        mint = int(position['mint']) / MINT_DIVISOR
        market = MAP_MARKET_ID_TO_NAME[position['market']['id']]
        metrics['mint_gauge'].labels(market=market).inc(mint)
        metrics['mint_gauge'].labels(market=ALL_MARKET_LABEL).inc(mint)

    if positions:
        # set timestamp range lower bound to timestamp of latest event
        next_timestamp_lower = int(positions[0]['createdAtTimestamp'])
        if len(positions) > 1:
            next_timestamp_upper = int(positions[-1]['createdAtTimestamp'])
        else:
            next_timestamp_upper = timestamp_start
    else:
        next_timestamp_lower = timestamp_lower
        next_timestamp_upper = timestamp_start
    return next_timestamp_lower, next_timestamp_upper


def query_mint():
    print('[ovl_token_minted] Starting query...')
    set_metrics_to_nan()
    try:
        iteration = 1

        # Calculate the total mint so far from the subgraph
        all_positions = subgraph_client.get_all_positions()
        initialize_metrics(all_positions)

        timestamp_start = datetime.datetime.now().timestamp()
        time.sleep(QUERY_INTERVAL)
        timestamp_lower = math.ceil(timestamp_start)
        timestamp_upper = math.ceil(datetime.datetime.now().timestamp())

        while True:
            try:
                print('===================================')
                print(f'[ovl_token_minted] Running iteration #{iteration}...')
                timestamp_start = math.ceil(datetime.datetime.now().timestamp())
                print(
                    '[ovl_token_minted] timestamp_lower',
                    datetime.datetime.utcfromtimestamp(timestamp_lower).strftime('%Y-%m-%d %H:%M:%S')
                )
                print(
                    '[ovl_token_minted] timestamp_upper',
                    datetime.datetime.utcfromtimestamp(timestamp_upper).strftime('%Y-%m-%d %H:%M:%S')
                )
                # Update ovl_token_minted metric
                positions = subgraph_client.get_positions(timestamp_lower, timestamp_upper)
                positions = [
                    position
                    for position in positions
                    if position['market']['id'] in AVAILABLE_MARKETS
                ]
                print(f'[ovl_token_minted] positions', len(positions))
                timestamp_lower, timestamp_upper = query_single_time_window(
                    positions,
                    timestamp_start,
                    timestamp_lower,
                    timestamp_upper
                )
            except Exception as e:
                print(
                    f"[ovl_token_minted] An error occurred on iteration "
                    f"{iteration} timestamp_lower "
                    f"{datetime.datetime.utcfromtimestamp(timestamp_lower).strftime('%Y-%m-%d %H:%M:%S')}:", e)
            finally:
                # Increment iteration
                iteration += 1

                # Wait for the next iteration
                time.sleep(QUERY_INTERVAL)
                
    except Exception as e:
        print(f"[ovl_token_minted] An error occurred:", e)
        set_metrics_to_nan()


thread = threading.Thread(target=query_mint)
