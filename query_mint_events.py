from flask import Response, Flask

import datetime
import math
import time
import requests
import prometheus_client
from prometheus_client import Gauge, start_http_server
import threading

app = Flask(__name__)

# Subgraph endpoint
# SUBGRAPH_URL = 'https://api.thegraph.com/subgraphs/name/bigboydiamonds/overlay-v1-subgraph'
SUBGRAPH_URL = 'https://api.studio.thegraph.com/proxy/49419/overlay-contracts/v0.0.7'

# Prometheus metric
# mint_gauge = Gauge('ovl_token_minted', 'Number of OVL tokens minted')

graphs = {}
graphs['mint_gauge'] = Gauge('ovl_token_minted', 'Number of OVL tokens minted')
# graphs['h'] = Histogram('python_request_duration_seconds', 'Histogram for the duration in seconds.', buckets=(1, 2, 5, 6, 10, _INF))


# Query for mint events
def query_positions(timestamp_lower, timestamp_upper, page_size = 100):
    query = f'''
    {{
        positions(where: {{ createdAtTimestamp_gt: { timestamp_lower }, createdAtTimestamp_lt: { timestamp_upper } }}, first: {page_size}, orderBy: createdAtTimestamp, orderDirection: desc)  {{
            id
            createdAtTimestamp
            mint
        }}
    }}
    '''
    # print('query', query)
    response = requests.post(SUBGRAPH_URL, json={'query': query})
    return response.json().get('data', {}).get('positions', [])

def get_mint_total(page_size = 1000):
    all_positions = []
    query = f'''
    {{
        positions(first: {page_size}, orderBy: createdAtTimestamp, orderDirection: desc)  {{
            id
            createdAtTimestamp
            mint
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
    query_interval = 5 # in seconds
    timestamp_window = 3600 * 24 # 1 day
    # timestamp = math.ceil(datetime.datetime.now().timestamp() - (3600 * 24 * 10))

    timstamp_start = datetime.datetime.now().timestamp() - (3600 * 24 * 30) # last 30 days
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
    # main()
    main_realtime()
    # get_mint_total()

# main()
