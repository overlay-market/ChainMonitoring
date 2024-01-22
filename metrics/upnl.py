import datetime
import json
import math
import traceback

import asyncio
import pandas as pd

from constants import (
    MAP_MARKET_ID_TO_NAME as MARKET_MAP,
    ALL_MARKET_LABEL,
    QUERY_INTERVAL,
    MINT_DIVISOR,
    CONTRACT_ADDRESS,
)
from utils import CMThread, handle_error
from prometheus_metrics import metrics
from blockchain.client import ResourceClient as BlockchainClient
from subgraph.client import ResourceClient as SubgraphClient


# Contract addresses
CONTRACT_ADDRESS = CONTRACT_ADDRESS


def write_to_json(data, filename):
    with open(filename, 'w') as json_file:
        json.dump({"data": data}, json_file, indent=4)


async def process_live_positions(blockchain_client, live_positions):
    """
    Asynchronously process live positions data.

    Args:
        live_positions (list): List of live position data, where each element is a dictionary
            containing information about a live position.

    Returns:
        pandas.DataFrame: DataFrame containing processed live position information.

    This asynchronous function processes live position data by filtering out positions not in available markets,
    retrieving their current values, and calculating UPNL (Unrealized Profit and Loss) metrics.

    Args Details:
        - `live_positions`: List of live position data.

    Note:
        - `AVAILABLE_MARKETS`, `get_current_value_of_live_positions`, and `MINT_DIVISOR` are assumed to be defined.
        - This function utilizes asynchronous operations for improved performance.

    """
    live_positions_df = pd.DataFrame(live_positions)
    # live_positions_df.drop(
    #     live_positions_df[~live_positions_df['market'].isin(AVAILABLE_MARKETS)].index,
    #     inplace = True
    # )
    # values = await get_current_value_of_live_positions(blockchain_client, live_positions_df)
    positions = live_positions_df[['market', 'owner.id', 'position_id']].values.tolist()
    values = await blockchain_client.get_value_of_positions(positions)
    values = [v / MINT_DIVISOR for v in values]
    live_positions_df['value'] = values
    live_positions_df['upnl'] = live_positions_df['value'] - live_positions_df['collateral_rem']
    live_positions_df['upnl_pct'] = live_positions_df['upnl'] / live_positions_df['collateral_rem']
    return live_positions_df


def set_metrics_to_nan(subgraph_client):
    """
    Set metrics values to NaN to indicate a query error.

    This function updates the 'mint_gauge' metrics labels for all markets, setting their values to NaN.
    This is typically used to indicate that there was an issue with the query or data retrieval.

    Note:
        - `metrics` is a global object representing a metrics collector.
        - `AVAILABLE_MARKETS` is a global variable.
        - `MARKET_MAP` is a global variable.
        - `ALL_MARKET_LABEL` is a global variable.

    Returns:
        None
    """
    # Set metric to NaN to indicate that something went wrong with the query
    metrics['upnl_gauge'].labels(market=ALL_MARKET_LABEL).set(math.nan)
    metrics['collateral_rem_gauge'].labels(market=ALL_MARKET_LABEL).set(math.nan)
    metrics['upnl_pct_gauge'].labels(market=ALL_MARKET_LABEL).set(math.nan)
    for market in subgraph_client.AVAILABLE_MARKETS:
        metrics['upnl_gauge'].labels(market=MARKET_MAP[market]).set(math.nan)
        metrics['collateral_rem_gauge'].labels(market=MARKET_MAP[market]).set(math.nan)
        metrics['upnl_pct_gauge'].labels(market=MARKET_MAP[market]).set(math.nan)


def set_metrics(subgraph_client, live_positions_df_with_curr_values):
    """
    Set metrics based on processed live positions data.

    Args:
        live_positions_df_with_curr_values (pandas.DataFrame): DataFrame containing processed live position information.

    Returns:
        None

    This function sets various metrics based on the processed live position data, including UPNL (Unrealized Profit and Loss),
    collateral, and UPNL percentage metrics.

    Args Details:
        - `live_positions_df_with_curr_values`: DataFrame containing processed live position information.

    Note:
        - `set_metrics_to_nan`, `metrics`, `AVAILABLE_MARKETS`, `MARKET_MAP`, and `ALL_MARKET_LABEL` are assumed to be defined.
        - This function updates metrics based on the provided live position data.

    """
    if not len(live_positions_df_with_curr_values):
        set_metrics_to_nan(subgraph_client)
        return

    # Calculate current value of each live position
    live_positions_df = live_positions_df_with_curr_values

    # Set initial value of upnl metric so far
    upnl_total = live_positions_df['upnl'].sum()
    upnl_total_per_market_df = live_positions_df.groupby(by='market')['upnl'].sum().reset_index()
    upnl_total_per_market = dict(zip(upnl_total_per_market_df['market'], upnl_total_per_market_df['upnl']))
    metrics['upnl_gauge'].labels(market=ALL_MARKET_LABEL).set(upnl_total)
    for market_id in upnl_total_per_market:
        metrics['upnl_gauge'].labels(market=MARKET_MAP[market_id]).set(upnl_total_per_market[market_id])

    # Set initial value for collateral metric so far
    collateral_total = live_positions_df['collateral_rem'].sum()
    collateral_total_per_market_df = live_positions_df.groupby(by='market')['collateral_rem'].sum().reset_index()
    collateral_total_per_market = dict(zip(collateral_total_per_market_df['market'], collateral_total_per_market_df['collateral_rem']))
    metrics['collateral_rem_gauge'].labels(market=ALL_MARKET_LABEL).set(collateral_total)
    for market_id in collateral_total_per_market:
        metrics['collateral_rem_gauge'].labels(market=MARKET_MAP[market_id]).set(collateral_total_per_market[market_id])
        metrics['upnl_pct_gauge'].labels(market=MARKET_MAP[market_id]).set(
            upnl_total_per_market[market_id] / collateral_total_per_market[market_id]
        )

    # live_positions_df['upnl_pct'] = live_positions_df['upnl'] / live_positions_df['collateral_rem']
    metrics['upnl_pct_gauge'].labels(market=ALL_MARKET_LABEL).set(upnl_total / collateral_total)


async def query_upnl(subgraph_client, blockchain_client, stop_at_iteration=math.inf):
    """
    Asynchronously query unrealized profit and loss (UPNL) metrics from the subgraph.

    Args:
        subgraph_client: An instance of the subgraph client used for querying data.
        blockchain_client: An instance of the blockchain client used for querying data.
        stop_at_iteration (int, optional): The maximum number of iterations to run the query. Default is math.inf.

    Returns:
        None

    This asynchronous function queries UPNL metrics from the provided subgraph client, connects to the Arbitrum network,
    and handles exceptions.

    It performs the following steps:
        1. Connects to the Arbitrum network.
        2. Initializes metrics and sets them to NaN.
        3. Fetches live positions from the subgraph and calculates current values.
        4. Sets UPNL metrics based on the live positions and current values.
        5. Runs iterations to update UPNL metrics.
        6. Handles exceptions and resets metrics if an error occurs.

    Note:
        - `process_live_positions`, `set_metrics`, and `set_metrics_to_nan` are defined functions.
        - `QUERY_INTERVAL` is a global variable.
        - `network` is a global object representing network connectivity.

    """
    print('[upnl] Starting query...')
    # 1/0
    blockchain_client.connect_to_network()
    set_metrics_to_nan(subgraph_client)
    try:
        iteration = 0

        # Fetch all live positions so far from the subgraph
        print('[upnl] Getting live positions from subgraph...')
        live_positions = subgraph_client.get_all_live_positions()
        print('live_positions', len(live_positions))
        # write_to_json(live_positions, 'live_positions.json')
        print('[upnl] Getting live positions current value from blockchain...')
        live_positions_df_with_curr_values = await process_live_positions(blockchain_client, live_positions)
        # write_to_json(
        #     live_positions_df_with_curr_values.to_dict(orient="records"),
        #     f"live_positions_with_current_values_{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}.json"
        # )
        print('[upnl] Calculating upnl metrics...')
        set_metrics(subgraph_client, live_positions_df_with_curr_values)

        await asyncio.sleep(QUERY_INTERVAL)

        while iteration < stop_at_iteration:
            try:
                print('===================================')
                print(f'[upnl] Running iteration #{iteration}...')
                timestamp_start = math.ceil(datetime.datetime.now().timestamp())
                print('[upnl] timestamp_start', datetime.datetime.utcfromtimestamp(timestamp_start).strftime('%Y-%m-%d %H:%M:%S'))

                # Fetch all live positions so far from the subgraph
                live_positions = subgraph_client.get_all_live_positions()
                live_positions_df_with_curr_values = await process_live_positions(blockchain_client, live_positions)
                set_metrics(subgraph_client, live_positions_df_with_curr_values)

                # Increment iteration
                iteration += 1

                # Wait for the next iteration
                await asyncio.sleep(QUERY_INTERVAL)
                # if iteration == 10:
                #     1 / 0
            except Exception as e:
                error_message = (
                    f"[upnl] An error occurred on iteration "
                    f"{iteration} timestamp_start "
                    f"{datetime.datetime.utcfromtimestamp(timestamp_start).strftime('%Y-%m-%d %H:%M:%S')}: {e}"
                )
                handle_error(error_message)
                print(error_message)
                traceback.print_exc()
    except Exception as e:
        error_message = f"[upnl] An error occurred: {e}"
        handle_error(error_message)
        print(error_message)
        traceback.print_exc()
        set_metrics_to_nan(subgraph_client)


subgraph_client = SubgraphClient()
blockchain_client = BlockchainClient()
thread = CMThread(target=asyncio.run, args=(query_upnl(subgraph_client, blockchain_client),))
