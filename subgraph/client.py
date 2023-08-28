import pandas as pd
import requests


def extract_live_positions(builds):
    builds_df = pd.json_normalize(builds)
    # Get market contract address and position id in separate columns
    builds_df[['market', 'position_id']] = builds_df['id'].str.split('-', expand=True)
    builds_df['position_id'] = builds_df['position_id'].apply(lambda x: int(x, 16))

    # Types and make readable
    builds_df['collateral'] = builds_df['collateral'].astype(float)/1e18
    builds_df['position.fractionUnwound'] = builds_df['position.fractionUnwound'].astype(float)/1e18
    builds_df['position.currentOi'] = builds_df['position.currentOi'].astype(float)/1e18

    # Adjust collateral based on position unwound
    builds_df['collateral_rem'] = builds_df['collateral'] * (1 - builds_df['position.fractionUnwound'])
    builds_df = builds_df[builds_df['position.currentOi'] > 0]
    # live_positions = builds_df[['market', 'owner.id', 'position_id', 'collateral_rem']].values.tolist()
    live_positions = builds_df.to_dict(orient='records')
    return live_positions


class ResourceClient:
    URL = 'https://api.studio.thegraph.com/proxy/49419/overlay-contracts/v0.0.8'
    PAGE_SIZE = 500

    def get_positions(self, timestamp_lower, timestamp_upper, page_size=PAGE_SIZE):
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
        response = requests.post(self.URL, json={'query': query})
        curr_positions = response.json().get('data', {}).get('positions', [])
        page_count = 0
        while len(curr_positions) > 0:
            page_count += 1
            print(f'Fetching positions page # {page_count}')
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
            response = requests.post(self.URL, json={'query': query})
            curr_positions = response.json().get('data', {}).get('positions', [])
        
        return all_positions

    def get_mint_total_per_market(self, page_size = PAGE_SIZE):
        all_positions = []
        mint_total_per_market = {}
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
        response = requests.post(self.URL, json={'query': query})
        curr_positions = response.json().get('data', {}).get('positions', [])
        # print('response', response.json())
        mint_total = 0
        while len(curr_positions) > 0:
            all_positions.extend(curr_positions)
            for position in curr_positions:
                if position['market']['id'] not in mint_total_per_market:
                    mint_total_per_market[position['market']['id']] = 0
                mint_total_per_market[position['market']['id']] += int(position['mint'])
                mint_total += int(position['mint'])

            query = f'''
            {{
                positions(
                    where: {{ createdAtTimestamp_lt: { int(curr_positions[-1]['createdAtTimestamp']) } }}, 
                    first: {page_size}, orderBy: createdAtTimestamp, orderDirection: desc)  {{
                    id
                    createdAtTimestamp
                    mint
                    market {{
                        id
                    }}
                }}
            }}
            '''
            response = requests.post(self.URL, json={'query': query})
            curr_positions = response.json().get('data', {}).get('positions', [])

        # print('all_positions', all_positions)
        print('mint_total', mint_total)
        print('mint_total_per_market', mint_total_per_market)
        return mint_total, mint_total_per_market

    def get_builds(self, timestamp_lower, timestamp_upper, page_size=PAGE_SIZE):
        builds = []
        query = f'''
        {{
            builds(where: {{ timestamp_gt: { timestamp_lower }, timestamp_lt: { timestamp_upper } }}, first: {page_size}, orderBy: timestamp, orderDirection: desc) {{
                timestamp
                collateral
                id
                position {{
                    currentOi
                    fractionUnwound
                }}
                owner {{
                    id
                }}
            }}
        }}
        '''
        response = requests.post(self.URL, json={'query': query})
        curr_builds = response.json().get('data', {}).get('builds', [])
        page_count = 0
        while len(curr_builds) > 0:
            page_count += 1
            print(f'Fetching builds page # {page_count}')
            builds.extend(curr_builds)
            query = f'''
            {{
                builds(where: {{ timestamp_gt: { timestamp_lower }, timestamp_lt: { timestamp_upper } }}, first: {page_size}, orderBy: timestamp, orderDirection: desc) {{
                    timestamp
                    collateral
                    id
                    position {{
                        currentOi
                        fractionUnwound
                    }}
                    owner {{
                        id
                    }}
                }}
            }}
            '''
            response = requests.post(self.URL, json={'query': query})
            curr_builds = response.json().get('data', {}).get('builds', [])

        return builds

    def get_all_builds(self, page_size=PAGE_SIZE):
        all_builds = []
        query = f'''
        {{
            builds(first: {page_size}, orderBy: timestamp, orderDirection: desc) {{
                timestamp
                collateral
                id
                position {{
                    currentOi
                    fractionUnwound
                }}
                owner {{
                    id
                }}
            }}
        }}
        '''
        response = requests.post(self.URL, json={'query': query})
        curr_builds = response.json().get('data', {}).get('builds', [])
        while len(curr_builds) > 0:
            all_builds.extend(curr_builds)
            query = f'''
            {{
                builds(where: {{ timestamp_lt: { int(curr_builds[-1]['timestamp']) } }}, first: {page_size}, orderBy: timestamp, orderDirection: desc) {{
                    timestamp
                    collateral
                    id
                    position {{
                        currentOi
                        fractionUnwound
                    }}
                    owner {{
                        id
                    }}
                }}
            }}
            '''
            response = requests.post(self.URL, json={'query': query})
            curr_builds = response.json().get('data', {}).get('builds', [])
        
        return all_builds

    def get_all_live_positions(self, page_size=PAGE_SIZE):
        live_positions = []
        query = f'''
        {{
            builds(first: {page_size}, orderBy: timestamp, orderDirection: desc) {{
                timestamp
                collateral
                id
                position {{
                    currentOi
                    fractionUnwound
                }}
                owner {{
                    id
                }}
            }}
        }}
        '''
        response = requests.post(self.URL, json={'query': query})
        curr_builds = response.json().get('data', {}).get('builds', [])
        curr_live_positions = extract_live_positions(curr_builds)

        while True:
            live_positions.extend(curr_live_positions)
            query = f'''
            {{
                builds(where: {{ timestamp_lt: { int(curr_builds[-1]['timestamp']) } }}, first: {page_size}, orderBy: timestamp, orderDirection: desc) {{
                    timestamp
                    collateral
                    id
                    position {{
                        currentOi
                        fractionUnwound
                    }}
                    owner {{
                        id
                    }}
                }}
            }}
            '''
            response = requests.post(self.URL, json={'query': query})
            curr_builds = response.json().get('data', {}).get('builds', [])

            if len(curr_builds) == 0:
                break

            curr_live_positions = extract_live_positions(curr_builds)
        return live_positions

    def get_live_positions(self, timestamp_lower, timestamp_upper, page_size=PAGE_SIZE):
        live_positions = []
        query = f'''
        {{
            builds(
                where: {{ timestamp_gt: { timestamp_lower }, timestamp_lt: { timestamp_upper } }},
                first: {page_size},
                orderBy: timestamp,
                orderDirection: desc
            ) {{
                timestamp
                collateral
                id
                position {{
                    currentOi
                    fractionUnwound
                }}
                owner {{
                    id
                }}
            }}
        }}
        '''
        response = requests.post(self.URL, json={'query': query})
        curr_builds = response.json().get('data', {}).get('builds', [])
        page_count = 0
        while len(curr_builds) > 0:
            page_count += 1
            print(f'Fetching builds page # {page_count}')
            curr_live_positions = extract_live_positions(curr_builds)
            live_positions.extend(curr_live_positions)
            query = f'''
            {{
                builds(
                    where: {{ timestamp_gt: { timestamp_lower }, timestamp_lt: { int(curr_builds[-1]['timestamp']) } }},
                    first: {page_size},
                    orderBy: timestamp,
                    orderDirection: desc
                ) {{
                    timestamp
                    collateral
                    id
                    position {{
                        currentOi
                        fractionUnwound
                    }}
                    owner {{
                        id
                    }}
                }}
            }}
            '''
            response = requests.post(self.URL, json={'query': query})
            curr_builds = response.json().get('data', {}).get('builds', [])

        return live_positions
