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
SUBGRAPH_URL = 'https://api.studio.thegraph.com/proxy/49419/overlay-contracts/v0.0.6'

# Prometheus metric
# mint_gauge = Gauge('ovl_token_minted', 'Number of OVL tokens minted')

graphs = {}
graphs['mint_gauge'] = Gauge('ovl_token_minted', 'Number of OVL tokens minted')
# graphs['h'] = Histogram('python_request_duration_seconds', 'Histogram for the duration in seconds.', buckets=(1, 2, 5, 6, 10, _INF))


# Query for mint events
def query_mint_events(timestamp):
    query = f'''
    {{
        positions(where: {{ createdAtTimestamp_gt: { timestamp } }}, first: 100, orderBy: createdAtTimestamp, orderDirection: desc)  {{
            id
            positionId
            createdAtTimestamp
            mint
            builds {{
                id
            }}
        }}
    }}
    '''
    print('query', query)
    response = requests.post(SUBGRAPH_URL, json={'query': query})
    return response.json().get('data', {}).get('positions', [])

# Start Prometheus server
start_http_server(8000)

# Periodically query for mint events
def main():
    last_minted_value = 0
    iteration = 1
    query_interval = 10 # in seconds
    timestamp = math.ceil(datetime.datetime.now().timestamp() - (3600 * 24 * 10))
    print('timestamp', timestamp)

    while True:
        print(f'Running iteration #{iteration}...')
        events = query_mint_events(timestamp)
        print('mint_events', events)
        for event in events:
            value = int(event['mint'])
            graphs['mint_gauge'].inc(value)
        # Wait for the next iteration
        time.sleep(query_interval)
        iteration += 1
        # timestamp = math.ceil(datetime.datetime.now().timestamp() - (1600 * 24))

if __name__ == '__main__':
    main()

main()

# @app.route("/metrics")
# def requests_count():
#     res = []
#     for k,v in graphs.items():
#         res.append(prometheus_client.generate_latest(v))
#     return Response(res, mimetype="text/plain")
