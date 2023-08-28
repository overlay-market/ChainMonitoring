import datetime
import math
import threading
import time

import asyncio
import pandas as pd
from web3.exceptions import ContractLogicError
from prometheus_client import start_http_server
from brownie import Contract, web3, network
from dank_mids.brownie_patch import patch_contract
from dank_mids.helpers import setup_dank_w3_from_sync

from metrics import metrics
from subgraph.client import ResourceClient as SubgraphClient
from subgraph.constants import MAP_MARKET_ID_TO_NAME

# Start Prometheus server
start_http_server(8000)

network.connect('arbitrum-main')

# Dank mids setup
dank_w3 = setup_dank_w3_from_sync(web3)

# Contract addresses
STATE = '0xC3cB99652111e7828f38544E3e94c714D8F9a51a'

subgraph_client = SubgraphClient()


AVAILABLE_MARKETS = [
  '0x02e5938904014901c96f534b063ec732ea3b48d5',
  '0x1067b7df86552a53d816ce3fed50d6d01310b48f',
  '0x33659282d39e62b62060c3f9fb2230e97db15f1e',
  # '0x35e1d28ad9d8a80cff5bbf163a735c54eb6c1342', # 'AZUKI / WETH'
  '0x5114215415ee91ab5d973ba62fa9153ece1f6c5a',
  '0x7c65c99ba1edfc94c535b7aa2d72b0f7357a676b',
  '0x833ba1a942dc6d33bc3e6959637ae00e0cdcb20b',
  # '0x8c7dc90243fc7984583339da8df0a5d57ec491db', # 'PUDGIES / WETH'
  # '0x8c82c349e349ffd9403c3984cb1ad1b0f76f7d2e', # 'PUNKS / WETH'
  '0xa811698d855153cc7472d1fb356149a94bd618e7',
  # '0xb31d222c23104cbc2c04df77941f1f2c478133dd', # 'BAYC / WETH'
  '0xc28350047d006ed387b0f210d4ea3218137a8a38',
  # '0xccd645835ca0033f0c1106e7b24f288e59e867e8', # 'MILADY / WETH'
  # '0xce45c64911bd0a088daabd73ee1bc09ae98cd84b', # 'MAYC / WETH'
  # '0xF30C5cB6205f115799b275430Ea0874359476304'.toLowerCase(), # Total Crypto Market Cap
  # '0x8440E56C2675d9b8E04183dA3a3a744a4a16ED33'.toLowerCase(), # memecoins
]


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
        state = load_contract(STATE)
        values.extend(
            await asyncio.gather(*[get_pos_value(state, pos) for pos in curr_post_list])
        )
        await asyncio.sleep(5)

    values = [v/1e18 for v in values]
    live_positions_df['value'] = values
    live_positions_df['upnl'] = live_positions_df['value'] - live_positions_df['collateral_rem']
    live_positions_df['upnl_pct'] = live_positions_df['upnl'] / live_positions_df['collateral_rem']
    return live_positions_df


async def query_upnl():
    print('[upnl] Starting query...')
    iteration = 1
    query_interval = 10 # in seconds
    timestamp_window = 60 * 60 * 24 * 100 # in seconds
    timstamp_start = datetime.datetime.now().timestamp()

    # Fetch all live positions so far from the subgraph
    live_positions = subgraph_client.get_all_live_positions()

    # Calculate current value of each live position
    live_positions_df = await process_live_positions(live_positions)

    # Set initial value of upnl metric so far
    upnl_total = live_positions_df['upnl'].sum()
    upnl_total_per_market_df = live_positions_df.groupby(by='market')['upnl'].sum().reset_index()
    upnl_total_per_market = dict(zip(upnl_total_per_market_df['market'], upnl_total_per_market_df['upnl']))

    metrics['upnl_gauge'].labels(market='').set(upnl_total)
    for market_id in upnl_total_per_market:
        metrics['upnl_gauge'].labels(market=MAP_MARKET_ID_TO_NAME[market_id]).set(upnl_total_per_market[market_id])

    print('upnl_total!!', upnl_total)
    print('upnl_total_per_market!!', upnl_total_per_market)

    print('live_positions size!', len(live_positions))
    print('live_positions!', live_positions)

    timestamp_lower = math.ceil(timstamp_start - timestamp_window)
    timestamp_upper = math.ceil(timstamp_start)

    while True:
        print('===================================')
        print(f'[upnl] Running iteration #{iteration}...')
        print('[upnl] timestamp_lower', datetime.datetime.utcfromtimestamp(timestamp_lower).strftime('%Y-%m-%d %H:%M:%S'))
        print('[upnl] timestamp_upper', datetime.datetime.utcfromtimestamp(timestamp_upper).strftime('%Y-%m-%d %H:%M:%S'))

        # Fetch new live positions
        live_positions = subgraph_client.get_live_positions(timestamp_lower, timestamp_upper)

        # Calculate current value of each live position
        if len(live_positions) > 0:
            live_positions_df = await process_live_positions(live_positions)
            for position in live_positions_df.to_dict(orient='records'):
                metrics['upnl_gauge'].labels(market=MAP_MARKET_ID_TO_NAME[position['market']]).inc(position['upnl'])
                metrics['upnl_gauge'].labels(market='').inc(position['upnl'])

        # Increment iteration
        iteration += 1

        # Wait for the next iteration
        await asyncio.sleep(query_interval)

        if live_positions:
            # set timestamp range lower bound to timestamp of latest event
            timestamp_lower = int(live_positions[0]['timestamp'])
            if len(live_positions) > 1:
                timestamp_upper = int(live_positions[-1]['timestamp'])
            else:
                timestamp_upper += timestamp_window
        else:
            timestamp_lower = timestamp_upper
            timestamp_upper += timestamp_window


def query_mint():
    print('[ovl_token_minted] Starting query...')
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
    timstamp_start = datetime.datetime.now().timestamp() - (timestamp_window)
    timestamp_lower = math.ceil(timstamp_start - timestamp_window)
    timestamp_upper = math.ceil(timstamp_start)

    while True:
        print('===================================')
        print(f'[ovl_token_minted] Running iteration #{iteration}...')
        print('[ovl_token_minted] timestamp_lower', datetime.datetime.utcfromtimestamp(timestamp_lower).strftime('%Y-%m-%d %H:%M:%S'))
        print('[ovl_token_minted] timestamp_upper', datetime.datetime.utcfromtimestamp(timestamp_upper).strftime('%Y-%m-%d %H:%M:%S'))
        
        # Update ovl_token_minted metric
        positions = subgraph_client.get_positions(timestamp_lower, timestamp_upper)
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


if __name__ == '__main__':
    # asyncio.run(query_upnl())
    thread_mint = threading.Thread(target=query_mint)
    thread_upnl = threading.Thread(target=asyncio.run, args=(query_upnl(),))

    # Start the threads
    thread_mint.start()
    thread_upnl.start()


try:
    # Keep the main thread alive to let the threads run
    while True:
        pass
except KeyboardInterrupt:
    # Terminate the threads when the main thread is interrupted (Ctrl+C)
    thread_mint.join()
    thread_upnl.join()
