import datetime
import math
import threading

import asyncio
import pandas as pd
from web3.exceptions import ContractLogicError
from brownie import Contract, web3, network
from dank_mids.brownie_patch import patch_contract
from dank_mids.helpers import setup_dank_w3_from_sync

from constants import MAP_MARKET_ID_TO_NAME as MARKET_MAP, AVAILABLE_MARKETS, ALL_MARKET_LABEL
from prometheus_metrics import metrics
from subgraph.client import ResourceClient as SubgraphClient


network.connect('arbitrum-main')

# Dank mids setup
dank_w3 = setup_dank_w3_from_sync(web3)

# Contract addresses
STATE = '0xC3cB99652111e7828f38544E3e94c714D8F9a51a'

subgraph_client = SubgraphClient()


def load_contract(address):
    try:
        # Loads faster from memory
        contract = Contract(address)
    except ValueError:
        # Loads from explorer first time script is run
        contract = Contract.from_explorer(address)
    dank_contract = patch_contract(contract, dank_w3)
    return dank_contract


async def get_pos_value(state, pos):
    try:
        return await state.value.coroutine(pos[0], pos[1], pos[2])
    except ContractLogicError as e:
        print(e)
        return


async def process_live_positions(live_positions):
    live_positions_df = pd.DataFrame(live_positions)
    live_positions_df.drop(
        live_positions_df[~live_positions_df['market'].isin(AVAILABLE_MARKETS)].index,
        inplace = True
    )
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

    values = [v/1e18 for v in values]
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


async def query_upnl():
    print('[upnl] Starting query...')
    try:
        iteration = 1
        query_interval = 10 # in seconds
        timestamp_window = 10 # in seconds
        timestamp_start = datetime.datetime.now().timestamp()

        # Fetch all live positions so far from the subgraph
        live_positions = subgraph_client.get_all_live_positions()

        # Calculate current value of each live position
        live_positions_df = await process_live_positions(live_positions)

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

        timestamp_lower = math.ceil(timestamp_start)
        timestamp_upper = math.ceil(timestamp_start + timestamp_window)

        while True:
            try:
                print('===================================')
                print(f'[upnl] Running iteration #{iteration}...')
                print('[upnl] timestamp_lower', datetime.datetime.utcfromtimestamp(timestamp_lower).strftime('%Y-%m-%d %H:%M:%S'))
                print('[upnl] timestamp_upper', datetime.datetime.utcfromtimestamp(timestamp_upper).strftime('%Y-%m-%d %H:%M:%S'))

                # Fetch new live positions
                live_positions = subgraph_client.get_live_positions(timestamp_lower, timestamp_upper)
                print(f'[upnl] live_positions', len(live_positions))

                # Calculate current value of each live position
                if len(live_positions) > 0:
                    live_positions_df = await process_live_positions(live_positions)
                    for position in live_positions_df.to_dict(orient='records'):
                        market = MARKET_MAP[position['market']]
                        metrics['upnl_gauge'].labels(market=market).inc(position['upnl'])
                        metrics['upnl_gauge'].labels(market=ALL_MARKET_LABEL).inc(position['upnl'])

                        metrics['collateral_rem_gauge'].labels(market=market).inc(position['collateral_rem'])
                        metrics['collateral_rem_gauge'].labels(market=ALL_MARKET_LABEL).inc(position['collateral_rem'])
                        
                        # live_positions_df['upnl_pct'] = live_positions_df['upnl'] / live_positions_df['collateral_rem']
                        # ._value.get()
                        metrics['upnl_pct_gauge'].labels(market=market).set(
                            metrics['upnl_gauge'].labels(market=market)._value.get()
                            / metrics['collateral_rem_gauge'].labels(market=market)._value.get()
                        )
                        metrics['upnl_pct_gauge'].labels(market=ALL_MARKET_LABEL).set(
                            metrics['upnl_gauge'].labels(market=ALL_MARKET_LABEL)._value.get()
                            / metrics['collateral_rem_gauge'].labels(market=ALL_MARKET_LABEL)._value.get()
                        )

                # Increment iteration
                iteration += 1

                # Wait for the next iteration
                await asyncio.sleep(query_interval)

                if len(live_positions) > 0:
                    # set timestamp range lower bound to timestamp of latest event
                    timestamp_lower = int(live_positions[0]['timestamp'])
                    if len(live_positions) > 1:
                        timestamp_upper = int(live_positions[-1]['timestamp'])
                    else:
                        timestamp_upper += timestamp_window
                else:
                    timestamp_lower = timestamp_upper
                    timestamp_upper += datetime.datetime.now().timestamp()
            except Exception as e:
                print(
                    f"[upnl] An error occurred on iteration "
                    f"{iteration} timestamp_lower "
                    f"{datetime.datetime.utcfromtimestamp(timestamp_lower).strftime('%Y-%m-%d %H:%M:%S')}:", e)
    except Exception as e:
        print(f"[upnl] An error occurred:", e)
        set_metrics_to_nan()


thread = threading.Thread(target=asyncio.run, args=(query_upnl(),))


if __name__ == '__main__':
    asyncio.run(query_upnl)
