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
from utils import format_datetime
from prometheus_metrics import metrics
from subgraph.client import ResourceClient as SubgraphClient


subgraph_client = SubgraphClient()


def set_metrics_to_nan():
    """
    Set metrics values to NaN to indicate a query error.

    This function updates the 'mint_gauge' metrics labels for all markets, setting their values to NaN.
    This is typically used to indicate that there was an issue with the query or data retrieval.

    Note:
        - `metrics` is a global object representing a metrics collector.
        - `AVAILABLE_MARKETS` is a global variable.
        - `MAP_MARKET_ID_TO_NAME` is a global variable.
        - `ALL_MARKET_LABEL` is a global variable.

    Returns:
        None
    """
    # Set metric to NaN to indicate that something went wrong with the query
    metrics['mint_gauge'].labels(market=ALL_MARKET_LABEL).set(math.nan)
    for market in AVAILABLE_MARKETS:
        metrics['mint_gauge'].labels(market=MAP_MARKET_ID_TO_NAME[market]).set(math.nan)


def initialize_metrics(all_positions):
    """
    Initialize metrics based on the provided positions.

    Args:
        all_positions (list): List of position data, where each element is a dictionary
            containing information about a position.

    Returns:
        None: This function modifies metrics directly.

    Note:
        - If `all_positions` is empty, the function does nothing.
        - `AVAILABLE_MARKETS` is a global variable.
        - `MAP_MARKET_ID_TO_NAME` is a global variable.
        - `metrics` is a global object representing a metrics collector.

    This function processes the provided positions and calculates various metrics based on them.
    It updates the metrics collector with relevant information.

    The steps include:
        1. Convert `all_positions` into a pandas DataFrame.
        2. Extract necessary information from the DataFrame.
        3. Filter out positions based on available markets.
        4. Calculate total mint and mint per market.
        5. Update the metrics collector with the calculated values.
    """
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

    metrics['mint_gauge'].labels(market=ALL_MARKET_LABEL).set(mint_total)
    for market_id in mint_total_per_market:
        if market_id not in AVAILABLE_MARKETS:
            continue
        market_total_mint = mint_total_per_market[market_id] / MINT_DIVISOR
        metrics['mint_gauge'].labels(market=MAP_MARKET_ID_TO_NAME[market_id]).set(
            market_total_mint)


def is_divisible(number, divisor):
    return number % divisor == 0


def query_single_time_window(
        positions,
        timestamp_lower
    ):
    """
    Query a single time window for position data and update metrics.

    Args:
        positions (list): List of position data, where each element is a dictionary
            containing information about a position.
        timestamp_lower (int): The lower bound of the timestamp range for the next query.

    Returns:
        tuple: A tuple containing the updated timestamp_lower and timestamp_upper.

    This function processes position data for a specified time window and updates metrics accordingly.

    It performs the following steps:
        1. Increments the 'mint_gauge' metrics labels for each market and the overall market based on position data.
        2. Sets the timestamp range for the next query based on the latest position's timestamp or the current time.

    Note:
        - `metrics` is a global object representing a metrics collector.
        - `MAP_MARKET_ID_TO_NAME` is a global variable.
        - `MINT_DIVISOR` is a global variable.
        - `ALL_MARKET_LABEL` is a global variable.

    """
    for position in positions:
        mint = int(position['mint']) / MINT_DIVISOR
        market = MAP_MARKET_ID_TO_NAME[position['market']['id']]
        metrics['mint_gauge'].labels(market=market).inc(mint)
        metrics['mint_gauge'].labels(market=ALL_MARKET_LABEL).inc(mint)

    if positions:
        # set next timestamp lower to timestamp of latest position
        next_timestamp_lower = int(positions[0]['createdAtTimestamp'])
    else:
        # If there are no new positions in the time window,
        # Keep the current timestamp lower
        next_timestamp_lower = timestamp_lower
    next_timestamp_upper = math.ceil(datetime.datetime.now().timestamp())
    return next_timestamp_lower, next_timestamp_upper


def query_mint():
    print('[ovl_token_minted] Starting query...')
    set_metrics_to_nan()
    try:
        iteration = 1

        # Calculate the total mint so far from the subgraph
        all_positions = subgraph_client.get_all_positions()
        initialize_metrics(all_positions)
        time.sleep(QUERY_INTERVAL)

        timestamp_lower = int(all_positions[0]['createdAtTimestamp'])
        timestamp_upper = math.ceil(datetime.datetime.now().timestamp())

        while True:
            try:
                print('===================================')
                print(f'[ovl_token_minted] Running iteration #{iteration}...')
                print(
                    '[ovl_token_minted] timestamp_lower',
                    format_datetime(timestamp_lower)
                )
                print(
                    '[ovl_token_minted] timestamp_upper',
                    format_datetime(timestamp_upper)
                )

                # Test market that overmints every 200th iteration
                # if is_divisible(iteration, 200):
                #     metrics['mint_gauge'].labels(market='TEST OVERMINT').inc(20)
                # if is_divisible(iteration, 30):
                #     metrics['mint_gauge'].labels(market='TEST OVERMINT').inc(0.02)

                # Update ovl_token_minted metric
                positions = subgraph_client.get_positions(
                    timestamp_lower, timestamp_upper)
                positions = [
                    position
                    for position in positions
                    if position['market']['id'] in AVAILABLE_MARKETS
                ]
                print(f'[ovl_token_minted] new positions', len(positions))
                timestamp_lower, timestamp_upper = query_single_time_window(
                    positions, timestamp_lower)
            except Exception as e:
                print(
                    f"[ovl_token_minted] An error occurred on iteration "
                    f"{iteration} timestamp_lower "
                    f"{format_datetime(timestamp_lower)}:", e)
                set_metrics_to_nan()
            finally:
                # Increment iteration
                iteration += 1

                # Wait for the next iteration
                time.sleep(QUERY_INTERVAL)
                
    except Exception as e:
        print(f"[ovl_token_minted] An error occurred:", e)
        set_metrics_to_nan()


thread = threading.Thread(target=query_mint)
