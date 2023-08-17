import datetime
import math
import time
import requests
from prometheus_client import Gauge, start_http_server


# Subgraph endpoint
SUBGRAPH_URL = 'https://api.studio.thegraph.com/proxy/49419/overlay-contracts/v0.0.8'

graphs = {}
graphs['mint_gauge'] = Gauge('ovl_token_minted', 'Number of OVL tokens minted', ['market'])

def query_positions(timestamp_lower, timestamp_upper, page_size=500):
    all_positions = []
    query = f'''
    {{
        positions(where: {{ createdAtTimestamp_gt: { timestamp_lower }, createdAtTimestamp_lt: { timestamp_upper } }}, first: {page_size}, orderBy: createdAtTimestamp, orderDirection: desc)  {{
            id
            createdAtTimestamp
            mint
            market {{
                id
            }}
        }}
    }}
    '''
    response = requests.post(SUBGRAPH_URL, json={'query': query})
    curr_positions = response.json().get('data', {}).get('positions', [])
    page_count = 0
    while len(curr_positions) > 0:
        page_count += 1
        print(f'Fetching page # {page_count}')
        all_positions.extend(curr_positions)
        query = f'''
        {{
            positions(where: {{ createdAtTimestamp_gt: {timestamp_lower}, createdAtTimestamp_lt: { int(curr_positions[-1]['createdAtTimestamp']) } }}, first: {page_size}, orderBy: createdAtTimestamp, orderDirection: desc)  {{
                id
                createdAtTimestamp
                mint
                market {{
                    id
                }}
            }}
        }}
        '''
        response = requests.post(SUBGRAPH_URL, json={'query': query})
        curr_positions = response.json().get('data', {}).get('positions', [])
    
    return all_positions


def get_mint_total(page_size = 1000):
    all_positions = []
    query = f'''
    {{
        positions(first: {page_size}, orderBy: createdAtTimestamp, orderDirection: desc)  {{
            id
            createdAtTimestamp
            mint
            market {{
                id
            }}
        }}
    }}
    '''
    response = requests.post(SUBGRAPH_URL, json={'query': query})
    curr_positions = response.json().get('data', {}).get('positions', [])
    # print('response', response.json())
    mint_total = 0
    while len(curr_positions) > 0:
        all_positions.extend(curr_positions)
        for position in curr_positions:
            mint_total += int(position['mint'])

        query = f'''
        {{
            positions(where: {{ createdAtTimestamp_lt: { int(curr_positions[-1]['createdAtTimestamp']) } }}, first: {page_size}, orderBy: createdAtTimestamp, orderDirection: desc)  {{
                id
                createdAtTimestamp
                mint
                market {{
                    id
                }}
            }}
        }}
        '''
        response = requests.post(SUBGRAPH_URL, json={'query': query})
        curr_positions = response.json().get('data', {}).get('positions', [])

    # print('all_positions', all_positions)
    print('mint_total', mint_total)
    return mint_total

# Start Prometheus server
start_http_server(8000)

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
        positions = query_positions(timestamp_lower, timestamp_upper)
        print('positions', len(positions))

        for position in positions:
            mint = int(position['mint']) / mint_divisor
            # graphs['mint_gauge'].inc(mint)
            graphs['mint_gauge'].labels(market=position['market']['id']).inc(mint)
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
    # timestamp = math.ceil(datetime.datetime.now().timestamp() - (3600 * 24 * 10))


    graphs['mint_gauge'].set(get_mint_total())

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
        positions = query_positions(timestamp_lower, timestamp_upper)
        print('positions', len(positions))

        for position in positions:
            mint = int(position['mint'])
            graphs['mint_gauge'].inc(mint)
        
        print('mint_gauge', graphs['mint_gauge']._value.get())
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

        # set timestamp range upper bound to timestamp now
        # timestamp_upper = math.ceil(datetime.datetime.now().timestamp())


if __name__ == '__main__':
    main()
    # main_realtime()
    # get_mint_total()

# main()
