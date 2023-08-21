import datetime
import math
import time
from prometheus_client import Gauge, start_http_server

from subgraph.client import ResourceClient as SubgraphClient
from subgraph.constants import MAP_MARKET_ID_TO_NAME

graphs = {}
graphs['mint_gauge'] = Gauge('ovl_token_minted', 'Number of OVL tokens minted', ['market'])

# Start Prometheus server
start_http_server(8000)

subgraph_client = SubgraphClient()

# Periodically query for mint events
def main():
    iteration = 1
    query_interval = 10 # in seconds
    timestamp_window = 3600 * 24 * 1 # 1 day
    mint_divisor = 10 ** 18

    timstamp_start = datetime.datetime.now().timestamp() - (3600 * 24 * 30 * 6) # last 6 months
    timestamp_upper = math.ceil(timstamp_start)
    timestamp_lower = math.ceil(timstamp_start - timestamp_window)

    while True:
        print('===================================')
        print(f'Running iteration #{iteration}...')
        print('timestamp_lower', datetime.datetime.utcfromtimestamp(timestamp_lower).strftime('%Y-%m-%d %H:%M:%S'), timestamp_lower)
        print('timestamp_upper', datetime.datetime.utcfromtimestamp(timestamp_upper).strftime('%Y-%m-%d %H:%M:%S'), timestamp_upper)
        positions = subgraph_client.get_positions(timestamp_lower, timestamp_upper)
        print('positions', len(positions))

        for position in positions:
            mint = int(position['mint']) / mint_divisor
            # graphs['mint_gauge'].inc(mint)
            graphs['mint_gauge'].labels(market=MAP_MARKET_ID_TO_NAME[position['market']['id']]).inc(mint)
            graphs['mint_gauge'].labels(market='').inc(mint)
        
        print('time now', datetime.datetime.now())
        # print('final mint_gauge', graphs['mint_gauge'].labels(market=position['market']['id'])._value.get())
        # Increment iteration
        iteration += 1

        # Wait for the next iteration
        time.sleep(query_interval)

        timestamp_lower = timestamp_upper
        timestamp_upper += timestamp_window
        if timestamp_upper > datetime.datetime.now().timestamp():
            timestamp_upper = datetime.datetime.now().timestamp()

        # set timestamp range upper bound to timestamp now
        # timestamp_upper = math.ceil(datetime.datetime.now().timestamp())

def main_realtime():
    iteration = 1
    query_interval = 10 # in seconds
    timestamp_window = 10 # 1 day
    mint_divisor = 10 ** 18

    mint_total, mint_total_per_market = subgraph_client.get_mint_total_per_market()
    graphs['mint_gauge'].labels(market='').set(mint_total / mint_divisor)
    for market_id in mint_total_per_market:
        graphs['mint_gauge'].labels(market=MAP_MARKET_ID_TO_NAME[market_id]).set(mint_total_per_market[market_id] / mint_divisor)

    # first ever timestamp is 1677258816
    # timstamp_start = datetime.datetime.now().timestamp() - (3600 * 24 * 30) # last 30 days
    timstamp_start = datetime.datetime.now().timestamp() - (timestamp_window) # last 30 days
    timestamp_upper = math.ceil(timstamp_start)
    timestamp_lower = math.ceil(timstamp_start - timestamp_window)

    while True:
        print('===================================')
        print(f'Running iteration #{iteration}...')
        print('timestamp_lower', datetime.datetime.utcfromtimestamp(timestamp_lower).strftime('%Y-%m-%d %H:%M:%S'))
        print('timestamp_upper', datetime.datetime.utcfromtimestamp(timestamp_upper).strftime('%Y-%m-%d %H:%M:%S'))
        positions = subgraph_client.get_positions(timestamp_lower, timestamp_upper)
        print('positions', len(positions))

        for position in positions:
            mint = int(position['mint']) / mint_divisor
            graphs['mint_gauge'].labels(market=MAP_MARKET_ID_TO_NAME[position['market']['id']]).inc(mint)
            graphs['mint_gauge'].labels(market='').inc(mint)
        
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
    # main()
    main_realtime()
