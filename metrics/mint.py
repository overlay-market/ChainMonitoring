import datetime
import math
import pandas as pd
import time
import traceback

from constants import (
    MAP_MARKET_ID_TO_NAME,
    ALL_MARKET_LABEL,
    QUERY_INTERVAL,
    MINT_DIVISOR,
)
from utils import format_datetime, CMThread, handle_error
from prometheus_metrics import metrics
from subgraph.client import ResourceClient as SubgraphClient


def set_metrics_to_nan(subgraph_client):
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
    for market in subgraph_client.AVAILABLE_MARKETS:
        metrics['mint_gauge'].labels(market=MAP_MARKET_ID_TO_NAME[market]).set(math.nan)


def initialize_metrics(unwinds_and_liquidates):
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
    if (not len(unwinds_and_liquidates)):
        return

    print('unwinds_and_liquidates!!', unwinds_and_liquidates[:10])
    unwinds_and_liquidates_df = pd.DataFrame(unwinds_and_liquidates)
    print('unwinds_and_liquidates_df!!', unwinds_and_liquidates_df)
    unwinds_and_liquidates_df['mint'] = unwinds_and_liquidates_df['mint'].apply(int)
    unwinds_and_liquidates_df[['market', 'position_id', 'num']] = unwinds_and_liquidates_df['id'].str.split(
        '-', expand=True)
    mint_total = unwinds_and_liquidates_df['mint'].sum() / MINT_DIVISOR
    mint_total_per_market_df = unwinds_and_liquidates_df.groupby(by='market')['mint'].sum().reset_index()
    mint_total_per_market = dict(
        zip(mint_total_per_market_df['market'], mint_total_per_market_df['mint']))

    metrics['mint_gauge'].labels(market=ALL_MARKET_LABEL).set(mint_total)
    for market_id in mint_total_per_market:
        market_total_mint = mint_total_per_market[market_id] / MINT_DIVISOR
        metrics['mint_gauge'].labels(market=MAP_MARKET_ID_TO_NAME[market_id]).set(
            market_total_mint)


def is_divisible(number, divisor):
    return number % divisor == 0


def query_single_time_window(
        unwinds_and_liquidates,
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
    # unwinds_and_liquidates = unwinds + liquidates
    for txn in unwinds_and_liquidates:
        mint = int(txn['mint']) / MINT_DIVISOR
        market = MAP_MARKET_ID_TO_NAME[txn['position']['market']['id']]
        metrics['mint_gauge'].labels(market=market).inc(mint)
        metrics['mint_gauge'].labels(market=ALL_MARKET_LABEL).inc(mint)

    if unwinds_and_liquidates:
        next_timestamp_lower = int(unwinds_and_liquidates[0]['timestamp'])
    else:
        # If there are no new positions in the time window,
        # Keep the current timestamp lower
        next_timestamp_lower = timestamp_lower
    next_timestamp_upper = math.ceil(datetime.datetime.now().timestamp())
    return next_timestamp_lower, next_timestamp_upper


def query_mint(subgraph_client, stop_at_iteration=math.inf):
    """
    Query mint data from the subgraph and update metrics.

    Args:
        subgraph_client: An instance of the subgraph client used for querying data.
        stop_at_iteration (int, optional): The maximum number of iterations to run the query. Default is math.inf.

    Returns:
        None

    This function queries mint data from the provided subgraph client, updates metrics, and handles exceptions.

    It performs the following steps:
        1. Initializes metrics and sets them to NaN.
        2. Gets all positions from the subgraph and initializes metrics based on the positions.
        3. Runs iterations to query mint data within specified time windows.
        4. Updates metrics with the queried data.
        5. Handles exceptions and resets metrics if an error occurs.

    Args Details:
        - `subgraph_client`: An instance of the subgraph client used for querying data.
        - `stop_at_iteration`: The maximum number of iterations to run the query (default is math.inf).

    Note:
        - `AVAILABLE_MARKETS` is a global variable.
        - `initialize_metrics`, `set_metrics_to_nan`, and `query_single_time_window` are defined functions.
        - `QUERY_INTERVAL` is a global variable.
    """
    print('[ovl_token_minted] Starting query...')
    # 1 / 0
    set_metrics_to_nan(subgraph_client)
    try:
        iteration = 0

        # Calculate the total mint so far from the subgraph
        # all_positions = subgraph_client.get_all_positions()
        all_unwinds_and_liquidates = subgraph_client.get_all_unwinds_and_liquidates()
        initialize_metrics(all_unwinds_and_liquidates)
        time.sleep(QUERY_INTERVAL)

        timestamp_lower = int(all_unwinds_and_liquidates[0]['timestamp'])
        timestamp_upper = math.ceil(datetime.datetime.now().timestamp())

        should_initialize_metrics = False

        while iteration < stop_at_iteration:
            try:
                print('===================================')
                print(f'[ovl_token_minted] Running iteration #{iteration}...')
                print(
                    f'[ovl_token_minted] timestamp_lower {timestamp_lower}',
                    format_datetime(timestamp_lower)
                )
                print(
                    f'[ovl_token_minted] timestamp_upper {timestamp_upper}',
                    format_datetime(timestamp_upper)
                )
                if should_initialize_metrics:
                    # all_positions = subgraph_client.get_all_positions()
                    # initialize_metrics(all_positions)
                    all_unwinds_and_liquidates = subgraph_client.get_all_unwinds_and_liquidates()
                    initialize_metrics(all_unwinds_and_liquidates)
                    should_initialize_metrics = False

                # Test market that overmints every 200th iteration
                # if is_divisible(iteration, 200):
                #     metrics['mint_gauge'].labels(market='TEST OVERMINT').inc(20)
                # if is_divisible(iteration, 30):
                #     metrics['mint_gauge'].labels(market='TEST OVERMINT').inc(0.02)

                # Update ovl_token_minted metric
                # unwinds = subgraph_client.get_unwinds(timestamp_lower, timestamp_upper)
                # liquidates = subgraph_client.get_liquidates(timestamp_lower, timestamp_upper)
                unwinds_and_liquidates = subgraph_client.get_unwinds_and_liquidates(timestamp_lower, timestamp_upper)
                print('[ovl_token_minted] new unwinds and liquidates', len(unwinds_and_liquidates))
                # print('[ovl_token_minted] new unwinds and liquidates', len(unwinds + liquidates))
                timestamp_lower, timestamp_upper = query_single_time_window(
                    unwinds_and_liquidates, timestamp_lower)
                # if iteration == 1:
                #     1 / 0
            except Exception as e:
                error_message = (
                    f"[ovl_token_minted] An error occurred on iteration "
                    f"{iteration} timestamp_lower "
                    f"{format_datetime(timestamp_lower)}: {e}"
                )
                handle_error(error_message)
                print(error_message)
                traceback.print_exc()
                set_metrics_to_nan(subgraph_client)
                should_initialize_metrics = True
            finally:
                # Increment iteration
                iteration += 1

                # Wait for the next iteration
                time.sleep(QUERY_INTERVAL)
                
    except Exception as e:
        error_message = f"[ovl_token_minted] An error occurred: {e}"
        handle_error(error_message)
        print(error_message)
        traceback.print_exc()
        set_metrics_to_nan(subgraph_client)

subgraph_client = SubgraphClient()
thread = CMThread(target=query_mint, args=(subgraph_client,))
