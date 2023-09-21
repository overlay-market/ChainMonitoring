import datetime
import json
import math
import threading

import asyncio
import pandas as pd
from web3.exceptions import ContractLogicError
from brownie import Contract, web3, network
from dank_mids.brownie_patch import patch_contract
from dank_mids.helpers import setup_dank_w3_from_sync

from constants import (
    MAP_MARKET_ID_TO_NAME as MARKET_MAP,
    AVAILABLE_MARKETS,
    ALL_MARKET_LABEL,
    QUERY_INTERVAL,
    MINT_DIVISOR,
    CONTRACT_ADDRESS
)
from utils import format_datetime
from prometheus_metrics import metrics
from subgraph.client import ResourceClient as SubgraphClient


# Contract addresses
STATE = CONTRACT_ADDRESS

# network.connect('arbitrum-main')

# # Dank mids setup
# dank_w3 = setup_dank_w3_from_sync(web3)

# subgraph_client = SubgraphClient()


def write_to_json(data, filename):
    with open(filename, 'w') as json_file:
        json.dump({"data": data}, json_file, indent=4)


def load_contract(address):
    try:
        # Loads faster from memory
        contract = Contract(address)
    except ValueError:
        # Loads from explorer first time script is run
        contract = Contract.from_explorer(address)
    dank_w3 = setup_dank_w3_from_sync(web3)
    dank_contract = patch_contract(contract, dank_w3)
    return dank_contract


async def get_pos_value(state, pos):
    try:
        return await state.value.coroutine(pos[0], pos[1], pos[2])
    except ContractLogicError as e:
        print(e)
        return


async def get_current_value_of_live_positions(live_positions_df):
    state = load_contract(STATE)
    pos_list = live_positions_df[['market', 'owner.id', 'position_id']].values.tolist()
    values = []
    batch_size = 50
    # Get current value of live positions by batches
    for i in range(math.ceil(len(pos_list) / batch_size)):
        index_lower = i * batch_size
        index_upper = (i + 1) * batch_size
        print(f'[upnl] fetching values for batch {index_upper} out of {len(pos_list)}...')
        if index_upper > len(pos_list):
            index_upper = len(pos_list)
        curr_post_list = pos_list[index_lower:index_upper]
        values.extend(
            await asyncio.gather(*[get_pos_value(state, pos) for pos in curr_post_list])
        )
        await asyncio.sleep(5)
    return values


async def process_live_positions(live_positions):
    live_positions_df = pd.DataFrame(live_positions)
    live_positions_df.drop(
        live_positions_df[~live_positions_df['market'].isin(AVAILABLE_MARKETS)].index,
        inplace = True
    )
    values = await get_current_value_of_live_positions(live_positions_df)
    values = [v / MINT_DIVISOR for v in values]
    live_positions_df['value'] = values
    live_positions_df['upnl'] = live_positions_df['value'] - live_positions_df['collateral_rem']
    live_positions_df['upnl_pct'] = live_positions_df['upnl'] / live_positions_df['collateral_rem']
    return live_positions_df


def set_metrics_to_nan():
    # Set metric to NaN to indicate that something went wrong with the query
    metrics['upnl_gauge'].labels(market=ALL_MARKET_LABEL).set(math.nan)
    metrics['collateral_rem_gauge'].labels(market=ALL_MARKET_LABEL).set(math.nan)
    metrics['upnl_pct_gauge'].labels(market=ALL_MARKET_LABEL).set(math.nan)
    for market in AVAILABLE_MARKETS:
        metrics['upnl_gauge'].labels(market=MARKET_MAP[market]).set(math.nan)
        metrics['collateral_rem_gauge'].labels(market=MARKET_MAP[market]).set(math.nan)
        metrics['upnl_pct_gauge'].labels(market=MARKET_MAP[market]).set(math.nan)


def set_metrics(live_positions_df_with_curr_values):
    if not len(live_positions_df_with_curr_values):
        set_metrics_to_nan()
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
    print('[upnl] upnl_total!!', upnl_total)
    print('[upnl] upnl_total_per_market!!', upnl_total_per_market)

    # Set initial value for collateral metric so far
    collateral_total = live_positions_df['collateral_rem'].sum()
    collateral_total_per_market_df = live_positions_df.groupby(by='market')['collateral_rem'].sum().reset_index()
    collateral_total_per_market = dict(zip(collateral_total_per_market_df['market'], collateral_total_per_market_df['collateral_rem']))
    print('[upnl] collateral_total!!', collateral_total)
    print('[upnl] collateral_total_per_market', collateral_total_per_market)
    metrics['collateral_rem_gauge'].labels(market=ALL_MARKET_LABEL).set(collateral_total)
    for market_id in collateral_total_per_market:
        metrics['collateral_rem_gauge'].labels(market=MARKET_MAP[market_id]).set(collateral_total_per_market[market_id])
        metrics['upnl_pct_gauge'].labels(market=MARKET_MAP[market_id]).set(
            upnl_total_per_market[market_id] / collateral_total_per_market[market_id]
        )

    # live_positions_df['upnl_pct'] = live_positions_df['upnl'] / live_positions_df['collateral_rem']
    metrics['upnl_pct_gauge'].labels(market=ALL_MARKET_LABEL).set(upnl_total / collateral_total)


async def query_upnl():
    print('[upnl] Starting query...')

    print('[upnl] Connecting to arbitrum network...')
    network.connect('arbitrum-main')

    subgraph_client = SubgraphClient()
    set_metrics_to_nan()
    try:
        iteration = 1

        # Fetch all live positions so far from the subgraph
        print('[upnl] Getting live positions from subgraph...')
        live_positions = subgraph_client.get_all_live_positions()
        # write_to_json(live_positions, 'live_positions.json')
        print('[upnl] Getting live positions current value from blockchain...')
        live_positions_df_with_curr_values = await process_live_positions(live_positions)
        # write_to_json(live_positions_df_with_curr_values.to_dict(orient="records"), 'live_positions_with_current_values.json')
        print('[upnl] Calculating upnl metrics...')
        set_metrics(live_positions_df_with_curr_values)

        await asyncio.sleep(QUERY_INTERVAL)

        while True:
            try:
                print('===================================')
                print(f'[upnl] Running iteration #{iteration}...')
                timestamp_start = math.ceil(datetime.datetime.now().timestamp())
                print('[upnl] timestamp_start', datetime.datetime.utcfromtimestamp(timestamp_start).strftime('%Y-%m-%d %H:%M:%S'))

                # Fetch all live positions so far from the subgraph
                live_positions = subgraph_client.get_all_live_positions()
                live_positions_df_with_curr_values = await process_live_positions(live_positions)
                set_metrics(live_positions_df_with_curr_values)

                # Increment iteration
                iteration += 1

                # Wait for the next iteration
                await asyncio.sleep(QUERY_INTERVAL)
            except Exception as e:
                print(
                    f"[upnl] An error occurred on iteration "
                    f"{iteration} timestamp_start "
                    f"{datetime.datetime.utcfromtimestamp(timestamp_start).strftime('%Y-%m-%d %H:%M:%S')}:", e)
    except Exception as e:
        print(f"[upnl] An error occurred:", e)
        set_metrics_to_nan()


thread = threading.Thread(target=asyncio.run, args=(query_upnl(),))


if __name__ == '__main__':
    asyncio.run(query_upnl)
